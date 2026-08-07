import React, { useState, useRef, useEffect } from 'react';
import { useAppStore } from '../store/useAppStore';
import { Menu, Send, ShieldAlert, Bot, FileText, PlusCircle, Loader2 } from 'lucide-react';

export const ChatPane: React.FC = () => {
  const {
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

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isQuerying]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isQuerying) return;
    const q = input;
    setInput('');
    await sendQuery(q);
  };

  return (
    <div className="h-full w-full bg-[#fcf9f6] flex flex-col border-r border-[#dcc1b8] relative font-sans overflow-hidden">
      {/* Top Bar */}
      <div className="p-4 border-b border-[#dcc1b8] flex items-center justify-between bg-[#fcf9f6]">
        <button
          onClick={() => setCurrentView('upload')}
          className="p-2.5 rounded-full bg-[#f0edeb] text-[#56423c] hover:bg-[#e5e2d8] transition-colors"
          title="Manage Documents"
        >
          <Menu className="w-5 h-5" />
        </button>

        <button
          onClick={() => resetSession()}
          className="flex items-center gap-1.5 text-xs font-medium text-[#9a4021] bg-[#e5e2d8] hover:bg-[#ffdbce] px-3 py-1.5 rounded-full border border-[#dcc1b8] transition-colors"
        >
          <PlusCircle className="w-3.5 h-3.5" />
          <span>New Session</span>
        </button>
      </div>

      {/* Messages Scrollable Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-5">
        {messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 text-[#56423c]">
            <div className="w-12 h-12 rounded-full bg-[#e5e2d8] flex items-center justify-center mb-3">
              <Bot className="w-6 h-6 text-[#9a4021]" />
            </div>
            <p className="font-serif text-lg font-medium text-[#1c1c1a] mb-1">
              Ask a question about your document
            </p>
            <p className="text-xs text-[#89726b] max-w-xs">
              Every claim will be anchored to exact pages and sections with zero hallucinations.
            </p>
          </div>
        )}

        {messages.map((msg) => {
          if (msg.role === 'user') {
            return (
              <div key={msg.id} className="flex justify-end">
                <div className="max-w-[85%] bg-[#e5e2e0] text-[#1c1c1a] px-4 py-3 rounded-2xl rounded-tr-sm text-sm shadow-xs">
                  {msg.text}
                </div>
              </div>
            );
          }

          const isRefused = msg.status === 'refused' || (!msg.citations || msg.citations.length === 0);

          if (isRefused) {
            return (
              <div key={msg.id} data-testid="refusal-bubble" className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-full bg-[#f0edeb] border border-[#dcc1b8] flex items-center justify-center shrink-0 mt-0.5">
                  <ShieldAlert className="w-4 h-4 text-[#56423c]" />
                </div>

                <div className="flex-1 max-w-[90%] bg-[#f6f3f1] border border-[#dcc1b8] rounded-2xl p-4 text-sm text-[#1c1c1a] flex items-start gap-2.5">
                  <FileText className="w-4 h-4 text-[#56423c] shrink-0 mt-0.5" />
                  <p className="leading-relaxed text-[#56423c] font-medium">
                    {msg.text}
                  </p>
                </div>
              </div>
            );
          }

          // Verified Answer Message
          return (
            <div key={msg.id} data-testid="answer-bubble" className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-full bg-[#9a4021] text-white flex items-center justify-center shrink-0 mt-0.5 shadow-xs">
                <Bot className="w-4 h-4" />
              </div>

              <div className="flex-1 max-w-[90%] space-y-3">
                <div className="bg-white border border-[#dcc1b8] rounded-2xl p-4 text-sm text-[#1c1c1a] leading-relaxed shadow-xs">
                  {msg.text}
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
                            isActive ? 'bg-[#ffdbce] border-[#9a4021] ring-1 ring-[#9a4021]' : ''
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
            <div className="w-8 h-8 rounded-full bg-[#9a4021] text-white flex items-center justify-center shrink-0">
              <Bot className="w-4 h-4 animate-bounce" />
            </div>
            <div className="bg-white border border-[#dcc1b8] rounded-2xl px-4 py-3 text-sm text-[#56423c] flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin text-[#9a4021]" />
              <span>Verifying citations against document chunks...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Bottom Input Area */}
      <div className="p-4 border-t border-[#dcc1b8] bg-[#fcf9f6]">
        <form onSubmit={handleSend} className="relative flex items-center">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question..."
            disabled={isQuerying}
            className="w-full bg-[#f0edeb] border border-[#dcc1b8] focus:border-[#9a4021] focus:ring-1 focus:ring-[#9a4021] rounded-full py-3.5 pl-5 pr-28 text-sm text-[#1c1c1a] placeholder-[#89726b] outline-none transition-all"
          />

          <button
            type="submit"
            disabled={!input.trim() || isQuerying}
            className="absolute right-1.5 top-1.5 bottom-1.5 bg-[#9a4021] hover:bg-[#b95837] text-white text-xs font-semibold px-4 rounded-full flex items-center gap-1.5 transition-colors disabled:opacity-50"
          >
            <span>Send</span>
            <Send className="w-3.5 h-3.5" />
          </button>
        </form>
      </div>
    </div>
  );
};
