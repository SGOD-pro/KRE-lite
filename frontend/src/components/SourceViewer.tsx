import React from 'react';
import { useAppStore } from '../store/useAppStore';
import { FileText, ChevronLeft, ChevronRight } from 'lucide-react';

export const SourceViewer: React.FC = () => {
  const { documents, activeCitation, activePage, setActivePage } = useAppStore();

  const totalPages = documents.reduce((sum, doc) => sum + (doc.pages || 1), 0) || 22;
  const currentDocName = documents[0]?.filename || 'Research_Paper_v2.pdf';

  const handlePrev = () => {
    if (activePage > 1) setActivePage(activePage - 1);
  };

  const handleNext = () => {
    if (activePage < totalPages) setActivePage(activePage + 1);
  };

  return (
    <div className="h-full w-full bg-[#f6f3f1] flex flex-col font-sans overflow-hidden">
      {/* Top Navigation Bar */}
      <div className="p-4 border-b border-[#dcc1b8] flex items-center justify-between bg-[#fcf9f6]">
        <div className="flex items-center gap-2 text-sm font-semibold text-[#1c1c1a] font-serif">
          <FileText className="w-4 h-4 text-[#9a4021]" />
          <span>{currentDocName}</span>
        </div>

        <div className="flex items-center gap-2 bg-[#f0edeb] border border-[#dcc1b8] rounded-full px-3 py-1 text-xs font-medium text-[#56423c]">
          <button
            onClick={handlePrev}
            disabled={activePage <= 1}
            className="hover:text-[#9a4021] disabled:opacity-30 transition-colors"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
          </button>
          <span>
            Page {activePage} of {totalPages}
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

      {/* Main Document Paper Container */}
      <div className="flex-1 overflow-y-auto p-8 flex justify-center">
        <div className="w-full max-w-2xl bg-white border border-[#dcc1b8] rounded-lg p-10 shadow-xs flex flex-col justify-between min-h-[680px]">
          
          {/* Document Content */}
          <div className="space-y-6">
            <div>
              <h2 className="text-2xl font-serif font-bold text-[#1c1c1a] mb-1">
                {activeCitation?.section || `Section ${activePage}`}
              </h2>
              <p className="text-xs text-[#89726b] font-mono">
                {activeCitation?.section ? `${activeCitation.section} Overview` : `Page ${activePage} Context`}
              </p>
            </div>

            <p className="text-sm text-[#1c1c1a] leading-relaxed">
              The preliminary phase of the study yielded baseline metrics across all demographic groups. 
              It was observed that the control group maintained a steady baseline, while the experimental cohort 
              showed early signs of variance.
            </p>

            {/* Active Citation Highlight Box */}
            {activeCitation && (
              <div className="quote-highlight transition-all animate-fade-in">
                <p className="text-xs font-semibold text-[#9a4021] mb-1 uppercase tracking-wider">
                  Verified Source Quote (p.{activeCitation.page || activePage} — {activeCitation.section || 'Section'})
                </p>
                <p className="text-sm leading-relaxed font-serif">
                  "{activeCitation.quote || 'Based on the provided document, Section 4.2 outlines three primary findings regarding the metabolic rate of the subjects under observation.'}"
                </p>
              </div>
            )}

            {!activeCitation && (
              <div className="p-4 bg-[#f6f3f1] border border-dashed border-[#dcc1b8] rounded-md text-xs text-[#89726b] italic text-center">
                Click any citation chip in the chat window to jump to and highlight the exact quote in this document pane.
              </div>
            )}

            <p className="text-sm text-[#1c1c1a] leading-relaxed">
              Furthermore, cognitive assessment scores indicated a marginal improvement in recall tasks, though 
              this was not statistically significant given the sample size constraints. Future longitudinal studies 
              are recommended to validate these early indicators.
            </p>
          </div>

          {/* Document Footer */}
          <div className="pt-8 border-t border-[#f0edeb] flex items-center justify-between text-[11px] font-mono text-[#89726b] tracking-wider uppercase">
            <span>Confidential Draft</span>
            <span>{activePage}</span>
          </div>

        </div>
      </div>
    </div>
  );
};
