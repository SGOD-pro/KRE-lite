import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface Citation {
  chunk_id?: string;
  page?: number;
  section?: string;
  quote?: string;
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
}

interface AppState {
  sessionId: string | null;
  documents: IngestedDoc[];
  currentView: 'upload' | 'chat';
  messages: Message[];
  activeCitation: Citation | null;
  activePage: number;
  isIngesting: boolean;
  isQuerying: boolean;

  // Actions
  setSessionId: (id: string | null) => void;
  setDocuments: (docs: IngestedDoc[]) => void;
  setCurrentView: (view: 'upload' | 'chat') => void;
  setActiveCitation: (citation: Citation | null) => void;
  setActivePage: (page: number) => void;
  resetSession: () => void;
  
  ingestFiles: (files: File[]) => Promise<void>;
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
      isIngesting: false,
      isQuerying: false,

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
          isIngesting: false,
          isQuerying: false,
        });
      },

      ingestFiles: async (files: File[]) => {
        set({ isIngesting: true });
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
            throw new Error(errorData.detail || 'Failed to ingest documents.');
          }

          const data = await response.json();
          set({
            sessionId: data.session_id,
            documents: data.documents,
            currentView: 'chat',
            isIngesting: false,
          });
        } catch (error) {
          set({ isIngesting: false });
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
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              question: question,
              session_id: sessionId,
            }),
          });

          if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to generate answer.');
          }

          const data = await response.json();
          // data: { status: "answered" | "refused", answer: str, citations: [...] }

          const assistantMsgId = `assistant_${Date.now()}`;
          const assistantMessage: Message = {
            id: assistantMsgId,
            role: 'assistant',
            text: data.answer || data.message || "I don't have enough information in the provided documents to answer that.",
            status: data.status,
            citations: data.citations || [],
            timestamp: Date.now(),
          };

          set((state) => ({
            messages: [...state.messages, assistantMessage],
            isQuerying: false,
          }));

          // If answer has citations, set the first citation as active
          if (data.citations && data.citations.length > 0) {
            get().setActiveCitation(data.citations[0]);
          }

        } catch (error: any) {
          const errorMsgId = `assistant_err_${Date.now()}`;
          const errorMessage: Message = {
            id: errorMsgId,
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
      }),
    }
  )
);
