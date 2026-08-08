import React, { useState, useRef } from 'react';
import { useAppStore } from '../store/useAppStore';
import type { IngestionPhase } from '../store/useAppStore';
import {
  Menu,
  FileUp,
  CheckCircle,
  Loader2,
  CloudUpload,
  Cpu,
  AlertCircle,
  FileText,
  X,
} from 'lucide-react';

// ── Progress Step Component ──────────────────────────────────────────────────
const ProgressStep: React.FC<{
  icon: React.ReactNode;
  label: string;
  sublabel?: string;
  state: 'idle' | 'active' | 'done' | 'pending';
}> = ({ icon, label, sublabel, state }) => {
  const colors = {
    idle:    'text-[#64748b] border-[#e2e8f0] bg-[#f8fafc]',
    pending: 'text-[#64748b] border-[#e2e8f0] bg-[#f8fafc]',
    active:  'text-[#9a4021] border-[#fdba74] bg-[#fff7ed]',
    done:    'text-[#9a4021] border-[#fed7aa] bg-[#fff7ed]',
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
    uploadFiles,
    analyzeSession,
    ingestionPhase,
    isIngesting,
    documents,
    setCurrentView,
  } = useAppStore();

  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const totalPages = documents.reduce((sum, d) => sum + (d.pages || 1), 0);
  const totalChunks = documents.reduce((sum, d) => sum + (d.chunks_created || 0), 0);

  // Allow switching to chat if we have ingested documents
  const canGoToChat = documents.length > 0;

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
    idle:      'Select PDF files to begin',
    uploading: 'Uploading & chunking documents...',
    ready:     'Documents uploaded. Click "Analyze Documents" to index.',
    analyzing: 'Indexing chunks with embeddings & BM25...',
    done:      'Analysis complete. Ready to chat!',
  };

  const showDropzone = ingestionPhase === 'idle' || ingestionPhase === 'ready';
  const showUploadBtn = showDropzone && selectedFiles.length > 0;
  const showAnalyzeBtn = ingestionPhase === 'ready' && selectedFiles.length === 0;
  const showAnalyzingSpinner = ingestionPhase === 'analyzing';

  return (
    <div className="min-h-screen w-full bg-[#f8fafc] flex flex-col relative font-sans">
      {/* Top Header */}
      <header className="p-6 flex items-center justify-between">
        <button
          onClick={() => { if (canGoToChat) setCurrentView('chat'); }}
          className="p-2.5 rounded-full bg-[#f1f5f9] text-[#334155] hover:bg-[#e2e8f0] transition-colors disabled:opacity-40 cursor-pointer"
          disabled={!canGoToChat}
          title={canGoToChat ? 'Switch to Chat' : 'Complete analysis first'}
        >
          <Menu className="w-5 h-5" />
        </button>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex items-center justify-center p-4">
        <div className="w-full max-w-lg bg-white border border-[#e2e8f0] rounded-2xl p-8 shadow-sm flex flex-col items-center text-center gap-6">

          <div>
            <h1 className="text-3xl font-serif font-medium text-[#0f172a] mb-2">
              Add your documents
            </h1>
            <p className="text-sm text-[#64748b]">
              Upload PDFs. The agent only answers from what's inside these files.
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

          {/* File Dropzone — only shown in idle/ready phases */}
          {showDropzone && (
            <>
              <div
                onClick={() => fileInputRef.current?.click()}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                className="w-full bg-[#f8fafc] border-2 border-dashed border-[#e2e8f0] rounded-xl p-8 flex flex-col items-center justify-center cursor-pointer hover:bg-[#f1f5f9] transition-colors"
              >
                <div className="p-3 bg-[#ffedd5] rounded-lg mb-3">
                  <FileUp className="w-6 h-6 text-[#9a4021]" />
                </div>
                <p className="text-sm font-medium text-[#0f172a] mb-1">
                  {selectedFiles.length > 0
                    ? `${selectedFiles.length} file(s) selected`
                    : 'Drop PDF files here, or click to browse'}
                </p>
                <p className="text-xs text-[#64748b]">Max file size: 50MB per file</p>
              </div>

              {selectedFiles.length > 0 && (
                <div className="w-full space-y-2">
                  {selectedFiles.map((file, idx) => (
                    <div
                      key={idx}
                      className="flex items-center gap-2 bg-[#f1f5f9] rounded-lg px-3 py-2 text-sm"
                    >
                      <FileText className="w-4 h-4 text-[#9a4021] shrink-0" />
                      <span className="flex-1 truncate text-left text-[#0f172a]">{file.name}</span>
                      <span className="text-xs text-[#64748b] shrink-0">
                        {(file.size / 1024 / 1024).toFixed(1)} MB
                      </span>
                      <button
                        onClick={() => removeFile(idx)}
                        className="text-[#64748b] hover:text-[#9a4021] transition-colors cursor-pointer"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}

          {/* Ingested Stats Badge */}
          {documents.length > 0 && ingestionPhase !== 'idle' && (
            <div className="w-full bg-[#fff7ed] text-[#9a4021] border border-[#fed7aa] rounded-xl p-3.5 flex items-center justify-center gap-2 text-sm font-medium">
              <CheckCircle className="w-4 h-4 text-[#9a4021]" />
              <span>
                {documents.length} doc(s) · {totalPages} pages · {totalChunks} chunks
              </span>
            </div>
          )}

          {/* Progress Steps */}
          {ingestionPhase !== 'idle' && (
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
                    : ingestionPhase === 'done'
                    ? 'done'
                    : 'pending'
                }
              />
            </div>
          )}

          {/* Status Text */}
          {ingestionPhase !== 'idle' && phaseLabels[ingestionPhase] && (
            <p className="text-xs text-[#64748b] font-medium animate-pulse">
              {phaseLabels[ingestionPhase]}
            </p>
          )}

          {/* Error */}
          {errorMsg && (
            <div className="w-full flex items-start gap-2 bg-[#fff0f0] border border-[#ffc0c0] rounded-lg px-3 py-2 text-xs text-[#ba1a1a]">
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
                className="w-full bg-[#9a4021] hover:bg-[#b95837] text-white font-medium py-3.5 px-6 rounded-xl transition-colors flex items-center justify-center gap-2 shadow-sm disabled:opacity-50 cursor-pointer"
              >
                {isIngesting ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span>Uploading & Chunking...</span>
                  </>
                ) : (
                  <>
                    <CloudUpload className="w-5 h-5" />
                    <span>Upload Documents</span>
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
                className="w-full bg-[#9a4021] hover:bg-[#b95837] text-white font-medium py-3.5 px-6 rounded-xl transition-colors flex items-center justify-center gap-2 shadow-sm disabled:opacity-60 cursor-pointer"
              >
                <Cpu className="w-5 h-5" />
                <span>Start Analyzing</span>
              </button>
            )}

            {/* Analyzing spinner */}
            {showAnalyzingSpinner && (
              <button
                disabled
                className="w-full bg-[#9a4021] text-white font-medium py-3.5 px-6 rounded-xl flex items-center justify-center gap-2 opacity-70 cursor-not-allowed"
              >
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>Indexing with Bedrock AI...</span>
              </button>
            )}

            {/* Go to Chat */}
            {ingestionPhase === 'done' && (
              <button
                data-testid="go-to-chat-button"
                onClick={() => setCurrentView('chat')}
                className="w-full bg-[#9a4021] hover:bg-[#b95837] text-white font-medium py-3.5 px-6 rounded-xl transition-colors flex items-center justify-center gap-2 shadow-sm cursor-pointer"
              >
                <CheckCircle className="w-5 h-5" />
                <span>Open Chat</span>
              </button>
            )}

          </div>
        </div>
      </main>
    </div>
  );
};
