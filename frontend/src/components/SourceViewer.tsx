import React from 'react';
import { useAppStore } from '../store/useAppStore';
import { FileText, ChevronLeft, ChevronRight, BookOpen, AlertCircle } from 'lucide-react';

export const SourceViewer: React.FC = () => {
  const { documents, activeCitation, activePage, setActivePage } = useAppStore();

  const totalPages = documents.reduce((sum, doc) => sum + (doc.pages || 1), 0) || 1;

  // Build the document label: prefer the source file from the active citation
  const currentDocName =
    activeCitation?.source_file ||
    documents[0]?.filename ||
    'Document';

  const handlePrev = () => {
    if (activePage > 1) setActivePage(activePage - 1);
  };

  const handleNext = () => {
    if (activePage < totalPages) setActivePage(activePage + 1);
  };

  // Extract real citation data
  const citedPage = activeCitation?.page ?? activePage;
  const citedSection = activeCitation?.section ?? null;
  const citedText = activeCitation?.text ?? null;   // actual chunk text from backend
  const citedQuote = activeCitation?.quote ?? null; // LLM-verified snippet

  return (
    <div data-testid="source-viewer" className="h-full w-full bg-[#f6f3f1] flex flex-col font-sans overflow-hidden">
      {/* Top Navigation Bar */}
      <div className="p-4 border-b border-[#dcc1b8] flex items-center justify-between bg-[#fcf9f6]">
        <div className="flex items-center gap-2 text-sm font-semibold text-[#1c1c1a] font-serif min-w-0">
          <FileText className="w-4 h-4 text-[#9a4021] shrink-0" />
          <span className="truncate">{currentDocName}</span>
        </div>

        <div className="flex items-center gap-2 bg-[#f0edeb] border border-[#dcc1b8] rounded-full px-3 py-1 text-xs font-medium text-[#56423c] shrink-0">
          <button
            onClick={handlePrev}
            disabled={activePage <= 1}
            className="hover:text-[#9a4021] disabled:opacity-30 transition-colors"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
          </button>
          <span>
            Page <span data-testid="page-nav-current">{activePage}</span> of {totalPages}
          </span>
          <button
            onClick={handleNext}
            disabled={activePage >= totalPages}
            className="hover:text-[#9a4021] disabled:opacity-30 transition-colors"
          >
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Main Document Container */}
      <div className="flex-1 overflow-y-auto p-6 flex justify-center">
        <div className="w-full max-w-2xl bg-white border border-[#dcc1b8] rounded-lg p-8 shadow-xs flex flex-col min-h-[600px] overflow-auto">

          {/* No citation selected */}
          {!activeCitation && (
            <div className="flex-1 flex flex-col items-center justify-center text-center gap-4">
              <div className="w-12 h-12 rounded-full bg-[#f0edeb] flex items-center justify-center">
                <BookOpen className="w-6 h-6 text-[#9a4021]" />
              </div>
              <div>
                <p className="font-serif text-lg font-medium text-[#1c1c1a] mb-1">
                  Source Viewer
                </p>
                <p className="text-xs text-[#89726b] max-w-xs leading-relaxed">
                  Click any citation chip in the chat window to jump to and highlight the exact source passage from your document.
                </p>
              </div>
            </div>
          )}

          {/* Citation selected — display real content */}
          {activeCitation && (
            <div className="space-y-6">
              {/* Section Header */}
              <div className="pb-4 border-b border-[#f0edeb]">
                <div className="flex items-start justify-between gap-2">
                  <h2 className="text-xl font-serif font-bold text-[#1c1c1a] leading-tight">
                    {citedSection || `Page ${citedPage}`}
                  </h2>
                  <span className="shrink-0 bg-[#ffdbce] text-[#9a4021] text-xs font-semibold px-2.5 py-1 rounded-full border border-[#f5b8a0]">
                    p.{citedPage}
                  </span>
                </div>
                <div className="flex items-center gap-1.5 mt-2">
                  <span className="text-xs text-[#89726b] font-mono truncate">{currentDocName}</span>
                </div>
              </div>

              {/* Actual chunk text from MongoDB (real document content) */}
              {citedText ? (
                <div data-testid="source-chunk-text" className="text-sm text-[#1c1c1a] leading-relaxed">
                  {/* Highlight the verified quote within the full chunk text */}
                  {citedQuote && citedText.includes(citedQuote) ? (
                    <>
                      {citedText.split(citedQuote).map((part, idx, arr) => (
                        <React.Fragment key={idx}>
                          <span>{part}</span>
                          {idx < arr.length - 1 && (
                            <mark className="bg-[#ffe5d0] text-[#6b2a0f] rounded px-0.5 font-medium not-italic">
                              {citedQuote}
                            </mark>
                          )}
                        </React.Fragment>
                      ))}
                    </>
                  ) : (
                    <span>{citedText}</span>
                  )}
                </div>
              ) : (
                <div className="flex items-start gap-2 text-xs text-[#89726b] bg-[#f6f3f1] border border-dashed border-[#dcc1b8] rounded-lg p-4">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-[#9a4021]" />
                  <span>
                    Full source text unavailable for this citation. The answer was grounded in the document but the exact passage could not be retrieved.
                  </span>
                </div>
              )}

              {/* Verified Quote Box */}
              {citedQuote && (
                <div
                  data-testid="citation-highlight"
                  className="quote-highlight transition-all animate-fade-in"
                >
                  <p className="text-xs font-semibold text-[#9a4021] mb-2 uppercase tracking-wider">
                    Verified Passage (p.{citedPage} — {citedSection || 'Section'})
                  </p>
                  <p className="text-sm leading-relaxed font-serif italic">
                    &ldquo;{citedQuote}&rdquo;
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Footer */}
          <div className="mt-auto pt-6 border-t border-[#f0edeb] flex items-center justify-between text-[11px] font-mono text-[#89726b] tracking-wider uppercase">
            <span>{currentDocName}</span>
            <span>{activeCitation ? `p.${citedPage}` : `p.${activePage}`}</span>
          </div>
        </div>
      </div>
    </div>
  );
};
