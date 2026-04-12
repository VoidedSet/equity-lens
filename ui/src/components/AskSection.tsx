"use client";

import { useState } from "react";
import { Citation } from "./Citation";

/* Strip markdown code fences and extract JSON or clean text */
function extractJSON(raw: string): string {
  const fenced = raw.match(/```(?:json)?\s*([\s\S]*?)```/);
  if (fenced) return fenced[1].trim();
  const braceMatch = raw.match(/\{[\s\S]*\}/);
  if (braceMatch) return braceMatch[0];
  return raw;
}

/* Format AI response — handle JSON objects, markdown-like lists, source refs */
function AssistantMessage({ content, companyId }: { content: string; companyId?: string }) {
  // Try to parse as JSON first
  try {
    const cleaned = extractJSON(content);
    const parsed = JSON.parse(cleaned);
    if (typeof parsed === "object" && parsed !== null) {
      return (
        <div className="space-y-3">
          {Object.entries(parsed).map(([key, val]) => {
            const label = key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
            if (Array.isArray(val) && val.length > 0) {
              return (
                <div key={key}>
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-[#999] mb-1">{label}</p>
                  <ul className="space-y-1">
                    {val.map((item, i) => (
                      <li key={i} className="text-[13px] text-[#333] leading-relaxed flex gap-2">
                        <span className="text-[#bbb] shrink-0">&bull;</span>
                        <span><SourceRefText text={String(item)} /></span>
                      </li>
                    ))}
                  </ul>
                </div>
              );
            }
            if (typeof val === "string" && val) {
              return (
                <div key={key}>
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-[#999] mb-1">{label}</p>
                  <p className="text-[13px] text-[#333] leading-relaxed"><SourceRefText text={val} /></p>
                </div>
              );
            }
            return null;
          })}
        </div>
      );
    }
  } catch {
    // Not JSON, render as formatted text
  }

  // Strip leftover code fences
  const text = content.replace(/```json\s*/g, "").replace(/```/g, "").trim();
  // Split into paragraphs
  const paragraphs = text.split(/\n\n+/).filter(Boolean);
  return (
    <div className="space-y-2">
      {paragraphs.map((p, i) => {
        // Check if it's a bullet list
        const lines = p.split("\n");
        const isList = lines.every((l) => /^[-*•]\s/.test(l.trim()) || !l.trim());
        if (isList) {
          return (
            <ul key={i} className="space-y-1">
              {lines.filter((l) => l.trim()).map((l, j) => (
                <li key={j} className="text-[13px] text-[#333] leading-relaxed flex gap-2">
                  <span className="text-[#bbb] shrink-0">&bull;</span>
                  <span><SourceRefText text={l.replace(/^[-*•]\s*/, "")} companyId={companyId} /></span>
                </li>
              ))}
            </ul>
          );
        }
        return <p key={i} className="text-[13px] text-[#333] leading-relaxed"><SourceRefText text={p} companyId={companyId} /></p>;
      })}
    </div>
  );
}

/* Render [Source: ...] refs as clickable buttons that open source modal */
function SourceRefText({ text, companyId }: { text: string; companyId?: string }) {
  const parts = text.split(/(\[Source:?[^\]]*\]|\[(?:AR|Q[1-4])\s+FY\d{2}[^\]]*\])/gi);
  return (
    <>
      {parts.map((part, i) => {
        const srcMatch = part.match(/\[(?:Source:?\s*)?(.+?)\]/i);
        if (srcMatch) {
          const ref = srcMatch[1].trim();
          return (
            <button
              key={i}
              onClick={() => {
                window.dispatchEvent(new CustomEvent("open-source", { detail: { ref, company: companyId || "IHCL", quote: "" } }));
              }}
              className="inline text-[#222] underline underline-offset-2 decoration-dotted hover:decoration-solid cursor-pointer font-medium text-[12px]"
            >
              {ref}
            </button>
          );
        }
        return <span key={i}>{part}</span>;
      })}
    </>
  );
}

const sampleQuestions = [
  "How many times has IHCL missed RevPAR guidance?",
  "Compare IHCL and EIH credibility scores",
  "What is the F&B margin risk for IHCL?",
  "Show supply overhang risk in Mumbai",
];

type Message = {
  role: "user" | "assistant";
  content: string;
  citations?: string[];
};

export function AskSection({ companyId }: { companyId?: string }) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSend = (question: string) => {
    if (!question.trim()) return;

    const userMsg: Message = { role: "user", content: question };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);

    fetch("/api/gpt/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    })
      .then((r) => r.json())
      .then((data) => {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: data.answer, citations: data.citations || [] },
        ]);
      })
      .catch(() => {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: "Error connecting to API. Please try again.", citations: [] },
        ]);
      })
      .finally(() => setIsLoading(false));
  };

  return (
    <>
      {/* Floating trigger button */}
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 z-40 flex items-center gap-2 px-4 py-3 bg-[#222] text-white rounded-full shadow-lg hover:bg-[#444] transition-all cursor-pointer group"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>
        </svg>
        <span className="text-sm font-medium">Research Desk</span>
      </button>

      {/* Slide-out panel */}
      {open && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={() => setOpen(false)} />

          <div className="relative z-10 w-full max-w-md bg-white shadow-2xl flex flex-col border-l border-[#e2e8f0]">
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-3 border-b border-[#e0e0e0] bg-white">
              <div>
                <p className="text-[10px] tracking-[0.15em] uppercase text-[#999] font-medium">EquityLens AI</p>
                <p className="text-[14px] font-serif font-medium text-[#222]">Research Desk</p>
              </div>
              <button onClick={() => setOpen(false)} className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-[#f0f0f0] transition-colors cursor-pointer text-[#888]">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M18 6 6 18"/><path d="m6 6 12 12"/>
                </svg>
              </button>
            </div>

            {/* Body */}
            <div className="flex-1 overflow-y-auto px-5 py-4">
              <p className="text-[13px] text-[#888] leading-relaxed mb-4">
                Source-cited answers only. If the data isn&apos;t in our ingested documents,
                the system says <strong className="text-[#222]">DATA NOT AVAILABLE</strong>.
              </p>

              {/* Sample questions */}
              {messages.length === 0 && (
                <div className="space-y-2 mb-6">
                  <p className="text-[10px] tracking-[0.15em] uppercase text-[#999] font-medium mb-2">Try asking</p>
                  {sampleQuestions.map((q) => (
                    <button
                      key={q}
                      onClick={() => handleSend(q)}
                      className="w-full text-left px-3 py-2 text-[12px] text-[#333] border border-[#eee] hover:bg-[#fafafa] hover:border-[#e0e0e0] transition-all cursor-pointer"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              )}

              {/* Messages */}
              {messages.length > 0 && (
                <div className="space-y-5">
                  {messages.map((msg, i) =>
                    msg.role === "user" ? (
                      <div key={i} className="flex justify-end">
                        <div className="bg-[#222] text-white rounded-2xl rounded-br-sm px-4 py-2.5 max-w-[85%]">
                          <p className="text-[13px] leading-relaxed">{msg.content}</p>
                        </div>
                      </div>
                    ) : (
                      <div key={i}>
                        <div className="bg-[#fafafa] rounded-2xl rounded-bl-sm px-4 py-3 border border-[#eee]">
                          <div className="mb-2"><AssistantMessage content={msg.content} companyId={companyId} /></div>
                          {msg.citations && msg.citations.length > 0 && (
                            <div className="flex flex-wrap gap-1 pt-2 border-t border-[#eee]">
                              {msg.citations.map((c, j) => (
                                <Citation key={j} source={c} />
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    )
                  )}
                  {isLoading && (
                    <div className="flex items-center gap-2 text-[13px] text-[#999] py-2">
                      <div className="w-4 h-4 border-2 border-[#e0e0e0] border-t-[#222] rounded-full animate-spin" />
                      Searching cited sources...
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Input */}
            <div className="px-4 py-3 border-t border-[#e0e0e0] bg-white">
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSend(input)}
                  placeholder="Ask about credibility, financials, risk..."
                  className="flex-1 px-3 py-2 bg-white border border-[#e0e0e0] rounded-lg text-[13px] text-[#222] placeholder:text-[#bbb] focus:outline-none focus:border-[#999] transition-colors"
                />
                <button
                  onClick={() => handleSend(input)}
                  disabled={!input.trim()}
                  className="px-3 py-2 bg-[#222] text-white text-[12px] font-medium rounded-lg hover:bg-[#444] disabled:opacity-30 disabled:cursor-not-allowed transition-colors cursor-pointer"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="m5 12 14-7-4.5 7H5Zm14-7-4.5 7H5l14 7-4.5-7Z"/>
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
