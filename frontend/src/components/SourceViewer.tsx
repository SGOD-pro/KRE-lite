import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useAppStore } from '../store/useAppStore';
import { FileText, BookOpen, AlertCircle, ArrowDown } from 'lucide-react';

export const SourceViewer: React.FC = () => {
  const { documents, activeCitation, activePage } = useAppStore();

  const totalPages = documents.reduce((sum, doc) => sum + (doc.pages || 1), 0) || 1;

  const [showScrollBtn, setShowScrollBtn] = useState(false);
  const viewportRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  const handleScroll = useCallback(() => {
    const el = viewportRef.current;
    if (!el) return;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    setShowScrollBtn(distanceFromBottom > 120);
  }, []);

  useEffect(() => {
    const el = viewportRef.current;
    if (!el) return;
    el.addEventListener('scroll', handleScroll, { passive: true });
    // Check initial state
    handleScroll();
    return () => el.removeEventListener('scroll', handleScroll);
  }, [handleScroll, activeCitation]);

  // Build the document label: prefer the source file from the active citation
  const currentDocName =
    activeCitation?.source_file ||
    documents[0]?.filename ||
    'Document';


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
    <div data-testid="source-viewer" className="h-full w-full bg-background flex flex-col font-sans overflow-hidden">
      {/* Top Navigation Bar */}
      <div className="p-4 border-b border-border flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2 text-sm font-semibold text-foreground font-serif min-w-0">
          <FileText className="w-4 h-4 text-primary shrink-0" />
          <span className="truncate">{currentDocName}</span>
        </div>

        <div className="flex items-center gap-2 bg-muted border border-border rounded-full px-3 py-1 text-xs font-medium text-foreground shrink-0">
          <span>
            Page <span data-testid="page-nav-current" className="font-semibold text-foreground">{activePage}</span> of {totalPages}
          </span>
        </div>
      </div>

      {/* Main Document Container */}
      <div className="flex-1 min-h-0 relative w-full">
        <div
          ref={viewportRef}
          className="h-full w-full overflow-y-auto overflow-x-hidden scroll-smooth p-6"
        >
        <div className="flex justify-center min-h-full">
          <div className="w-full max-w-2xl bg-card border border-border rounded-xl p-8 shadow-sm flex flex-col min-h-[600px]">

          {/* No citation selected */}
          {!activeCitation && (
            <div className="flex-1 flex flex-col items-center justify-center text-center gap-4">
              <div className="w-12 h-12 rounded-full bg-accent flex items-center justify-center">
                <BookOpen className="w-6 h-6 text-primary" />
              </div>
              <div>
                <p className="font-serif text-lg font-medium text-foreground mb-1">
                  Source Viewer
                </p>
                <p className="text-xs text-muted-foreground max-w-xs leading-relaxed">
                  Click any citation chip in the chat window to jump to and highlight the exact source passage from your document.
                </p>
              </div>
            </div>
          )}

          {/* Citation selected — display real content */}
          {activeCitation && (
            <div className="space-y-6">
              {/* Section Header */}
              <div className="pb-4 border-b border-border">
                <div className="flex items-start justify-between gap-2">
                  <h2 className="text-xl font-serif font-bold text-foreground leading-tight">
                    {citedSection || `Page ${citedPage}`}
                  </h2>
                  <span className="shrink-0 bg-accent text-primary text-xs font-semibold px-2.5 py-1 rounded-full border border-primary/20">
                    p.{citedPage}
                  </span>
                </div>
                <div className="flex items-center gap-1.5 mt-2">
                  <span className="text-xs text-muted-foreground font-mono truncate">{currentDocName}</span>
                </div>
              </div>

              {/* Actual chunk text from MongoDB (real document content) */}
              {cleanCitedText ? (
                <div data-testid="source-chunk-text" className="text-sm text-foreground leading-relaxed whitespace-pre-line">
                  {/* Highlight the verified quote within the full chunk text */}
                  {citedQuote && cleanCitedText.includes(citedQuote) ? (
                    <>
                      {cleanCitedText.split(citedQuote).map((part, idx, arr) => (
                        <React.Fragment key={idx}>
                          <span>{part}</span>
                          {idx < arr.length - 1 && (
                            <mark className="bg-accent text-accent-foreground rounded px-1 py-0.5 font-medium not-italic">
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
                <div className="flex items-start gap-2 text-xs text-muted-foreground bg-background border border-dashed border-border rounded-lg p-4">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-primary" />
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
                  <p className="text-xs font-semibold text-primary mb-2 uppercase tracking-wider">
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
          <div className="mt-auto pt-6 border-t border-border flex items-center justify-between text-[11px] font-mono text-muted-foreground tracking-wider uppercase">
            <span>{currentDocName}</span>
            <span>{activeCitation ? `p.${citedPage}` : `p.${activePage}`}</span>
          </div>
          </div>
          <div ref={bottomRef} className="h-1" />
        </div>
        </div>

        {/* Scroll to bottom button */}
        {showScrollBtn && (
          <button
            onClick={scrollToBottom}
            className="absolute bottom-6 left-1/2 -translate-x-1/2 z-10 w-9 h-9 rounded-full bg-background border border-border shadow-lg flex items-center justify-center text-muted-foreground hover:text-primary hover:border-primary/20 transition-all cursor-pointer animate-fade-in"
            title="Scroll to bottom"
          >
            <ArrowDown className="w-4.5 h-4.5" />
          </button>
        )}
      </div>
    </div>
  );
};
