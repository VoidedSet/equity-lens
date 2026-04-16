"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import ReactMarkdown from "react-markdown";

/* ── Types ─────────────────────────────────────────────── */
type Message = { role: "user" | "assistant"; content: string; charts?: string[] };

/* ── Pipeline steps for n8n-style workflow viz ─────────── */
const STEPS = [
  { id: "analyze", label: "Parse Query" },
  { id: "route", label: "Select Tool" },
  { id: "execute", label: "Run Tool" },
  { id: "synthesize", label: "Write Report" },
] as const;

type StepId = (typeof STEPS)[number]["id"];

function mapEventToStep(type: string, message?: string): StepId | null {
  if (type === "status" && message?.includes("Analyzing")) return "analyze";
  if (type === "thought") return "route";
  if (type === "status" && message?.includes("Executing")) return "execute";
  if (type === "status" && message?.includes("Generating")) return "synthesize";
  return null;
}

/* ── Workflow Viz (n8n-style) ──────────────────────────── */
function WorkflowViz({
  activeStep,
  completedSteps,
  thought,
  tool,
  toolArgs,
}: {
  activeStep: StepId | null;
  completedSteps: StepId[];
  thought: string;
  tool: string;
  toolArgs: string;
}) {
  const stepIndex = (id: StepId) => STEPS.findIndex((s) => s.id === id);
  const activeIdx = activeStep ? stepIndex(activeStep) : -1;

  return (
    <div className="mb-5">
      <div className="flex items-center gap-0">
        {STEPS.map((step, i) => {
          const done = completedSteps.includes(step.id);
          const active = step.id === activeStep;
          const pending = !done && !active;
          return (
            <div key={step.id} className="flex items-center" style={{ flex: 1 }}>
              <div
                className={`
                  relative flex flex-col items-center justify-center px-2 py-2.5 rounded border text-center w-full
                  font-mono text-[10px] leading-tight transition-all duration-300
                  ${active ? "border-[#1a73e8] bg-[#e8f0fe] text-[#1a73e8] shadow-[0_0_8px_rgba(26,115,232,0.25)]" : ""}
                  ${done ? "border-[#34a853] bg-[#e6f4ea] text-[#34a853]" : ""}
                  ${pending ? "border-[#ddd] bg-[#fafafa] text-[#bbb]" : ""}
                `}
              >
                <span className="text-[13px] mb-0.5">
                  {done ? "\u2713" : active ? "\u25CF" : "\u25CB"}
                </span>
                <span className="tracking-wide uppercase font-medium">{step.label}</span>
                {active && (
                  <span className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-1 h-1 rounded-full bg-[#1a73e8] animate-ping" />
                )}
              </div>
              {i < STEPS.length - 1 && (
                <div className={`h-[2px] w-4 shrink-0 transition-colors duration-300 ${i < activeIdx || done ? "bg-[#34a853]" : "bg-[#ddd]"}`} />
              )}
            </div>
          );
        })}
      </div>

      {(thought || tool) && (
        <div className="mt-3 px-3 py-2 bg-[#f8f8f8] border border-[#eee] rounded font-mono text-[11px] text-[#555] leading-relaxed space-y-1">
          {thought && (
            <p><span className="text-[#999]">thought </span>{thought}</p>
          )}
          {tool && (
            <p><span className="text-[#999]">tool </span><span className="font-semibold text-[#333]">{tool}</span>{toolArgs && <span className="text-[#888]"> {toolArgs}</span>}</p>
          )}
        </div>
      )}
    </div>
  );
}

/* ── Sample prompts ────────────────────────────────────── */
const SAMPLE_PROMPTS = [
  "Compare ROE of all hotel companies",
  "Show IHCL quarterly revenue trend",
  "Which company has the highest debt-to-equity?",
  "Financial health scorecard for Chalet Hotels",
];

const AGENT_URL = "http://localhost:8001/agent/stream";
const RAG_URL = "/api/gpt/query";

/* ── Main Component ────────────────────────────────────── */
export function AskSection({ companyId }: { companyId?: string }) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const [activeStep, setActiveStep] = useState<StepId | null>(null);
  const [completedSteps, setCompletedSteps] = useState<StepId[]>([]);
  const [thought, setThought] = useState("");
  const [tool, setTool] = useState("");
  const [toolArgs, setToolArgs] = useState("");
  const [chartPaths, setChartPaths] = useState<string[]>([]);

  const scrollRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, isLoading, activeStep]);

  const resetWorkflow = useCallback(() => {
    setActiveStep(null);
    setCompletedSteps([]);
    setThought("");
    setTool("");
    setToolArgs("");
    setChartPaths([]);
  }, []);

  const advanceStep = useCallback((stepId: StepId) => {
    setCompletedSteps((prev) => {
      const idx = STEPS.findIndex((s) => s.id === stepId);
      const earlier = STEPS.slice(0, idx).map((s) => s.id).filter((id) => !prev.includes(id));
      return [...prev, ...earlier];
    });
    setActiveStep(stepId);
  }, []);

  /* ── Agent SSE stream with RAG fallback ── */
  const handleSend = useCallback(async (question: string) => {
    if (!question.trim() || isLoading) return;
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setInput("");
    setIsLoading(true);
    resetWorkflow();

    let answered = false;

    try {
      const res = await fetch(AGENT_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: question, history: messages.slice(-6).map((m) => ({ role: m.role, content: m.content })) }),
      });

      if (!res.ok || !res.body) throw new Error("agent-unavailable");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      const collectedCharts: string[] = [];

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const data = JSON.parse(line.slice(6));
            const step = mapEventToStep(data.type, data.message);
            if (step) advanceStep(step);

            if (data.type === "thought") {
              setThought(data.thought || "");
              setTool(data.tool || "");
              setToolArgs(data.args ? JSON.stringify(data.args) : "");
            }
            if (data.type === "charts" && data.paths) {
              collectedCharts.push(...data.paths);
              setChartPaths((p) => [...p, ...data.paths]);
            }
            if (data.type === "result") {
              setCompletedSteps(STEPS.map((s) => s.id));
              setActiveStep(null);
              setMessages((prev) => [...prev, { role: "assistant", content: data.content, charts: collectedCharts }]);
              answered = true;
            }
            if (data.type === "error") {
              setMessages((prev) => [...prev, { role: "assistant", content: `Error: ${data.message}` }]);
              answered = true;
            }
          } catch { /* skip parse errors */ }
        }
      }

      if (!answered) throw new Error("no-result");
    } catch {
      resetWorkflow();
      try {
        const res = await fetch(RAG_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question, company: companyId }),
        });
        const data = await res.json();
        setMessages((prev) => [...prev, { role: "assistant", content: data.answer || "No answer available." }]);
      } catch {
        setMessages((prev) => [...prev, { role: "assistant", content: "Both agent and RAG endpoints unavailable. Check if the servers are running." }]);
      }
    } finally {
      setIsLoading(false);
    }
  }, [isLoading, messages, companyId, resetWorkflow, advanceStep]);

  return (
    <>
      {/* ── Floating button ── */}
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 z-40 flex items-center gap-2.5 pl-3.5 pr-4 py-2.5 bg-[#1a1a1a] text-[#e0e0e0] shadow-lg hover:bg-[#333] transition-all cursor-pointer border border-[#333]"
      >
        <span className="font-mono text-[13px] tracking-tight">&#9655; ask</span>
      </button>

      {/* ── Slide-out panel ── */}
      {open && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div className="absolute inset-0 bg-black/20" onClick={() => setOpen(false)} />

          <div className="relative z-10 w-full max-w-lg bg-white shadow-2xl flex flex-col border-l border-[#e0e0e0]">
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-3 border-b border-[#e0e0e0] bg-white">
              <div className="flex items-baseline gap-3">
                <span className="font-mono text-[11px] tracking-[0.2em] uppercase text-[#999]">Research Terminal</span>
                <span className="text-[10px] text-[#ccc]">v2.0</span>
              </div>
              <button onClick={() => setOpen(false)} className="w-7 h-7 flex items-center justify-center hover:bg-[#f0f0f0] transition-colors cursor-pointer text-[#888] font-mono text-[14px]">
                &times;
              </button>
            </div>

            {/* Body */}
            <div ref={scrollRef} className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
              {/* Empty state */}
              {messages.length === 0 && !isLoading && (
                <div>
                  <p className="text-[12px] text-[#888] leading-relaxed mb-4 font-mono">
                    Financial analysis agent. Runs tools on live data, generates charts, writes reports.
                  </p>
                  <div className="space-y-1.5">
                    {SAMPLE_PROMPTS.map((q) => (
                      <button
                        key={q}
                        onClick={() => handleSend(q)}
                        className="w-full text-left px-3 py-2 text-[12px] text-[#444] font-mono border border-[#eee] hover:bg-[#f8f8f8] hover:border-[#ccc] transition-all cursor-pointer"
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Messages */}
              {messages.map((msg, i) => (
                <div key={i} className={msg.role === "user" ? "flex justify-end" : ""}>
                  {msg.role === "user" ? (
                    <div className="bg-[#1a1a1a] text-[#e0e0e0] px-4 py-2.5 max-w-[85%] font-mono text-[12px]">
                      {msg.content}
                    </div>
                  ) : (
                    <div className="border-l-2 border-[#222] pl-4">
                      <div className="prose prose-sm max-w-none text-[13px] text-[#333] leading-relaxed [&_strong]:text-[#111] [&_h1]:text-[15px] [&_h2]:text-[14px] [&_h3]:text-[13px] [&_h1]:font-serif [&_h2]:font-serif [&_h3]:font-serif [&_p]:mb-2 [&_ul]:mb-2 [&_li]:mb-0.5">
                        <ReactMarkdown>{msg.content}</ReactMarkdown>
                      </div>
                      {msg.charts && msg.charts.length > 0 && (
                        <div className="mt-3 space-y-2">
                          {msg.charts.map((p, j) => {
                            const filename = p.split(/[/\\]/).pop();
                            return (
                              <div key={j} className="border border-[#eee] p-1 bg-[#fafafa]">
                                <img
                                  src={`http://localhost:8001/output/${filename}`}
                                  alt={filename || "chart"}
                                  className="w-full h-auto max-h-[350px] object-contain"
                                />
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}

              {/* Workflow viz while processing */}
              {isLoading && (
                <WorkflowViz
                  activeStep={activeStep}
                  completedSteps={completedSteps}
                  thought={thought}
                  tool={tool}
                  toolArgs={toolArgs}
                />
              )}
            </div>

            {/* Input */}
            <div className="px-4 py-3 border-t border-[#e0e0e0] bg-white">
              <div className="flex items-center gap-2 font-mono">
                <span className="text-[#999] text-[14px] select-none">&#10095;</span>
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSend(input)}
                  placeholder={isLoading ? "running..." : "query"}
                  disabled={isLoading}
                  className="flex-1 py-2 bg-transparent text-[13px] text-[#222] placeholder:text-[#ccc] focus:outline-none"
                />
                <button
                  onClick={() => handleSend(input)}
                  disabled={!input.trim() || isLoading}
                  className="px-3 py-1.5 bg-[#1a1a1a] text-white text-[11px] font-mono tracking-wider uppercase hover:bg-[#333] disabled:opacity-20 disabled:cursor-not-allowed transition-colors cursor-pointer"
                >
                  run
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
