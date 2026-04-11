"use client";

import { useState } from "react";
import { Citation } from "./Citation";

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

const hardcodedResponses: Record<string, { content: string; citations: string[] }> = {
  "How many times has IHCL missed RevPAR guidance?": {
    content: "IHCL has missed RevPAR guidance in 3 consecutive quarters (Q1–Q3 FY24). The most significant miss was in Q2 FY24, where management guided 15% RevPAR growth for FY25, but actual growth came in at 9.2% — a delta of -5.8 percentage points. This pattern of consistent over-guidance on RevPAR suggests management may be systematically over-projecting pricing power in the luxury segment.",
    citations: ["Q2 FY24 Earnings Call | 12:41", "AR FY25 | Page 87", "Q1 FY24 Earnings Call | 05:22"],
  },
  "Compare IHCL and EIH credibility scores": {
    content: "EIH (Oberoi) scores significantly higher on credibility (81/100) compared to IHCL (58/100). The 23-point gap is primarily driven by IHCL's consistent over-guidance on room additions and RevPAR targets. EIH tends to guide conservatively and frequently delivers at or above guided levels. EIH's composite score (76) also leads IHCL (71) despite IHCL's stronger industry position score (88 vs 71), because credibility carries 40% weight in the composite formula.",
    citations: ["Credibility Scores | FY24", "Deviation Tracker | IHCL vs EIH"],
  },
  "What is the F&B margin risk for IHCL?": {
    content: "IHCL's F&B revenue share has risen from 28% in FY21 to 36% in FY24. Since F&B operations carry lower margins than room revenue, this compositional shift has been silently compressing EBITDA margins — from 32% (FY21) to 33.2% (FY24, which looks healthy but masks the mix-shift). Management guided 35%+ EBITDA margins in Q4 FY23 but delivered 33.2%. If the F&B share continues rising, margin pressure will intensify even if RevPAR stays healthy.",
    citations: ["AR FY21-FY24 | Revenue Notes", "Q4 FY23 Earnings Call | 22:10", "AR FY24 | P&L Statement"],
  },
  "Show supply overhang risk in Mumbai": {
    content: "IHCL derives approximately 32% of its consolidated room revenue from Mumbai. There are currently 1,800 new 5-star keys under construction in the Mumbai market from competitors. This represents significant supply overhang in IHCL's most critical revenue market. Notably, Chalet Hotels also has 45% revenue exposure to Mumbai, making both companies vulnerable to this supply addition. Management has not proactively addressed this risk in recent earnings calls.",
    citations: ["AR FY24 | Page 45", "Competitor DRHP | Page 88", "Chalet AR FY24 | Revenue Segment"],
  },
};

export function AskSection() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSend = (question: string) => {
    if (!question.trim()) return;

    const userMsg: Message = { role: "user", content: question };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);

    setTimeout(() => {
      const response = hardcodedResponses[question] ?? {
        content: "DATA NOT AVAILABLE — This query requires data not yet ingested. The system refuses to answer without source-cited evidence.",
        citations: [],
      };
      setMessages((prev) => [...prev, { role: "assistant", content: response.content, citations: response.citations }]);
      setIsLoading(false);
    }, 800);
  };

  return (
    <section className="max-w-2xl mx-auto px-6 py-12" id="ask">
      <div className="border-t border-[#e2e8f0] mb-10" />

      <h2 className="text-xs tracking-[0.2em] uppercase text-[#94a3b8] font-medium mb-4">
        Ask EquityLens
      </h2>

      <p className="text-[15px] text-[#334155] leading-[1.85] mb-6">
        Source-cited answers only. If the data isn&apos;t in our ingested documents, the system
        says <strong className="text-[#0f172a]">DATA NOT AVAILABLE</strong>.
      </p>

      {/* Sample questions */}
      {messages.length === 0 && (
        <div className="flex flex-wrap gap-2 mb-8">
          {sampleQuestions.map((q) => (
            <button
              key={q}
              onClick={() => handleSend(q)}
              className="px-3 py-1.5 text-xs text-[#334155] border border-[#e2e8f0] rounded-full hover:bg-[#0f172a] hover:text-white hover:border-[#0f172a] transition-all cursor-pointer"
            >
              {q}
            </button>
          ))}
        </div>
      )}

      {/* Messages */}
      {messages.length > 0 && (
        <div className="space-y-8 mb-8">
          {messages.map((msg, i) =>
            msg.role === "user" ? (
              <p key={i} className="text-[15px] font-semibold text-[#0f172a]">
                {msg.content}
              </p>
            ) : (
              <div key={i} className="border-l-[3px] border-l-[#1e3a5f] pl-6">
                <p className="text-[15px] text-[#334155] leading-[1.85] mb-3">{msg.content}</p>
                {msg.citations && msg.citations.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {msg.citations.map((c, j) => (
                      <Citation key={j} source={c} />
                    ))}
                  </div>
                )}
              </div>
            )
          )}
          {isLoading && (
            <div className="border-l-[3px] border-l-[#e2e8f0] pl-6 py-2">
              <span className="text-sm text-[#94a3b8]">Searching cited sources...</span>
            </div>
          )}
        </div>
      )}

      {/* Input */}
      <div className="flex items-center gap-3">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend(input)}
          placeholder="Ask about credibility, financials, or risk flags..."
          className="flex-1 px-4 py-2.5 bg-white border border-[#e2e8f0] rounded-lg text-sm text-[#0f172a] placeholder:text-[#b0b8c4] focus:outline-none focus:border-[#94a3b8] transition-colors"
        />
        <button
          onClick={() => handleSend(input)}
          disabled={!input.trim()}
          className="px-4 py-2.5 bg-[#0f172a] text-white text-sm font-medium rounded-lg hover:bg-[#1e293b] disabled:opacity-30 disabled:cursor-not-allowed transition-colors cursor-pointer"
        >
          Ask
        </button>
      </div>
    </section>
  );
}
