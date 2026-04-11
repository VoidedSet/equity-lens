"use client";

import { useState, useEffect, useRef, useCallback } from "react";

/* ── types ─────────────────────────────────────────────── */
type SNode = {
  id: string;
  type: string;
  name: string;
  count: number;
  companies?: string[];
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  pinned: boolean;
};

type SEdge = {
  source: string;
  target: string;
  type: string;
  weight: number;
};

/* ── colours ───────────────────────────────────────────── */
const COLORS: Record<string, string> = {
  Company: "#c4a0e8",
  TOPIC: "#e07070", Topic: "#e07070",
  BRAND: "#f0a0c0", Brand: "#f0a0c0",
  LOCATION: "#79b8e8", Location: "#79b8e8",
  STRATEGY: "#f0a060", Strategy: "#f0a060",
  PERSON: "#9070a0", Person: "#9070a0",
  TIME_PERIOD: "#aab4c0", TimePeriod: "#aab4c0",
};
const col = (t: string) => COLORS[t] ?? "#aab4c0";

/* ── simulation class (all mutable, no React state) ────── */
class ForceGraph {
  nodes: SNode[] = [];
  edges: SEdge[] = [];
  idx = new Map<string, number>();
  adj = new Map<string, Set<string>>();
  alpha = 1;
  dragged: SNode | null = null;
  hovered: SNode | null = null;
  cam = { ox: 0, oy: 0, scale: 1 };
  panning = false;
  panStart = { x: 0, y: 0 };
  W = 800;
  H = 600;

  load(
    apiNodes: { id: string | number; type: string; name: string; count: number; companies?: string[] }[],
    apiEdges: { source: string | number; target: string | number; type: string; weight: number }[]
  ) {
    const ids = new Set(apiNodes.map((n) => String(n.id)));
    this.nodes = apiNodes.map((n) => ({
      id: String(n.id),
      type: n.type,
      name: n.name || n.type,
      count: n.count || 0,
      companies: n.companies,
      x: (Math.random() - 0.5) * 300,
      y: (Math.random() - 0.5) * 200,
      vx: 0,
      vy: 0,
      radius: n.type === "Company" ? 14 : Math.max(5, Math.min(11, Math.sqrt(n.count || 1) * 0.7 + 3)),
      pinned: false,
    }));
    this.edges = apiEdges
      .filter((e) => ids.has(String(e.source)) && ids.has(String(e.target)))
      .map((e) => ({ source: String(e.source), target: String(e.target), type: e.type, weight: e.weight || 1 }));

    this.idx.clear();
    this.adj.clear();
    this.nodes.forEach((n, i) => {
      this.idx.set(n.id, i);
      this.adj.set(n.id, new Set());
    });
    for (const e of this.edges) {
      this.adj.get(e.source)?.add(e.target);
      this.adj.get(e.target)?.add(e.source);
    }
    this.alpha = 1;
    this.cam = { ox: 0, oy: 0, scale: 1 };
  }

  tick() {
    if (this.alpha < 0.001) return;
    const N = this.nodes;
    const REPULSION = 3000;
    const LINK_DIST = 80;
    const LINK_STR = 0.06;
    const CENTER = 0.008;
    const DAMP = 0.88;

    // charge repulsion (Barnes–Hut would be better for >200 nodes)
    for (let i = 0; i < N.length; i++) {
      for (let j = i + 1; j < N.length; j++) {
        const a = N[i], b = N[j];
        let dx = a.x - b.x, dy = a.y - b.y;
        let d2 = dx * dx + dy * dy;
        if (d2 < 1) { dx = Math.random() - 0.5; dy = Math.random() - 0.5; d2 = 1; }
        const d = Math.sqrt(d2);
        const f = (REPULSION * this.alpha) / d2;
        const fx = (dx / d) * f, fy = (dy / d) * f;
        a.vx += fx; a.vy += fy;
        b.vx -= fx; b.vy -= fy;
      }
    }

    // link springs
    for (const e of this.edges) {
      const si = this.idx.get(e.source), ti = this.idx.get(e.target);
      if (si === undefined || ti === undefined) continue;
      const a = N[si], b = N[ti];
      let dx = b.x - a.x, dy = b.y - a.y;
      const d = Math.sqrt(dx * dx + dy * dy) || 1;
      const f = (d - LINK_DIST) * LINK_STR * this.alpha * Math.min(e.weight, 3);
      const fx = (dx / d) * f, fy = (dy / d) * f;
      a.vx += fx; a.vy += fy;
      b.vx -= fx; b.vy -= fy;
    }

    // center gravity
    for (const n of N) {
      n.vx -= n.x * CENTER * this.alpha;
      n.vy -= n.y * CENTER * this.alpha;
    }

    // integrate
    for (const n of N) {
      if (n.pinned) { n.vx = 0; n.vy = 0; continue; }
      n.vx *= DAMP; n.vy *= DAMP;
      n.x += n.vx; n.y += n.vy;
    }

    this.alpha *= 0.995;
  }

  draw(ctx: CanvasRenderingContext2D) {
    const { ox, oy, scale } = this.cam;
    ctx.clearRect(0, 0, this.W, this.H);
    ctx.save();
    ctx.translate(this.W / 2 + ox, this.H / 2 + oy);
    ctx.scale(scale, scale);

    const hId = this.hovered?.id;
    const hAdj = hId ? this.adj.get(hId) : null;

    // edges
    for (const e of this.edges) {
      const si = this.idx.get(e.source), ti = this.idx.get(e.target);
      if (si === undefined || ti === undefined) continue;
      const a = this.nodes[si], b = this.nodes[ti];
      const connected = hId && (e.source === hId || e.target === hId);
      ctx.strokeStyle = connected ? "rgba(80,80,80,0.5)" : "rgba(160,170,185,0.15)";
      ctx.lineWidth = connected ? 1.2 : 0.5;
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.stroke();
    }

    // nodes
    for (const n of this.nodes) {
      const isH = n.id === hId;
      const isAdj = hAdj?.has(n.id);
      const dim = hId && !isH && !isAdj;

      ctx.beginPath();
      ctx.arc(n.x, n.y, n.radius * (isH ? 1.3 : 1), 0, Math.PI * 2);
      ctx.fillStyle = col(n.type);
      ctx.globalAlpha = dim ? 0.2 : isH ? 1 : 0.8;
      ctx.fill();
      ctx.globalAlpha = 1;

      if (isH) {
        ctx.strokeStyle = "#333";
        ctx.lineWidth = 2;
        ctx.stroke();
      }
    }

    // labels
    const fs = Math.max(9, 11 / scale);
    ctx.textAlign = "center";
    ctx.textBaseline = "bottom";
    for (const n of this.nodes) {
      const isH = n.id === hId;
      const isAdj = hAdj?.has(n.id);
      const show = isH || isAdj || n.type === "Company" || (n.radius >= 9 && scale > 0.6);
      if (!show) continue;
      ctx.font = `${isH ? "bold " : ""}${fs}px Inter, system-ui, sans-serif`;
      ctx.fillStyle = isH ? "#000" : "#444";
      ctx.globalAlpha = (hId && !isH && !isAdj) ? 0.2 : 1;
      ctx.fillText(n.name.length > 18 ? n.name.slice(0, 16) + "…" : n.name, n.x, n.y - n.radius - 3);
      ctx.globalAlpha = 1;
    }

    ctx.restore();
  }

  screenToGraph(cx: number, cy: number): [number, number] {
    return [
      (cx - this.W / 2 - this.cam.ox) / this.cam.scale,
      (cy - this.H / 2 - this.cam.oy) / this.cam.scale,
    ];
  }

  hitTest(cx: number, cy: number): SNode | null {
    const [gx, gy] = this.screenToGraph(cx, cy);
    for (let i = this.nodes.length - 1; i >= 0; i--) {
      const n = this.nodes[i];
      const dx = gx - n.x, dy = gy - n.y;
      if (dx * dx + dy * dy <= (n.radius + 3) ** 2) return n;
    }
    return null;
  }
}

/* ── React component ───────────────────────────────────── */
export function KnowledgeGraph({ companyCode }: { companyCode?: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const simRef = useRef(new ForceGraph());
  const rafRef = useRef(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<{ n: number; e: number }>({ n: 0, e: 0 });
  const [searchQuery, setSearchQuery] = useState("");
  const [tooltip, setTooltip] = useState<{ name: string; type: string; count: number } | null>(null);
  const [selectedNode, setSelectedNode] = useState<SNode | null>(null);
  const [aiQuery, setAiQuery] = useState("");
  const [aiLoading, setAiLoading] = useState(false);
  const [aiResult, setAiResult] = useState<string | null>(null);

  /* ── animation loop ──────────────────────────────────── */
  const startLoop = useCallback(() => {
    cancelAnimationFrame(rafRef.current);
    const loop = () => {
      const sim = simRef.current;
      const canvas = canvasRef.current;
      if (!canvas) { rafRef.current = requestAnimationFrame(loop); return; }
      const ctx = canvas.getContext("2d");
      if (!ctx) { rafRef.current = requestAnimationFrame(loop); return; }
      sim.tick();
      sim.draw(ctx);
      rafRef.current = requestAnimationFrame(loop);
    };
    rafRef.current = requestAnimationFrame(loop);
  }, []);

  useEffect(() => () => cancelAnimationFrame(rafRef.current), []);

  /* ── resize ──────────────────────────────────────────── */
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const resize = () => {
      const r = canvas.parentElement?.getBoundingClientRect();
      if (!r) return;
      canvas.width = r.width * devicePixelRatio;
      canvas.height = r.height * devicePixelRatio;
      canvas.style.width = r.width + "px";
      canvas.style.height = r.height + "px";
      const ctx = canvas.getContext("2d");
      if (ctx) ctx.scale(devicePixelRatio, devicePixelRatio);
      simRef.current.W = r.width;
      simRef.current.H = r.height;
    };
    resize();
    window.addEventListener("resize", resize);
    return () => window.removeEventListener("resize", resize);
  }, []);

  /* ── data loading helpers ────────────────────────────── */
  const loadData = useCallback((nodes: any[], edges: any[]) => {
    simRef.current.load(nodes, edges);
    setInfo({ n: simRef.current.nodes.length, e: simRef.current.edges.length });
    startLoop();
  }, [startLoop]);

  const loadCompanySubgraph = useCallback(async (code: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/graph/company/${code}/subgraph?max_nodes=60`);
      if (!res.ok) throw new Error("Failed to load graph");
      const data = await res.json();
      loadData(data.nodes || [], data.edges || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load graph");
    } finally {
      setLoading(false);
    }
  }, [loadData]);

  /* ── search ──────────────────────────────────────────── */
  const handleSearch = useCallback(async () => {
    if (!searchQuery.trim()) {
      if (companyCode) loadCompanySubgraph(companyCode);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(
        `/api/graph/search?q=${encodeURIComponent(searchQuery)}&company=${companyCode || ""}&limit=10`
      );
      const data = await res.json();
      if (!data.nodes?.length) { setError(`No results for "${searchQuery}"`); setLoading(false); return; }

      const top = data.nodes[0];
      const nRes = await fetch(`/api/graph/node/${top.id}/neighbors?max_nodes=40`);
      const nData = await nRes.json();

      const allIds = new Set((nData.nodes || []).map((n: any) => String(n.id)));
      const merged = [...(nData.nodes || [])];
      for (const sn of data.nodes) if (!allIds.has(String(sn.id))) merged.push(sn);

      loadData(merged, nData.edges || []);
    } catch { setError("Search failed"); } finally { setLoading(false); }
  }, [searchQuery, companyCode, loadCompanySubgraph, loadData]);

  /* ── AI query ────────────────────────────────────────── */
  const handleAiQuery = useCallback(async () => {
    if (!aiQuery.trim()) return;
    setAiLoading(true);
    setAiResult(null);
    try {
      const res = await fetch("/api/graph/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: aiQuery, company: companyCode }),
      });
      const data = await res.json();
      if (!res.ok) setAiResult(`Error: ${data.detail || data.error || "Unknown"}`);
      else if (data.result) setAiResult(
        `Cypher: ${data.cypher}\n\nResults (${data.result.count} rows):\n${JSON.stringify(data.result.data?.slice(0, 5), null, 2)}`
      );
    } catch {
      setAiResult("AI query failed — is OPENROUTER_API_KEY set in .env?");
    } finally { setAiLoading(false); }
  }, [aiQuery, companyCode]);

  /* ── initial load ────────────────────────────────────── */
  useEffect(() => {
    if (companyCode) loadCompanySubgraph(companyCode);
  }, [companyCode, loadCompanySubgraph]);

  /* ── mouse handlers (all imperative, no React state in hot path) ── */
  const onMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const cx = e.clientX - rect.left, cy = e.clientY - rect.top;
    const sim = simRef.current;

    // node dragging
    if (sim.dragged) {
      const [gx, gy] = sim.screenToGraph(cx, cy);
      sim.dragged.x = gx;
      sim.dragged.y = gy;
      sim.dragged.vx = 0;
      sim.dragged.vy = 0;
      sim.alpha = Math.max(sim.alpha, 0.3);
      return;
    }

    // panning
    if (sim.panning) {
      sim.cam.ox += cx - sim.panStart.x;
      sim.cam.oy += cy - sim.panStart.y;
      sim.panStart = { x: cx, y: cy };
      return;
    }

    // hover
    const hit = sim.hitTest(cx, cy);
    sim.hovered = hit;
    if (canvasRef.current) canvasRef.current.style.cursor = hit ? "grab" : "default";
    setTooltip(hit ? { name: hit.name, type: hit.type, count: hit.count } : null);
  }, []);

  const onMouseDown = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const cx = e.clientX - rect.left, cy = e.clientY - rect.top;
    const sim = simRef.current;
    const hit = sim.hitTest(cx, cy);
    if (hit) {
      sim.dragged = hit;
      hit.pinned = true;
      sim.alpha = Math.max(sim.alpha, 0.3);
      if (canvasRef.current) canvasRef.current.style.cursor = "grabbing";
    } else {
      sim.panning = true;
      sim.panStart = { x: cx, y: cy };
    }
  }, []);

  const onMouseUp = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const sim = simRef.current;
    if (sim.dragged) {
      const rect = canvasRef.current?.getBoundingClientRect();
      if (rect) {
        const cx = e.clientX - rect.left, cy = e.clientY - rect.top;
        const hit = sim.hitTest(cx, cy);
        if (hit) setSelectedNode({ ...hit });
      }
      sim.dragged.pinned = false;
      sim.dragged = null;
    }
    sim.panning = false;
    if (canvasRef.current) canvasRef.current.style.cursor = "default";
  }, []);

  const onWheel = useCallback((e: React.WheelEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    const sim = simRef.current;
    const f = e.deltaY > 0 ? 0.92 : 1.08;
    sim.cam.scale = Math.max(0.15, Math.min(6, sim.cam.scale * f));
  }, []);

  /* ── render ──────────────────────────────────────────── */
  return (
    <div className="ed-section-ruled" id="knowledge-graph">
      <div className="ed-container">
        <p className="kicker mb-2">Knowledge Graph</p>
        <h2 className="font-serif text-3xl lg:text-4xl text-[#222] leading-tight mb-6">
          Industry Knowledge Map
        </h2>

        <p className="text-[15px] text-[#333] leading-[1.9] mb-6 max-w-3xl">
          Interactive knowledge graph built from {companyCode ? `${companyCode}'s` : "all"} annual reports,
          transcripts, and filings. Explore connections between topics, brands, locations, and strategies.
        </p>

        {/* Search */}
        <div className="mb-4 space-y-3">
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Search nodes (e.g., 'Mumbai', 'Revenue', 'Taj')..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              className="flex-1 px-3 py-2 border border-[#e0e0e0] rounded text-sm"
            />
            <button onClick={handleSearch} className="px-4 py-2 bg-[#222] text-white rounded text-sm hover:bg-[#333]">Search</button>
            <button
              onClick={() => { setSearchQuery(""); if (companyCode) loadCompanySubgraph(companyCode); }}
              className="px-4 py-2 border border-[#e0e0e0] rounded text-sm hover:bg-[#f5f5f5]"
            >Reset</button>
          </div>
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Ask AI (e.g., 'Which companies operate in Mumbai luxury segment?')..."
              value={aiQuery}
              onChange={(e) => setAiQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleAiQuery()}
              className="flex-1 px-3 py-2 border border-[#e0e0e0] rounded text-sm bg-[#fffbeb]"
            />
            <button
              onClick={handleAiQuery}
              disabled={aiLoading}
              className="px-4 py-2 bg-[#f59e0b] text-white rounded text-sm hover:bg-[#d97706] disabled:opacity-50"
            >{aiLoading ? "Thinking..." : "Ask AI"}</button>
          </div>
        </div>

        {aiResult && (
          <div className="mb-4 p-3 bg-[#fffbeb] border border-[#f59e0b]/30 rounded text-xs font-mono whitespace-pre-wrap max-h-40 overflow-auto">
            {aiResult}
          </div>
        )}

        {/* Legend */}
        <div className="flex flex-wrap gap-3 mb-4 text-xs">
          {[["Company","#c4a0e8"],["Topic","#e07070"],["Brand","#f0a0c0"],["Location","#79b8e8"],["Strategy","#f0a060"],["Person","#9070a0"],["TimePeriod","#aab4c0"]].map(
            ([t,c]) => (
              <div key={t} className="flex items-center gap-1.5">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: c }} />
                <span className="text-[#888]">{t}</span>
              </div>
            )
          )}
        </div>

        {error && (
          <div className="mb-4 bg-red-50 border border-red-200 rounded p-3">
            <p className="text-red-800 text-sm">{error}</p>
          </div>
        )}

        {/* Canvas */}
        <div className="relative border border-[#e0e0e0] rounded-lg overflow-hidden" style={{ height: 600, background: "#fafafa" }}>
          {loading && info.n === 0 ? (
            <div className="flex items-center justify-center h-full"><p className="text-[#888] text-sm">Loading graph...</p></div>
          ) : (
            <canvas
              ref={canvasRef}
              onMouseMove={onMouseMove}
              onMouseDown={onMouseDown}
              onMouseUp={onMouseUp}
              onMouseLeave={() => { simRef.current.dragged = null; simRef.current.panning = false; simRef.current.hovered = null; setTooltip(null); }}
              onWheel={onWheel}
              style={{ width: "100%", height: "100%", display: "block" }}
            />
          )}

          {tooltip && (
            <div className="absolute top-3 right-3 bg-white/95 border border-[#e0e0e0] rounded shadow-sm px-3 py-2 text-xs pointer-events-none">
              <p className="font-semibold text-[#222]">{tooltip.name}</p>
              <p className="text-[#888]">{tooltip.type} &middot; {tooltip.count} mentions</p>
            </div>
          )}

          <div className="absolute bottom-3 left-3 text-[10px] text-[#aaa] bg-white/80 px-2 py-1 rounded">
            {info.n} nodes &middot; {info.e} edges
          </div>
        </div>

        {selectedNode && (
          <div className="mt-4 p-4 bg-[#f8f8f8] border border-[#e0e0e0] rounded">
            <h3 className="font-semibold text-sm mb-2">{selectedNode.name}</h3>
            <div className="text-xs text-[#666] space-y-1">
              <p>Type: <span className="font-mono">{selectedNode.type}</span></p>
              <p>Mentions: <span className="font-mono">{selectedNode.count}</span></p>
              {selectedNode.companies?.length ? (
                <p>Companies: <span className="font-mono">{selectedNode.companies.join(", ")}</span></p>
              ) : null}
            </div>
          </div>
        )}

        <p className="text-xs text-[#bbb] mt-4">
          Source: Knowledge graph built from Data Ingestion pipeline. Powered by Neo4j.
        </p>
      </div>
    </div>
  );
}
