"use client";

import { useState, useCallback, useRef, useMemo } from "react";
import ReactFlow, {
  Node,
  Edge,
  addEdge,
  Connection,
  useNodesState,
  useEdgesState,
  Controls,
  Background,
  BackgroundVariant,
  Panel,
  NodeProps,
  Handle,
  Position,
  MarkerType,
  EdgeLabelRenderer,
  BaseEdge,
  getBezierPath,
  EdgeProps,
} from "reactflow";
import "reactflow/dist/style.css";
import Link from "next/link";

/* ─── Types ─── */
type FactData = {
  title: string;
  body: string;
  source: string;
  sentiment: "positive" | "negative" | "neutral" | "warning";
  company?: string;
  metric?: string;
  period?: string;
};

type BoardAnalysis = {
  narrative: string;
  risks: string[];
  connections: string[];
  recommendation: string;
};

/* ─── JSON extraction helper (strips ```json fences) ─── */
function extractJSON(raw: string): string {
  // Strip markdown code fences like ```json ... ```
  const fenced = raw.match(/```(?:json)?\s*([\s\S]*?)```/);
  if (fenced) return fenced[1].trim();
  // Try to find raw JSON object
  const braceMatch = raw.match(/\{[\s\S]*\}/);
  if (braceMatch) return braceMatch[0];
  return raw;
}

/* ─── Render text with [Source: ...] as clickable links ─── */
function SourceLinkedText({ text, facts }: { text: string; facts: { id: string; title: string; source: string; company?: string }[] }) {
  // Match patterns like [Source: Q2 FY24 Earnings Call | 12:41] or [Source N] or (Source: ...)
  const parts = text.split(/(\[Source[^\]]*\]|\(Source[^)]*\))/gi);
  return (
    <>
      {parts.map((part, i) => {
        const sourceMatch = part.match(/(?:\[|\()Source:?\s*(.+?)(?:\]|\))/i);
        if (sourceMatch) {
          const ref = sourceMatch[1].trim();
          // Try to find matching fact
          const fact = facts.find((f) =>
            f.source && (f.source.toLowerCase().includes(ref.toLowerCase()) || ref.toLowerCase().includes(f.title.toLowerCase()))
          );
          if (fact?.source) {
            return (
              <button
                key={i}
                onClick={() => {
                  window.dispatchEvent(new CustomEvent("open-source", { detail: { ref: fact.source, company: fact.company || "IHCL", quote: "" } }));
                }}
                className="inline text-[#222] underline underline-offset-2 decoration-dotted hover:decoration-solid cursor-pointer font-medium"
              >
                {part}
              </button>
            );
          }
        }
        return <span key={i}>{part}</span>;
      })}
    </>
  );
}

/* ─── Sentiment Colors ─── */
const SENT_COLORS: Record<string, { border: string; bg: string; dot: string; label: string }> = {
  positive: { border: "border-green-400", bg: "bg-green-50", dot: "bg-green-500", label: "Positive" },
  negative: { border: "border-red-400", bg: "bg-red-50", dot: "bg-red-500", label: "Negative" },
  neutral: { border: "border-gray-300", bg: "bg-gray-50", dot: "bg-gray-400", label: "Neutral" },
  warning: { border: "border-amber-400", bg: "bg-amber-50", dot: "bg-amber-500", label: "Warning" },
};

/* ─── Relationship Types ─── */
const RELATION_TYPES = [
  { value: "supports", label: "Supports", color: "#22c55e" },
  { value: "contradicts", label: "Contradicts", color: "#ef4444" },
  { value: "causes", label: "Causes", color: "#f59e0b" },
  { value: "correlates", label: "Correlates", color: "#3b82f6" },
  { value: "precedes", label: "Precedes", color: "#8b5cf6" },
  { value: "unknown", label: "Related", color: "#888888" },
];

/* ─── Custom Fact Node ─── */
function FactNode({ data, selected }: NodeProps<FactData>) {
  const s = SENT_COLORS[data.sentiment] || SENT_COLORS.neutral;
  return (
    <div
      className={`w-[260px] border-2 ${s.border} ${selected ? "ring-2 ring-blue-400 ring-offset-2" : ""} bg-white rounded-lg shadow-md transition-shadow hover:shadow-lg`}
    >
      <Handle type="target" position={Position.Top} className="!w-3 !h-3 !bg-[#222] !border-2 !border-white" />
      <Handle type="source" position={Position.Bottom} className="!w-3 !h-3 !bg-[#222] !border-2 !border-white" />
      <Handle type="target" position={Position.Left} className="!w-3 !h-3 !bg-[#222] !border-2 !border-white" />
      <Handle type="source" position={Position.Right} className="!w-3 !h-3 !bg-[#222] !border-2 !border-white" />

      {/* Header */}
      <div className={`px-3 py-2 ${s.bg} border-b ${s.border} rounded-t-lg`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <div className={`w-2 h-2 rounded-full ${s.dot}`} />
            <span className="text-[10px] font-bold uppercase tracking-wider text-[#888]">{s.label}</span>
          </div>
          {data.company && (
            <span className="text-[10px] font-mono text-[#999]">{data.company}</span>
          )}
        </div>
      </div>

      {/* Body */}
      <div className="px-3 py-2.5">
        <h4 className="text-[13px] font-semibold text-[#222] leading-tight mb-1.5">{data.title}</h4>
        <p className="text-[11px] text-[#666] leading-relaxed mb-2 line-clamp-3">{data.body}</p>

        {/* Meta */}
        <div className="flex items-center gap-2 text-[9px] text-[#999]">
          {data.period && <span className="font-mono">{data.period}</span>}
          {data.metric && (
            <>
              <span>&middot;</span>
              <span>{data.metric}</span>
            </>
          )}
        </div>

        {/* Source */}
        {data.source && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              window.dispatchEvent(
                new CustomEvent("open-source", { detail: { ref: data.source, company: data.company || "IHCL", quote: data.body } })
              );
            }}
            className="mt-2 text-[10px] text-[#bbb] hover:text-[#222] transition-colors cursor-pointer flex items-center gap-1"
          >
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
              <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
            </svg>
            {data.source}
          </button>
        )}
      </div>
    </div>
  );
}

/* ─── Custom Edge with Label ─── */
function RelationEdge({ id, sourceX, sourceY, targetX, targetY, data, style, markerEnd }: EdgeProps) {
  const [edgePath, labelX, labelY] = getBezierPath({ sourceX, sourceY, targetX, targetY });
  const relation = RELATION_TYPES.find((r) => r.value === data?.relation) || RELATION_TYPES[5];

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        style={{ ...style, stroke: relation.color, strokeWidth: 2 }}
        markerEnd={markerEnd}
      />
      <EdgeLabelRenderer>
        <div
          className="nodrag nopan pointer-events-auto"
          style={{
            position: "absolute",
            transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
          }}
        >
          <span
            className="px-2 py-0.5 text-[10px] font-semibold rounded-full text-white shadow-sm"
            style={{ backgroundColor: relation.color }}
          >
            {relation.label}
          </span>
        </div>
      </EdgeLabelRenderer>
    </>
  );
}

/* ─── Add Fact Modal ─── */
function AddFactModal({
  onAdd,
  onClose,
}: {
  onAdd: (fact: FactData) => void;
  onClose: () => void;
}) {
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [source, setSource] = useState("");
  const [sentiment, setSentiment] = useState<FactData["sentiment"]>("neutral");
  const [company, setCompany] = useState("");
  const [metric, setMetric] = useState("");
  const [period, setPeriod] = useState("");

  const handleSubmit = () => {
    if (!title.trim() || !body.trim()) return;
    onAdd({ title, body, source, sentiment, company: company || undefined, metric: metric || undefined, period: period || undefined });
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose} />
      <div className="relative z-10 bg-white rounded-lg shadow-2xl w-full max-w-md p-6">
        <h3 className="font-serif text-xl text-[#222] mb-4">Pin a Fact</h3>

        <div className="space-y-3">
          <div>
            <label className="text-[10px] font-semibold uppercase tracking-wider text-[#999] block mb-1">Title *</label>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="RevPAR guidance miss Q2 FY24"
              className="w-full px-3 py-2 text-[13px] border border-[#e0e0e0] rounded focus:outline-none focus:border-[#999]"
            />
          </div>
          <div>
            <label className="text-[10px] font-semibold uppercase tracking-wider text-[#999] block mb-1">Details *</label>
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={3}
              placeholder="MD guided 15% RevPAR growth; actual was 9.2%. Third consecutive miss."
              className="w-full px-3 py-2 text-[13px] border border-[#e0e0e0] rounded focus:outline-none focus:border-[#999] resize-none"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[10px] font-semibold uppercase tracking-wider text-[#999] block mb-1">Company</label>
              <input
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                placeholder="IHCL"
                className="w-full px-3 py-2 text-[13px] border border-[#e0e0e0] rounded focus:outline-none focus:border-[#999]"
              />
            </div>
            <div>
              <label className="text-[10px] font-semibold uppercase tracking-wider text-[#999] block mb-1">Period</label>
              <input
                value={period}
                onChange={(e) => setPeriod(e.target.value)}
                placeholder="Q2 FY24"
                className="w-full px-3 py-2 text-[13px] border border-[#e0e0e0] rounded focus:outline-none focus:border-[#999]"
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[10px] font-semibold uppercase tracking-wider text-[#999] block mb-1">Metric</label>
              <input
                value={metric}
                onChange={(e) => setMetric(e.target.value)}
                placeholder="RevPAR"
                className="w-full px-3 py-2 text-[13px] border border-[#e0e0e0] rounded focus:outline-none focus:border-[#999]"
              />
            </div>
            <div>
              <label className="text-[10px] font-semibold uppercase tracking-wider text-[#999] block mb-1">Source</label>
              <input
                value={source}
                onChange={(e) => setSource(e.target.value)}
                placeholder="Q2 FY24 Earnings Call | 12:41"
                className="w-full px-3 py-2 text-[13px] border border-[#e0e0e0] rounded focus:outline-none focus:border-[#999]"
              />
            </div>
          </div>
          <div>
            <label className="text-[10px] font-semibold uppercase tracking-wider text-[#999] block mb-1">Sentiment</label>
            <div className="flex gap-2">
              {(["positive", "negative", "neutral", "warning"] as const).map((s) => (
                <button
                  key={s}
                  onClick={() => setSentiment(s)}
                  className={`flex-1 py-1.5 text-[11px] font-medium rounded border transition-all cursor-pointer ${
                    sentiment === s
                      ? `${SENT_COLORS[s].bg} ${SENT_COLORS[s].border} text-[#222]`
                      : "border-[#e0e0e0] text-[#999] hover:border-[#bbb]"
                  }`}
                >
                  {SENT_COLORS[s].label}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="flex gap-2 mt-5">
          <button onClick={onClose} className="flex-1 py-2 text-[13px] text-[#888] border border-[#e0e0e0] rounded hover:bg-[#fafafa] transition-colors cursor-pointer">
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!title.trim() || !body.trim()}
            className="flex-1 py-2 text-[13px] font-semibold text-white bg-[#222] rounded hover:bg-[#444] disabled:opacity-30 transition-colors cursor-pointer"
          >
            Pin to Board
          </button>
        </div>
      </div>
    </div>
  );
}

/* ─── Connection Relation Picker ─── */
function RelationPicker({
  onSelect,
  onClose,
}: {
  onSelect: (relation: string) => void;
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/20" onClick={onClose} />
      <div className="relative z-10 bg-white rounded-lg shadow-xl p-4 min-w-[200px]">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-[#999] mb-2">Relationship Type</p>
        <div className="space-y-1">
          {RELATION_TYPES.map((r) => (
            <button
              key={r.value}
              onClick={() => onSelect(r.value)}
              className="w-full text-left px-3 py-2 text-[13px] rounded hover:bg-[#fafafa] transition-colors cursor-pointer flex items-center gap-2"
            >
              <div className="w-3 h-3 rounded-full" style={{ backgroundColor: r.color }} />
              {r.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ─── AI Analysis Panel ─── */
function AnalysisPanel({
  analysis,
  loading,
  onClose,
  facts,
}: {
  analysis: BoardAnalysis | null;
  loading: boolean;
  onClose: () => void;
  facts: { id: string; title: string; source: string; company?: string }[];
}) {
  if (!analysis && !loading) return null;

  return (
    <div className="absolute top-4 right-4 z-20 w-[380px] bg-white border border-[#e0e0e0] rounded-lg shadow-xl overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-[#e0e0e0]">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          <span className="text-[12px] font-semibold text-[#222]">AI Analysis</span>
        </div>
        <button onClick={onClose} className="text-[#bbb] hover:text-[#222] transition-colors cursor-pointer">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 6 6 18" /><path d="m6 6 12 12" />
          </svg>
        </button>
      </div>

      <div className="px-4 py-3 max-h-[60vh] overflow-y-auto">
        {loading ? (
          <div className="flex items-center gap-2 py-8 justify-center">
            <div className="w-5 h-5 border-2 border-[#e0e0e0] border-t-[#222] rounded-full animate-spin" />
            <span className="text-[13px] text-[#999]">Analyzing connections...</span>
          </div>
        ) : analysis ? (
          <div className="space-y-4">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wider text-[#999] mb-1">Narrative Synthesis</p>
              <p className="text-[13px] text-[#333] leading-relaxed"><SourceLinkedText text={analysis.narrative} facts={facts} /></p>
            </div>
            {analysis.connections.length > 0 && (
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wider text-[#999] mb-1">Key Connections</p>
                <ul className="space-y-1.5">
                  {analysis.connections.map((c, i) => (
                    <li key={i} className="text-[12px] text-[#666] leading-relaxed flex gap-2">
                      <span className="text-[#bbb] shrink-0">&bull;</span>
                      <span><SourceLinkedText text={c} facts={facts} /></span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {analysis.risks.length > 0 && (
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wider text-red-500 mb-1">Risk Factors</p>
                <ul className="space-y-1.5">
                  {analysis.risks.map((r, i) => (
                    <li key={i} className="text-[12px] text-[#666] leading-relaxed flex gap-2">
                      <span className="text-red-400 shrink-0">&bull;</span>
                      <span><SourceLinkedText text={r} facts={facts} /></span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {analysis.recommendation && (
              <div className="border-t border-[#eee] pt-3">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-green-600 mb-1">Recommendation</p>
                <p className="text-[13px] text-[#333] leading-relaxed font-medium"><SourceLinkedText text={analysis.recommendation} facts={facts} /></p>
              </div>
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
}

/* ═══ MAIN BOARD PAGE ═══ */
const nodeTypes = { fact: FactNode };
const edgeTypes = { relation: RelationEdge };

export default function BoardPage() {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [pendingConnection, setPendingConnection] = useState<Connection | null>(null);
  const [analysis, setAnalysis] = useState<BoardAnalysis | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [showAnalysis, setShowAnalysis] = useState(false);
  const nodeIdRef = useRef(1);

  const defaultEdgeOptions = useMemo(
    () => ({
      type: "relation",
      markerEnd: { type: MarkerType.ArrowClosed, width: 16, height: 16, color: "#888" },
    }),
    []
  );

  /* Add a new fact node */
  const handleAddFact = useCallback(
    (fact: FactData) => {
      const id = `fact-${nodeIdRef.current++}`;
      const newNode: Node<FactData> = {
        id,
        type: "fact",
        position: { x: 100 + Math.random() * 400, y: 100 + Math.random() * 300 },
        data: fact,
      };
      setNodes((nds) => [...nds, newNode]);
    },
    [setNodes]
  );

  /* Handle edge connection — show relation picker */
  const onConnect = useCallback(
    (connection: Connection) => {
      setPendingConnection(connection);
    },
    []
  );

  const handleRelationSelect = useCallback(
    (relation: string) => {
      if (!pendingConnection) return;
      const rel = RELATION_TYPES.find((r) => r.value === relation) || RELATION_TYPES[5];
      const newEdge: Edge = {
        id: `e-${pendingConnection.source}-${pendingConnection.target}-${Date.now()}`,
        source: pendingConnection.source!,
        target: pendingConnection.target!,
        sourceHandle: pendingConnection.sourceHandle,
        targetHandle: pendingConnection.targetHandle,
        type: "relation",
        data: { relation },
        markerEnd: { type: MarkerType.ArrowClosed, width: 16, height: 16, color: rel.color },
      };
      setEdges((eds) => addEdge(newEdge, eds));
      setPendingConnection(null);
    },
    [pendingConnection, setEdges]
  );

  /* AI Analyze Board */
  const handleAnalyze = useCallback(async () => {
    if (nodes.length === 0) return;

    setAnalysisLoading(true);
    setShowAnalysis(true);
    setAnalysis(null);

    const facts = nodes.map((n) => ({
      id: n.id,
      ...n.data,
    }));

    const connections = edges.map((e) => {
      const srcNode = nodes.find((n) => n.id === e.source);
      const tgtNode = nodes.find((n) => n.id === e.target);
      return {
        from: srcNode?.data?.title || e.source,
        to: tgtNode?.data?.title || e.target,
        relation: e.data?.relation || "related",
      };
    });

    try {
      const res = await fetch("/api/gpt/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: `You are an equity research analyst examining an evidence board. Analyze these pinned facts and their connections, then provide:
1. A narrative synthesis (2-3 sentences connecting the key findings)
2. Key connections between facts (bullet points)
3. Risk factors identified (bullet points)
4. A one-sentence investment recommendation

FACTS ON BOARD:
${facts.map((f, i) => `${i + 1}. [${f.sentiment.toUpperCase()}] "${f.title}" — ${f.body}\n   Source: ${f.source || "N/A"} | Period: ${f.period || "N/A"} | Company: ${f.company || "N/A"}`).join("\n")}

CONNECTIONS DRAWN BY ANALYST:
${connections.length > 0 ? connections.map((c) => `- "${c.from}" ${c.relation} "${c.to}"`).join("\n") : "None drawn yet."}

IMPORTANT: When citing sources, use the EXACT source document string from the fact, formatted as [Source: <exact source string>]. For example: [Source: Q2 FY24 Earnings Call | 12:41]. Do NOT use generic labels like "Source 1".

Respond ONLY with a JSON object (no markdown, no code fences): {"narrative": "...", "connections": ["..."], "risks": ["..."], "recommendation": "..."}`,
        }),
      });

      const data = await res.json();
      try {
        const cleaned = extractJSON(data.answer);
        const parsed = JSON.parse(cleaned);
        setAnalysis({
          narrative: parsed.narrative || "",
          connections: Array.isArray(parsed.connections) ? parsed.connections : [],
          risks: Array.isArray(parsed.risks) ? parsed.risks : [],
          recommendation: parsed.recommendation || "",
        });
      } catch {
        // If JSON parse still fails, try to render the raw text nicely
        const text = data.answer?.replace(/```json\s*/g, "").replace(/```/g, "").trim() || "";
        setAnalysis({
          narrative: text,
          connections: [],
          risks: [],
          recommendation: "",
        });
      }
    } catch {
      setAnalysis({
        narrative: "Error connecting to AI. Please try again.",
        connections: [],
        risks: [],
        recommendation: "",
      });
    } finally {
      setAnalysisLoading(false);
    }
  }, [nodes, edges]);

  /* Clear board */
  const handleClear = useCallback(() => {
    setNodes([]);
    setEdges([]);
    setAnalysis(null);
    setShowAnalysis(false);
    nodeIdRef.current = 1;
  }, [setNodes, setEdges]);

  /* Add sample facts for demo */
  const handleAddSamples = useCallback(() => {
    const samples: { fact: FactData; pos: { x: number; y: number } }[] = [
      {
        fact: { title: "RevPAR Guidance Miss", body: "MD guided 15% RevPAR growth for FY25. Actual: 9.2%. Delta: -5.8pp. Third consecutive quarterly miss.", source: "Q2 FY24 Earnings Call | 12:41", sentiment: "negative", company: "IHCL", metric: "RevPAR", period: "Q2 FY24" },
        pos: { x: 80, y: 80 },
      },
      {
        fact: { title: "Room Addition Shortfall", body: "Guided 2,000 new keys by FY26. Only 1,340 delivered. 660-room gap. Delivery shortfall 3 years running.", source: "Q1 FY24 Earnings Call", sentiment: "negative", company: "IHCL", metric: "Room Keys", period: "FY24" },
        pos: { x: 420, y: 80 },
      },
      {
        fact: { title: "Occupancy-Led Growth Mismatch", body: "Management claimed ADR-led pricing power. Actual data: Occupancy up 8pp, ADR flat YoY. Growth is volume-driven, not pricing.", source: "AR FY24 | Page 91", sentiment: "warning", company: "IHCL", metric: "ADR vs Occupancy", period: "FY24" },
        pos: { x: 80, y: 340 },
      },
      {
        fact: { title: "F&B Margin Compression", body: "F&B revenue share rising: 28% (FY21) → 36% (FY24). F&B earns lower margins than rooms. EBITDA margin fell from 32% to 26%.", source: "AR FY24 | Revenue Note", sentiment: "warning", company: "IHCL", metric: "F&B Share", period: "FY21-FY24" },
        pos: { x: 420, y: 340 },
      },
      {
        fact: { title: "Mumbai Supply Overhang", body: "IHCL derives 32% revenue from Mumbai. 1,800 new 5-star keys under construction in Mumbai from competitors.", source: "Competitor DRHP | Page 88", sentiment: "negative", company: "IHCL", metric: "Supply Risk", period: "FY24-26" },
        pos: { x: 250, y: 580 },
      },
    ];

    const newNodes: Node<FactData>[] = samples.map((s, i) => ({
      id: `fact-${nodeIdRef.current + i}`,
      type: "fact",
      position: s.pos,
      data: s.fact,
    }));
    nodeIdRef.current += samples.length;

    const newEdges: Edge[] = [
      {
        id: "e-sample-1",
        source: newNodes[0].id,
        target: newNodes[1].id,
        type: "relation",
        data: { relation: "correlates" },
        markerEnd: { type: MarkerType.ArrowClosed, width: 16, height: 16, color: "#3b82f6" },
      },
      {
        id: "e-sample-2",
        source: newNodes[2].id,
        target: newNodes[0].id,
        type: "relation",
        data: { relation: "contradicts" },
        markerEnd: { type: MarkerType.ArrowClosed, width: 16, height: 16, color: "#ef4444" },
      },
      {
        id: "e-sample-3",
        source: newNodes[3].id,
        target: newNodes[4].id,
        type: "relation",
        data: { relation: "causes" },
        markerEnd: { type: MarkerType.ArrowClosed, width: 16, height: 16, color: "#f59e0b" },
      },
    ];

    setNodes((nds) => [...nds, ...newNodes]);
    setEdges((eds) => [...eds, ...newEdges]);
  }, [setNodes, setEdges]);

  return (
    <div className="h-screen w-screen flex flex-col bg-[#fafafa]">
      {/* Top bar */}
      <div className="flex items-center justify-between px-4 py-2 bg-white border-b border-[#e0e0e0] shrink-0 z-10">
        <div className="flex items-center gap-4">
          <Link href="/" className="font-serif text-[15px] font-bold text-[#222] hover:opacity-60 transition-opacity">
            EquityLens
          </Link>
          <span className="text-[#e0e0e0]">|</span>
          <span className="text-[13px] font-semibold text-[#222]">Evidence Board</span>
          <span className="text-[11px] text-[#999]">{nodes.length} facts &middot; {edges.length} connections</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleAddSamples}
            className="px-3 py-1.5 text-[11px] text-[#888] border border-[#e0e0e0] rounded hover:bg-[#f5f5f5] transition-colors cursor-pointer"
          >
            Load Demo
          </button>
          <button
            onClick={handleClear}
            className="px-3 py-1.5 text-[11px] text-[#888] border border-[#e0e0e0] rounded hover:bg-[#f5f5f5] transition-colors cursor-pointer"
          >
            Clear
          </button>
          <button
            onClick={() => setShowAddModal(true)}
            className="px-3 py-1.5 text-[11px] font-semibold text-white bg-[#222] rounded hover:bg-[#444] transition-colors cursor-pointer"
          >
            + Pin Fact
          </button>
          <button
            onClick={handleAnalyze}
            disabled={nodes.length === 0 || analysisLoading}
            className="px-3 py-1.5 text-[11px] font-semibold text-white bg-green-600 rounded hover:bg-green-700 disabled:opacity-30 transition-colors cursor-pointer flex items-center gap-1.5"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48 2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48 2.83-2.83" />
            </svg>
            {analysisLoading ? "Analyzing..." : "AI Analyze"}
          </button>
        </div>
      </div>

      {/* React Flow Canvas */}
      <div className="flex-1">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          defaultEdgeOptions={defaultEdgeOptions}
          fitView
          snapToGrid
          snapGrid={[20, 20]}
          className="bg-[#fafafa]"
        >
          <Controls className="!bg-white !border-[#e0e0e0] !shadow-md [&>button]:!bg-white [&>button]:!border-[#e0e0e0] [&>button]:!text-[#666] [&>button:hover]:!bg-[#f5f5f5]" />
          <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#ddd" />

          {/* Empty state */}
          {nodes.length === 0 && (
            <Panel position="top-center">
              <div className="text-center mt-32">
                <div className="w-16 h-16 rounded-full bg-[#f0f0f0] flex items-center justify-center mx-auto mb-4">
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#bbb" strokeWidth="1.5">
                    <rect x="3" y="3" width="7" height="7" rx="1" />
                    <rect x="14" y="3" width="7" height="7" rx="1" />
                    <rect x="3" y="14" width="7" height="7" rx="1" />
                    <rect x="14" y="14" width="7" height="7" rx="1" />
                  </svg>
                </div>
                <h3 className="font-serif text-xl text-[#222] mb-2">Your Evidence Board</h3>
                <p className="text-[13px] text-[#888] leading-relaxed max-w-sm mx-auto mb-4">
                  Pin facts from your research, draw connections between them,
                  and let AI synthesize your findings into actionable insights.
                </p>
                <div className="flex gap-2 justify-center">
                  <button
                    onClick={() => setShowAddModal(true)}
                    className="px-4 py-2 text-[12px] font-semibold text-white bg-[#222] rounded hover:bg-[#444] transition-colors cursor-pointer"
                  >
                    + Pin Your First Fact
                  </button>
                  <button
                    onClick={handleAddSamples}
                    className="px-4 py-2 text-[12px] text-[#888] border border-[#e0e0e0] rounded hover:bg-[#f5f5f5] transition-colors cursor-pointer"
                  >
                    Load Demo Board
                  </button>
                </div>
              </div>
            </Panel>
          )}
        </ReactFlow>
      </div>

      {/* Analysis panel overlay */}
      {showAnalysis && (
        <AnalysisPanel
          analysis={analysis}
          loading={analysisLoading}
          onClose={() => setShowAnalysis(false)}
          facts={nodes.map((n) => ({ id: n.id, title: n.data.title, source: n.data.source, company: n.data.company }))}
        />
      )}

      {/* Add fact modal */}
      {showAddModal && <AddFactModal onAdd={handleAddFact} onClose={() => setShowAddModal(false)} />}

      {/* Relation picker modal */}
      {pendingConnection && (
        <RelationPicker
          onSelect={handleRelationSelect}
          onClose={() => setPendingConnection(null)}
        />
      )}
    </div>
  );
}
