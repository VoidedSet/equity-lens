"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import dynamic from "next/dynamic";

/* ── Types ─────────────────────────────────────────────── */
type GNode = {
  id: string;
  type: string;
  name: string;
  count: number;
  companies?: string[];
  // Added by react-force-graph at runtime:
  x?: number;
  y?: number;
  fx?: number;
  fy?: number;
  [key: string]: unknown;
};

type GLink = {
  source: string | GNode;
  target: string | GNode;
  type: string;
  weight: number;
  [key: string]: unknown;
};

type GraphData = { nodes: GNode[]; links: GLink[] };

/* ── Colors ─────────────────────────────────────────────── */
const NODE_COLORS: Record<string, string> = {
  Company:      "#5b21b6",
  TOPIC:        "#dc2626",  Topic:        "#dc2626",
  BRAND:        "#db2777",  Brand:        "#db2777",
  LOCATION:     "#1d4ed8",  Location:     "#1d4ed8",
  STRATEGY:     "#c2410c",  Strategy:     "#c2410c",
  PERSON:       "#6d28d9",  Person:       "#6d28d9",
  TIME_PERIOD:  "#475569",  TimePeriod:   "#475569",
  RISK:         "#b91c1c",  Risk:         "#b91c1c",
  METRIC:       "#0369a1",  Metric:       "#0369a1",
};
const nodeColor = (type: string) => NODE_COLORS[type] ?? "#64748b";

/* ── Dynamic import (no SSR) ────────────────────────────── */
const ForceGraph2D = dynamic(
  () => import("react-force-graph-2d"),
  {
    ssr: false,
    loading: () => (
      <div className="flex items-center justify-center h-full">
        <div className="text-center space-y-2">
          <div className="w-8 h-8 border-2 border-[#e0e0e0] border-t-[#7c3aed] rounded-full animate-spin mx-auto" />
          <p className="text-[#888] text-sm">Initialising graph engine…</p>
        </div>
      </div>
    ),
  }
);

/* ── Main Component ─────────────────────────────────────── */
export function KnowledgeGraph({ companyCode }: { companyCode?: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const fgRef = useRef<any>(null);

  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dims, setDims] = useState({ w: 800, h: 580 });

  // Controls
  const [searchQuery, setSearchQuery] = useState("");
  const [aiQuery, setAiQuery] = useState("");
  const [aiLoading, setAiLoading] = useState(false);
  const [aiResult, setAiResult] = useState<{ cypher: string; count: number; explanation: string } | null>(null);
  const [aiError, setAiError] = useState<string | null>(null);

  // Hover / selection
  const [hoveredNode, setHoveredNode] = useState<GNode | null>(null);
  const [selectedNode, setSelectedNode] = useState<GNode | null>(null);

  /* ── Force tuning: repulsion + collision to prevent overlap ─ */
  useEffect(() => {
    if (!fgRef.current || !graphData.nodes.length) return;
    const fg = fgRef.current as any;
    import("d3-force-3d").then(({ forceCollide, forceManyBody }) => {
      fg.d3Force("charge", forceManyBody().strength(-280));
      fg.d3Force("collision", forceCollide().radius(40).strength(1).iterations(3));
      fg.d3ReheatSimulation();
    });
  }, [graphData.nodes.length]);

  /* ── Container size observer ─────────────────────────── */
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      for (const e of entries) {
        setDims({ w: e.contentRect.width, h: Math.max(500, e.contentRect.height) });
      }
    });
    ro.observe(el);
    setDims({ w: el.clientWidth || 800, h: 580 });
    return () => ro.disconnect();
  }, []);

  /* ── Data conversion helper ──────────────────────────── */
  const loadData = useCallback((nodes: any[], edges: any[]) => {
    const gNodes: GNode[] = nodes.map((n: any) => ({
      id: String(n.id),
      type: n.type || "TOPIC",
      name: n.name || n.label || String(n.id),
      count: Number(n.count) || 0,
      companies: n.companies || [],
    }));
    const idSet = new Set(gNodes.map((n) => n.id));
    const gLinks: GLink[] = (edges || [])
      .filter((e: any) => idSet.has(String(e.source)) && idSet.has(String(e.target)))
      .map((e: any) => ({
        source: String(e.source),
        target: String(e.target),
        type: e.type || "CO_OCCURS",
        weight: Number(e.weight) || 1,
      }));
    setGraphData({ nodes: gNodes, links: gLinks });
    // Zoom to fit after layout settles
    setTimeout(() => fgRef.current?.zoomToFit(400, 40), 800);
  }, []);

  /* ── Load company subgraph ───────────────────────────── */
  const loadCompanySubgraph = useCallback(
    async (code: string) => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`/api/graph/company/${code}/subgraph?max_nodes=80`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        loadData(data.nodes || [], data.edges || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load graph");
      } finally {
        setLoading(false);
      }
    },
    [loadData]
  );

  useEffect(() => {
    if (companyCode) loadCompanySubgraph(companyCode);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [companyCode]);

  /* ── Search ──────────────────────────────────────────── */
  const handleSearch = useCallback(async () => {
    if (!searchQuery.trim()) {
      if (companyCode) loadCompanySubgraph(companyCode);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(
        `/api/graph/search?q=${encodeURIComponent(searchQuery)}&company=${companyCode || ""}&limit=15`
      );
      const data = await res.json();
      if (!data.nodes?.length) {
        setError(`No results for "${searchQuery}"`);
        setLoading(false);
        return;
      }
      // Expand neighborhood of the best match
      const top = data.nodes[0];
      const nRes = await fetch(`/api/graph/node/${top.id}/neighbors?max_nodes=50`);
      const nData = await nRes.json();
      // Merge search result nodes into neighborhood
      const allIds = new Set((nData.nodes || []).map((n: any) => String(n.id)));
      const merged = [...(nData.nodes || [])];
      for (const sn of data.nodes) if (!allIds.has(String(sn.id))) merged.push(sn);
      loadData(merged, nData.edges || []);
    } catch {
      setError("Search failed");
    } finally {
      setLoading(false);
    }
  }, [searchQuery, companyCode, loadCompanySubgraph, loadData]);

  /* ── AI Query ────────────────────────────────────────── */
  const handleAiQuery = useCallback(async () => {
    if (!aiQuery.trim()) return;
    setAiLoading(true);
    setAiResult(null);
    setAiError(null);
    try {
      const res = await fetch("/api/graph/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: aiQuery, company: companyCode }),
      });
      const data = await res.json();
      if (!res.ok) {
        setAiError(data.detail || data.error || `Error ${res.status}`);
        return;
      }
      setAiResult({
        cypher: data.cypher,
        count: data.result?.count ?? 0,
        explanation: data.explanation || "",
      });
      // If Groq returned graph nodes, visualize them
      if (data.graph?.nodes?.length) {
        loadData(data.graph.nodes, data.graph.edges || []);
      } else if (data.result?.data?.length) {
        // Fallback: convert tabular result rows to nodes
        const nodes = data.result.data
          .filter((r: any) => r.id || r.name)
          .map((r: any, i: number) => ({
            id: String(r.id || `ai-${i}`),
            type: r.type || "TOPIC",
            name: String(r.name || r.id || ""),
            count: Number(r.count || 0),
            companies: r.companies || [],
          }));
        loadData(nodes, []);
      }
    } catch (e) {
      setAiError("AI query failed. Is the graph server running?");
    } finally {
      setAiLoading(false);
    }
  }, [aiQuery, companyCode, loadData]);

  /* ── Node click → expand neighbors ──────────────────── */
  const handleNodeClick = useCallback(
    async (node: GNode) => {
      setSelectedNode(node);
      try {
        const res = await fetch(`/api/graph/node/${node.id}/neighbors?max_nodes=30`);
        if (!res.ok) return;
        const data = await res.json();
        // Merge new nodes into existing graph
        setGraphData((prev) => {
          const existingIds = new Set(prev.nodes.map((n) => n.id));
          const newNodes: GNode[] = (data.nodes || [])
            .filter((n: any) => !existingIds.has(String(n.id)))
            .map((n: any) => ({
              id: String(n.id),
              type: n.type || "TOPIC",
              name: n.name || String(n.id),
              count: Number(n.count) || 0,
              companies: n.companies || [],
            }));
          const existingLinkKeys = new Set(
            prev.links.map((l) => {
              const s = typeof l.source === "object" ? l.source.id : l.source;
              const t = typeof l.target === "object" ? l.target.id : l.target;
              return `${s}__${t}`;
            })
          );
          const allIds = new Set([...prev.nodes.map((n) => n.id), ...newNodes.map((n) => n.id)]);
          const newLinks: GLink[] = (data.edges || [])
            .filter((e: any) => {
              const s = String(e.source), t = String(e.target);
              return allIds.has(s) && allIds.has(t) && !existingLinkKeys.has(`${s}__${t}`);
            })
            .map((e: any) => ({
              source: String(e.source),
              target: String(e.target),
              type: e.type || "CO_OCCURS",
              weight: Number(e.weight) || 1,
            }));
          return {
            nodes: [...prev.nodes, ...newNodes],
            links: [...prev.links, ...newLinks],
          };
        });
      } catch {
        // silently ignore expand errors
      }
    },
    []
  );

  /* ── Custom node canvas painter (labels inside) ─────── */
  const paintNode = useCallback(
    (node: GNode, ctx: CanvasRenderingContext2D, _gs: number) => {
      const isHovered = hoveredNode?.id === node.id;
      const isSelected = selectedNode?.id === node.id;
      const x = node.x ?? 0;
      const y = node.y ?? 0;
      const color = nodeColor(node.type);

      // Radius: Company nodes are largest, others scale with mention count
      const baseR = node.type === "Company"
        ? 24
        : Math.max(14, Math.min(22, Math.sqrt(node.count || 1) * 1.6 + 9));

      // Outer ring for selected / hovered
      if (isSelected || isHovered) {
        ctx.beginPath();
        ctx.arc(x, y, baseR + 5, 0, 2 * Math.PI);
        ctx.strokeStyle = color;
        ctx.lineWidth = 2.5;
        ctx.stroke();
      }

      // White border (creates separation on light background)
      ctx.beginPath();
      ctx.arc(x, y, baseR + 1.5, 0, 2 * Math.PI);
      ctx.fillStyle = "#ffffff";
      ctx.fill();

      // Filled circle
      ctx.beginPath();
      ctx.arc(x, y, baseR, 0, 2 * Math.PI);
      ctx.fillStyle = color;
      ctx.fill();

      // Label INSIDE the node
      const maxChars = node.type === "Company" ? 14 : 11;
      const label = node.name.length > maxChars
        ? node.name.slice(0, maxChars - 1) + "…"
        : node.name;
      const fontSize = node.type === "Company" ? 10 : 8;
      ctx.font = `700 ${fontSize}px Inter, system-ui, sans-serif`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillStyle = "#ffffff";
      ctx.fillText(label, x, y);
    },
    [hoveredNode, selectedNode]
  );

  /* ── Edge label painter ──────────────────────────────── */
  const paintLink = useCallback(
    (link: GLink, ctx: CanvasRenderingContext2D, globalScale: number) => {
      if (globalScale < 1.4) return;
      const source = link.source as GNode;
      const target = link.target as GNode;
      if (typeof source !== "object" || typeof target !== "object") return;
      const sx = source.x ?? 0, sy = source.y ?? 0;
      const tx = target.x ?? 0, ty = target.y ?? 0;

      const rawLabel = (link.type || "").replace(/_/g, " ").toLowerCase();
      if (!rawLabel || rawLabel === "co occurs" || rawLabel === "related") return;

      const midX = (sx + tx) / 2;
      const midY = (sy + ty) / 2;
      const fontSize = 7;
      ctx.font = `500 ${fontSize}px Inter, system-ui, sans-serif`;
      const tw = ctx.measureText(rawLabel).width;
      const pad = 2.5;

      // Pill background
      ctx.fillStyle = "rgba(245,245,245,0.92)";
      ctx.strokeStyle = "rgba(180,180,180,0.7)";
      ctx.lineWidth = 0.5;
      const bx = midX - tw / 2 - pad;
      const by = midY - fontSize / 2 - pad;
      const bw = tw + pad * 2;
      const bh = fontSize + pad * 2;
      ctx.beginPath();
      ctx.roundRect(bx, by, bw, bh, 3);
      ctx.fill();
      ctx.stroke();

      // Text
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillStyle = "#555";
      ctx.fillText(rawLabel, midX, midY);
    },
    []
  );

  /* ── Render ──────────────────────────────────────────── */
  const hasGraph = graphData.nodes.length > 0;

  return (
    <div className="ed-section-ruled" id="knowledge-graph">
      <div className="ed-container">
        <p className="kicker mb-2">Knowledge Graph</p>
        <h2 className="font-serif text-3xl lg:text-4xl text-[#222] leading-tight mb-4">
          Industry Knowledge Map
        </h2>
        <p className="text-[15px] text-[#333] leading-[1.9] mb-6 max-w-3xl">
          Interactive knowledge graph from {companyCode ? `${companyCode}'s` : "all"} annual reports,
          transcripts, and filings. Click any node to expand its neighbourhood.
          Ask AI to generate and visualise custom queries.
        </p>

        {/* Controls */}
        <div className="mb-4 space-y-2.5">
          {/* Keyword search */}
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Search nodes — e.g. 'Mumbai', 'Revenue', 'Taj'…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              className="flex-1 px-3 py-2 border border-[#e0e0e0] rounded-lg text-sm bg-white focus:outline-none focus:border-[#999]"
            />
            <button
              onClick={handleSearch}
              className="px-4 py-2 bg-[#222] text-white rounded-lg text-sm hover:bg-[#333] transition-colors cursor-pointer"
            >
              Search
            </button>
            <button
              onClick={() => {
                setSearchQuery("");
                setAiResult(null);
                setAiError(null);
                if (companyCode) loadCompanySubgraph(companyCode);
              }}
              className="px-4 py-2 border border-[#e0e0e0] rounded-lg text-sm hover:bg-[#f5f5f5] transition-colors cursor-pointer"
            >
              Reset
            </button>
          </div>

          {/* AI query */}
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Ask AI — e.g. 'Which companies are exposed to Mumbai supply risk?'"
              value={aiQuery}
              onChange={(e) => setAiQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleAiQuery()}
              className="flex-1 px-3 py-2 border border-[#f59e0b]/60 rounded-lg text-sm bg-[#fffbeb] focus:outline-none focus:border-[#f59e0b]"
            />
            <button
              onClick={handleAiQuery}
              disabled={aiLoading}
              className="px-4 py-2 bg-[#f59e0b] text-white rounded-lg text-sm hover:bg-[#d97706] disabled:opacity-50 transition-colors cursor-pointer whitespace-nowrap"
            >
              {aiLoading ? (
                <span className="flex items-center gap-1.5">
                  <span className="w-3 h-3 border border-white/50 border-t-white rounded-full animate-spin inline-block" />
                  Thinking…
                </span>
              ) : "Ask AI"}
            </button>
          </div>
        </div>

        {/* AI result banner */}
        {aiResult && (
          <div className="mb-4 p-3 bg-[#fffbeb] border border-[#f59e0b]/40 rounded-lg text-xs space-y-1">
            <p className="font-semibold text-[#92400e]">{aiResult.explanation}</p>
            <p className="text-[#78350f]">{aiResult.count} result{aiResult.count !== 1 ? "s" : ""} — visualised above</p>
            <details className="mt-1">
              <summary className="cursor-pointer text-[#b45309] hover:text-[#92400e]">View Cypher</summary>
              <pre className="mt-1 font-mono text-[10px] text-[#555] overflow-x-auto whitespace-pre-wrap">{aiResult.cypher}</pre>
            </details>
          </div>
        )}
        {aiError && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700">
            {aiError}
          </div>
        )}

        {/* Legend */}
        <div className="flex flex-wrap gap-x-4 gap-y-1.5 mb-4 text-[11px]">
          {Object.entries({
            Company: "#5b21b6", Topic: "#dc2626", Brand: "#db2777",
            Location: "#1d4ed8", Strategy: "#c2410c", Person: "#6d28d9", Metric: "#0369a1",
          }).map(([t, c]) => (
            <div key={t} className="flex items-center gap-1.5">
              <div className="w-2.5 h-2.5 rounded-full border border-white/50" style={{ backgroundColor: c }} />
              <span className="text-[#777]">{t}</span>
            </div>
          ))}
        </div>

        {error && (
          <div className="mb-4 bg-red-50 border border-red-200 rounded-lg p-3">
            <p className="text-red-700 text-sm">{error}</p>
          </div>
        )}

        {/* Graph canvas */}
        <div
          ref={containerRef}
          className="relative border border-[#e0e0e0] rounded-xl overflow-hidden"
          style={{ height: 600, background: "#f8f8f8" }}
        >
          {loading && !hasGraph ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center space-y-2">
                <div className="w-8 h-8 border-2 border-[#ddd] border-t-[#5b21b6] rounded-full animate-spin mx-auto" />
                <p className="text-[#666] text-sm">Loading knowledge graph…</p>
              </div>
            </div>
          ) : (
            <ForceGraph2D
              ref={fgRef}
              graphData={graphData}
              width={dims.w}
              height={600}
              backgroundColor="#f8f8f8"
              nodeId="id"
              nodeLabel={(n: any) => `${(n as GNode).name} (${(n as GNode).type}) — ${(n as GNode).count} mentions`}
              nodeCanvasObject={(n: any, ctx: CanvasRenderingContext2D, gs: number) => paintNode(n as GNode, ctx, gs)}
              nodeCanvasObjectMode={() => "replace"}
              linkColor={() => "rgba(30,30,30,0.30)"}
              linkWidth={(l: any) => Math.min(2, Number((l as GLink).weight) * 0.4 + 0.4)}
              linkCanvasObject={(l: any, ctx: CanvasRenderingContext2D, gs: number) => paintLink(l as GLink, ctx, gs)}
              linkCanvasObjectMode={() => "after"}
              linkDirectionalArrowLength={4}
              linkDirectionalArrowRelPos={1}
              linkDirectionalArrowColor={() => "rgba(30,30,30,0.40)"}
              linkDirectionalParticles={0}
              onNodeClick={(node: any) => handleNodeClick(node as GNode)}
              onNodeHover={(node: any) => setHoveredNode(node as GNode | null)}
              cooldownTicks={120}
              d3AlphaDecay={0.015}
              d3VelocityDecay={0.3}
              enableNodeDrag
              enableZoomInteraction
              enablePanInteraction
            />
          )}

          {/* Stats overlay */}
          {hasGraph && (
            <div className="absolute bottom-3 left-3 flex items-center gap-3 text-[10px] text-[#666] bg-white/80 border border-[#e0e0e0] px-2.5 py-1.5 rounded-lg backdrop-blur-sm">
              <span>{graphData.nodes.length} nodes</span>
              <span className="text-[#ccc]">·</span>
              <span>{graphData.links.length} edges</span>
              {loading && <span className="text-[#5b21b6]">updating…</span>}
            </div>
          )}

          {/* Controls hint */}
          {hasGraph && (
            <div className="absolute bottom-3 right-3 text-[10px] text-[#777] bg-white/80 border border-[#e0e0e0] px-2.5 py-1.5 rounded-lg backdrop-blur-sm">
              Scroll to zoom · Drag to pan · Click node to expand
            </div>
          )}
        </div>

        {/* Selected node detail */}
        {selectedNode && (
          <div className="mt-4 p-4 bg-[#fafafa] border border-[#e0e0e0] rounded-xl flex items-start gap-4">
            <div
              className="w-4 h-4 rounded-full mt-0.5 shrink-0 border-2 border-white shadow"
              style={{ backgroundColor: nodeColor(selectedNode.type) }}
            />
            <div className="flex-1 min-w-0">
              <p className="font-semibold text-[#222] text-sm">{selectedNode.name}</p>
              <div className="flex gap-4 mt-1 text-xs text-[#888]">
                <span>Type: <span className="font-mono text-[#555]">{selectedNode.type}</span></span>
                <span>Mentions: <span className="font-mono text-[#555]">{selectedNode.count}</span></span>
                {selectedNode.companies?.length ? (
                  <span>Companies: <span className="font-mono text-[#555]">{selectedNode.companies.join(", ")}</span></span>
                ) : null}
              </div>
            </div>
            <button
              onClick={() => setSelectedNode(null)}
              className="text-[#bbb] hover:text-[#666] transition-colors cursor-pointer text-xs"
            >
              ✕
            </button>
          </div>
        )}

        <p className="text-[11px] text-[#bbb] mt-4">
          Powered by Neo4j · Groq Llama 3.3 70B · react-force-graph-2d
        </p>
      </div>
    </div>
  );
}
