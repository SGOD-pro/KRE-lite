import React from 'react';
import { useAppStore } from '../store/useAppStore';
import { FileText, ChevronLeft, ChevronRight, BookOpen, AlertCircle } from 'lucide-react';
import { ScrollArea } from './ui/scroll-area';

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
  const rawCitedText = activeCitation?.text ?? null;   // actual chunk text from backend
  const citedQuote = activeCitation?.quote ?? null; // LLM-verified snippet

  // Deduplicate repeated sentences or bullet chunks if any exist in the retrieved context
  const cleanCitedText = React.useMemo(() => {
    if (!rawCitedText) return null;
    
    // Split by newlines or bullet markers
    const parts = rawCitedText.split(/(?=\s*•\s*|\n\s*\n)/g).map(p => p.trim()).filter(Boolean);
    if (parts.length <= 1) return rawCitedText;

    const seen = new Set<string>();
    const uniqueParts: string[] = [];
    for (const part of parts) {
      const normalized = part.replace(/\s+/g, ' ').toLowerCase();
      if (!seen.has(normalized)) {
        seen.add(normalized);
        uniqueParts.push(part);
      }
    }
    return uniqueParts.join('\n\n');
  }, [rawCitedText]);

  return (
    <div data-testid="source-viewer" className="h-full w-full bg-[#f8fafc] flex flex-col font-sans overflow-hidden">
      {/* Top Navigation Bar */}
      <div className="p-4 border-b border-[#e2e8f0] flex items-center justify-between bg-white shrink-0">
        <div className="flex items-center gap-2 text-sm font-semibold text-[#0f172a] font-serif min-w-0">
          <FileText className="w-4 h-4 text-[#9a4021] shrink-0" />
          <span className="truncate">{currentDocName}</span>
        </div>

        <div className="flex items-center gap-2 bg-[#f1f5f9] border border-[#e2e8f0] rounded-full px-3 py-1 text-xs font-medium text-[#334155] shrink-0">
          <button
            onClick={handlePrev}
            disabled={activePage <= 1}
            className="hover:text-[#9a4021] disabled:opacity-30 transition-colors cursor-pointer"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
          </button>
          <span>
            Page <span data-testid="page-nav-current" className="font-semibold text-[#0f172a]">{activePage}</span> of {totalPages}
          </span>
          <button
            onClick={handleNext}
            disabled={activePage >= totalPages}
            className="hover:text-[#9a4021] disabled:opacity-30 transition-colors cursor-pointer"
          >
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Main Document Container */}
      <ScrollArea className="flex-1 min-h-0 w-full p-6">
        <div className="flex justify-center min-h-full">
          <div className="w-full max-w-2xl bg-white border border-[#e2e8f0] rounded-xl p-8 shadow-sm flex flex-col min-h-[600px]">

          {/* No citation selected */}
          {!activeCitation && (
            <div className="flex-1 flex flex-col items-center justify-center text-center gap-4">
              <div className="w-12 h-12 rounded-full bg-[#ffedd5] flex items-center justify-center">
                <BookOpen className="w-6 h-6 text-[#9a4021]" />
              </div>
              <div>
                <p className="font-serif text-lg font-medium text-[#0f172a] mb-1">
                  Source Viewer
                </p>
                <p className="text-xs text-[#64748b] max-w-xs leading-relaxed">
                  Click any citation chip in the chat window to jump to and highlight the exact source passage from your document.
                </p>
              </div>
            </div>
          )}

          {/* Citation selected — display real content */}
          {activeCitation && (
            <div className="space-y-6">
              {/* Section Header */}
              <div className="pb-4 border-b border-[#f1f5f9]">
                <div className="flex items-start justify-between gap-2">
                  <h2 className="text-xl font-serif font-bold text-[#0f172a] leading-tight">
                    {citedSection || `Page ${citedPage}`}
                  </h2>
                  <span className="shrink-0 bg-[#ffedd5] text-[#9a4021] text-xs font-semibold px-2.5 py-1 rounded-full border border-[#fdba74]">
                    p.{citedPage}
                  </span>
                </div>
                <div className="flex items-center gap-1.5 mt-2">
                  <span className="text-xs text-[#64748b] font-mono truncate">{currentDocName}</span>
                </div>
              </div>

              {/* Actual chunk text from MongoDB (real document content) */}
              {cleanCitedText ? (
                <div data-testid="source-chunk-text" className="text-sm text-[#0f172a] leading-relaxed whitespace-pre-line">
                  {/* Highlight the verified quote within the full chunk text */}
                  {citedQuote && cleanCitedText.includes(citedQuote) ? (
                    <>
                      {cleanCitedText.split(citedQuote).map((part, idx, arr) => (
                        <React.Fragment key={idx}>
                          <span>{part}</span>
                          {idx < arr.length - 1 && (
                            <mark className="bg-[#ffedd5] text-[#9a3412] rounded px-1 py-0.5 font-medium not-italic">
                              {citedQuote}
                            </mark>
                          )}
                        </React.Fragment>
                      ))}
                    </>
                  ) : (
                    <span>{cleanCitedText}</span>
                  )}
                </div>
              ) : (
                <div className="flex items-start gap-2 text-xs text-[#64748b] bg-[#f8fafc] border border-dashed border-[#e2e8f0] rounded-lg p-4">
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
          <div className="mt-auto pt-6 border-t border-[#f1f5f9] flex items-center justify-between text-[11px] font-mono text-[#94a3b8] tracking-wider uppercase">
            <span>{currentDocName}</span>
            <span>{activeCitation ? `p.${citedPage}` : `p.${activePage}`}</span>
          </div>
        </div>
        </div>
      </ScrollArea>
    </div>
  );
};
