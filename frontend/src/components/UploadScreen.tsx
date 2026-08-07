import React, { useState, useRef } from 'react';
import { useAppStore } from '../store/useAppStore';
import { Menu, FileUp, CheckCircle, Loader2 } from 'lucide-react';

export const UploadScreen: React.FC = () => {
  const { ingestFiles, isIngesting, documents, setCurrentView } = useAppStore();
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const filesArray = Array.from(e.target.files);
      setSelectedFiles(filesArray);
      setErrorMsg(null);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const filesArray = Array.from(e.dataTransfer.files).filter(f => f.name.endsWith('.pdf'));
      if (filesArray.length === 0) {
        setErrorMsg('Only PDF files are supported.');
        return;
      }
      setSelectedFiles(filesArray);
      setErrorMsg(null);
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
  };

  const handleSubmit = async () => {
    if (selectedFiles.length === 0 && documents.length === 0) {
      setErrorMsg('Please select at least one PDF file to upload.');
      return;
    }

    if (selectedFiles.length === 0 && documents.length > 0) {
      // User already has ingested documents in this session, proceed to chat
      setCurrentView('chat');
      return;
    }

    try {
      await ingestFiles(selectedFiles);
    } catch (err: any) {
      setErrorMsg(err.message || 'Error ingesting documents.');
    }
  };

  const totalPages = documents.reduce((sum, doc) => sum + doc.pages, 0);
  const totalChunks = documents.reduce((sum, doc) => sum + doc.chunks_created, 0);

  return (
    <div className="min-h-screen w-full bg-[#fcf9f6] flex flex-col relative font-sans">
      {/* Top Header */}
      <header className="p-6 flex items-center justify-between">
        <button 
          onClick={() => {
            if (documents.length > 0) setCurrentView('chat');
          }}
          className="p-2.5 rounded-full bg-[#f0edeb] text-[#56423c] hover:bg-[#e5e2d8] transition-colors"
          title={documents.length > 0 ? "Switch to Chat" : "Menu"}
        >
          <Menu className="w-5 h-5" />
        </button>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 flex items-center justify-center p-4">
        <div className="w-full max-w-lg bg-[#fcf9f6] border border-[#dcc1b8] rounded-2xl p-8 shadow-sm flex flex-col items-center text-center">
          
          <h1 className="text-3xl font-serif font-medium text-[#1c1c1a] mb-2">
            Add your documents
          </h1>
          <p className="text-sm text-[#56423c] mb-6">
            Upload PDFs. The agent will only answer from what's inside these files.
          </p>

          {/* Dropzone */}
          <div 
            onClick={() => fileInputRef.current?.click()}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            className="w-full bg-[#f0edeb] border-2 border-dashed border-[#dcc1b8] rounded-xl p-8 flex flex-col items-center justify-center cursor-pointer hover:bg-[#e5e2d8] transition-colors mb-4"
          >
            <input 
              type="file" 
              ref={fileInputRef} 
              onChange={handleFileChange} 
              accept=".pdf" 
              multiple 
              className="hidden" 
            />
            <div className="p-3 bg-[#e5e2d8] rounded-lg mb-3">
              <FileUp className="w-6 h-6 text-[#9a4021]" />
            </div>
            <p className="text-sm font-medium text-[#1c1c1a] mb-1">
              {selectedFiles.length > 0
                ? `${selectedFiles.length} file(s) selected: ${selectedFiles.map(f => f.name).join(', ')}`
                : 'Drop PDF files here, or click to browse'}
            </p>
            <p className="text-xs text-[#89726b]">
              Max file size: 50MB
            </p>
          </div>

          {/* Ingested Status Badge (If already ingested) */}
          {documents.length > 0 && selectedFiles.length === 0 && (
            <div className="w-full bg-[#e5e2d8] text-[#1c1c1a] border border-[#dcc1b8] rounded-xl p-3.5 flex items-center justify-center gap-2 mb-4 text-sm font-medium">
              <CheckCircle className="w-4 h-4 text-[#9a4021]" />
              <span>{totalPages} pages, {totalChunks} sections indexed</span>
            </div>
          )}

          {errorMsg && (
            <p className="text-xs text-[#ba1a1a] mb-3 font-medium">
              {errorMsg}
            </p>
          )}

          {/* Primary Action Button */}
          <button
            onClick={handleSubmit}
            disabled={isIngesting}
            className="w-full bg-[#9a4021] hover:bg-[#b95837] text-white font-medium py-3.5 px-6 rounded-xl transition-colors flex items-center justify-center gap-2 shadow-sm disabled:opacity-50"
          >
            {isIngesting ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>Processing & Indexing...</span>
              </>
            ) : (
              <span>{documents.length > 0 && selectedFiles.length === 0 ? 'Go to Chat' : 'Ingest documents'}</span>
            )}
          </button>

        </div>
      </main>
    </div>
  );
};
