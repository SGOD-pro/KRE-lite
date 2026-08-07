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
    idle:    'text-[#89726b] border-[#dcc1b8] bg-[#f6f3f1]',
    pending: 'text-[#89726b] border-[#dcc1b8] bg-[#f6f3f1]',
    active:  'text-[#9a4021] border-[#9a4021] bg-[#fff5f0]',
    done:    'text-[#2a7d4f] border-[#2a7d4f] bg-[#f0faf4]',
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

  const totalPages = documents.reduce((sum, doc) => sum + doc.pages, 0);
  const totalChunks = documents.reduce((sum, doc) => sum + doc.chunks_created, 0);
  const canGoToChat = ingestionPhase === 'done' && documents.length > 0;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const filesArray = Array.from(e.target.files).filter((f) =>
        f.name.toLowerCase().endsWith('.pdf')
      );
      if (filesArray.length === 0) {
        setErrorMsg('Only PDF files are supported.');
        return;
      }
      setSelectedFiles(filesArray);
      setErrorMsg(null);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const filesArray = Array.from(e.dataTransfer.files).filter((f) =>
      f.name.toLowerCase().endsWith('.pdf')
    );
    if (filesArray.length === 0) {
      setErrorMsg('Only PDF files are supported.');
      return;
    }
    setSelectedFiles(filesArray);
    setErrorMsg(null);
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
  };

  const removeFile = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0) {
      setErrorMsg('Please select at least one PDF file.');
      return;
    }
    setErrorMsg(null);
    try {
      await uploadFiles(selectedFiles);
      setSelectedFiles([]);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Upload failed.');
    }
  };

  const handleAnalyze = async () => {
    setErrorMsg(null);
    try {
      await analyzeSession();
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Analysis failed.');
    }
  };

  const phaseLabels: Record<IngestionPhase, string> = {
    idle:      '',
    uploading: 'Uploading to S3 & chunking document...',
    ready:     'Upload complete! Click "Start Analyzing" to index.',
    analyzing: 'Embedding with Bedrock Titan (may take a few minutes)...',
    done:      'Analysis complete. Ready to chat!',
  };

  const showDropzone = ingestionPhase === 'idle' || ingestionPhase === 'ready';
  const showUploadBtn = showDropzone && selectedFiles.length > 0;
  const showAnalyzeBtn = ingestionPhase === 'ready' && selectedFiles.length === 0;
  const showAnalyzingSpinner = ingestionPhase === 'analyzing';

  return (
    <div className="min-h-screen w-full bg-[#fcf9f6] flex flex-col relative font-sans">
      {/* Top Header */}
      <header className="p-6 flex items-center justify-between">
        <button
          onClick={() => { if (canGoToChat) setCurrentView('chat'); }}
          className="p-2.5 rounded-full bg-[#f0edeb] text-[#56423c] hover:bg-[#e5e2d8] transition-colors disabled:opacity-40"
          disabled={!canGoToChat}
          title={canGoToChat ? 'Switch to Chat' : 'Complete analysis first'}
        >
          <Menu className="w-5 h-5" />
        </button>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex items-center justify-center p-4">
        <div className="w-full max-w-lg bg-[#fcf9f6] border border-[#dcc1b8] rounded-2xl p-8 shadow-sm flex flex-col items-center text-center gap-6">

          <div>
            <h1 className="text-3xl font-serif font-medium text-[#1c1c1a] mb-2">
              Add your documents
            </h1>
            <p className="text-sm text-[#56423c]">
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
                className="w-full bg-[#f0edeb] border-2 border-dashed border-[#dcc1b8] rounded-xl p-8 flex flex-col items-center justify-center cursor-pointer hover:bg-[#e5e2d8] transition-colors"
              >
                <div className="p-3 bg-[#e5e2d8] rounded-lg mb-3">
                  <FileUp className="w-6 h-6 text-[#9a4021]" />
                </div>
                <p className="text-sm font-medium text-[#1c1c1a] mb-1">
                  {selectedFiles.length > 0
                    ? `${selectedFiles.length} file(s) selected`
                    : 'Drop PDF files here, or click to browse'}
                </p>
                <p className="text-xs text-[#89726b]">Max file size: 50MB per file</p>
              </div>

              {selectedFiles.length > 0 && (
                <div className="w-full space-y-2">
                  {selectedFiles.map((file, idx) => (
                    <div
                      key={idx}
                      className="flex items-center gap-2 bg-[#f0edeb] rounded-lg px-3 py-2 text-sm"
                    >
                      <FileText className="w-4 h-4 text-[#9a4021] shrink-0" />
                      <span className="flex-1 truncate text-left text-[#1c1c1a]">{file.name}</span>
                      <span className="text-xs text-[#89726b] shrink-0">
                        {(file.size / 1024 / 1024).toFixed(1)} MB
                      </span>
                      <button
                        onClick={() => removeFile(idx)}
                        className="text-[#89726b] hover:text-[#9a4021] transition-colors"
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
            <div className="w-full bg-[#e5e2d8] text-[#1c1c1a] border border-[#dcc1b8] rounded-xl p-3.5 flex items-center justify-center gap-2 text-sm font-medium">
              <CheckCircle className="w-4 h-4 text-[#2a7d4f]" />
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
            <p className="text-xs text-[#56423c] font-medium animate-pulse">
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
                className="w-full bg-[#9a4021] hover:bg-[#b95837] text-white font-medium py-3.5 px-6 rounded-xl transition-colors flex items-center justify-center gap-2 shadow-sm disabled:opacity-50"
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
                className="w-full bg-[#9a4021] hover:bg-[#b95837] text-white font-medium py-3.5 px-6 rounded-xl transition-colors flex items-center justify-center gap-2 shadow-sm disabled:opacity-60"
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
                className="w-full bg-[#2a7d4f] hover:bg-[#3a9d6f] text-white font-medium py-3.5 px-6 rounded-xl transition-colors flex items-center justify-center gap-2 shadow-sm"
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
