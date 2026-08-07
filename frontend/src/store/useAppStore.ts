import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface Citation {
  chunk_id?: string;
  page?: number;
  section?: string;
  quote?: string;
  source_file?: string;
  text?: string; // actual chunk text for SourceViewer
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  status?: 'answered' | 'refused' | 'error';
  citations?: Citation[];
  timestamp: number;
}

export interface IngestedDoc {
  filename: string;
  chunks_created: number;
  pages: number;
  s3_key?: string;
}

export type IngestionPhase =
  | 'idle'
  | 'uploading'   // POST /ingest running (upload + chunk)
  | 'ready'       // /ingest complete, waiting for user to click "Start Analyzing"
  | 'analyzing'   // POST /analyze running (Bedrock embeddings)
  | 'done';       // /analyze complete, chat unlocked

interface AppState {
  sessionId: string | null;
  documents: IngestedDoc[];
  currentView: 'upload' | 'chat';
  messages: Message[];
  activeCitation: Citation | null;
  activePage: number;
  ingestionPhase: IngestionPhase;
  isQuerying: boolean;

  // Derived helpers
  isIngesting: boolean; // true during uploading or analyzing

  // Actions
  setSessionId: (id: string | null) => void;
  setDocuments: (docs: IngestedDoc[]) => void;
  setCurrentView: (view: 'upload' | 'chat') => void;
  setActiveCitation: (citation: Citation | null) => void;
  setActivePage: (page: number) => void;
  resetSession: () => void;

  uploadFiles: (files: File[]) => Promise<void>;
  analyzeSession: () => Promise<void>;
  sendQuery: (question: string) => Promise<void>;
}

const API_BASE_URL = 'http://localhost:8000';

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      sessionId: null,
      documents: [],
      currentView: 'upload',
      messages: [],
      activeCitation: null,
      activePage: 1,
      ingestionPhase: 'idle',
      isQuerying: false,
      isIngesting: false,

      setSessionId: (id) => set({ sessionId: id }),
      setDocuments: (docs) => set({ documents: docs }),
      setCurrentView: (view) => set({ currentView: view }),
      setActiveCitation: (citation) => {
        set({ activeCitation: citation });
        if (citation?.page) {
          set({ activePage: citation.page });
        }
      },
      setActivePage: (page) => set({ activePage: page }),

      resetSession: () => {
        set({
          sessionId: null,
          documents: [],
          currentView: 'upload',
          messages: [],
          activeCitation: null,
          activePage: 1,
          ingestionPhase: 'idle',
          isQuerying: false,
          isIngesting: false,
        });
      },

      /** Phase 1: upload files to S3 + chunk to MongoDB */
      uploadFiles: async (files: File[]) => {
        set({ ingestionPhase: 'uploading', isIngesting: true });
        try {
          const formData = new FormData();
          files.forEach((file) => formData.append('files', file));

          const { sessionId } = get();
          if (sessionId) {
            formData.append('session_id', sessionId);
          }

          const response = await fetch(`${API_BASE_URL}/ingest`, {
            method: 'POST',
            body: formData,
          });

          if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to upload documents.');
          }

          const data = await response.json();
          // data: { status: "uploaded", session_id, documents: [...] }
          set({
            sessionId: data.session_id,
            documents: data.documents,
            ingestionPhase: 'ready',
            isIngesting: false,
          });
        } catch (error) {
          set({ ingestionPhase: 'idle', isIngesting: false });
          throw error;
        }
      },

      /** Phase 2: trigger Bedrock embeddings for the session */
      analyzeSession: async () => {
        const { sessionId } = get();
        if (!sessionId) return;

        set({ ingestionPhase: 'analyzing', isIngesting: true });
        try {
          const response = await fetch(`${API_BASE_URL}/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId }),
          });

          if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to analyze documents.');
          }

          set({
            ingestionPhase: 'done',
            isIngesting: false,
            currentView: 'chat',
          });
        } catch (error) {
          set({ ingestionPhase: 'ready', isIngesting: false }); // revert to ready so user can retry
          throw error;
        }
      },

      sendQuery: async (question: string) => {
        if (!question.trim()) return;

        const userMsgId = `user_${Date.now()}`;
        const userMessage: Message = {
          id: userMsgId,
          role: 'user',
          text: question,
          timestamp: Date.now(),
        };

        set((state) => ({
          messages: [...state.messages, userMessage],
          isQuerying: true,
        }));

        try {
          const { sessionId } = get();
          const response = await fetch(`${API_BASE_URL}/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question, session_id: sessionId }),
          });

          if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to generate answer.');
          }

          const data = await response.json();
          // data: { status, answer, citations: [{chunk_id, page, section, quote, text, source_file}] }

          const assistantMessage: Message = {
            id: `assistant_${Date.now()}`,
            role: 'assistant',
            text: data.answer || "I don't have enough information in the provided documents to answer that.",
            status: data.status,
            citations: data.citations || [],
            timestamp: Date.now(),
          };

          set((state) => ({
            messages: [...state.messages, assistantMessage],
            isQuerying: false,
          }));

          // Auto-select first citation so Source Viewer shows real text immediately
          if (data.citations && data.citations.length > 0) {
            get().setActiveCitation(data.citations[0]);
          }
        } catch (error: any) {
          const errorMessage: Message = {
            id: `assistant_err_${Date.now()}`,
            role: 'assistant',
            text: `Error: ${error.message || 'Something went wrong.'}`,
            status: 'error',
            timestamp: Date.now(),
          };
          set((state) => ({
            messages: [...state.messages, errorMessage],
            isQuerying: false,
          }));
        }
      },
    }),
    {
      name: 'cited-or-silent-store',
      partialize: (state) => ({
        sessionId: state.sessionId,
        documents: state.documents,
        currentView: state.currentView,
        messages: state.messages,
        ingestionPhase: state.ingestionPhase,
      }),
    }
  )
);
