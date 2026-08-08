import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useAppStore } from '../store/useAppStore';
import { Plus, Send, ShieldAlert, Bot, FileText, PlusCircle, Loader2, ArrowDown } from 'lucide-react';
import { Button } from './ui/button';

// ── Simple markdown-like renderer for answer text ────────────────────────────
// Supports: **bold**, bullet points (- / •), numbered lists (1.), line breaks
const RichText: React.FC<{ text: string }> = ({ text }) => {
  const lines = text.split('\n');
  const elements: React.ReactNode[] = [];
  let listItems: { type: 'ul' | 'ol'; items: string[] } | null = null;

  const flushList = () => {
    if (!listItems) return;
    const Tag = listItems.type === 'ul' ? 'ul' : 'ol';
    const cls = listItems.type === 'ul'
      ? 'list-disc pl-5 space-y-1 my-2'
      : 'list-decimal pl-5 space-y-1 my-2';
    elements.push(
      <Tag key={elements.length} className={cls}>
        {listItems.items.map((item, i) => (
          <li key={i}>{renderInline(item)}</li>
        ))}
      </Tag>
    );
    listItems = null;
  };

  const renderInline = (str: string): React.ReactNode => {
    // Handle **bold** markers
    const parts = str.split(/(\*\*[^*]+\*\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={i} className="font-semibold">{part.slice(2, -2)}</strong>;
      }
      return <span key={i}>{part}</span>;
    });
  };

  for (const line of lines) {
    const trimmed = line.trim();

    // Bullet point: - item or • item
    const bulletMatch = trimmed.match(/^[-•]\s+(.+)/);
    if (bulletMatch) {
      if (listItems && listItems.type !== 'ul') flushList();
      if (!listItems) listItems = { type: 'ul', items: [] };
      listItems.items.push(bulletMatch[1]);
      continue;
    }

    // Numbered list: 1. item, 2) item
    const numMatch = trimmed.match(/^\d+[.)]\s+(.+)/);
    if (numMatch) {
      if (listItems && listItems.type !== 'ol') flushList();
      if (!listItems) listItems = { type: 'ol', items: [] };
      listItems.items.push(numMatch[1]);
      continue;
    }

    // Regular line
    flushList();
    if (trimmed === '') {
      elements.push(<br key={elements.length} />);
    } else {
      elements.push(
        <p key={elements.length} className="mb-1.5 last:mb-0">
          {renderInline(trimmed)}
        </p>
      );
    }
  }
  flushList();

  return <>{elements}</>;
};

// ── Chat Pane Component ─────────────────────────────────────────────────────
export const ChatPane: React.FC = () => {
  const {
    sessionId,
    messages,
    sendQuery,
    isQuerying,
    setActiveCitation,
    resetSession,
    setCurrentView,
    activeCitation,
  } = useAppStore();

  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const viewportRef = useRef<HTMLDivElement>(null);
  const [showScrollBtn, setShowScrollBtn] = useState(false);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  // Auto-scroll on new messages
  useEffect(() => {
    scrollToBottom();
  }, [messages, isQuerying, scrollToBottom]);

  // Detect scroll position to show/hide the scroll-to-bottom button
  const handleScroll = useCallback(() => {
    const el = viewportRef.current;
    if (!el) return;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    setShowScrollBtn(distanceFromBottom > 120);
  }, []);

  // Attach scroll listener to the viewport
  useEffect(() => {
    const el = viewportRef.current;
    if (!el) return;
    el.addEventListener('scroll', handleScroll, { passive: true });
    return () => el.removeEventListener('scroll', handleScroll);
  }, [handleScroll]);

  // Find the viewport element rendered by ScrollArea after mount
  useEffect(() => {
    const timer = setTimeout(() => {
      const viewport = document.querySelector('[data-slot="scroll-area-viewport"]') as HTMLDivElement | null;
      if (viewport && viewport.closest('[data-chat-scroll]')) {
        viewportRef.current = viewport;
        viewport.addEventListener('scroll', handleScroll, { passive: true });
      }
    }, 100);
    return () => clearTimeout(timer);
  }, [handleScroll]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!sessionId || !input.trim() || isQuerying) return;
    const q = input;
    setInput('');
    await sendQuery(q);
  };

  return (
    <div className="h-full w-full flex flex-col border-r border-border relative font-sans overflow-hidden">
      {/* Top Bar */}
      <div className="p-4 pl-16 border-b border-border flex items-center justify-between bg-background shrink-0">
        <Button
          onClick={() => setCurrentView('upload')}
          size='icon'
          variant={"secondary"}
          title="Add/Manage Documents"
        >
          <Plus/>
        </Button>

        <button
          onClick={() => resetSession()}
          className="flex items-center gap-1.5 text-xs font-medium text-primary bg-accent hover:bg-accent/80 px-3.5 py-1.5 rounded-full border border-primary/20 transition-colors cursor-pointer"
        >
          <PlusCircle className="w-3.5 h-3.5" />
          <span>New Session</span>
        </button>
      </div>

      {/* Messages Scrollable Area */}
      <div data-chat-scroll className="flex-1 min-h-0 relative overflow-hidden">
        <div
          ref={viewportRef}
          className="h-full w-full overflow-y-auto overflow-x-hidden scroll-smooth p-4"
        >
          <div className="space-y-5">
          {messages.length === 0 && (
            <div className="h-full min-h-[350px] flex flex-col items-center justify-center text-center p-6 text-muted-foreground">
              <div className="w-12 h-12 rounded-full bg-accent flex items-center justify-center mb-3">
                <Bot className="w-6 h-6 text-primary" />
              </div>
              <p className="font-serif text-lg font-medium text-foreground mb-1">
                Ask a question about your document
              </p>
              <p className="text-xs text-muted-foreground max-w-xs">
                Every claim will be anchored to exact pages and sections with zero hallucinations.
              </p>
            </div>
          )}

          {messages.map((msg) => {
            if (msg.role === 'user') {
              return (
                <div key={msg.id} className="flex justify-end">
                  <div className="max-w-[85%] bg-foreground text-background px-4 py-3 rounded-2xl rounded-tr-sm text-sm shadow-xs leading-relaxed">
                    {msg.text}
                  </div>
                </div>
              );
            }

            const isRefused = msg.status === 'refused' || (!msg.citations || msg.citations.length === 0);

            if (isRefused) {
              return (
                <div key={msg.id} data-testid="refusal-bubble" className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-full bg-muted border border-border flex items-center justify-center shrink-0 mt-0.5">
                    <ShieldAlert className="w-4 h-4 text-muted-foreground" />
                  </div>

                  <div className="flex-1 max-w-[90%]  border border-border rounded-2xl p-4 text-sm text-foreground flex items-start gap-2.5 shadow-xs bg-card">
                    <FileText className="w-4 h-4 text-muted-foreground shrink-0 mt-0.5" />
                    <p className="leading-relaxed font-medium">
                      {msg.text}
                    </p>
                  </div>
                </div>
              );
            }

            // Verified Answer Message
            return (
              <div key={msg.id} data-testid="answer-bubble" className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-full bg-primary text-white flex items-center justify-center shrink-0 mt-0.5 shadow-xs">
                  <Bot className="w-4 h-4" />
                </div>

                <div className="flex-1 max-w-[90%] space-y-3">
                  <div className="bg-card border border-border rounded-2xl p-4 text-sm text-foreground leading-relaxed shadow-xs">
                    <RichText text={msg.text} />
                  </div>

                  {/* Citation Chips */}
                  {msg.citations && msg.citations.length > 0 && (
                    <div className="flex flex-wrap gap-2">
                      {msg.citations.map((cite, idx) => {
                        const isActive =
                          activeCitation?.quote === cite.quote ||
                          (activeCitation?.page === cite.page && activeCitation?.section === cite.section);

                        return (
                          <button
                            key={idx}
                            data-testid="citation-chip"
                            onClick={() => setActiveCitation(cite)}
                            className={`citation-chip ${
                              isActive ? 'bg-accent border-[#9a4021] text-primary ring-1 ring-[#9a4021]' : ''
                            }`}
                          >
                            <FileText className="w-3.5 h-3.5" />
                            <span>
                              p.{cite.page || 1} — {cite.section || 'Section'}
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {isQuerying && (
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-full bg-primary text-white flex items-center justify-center shrink-0">
                <Bot className="w-4 h-4 animate-bounce" />
              </div>
              <div className="bg-background border border-border rounded-2xl px-4 py-3 text-sm text-foreground flex items-center gap-2 shadow-xs">
                <Loader2 className="w-4 h-4 animate-spin text-primary" />
                <span>Verifying citations against document chunks...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Scroll to Bottom Button */}
        {showScrollBtn && (
          <button
            onClick={scrollToBottom}
            className="absolute bottom-4 left-1/2 -translate-x-1/2 z-10 w-9 h-9 rounded-full bg-background border border-border shadow-lg flex items-center justify-center text-muted-foreground hover:text-primary hover:border-primary/20 transition-all cursor-pointer animate-fade-in"
            title="Scroll to bottom"
          >
            <ArrowDown className="w-4.5 h-4.5" />
          </button>
        )}
      </div>

      {/* Bottom Input Area */}
      <div className="p-4 border-t border-border bg-background shrink-0">
        <form onSubmit={handleSend} className="relative flex items-center">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={!sessionId ? 'Please upload documents to start...' : 'Ask a question...'}
            disabled={!sessionId || isQuerying}
            className="w-full bg-muted border border-border focus:border-primary focus:ring-1 focus:ring-primary rounded-full py-3.5 pl-5 pr-28 text-sm text-foreground placeholder-muted-foreground outline-none transition-all disabled:opacity-60 disabled:cursor-not-allowed"
          />

          <button
            type="submit"
            disabled={!sessionId || !input.trim() || isQuerying}
            className="absolute right-1.5 top-1.5 bottom-1.5 bg-primary hover:bg-primary/90 text-white text-xs font-semibold px-4 rounded-full flex items-center gap-1.5 transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            <span>Send</span>
            <Send className="w-3.5 h-3.5" />
          </button>
        </form>
      </div>
    </div>
  );
};
