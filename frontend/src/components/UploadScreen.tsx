import React, { useState, useRef } from 'react';
import { useAppStore } from '../store/useAppStore';
import type { IngestionPhase } from '../store/useAppStore';
import {
  FileUp,
  CheckCircle,
  Loader2,
  CloudUpload,
  Cpu,
  AlertCircle,
  FileText,
  X,
  Plus,
  ArrowLeft,
} from 'lucide-react';
import { ScrollArea } from './ui/scroll-area';

// ── Progress Step Component ──────────────────────────────────────────────────
const ProgressStep: React.FC<{
  icon: React.ReactNode;
  label: string;
  sublabel?: string;
  state: 'idle' | 'active' | 'done' | 'pending';
}> = ({ icon, label, sublabel, state }) => {
  const colors = {
    idle: 'text-[#64748b] border-[#e2e8f0] bg-[#f8fafc] dark:text-[#94a3b8] dark:border-[#1e293b] dark:bg-[#1e293b]',
    pending: 'text-[#64748b] border-[#e2e8f0] bg-[#f8fafc] dark:text-[#94a3b8] dark:border-[#1e293b] dark:bg-[#1e293b]',
    active: 'text-[#9a4021] border-[#fdba74] bg-[#fff7ed] dark:text-[#fb923c] dark:border-[#431407] dark:bg-[#431407]/30',
    done: 'text-[#9a4021] border-[#fed7aa] bg-[#fff7ed] dark:text-[#fb923c] dark:border-[#431407] dark:bg-[#431407]/30',
  };
  return (
    <div className={`flex items-center gap-3 p-3 rounded-xl border transition-all ${colors[state]}`}>
      <div className="shrink-0">
        {state === 'active' ? (
          <Loader2 className="w-5 h-5 animate-spin" />
        ) : state === 'done' ? (
          <CheckCircle className="w-5 h-5" />
        ) : (
          icon
        )}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold truncate">{label}</p>
        {sublabel && <p className="text-xs opacity-70 truncate">{sublabel}</p>}
      </div>
    </div>
  );
};

// ── Main Component ────────────────────────────────────────────────────────────
export const UploadScreen: React.FC = () => {
  const {
    sessionId,
    uploadFiles,
    analyzeSession,
    ingestionPhase,
    isIngesting,
    documents,
    setCurrentView,
    setIngestionPhase,
  } = useAppStore();

  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const totalPages = documents.reduce((sum, d) => sum + (d.pages || 1), 0);
  const totalChunks = documents.reduce((sum, d) => sum + (d.chunks_created || 0), 0);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFiles(Array.from(e.target.files));
      setErrorMsg(null);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const pdfs = Array.from(e.dataTransfer.files).filter(
        (f) => f.type === 'application/pdf' || f.name.endsWith('.pdf')
      );
      if (pdfs.length > 0) {
        setSelectedFiles(pdfs);
        setErrorMsg(null);
      } else {
        setErrorMsg('Please upload PDF files only.');
      }
    }
  };

  const handleDragOver = (e: React.DragEvent) => e.preventDefault();

  const removeFile = (idx: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0) return;
    setErrorMsg(null);
    try {
      await uploadFiles(selectedFiles);
      setSelectedFiles([]); // Clear files so UI transitions to "Start Analyzing"
    } catch (err: any) {
      setErrorMsg(err.message || 'Upload failed. Please try again.');
    }
  };

  const handleAnalyze = async () => {
    setErrorMsg(null);
    try {
      await analyzeSession();
    } catch (err: any) {
      setErrorMsg(err.message || 'Analysis failed. Please try again.');
    }
  };

  const phaseLabels: Record<IngestionPhase, string> = {
    idle: 'Select PDF files to begin',
    uploading: 'Uploading & chunking documents...',
    ready: 'Documents uploaded. Click "Analyze Documents" to index.',
    analyzing: 'Indexing chunks with embeddings & BM25...',
    done: 'Analysis complete. Ready to chat!',
  };

  const showDropzone = ingestionPhase === 'idle' || ingestionPhase === 'ready';
  const showUploadBtn = showDropzone && selectedFiles.length > 0;
  const showAnalyzeBtn = ingestionPhase === 'ready' && selectedFiles.length === 0;
  const showAnalyzingSpinner = ingestionPhase === 'analyzing';

  // Whether we are in "append more docs" mode (already have a session, revisiting upload)
  const isAppendMode = documents.length > 0 && (ingestionPhase === 'done' || ingestionPhase === 'ready');

  return (
    <ScrollArea>
      <div className="min-h-screen w-full bg-[#f8fafc] dark:bg-[#0f172a] flex flex-col relative font-sans">
        {/* Top Header */}
        <header className="p-4 pl-14 flex items-center justify-between z-10 relative">
          {sessionId ? (
            <button
              onClick={() => setCurrentView('chat')}
              className="flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to Chat
            </button>
          ) : (
            <div />
          )}
          <h1 className="text-[26dvw] fixed top-4 left-1/2 -translate-x-1/2 font-bold tracking-widest bg-gradient-to-b from-primary from-10% to-transparent bg-clip-text text-transparent pointer-events-none select-none opacity-40 z-0 leading-none">KRE</h1>
        </header>

        {/* Main Content */}
        <main className="flex-1 flex items-center justify-center p-4">
          <div className="w-full max-w-lg bg-white/40 dark:bg-[#1e293b]/40 border border-[#e2e8f0] dark:border-[#334155] rounded-2xl p-8 shadow-sm flex flex-col items-center text-center gap-6 backdrop-blur-xs">

            {/* ── Gradient Title (Grok-style) ─────────────────────────────────── */}
            <div className="relative w-full flex flex-col items-center">
              {/* Background gradient blob */}

              <h1 className="relative text-3xl font-serif font-medium mb-2 bg-gradient-to-br from-[#9a4021] via-[#f97316] to-[#fdba74] bg-clip-text text-transparent">
                {isAppendMode ? 'Add more documents' : 'Add your documents'}
              </h1>
              {/* Bottom fade overlay on the gradient blob */}
              <div
                aria-hidden="true"
                className="absolute bottom-0 inset-x-0 h-8 pointer-events-none bg-gradient-to-b from-transparent to-card"
              />
              <p className="relative text-sm text-[#64748b] dark:text-[#94a3b8]">
                {isAppendMode
                  ? 'Upload additional PDFs to the same session — chat history is preserved.'
                  : 'Upload PDFs. The agent only answers from what\'s inside these files.'}
              </p>
            </div>

            {/* Always-present hidden file input — MUST stay here for Playwright setInputFiles */}
            <input
              data-testid="file-input"
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              accept=".pdf"
              multiple
              className="hidden"
            />

            {/* ── Already-ingested documents list ──────────────────────────────── */}
            {documents.length > 0 && (
              <div className="w-full space-y-1.5">
                <p className="text-xs font-semibold text-[#64748b] dark:text-[#94a3b8] text-left mb-1 uppercase tracking-wide">
                  Ingested documents
                </p>
                {documents.map((doc, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-2 bg-[#f1f5f9] dark:bg-[#0f172a] rounded-lg px-3 py-2 text-sm border border-[#e2e8f0] dark:border-[#1e293b]"
                  >
                    <CheckCircle className="w-4 h-4 text-[#9a4021] dark:text-[#f97316] shrink-0" />
                    <span className="flex-1 truncate text-left text-[#0f172a] dark:text-[#f1f5f9] font-medium">
                      {doc.filename}
                    </span>
                    <span className="text-xs text-[#64748b] dark:text-[#94a3b8] shrink-0">
                      {doc.pages}p · {doc.chunks_created} chunks
                    </span>
                  </div>
                ))}
              </div>
            )}

            {/* File Dropzone — only shown in idle/ready phases */}
            {showDropzone && (
              <>
                <div
                  onClick={() => fileInputRef.current?.click()}
                  onDrop={handleDrop}
                  onDragOver={handleDragOver}
                  className="w-full bg-[#f8fafc] dark:bg-[#0f172a] border-2 border-dashed border-[#e2e8f0] dark:border-[#334155] rounded-xl p-8 flex flex-col items-center justify-center cursor-pointer hover:bg-[#f1f5f9] dark:hover:bg-[#1e293b] transition-colors"
                >
                  <div className="p-3 bg-[#ffedd5] dark:bg-[#431407]/50 rounded-lg mb-3">
                    <FileUp className="w-6 h-6 text-[#9a4021] dark:text-[#f97316]" />
                  </div>
                  <p className="text-sm font-medium text-[#0f172a] dark:text-[#f1f5f9] mb-1">
                    {selectedFiles.length > 0
                      ? `${selectedFiles.length} file(s) selected`
                      : isAppendMode
                        ? 'Drop more PDF files here, or click to browse'
                        : 'Drop PDF files here, or click to browse'}
                  </p>
                  <p className="text-xs text-[#64748b] dark:text-[#94a3b8]">Max file size: 10 MB per file</p>
                </div>

                {selectedFiles.length > 0 && (
                  <div className="w-full space-y-2">
                    {selectedFiles.map((file, idx) => (
                      <div
                        key={idx}
                        className="flex items-center gap-2 bg-[#f1f5f9] dark:bg-[#0f172a] rounded-lg px-3 py-2 text-sm"
                      >
                        <FileText className="w-4 h-4 text-[#9a4021] dark:text-[#f97316] shrink-0" />
                        <span className="flex-1 truncate text-left text-[#0f172a] dark:text-[#f1f5f9]">{file.name}</span>
                        <span className="text-xs text-[#64748b] dark:text-[#94a3b8] shrink-0">
                          {(file.size / 1024 / 1024).toFixed(1)} MB
                        </span>
                        <button
                          onClick={() => removeFile(idx)}
                          className="text-[#64748b] hover:text-[#9a4021] dark:hover:text-[#f97316] transition-colors cursor-pointer"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}

            {/* Ingested Stats Badge (only when no documents list shown) */}
            {documents.length > 0 && ingestionPhase !== 'idle' && ingestionPhase !== 'done' && (
              <div className="w-full bg-[#fff7ed] dark:bg-[#431407]/30 text-[#9a4021] dark:text-[#fb923c] border border-[#fed7aa] dark:border-[#431407] rounded-xl p-3.5 flex items-center justify-center gap-2 text-sm font-medium">
                <CheckCircle className="w-4 h-4" />
                <span>
                  {documents.length} doc(s) · {totalPages} pages · {totalChunks} chunks
                </span>
              </div>
            )}

            {/* Progress Steps */}
            {ingestionPhase !== 'idle' && ingestionPhase !== 'done' && (
              <div className="w-full space-y-2">
                <ProgressStep
                  icon={<CloudUpload className="w-5 h-5" />}
                  label="Upload & Chunk"
                  sublabel="S3 upload + text extraction"
                  state={
                    ingestionPhase === 'uploading'
                      ? 'active'
                      : 'done'
                  }
                />
                <ProgressStep
                  icon={<Cpu className="w-5 h-5" />}
                  label="Semantic Indexing"
                  sublabel="Bedrock Titan embeddings → Qdrant"
                  state={
                    ingestionPhase === 'analyzing'
                      ? 'active'
                      : 'pending'
                  }
                />
              </div>
            )}

            {/* Status Text */}
            {ingestionPhase !== 'idle' && phaseLabels[ingestionPhase] && (
              <p className="text-xs text-[#64748b] dark:text-[#94a3b8] font-medium animate-pulse">
                {phaseLabels[ingestionPhase]}
              </p>
            )}

            {/* Error */}
            {errorMsg && (
              <div className="w-full flex items-start gap-2 bg-[#fff0f0] dark:bg-[#450a0a]/50 border border-[#ffc0c0] dark:border-[#7f1d1d] rounded-lg px-3 py-2 text-xs text-[#ba1a1a] dark:text-[#f87171]">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                <span>{errorMsg}</span>
              </div>
            )}

            {/* Action Buttons */}
            <div className="w-full space-y-3">

              {/* Phase 1: Upload button */}
              {showUploadBtn && (
                <button
                  data-testid="upload-button"
                  onClick={handleUpload}
                  disabled={isIngesting}
                  className="w-full bg-[#9a4021] hover:bg-[#b95837] dark:bg-[#f97316] dark:hover:bg-[#fb923c] text-white font-medium py-3.5 px-6 rounded-xl transition-colors flex items-center justify-center gap-2 shadow-sm disabled:opacity-50 cursor-pointer"
                >
                  {isIngesting ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      <span>Uploading & Chunking...</span>
                    </>
                  ) : (
                    <>
                      <CloudUpload className="w-5 h-5" />
                      <span>{isAppendMode ? 'Upload Additional Documents' : 'Upload Documents'}</span>
                    </>
                  )}
                </button>
              )}

              {/* Phase 2: Start Analyzing button */}
              {showAnalyzeBtn && (
                <button
                  data-testid="ingest-button"
                  onClick={handleAnalyze}
                  disabled={isIngesting}
                  className="w-full bg-[#9a4021] hover:bg-[#b95837] dark:bg-[#f97316] dark:hover:bg-[#fb923c] text-white font-medium py-3.5 px-6 rounded-xl transition-colors flex items-center justify-center gap-2 shadow-sm disabled:opacity-60 cursor-pointer"
                >
                  <Cpu className="w-5 h-5" />
                  <span>Start Analyzing</span>
                </button>
              )}

              {/* Analyzing spinner */}
              {showAnalyzingSpinner && (
                <button
                  disabled
                  className="w-full bg-[#9a4021] dark:bg-[#f97316] text-white font-medium py-3.5 px-6 rounded-xl flex items-center justify-center gap-2 opacity-70 cursor-not-allowed"
                >
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>Indexing with Bedrock AI...</span>
                </button>
              )}

              {/* Go to Chat / Add More docs (when done) */}
              {ingestionPhase === 'done' && (
                <>
                  <button
                    data-testid="go-to-chat-button"
                    onClick={() => setCurrentView('chat')}
                    className="w-full bg-[#9a4021] hover:bg-[#b95837] dark:bg-[#f97316] dark:hover:bg-[#fb923c] text-white font-medium py-3.5 px-6 rounded-xl transition-colors flex items-center justify-center gap-2 shadow-sm cursor-pointer"
                  >
                    <CheckCircle className="w-5 h-5" />
                    <span>Open Chat</span>
                  </button>

                  {/* Add more PDFs — reuses same session_id via uploadFiles action */}
                  <button
                    data-testid="add-document-button"
                    onClick={() => {
                      // Reset phase to 'ready' — dropzone reappears without clearing session
                      setIngestionPhase('ready');
                      setSelectedFiles([]);
                    }}
                    className="w-full flex items-center justify-center gap-2 border border-[#e2e8f0] dark:border-[#334155] rounded-xl py-3 px-6 text-sm font-medium text-[#64748b] dark:text-[#94a3b8] hover:bg-[#f1f5f9] dark:hover:bg-[#1e293b] transition-colors cursor-pointer"
                  >
                    <Plus className="w-4 h-4" />
                    <span>Add more PDFs</span>
                  </button>
                </>
              )}

            </div>
          </div>
        </main>
      </div>
    </ScrollArea>
  );
};
