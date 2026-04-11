"use client";

import { useState } from "react";

type GraphNode = { id: string; label: string; type: "company" | "city" | "segment" | "theme" | "warning" | "strategy"; x: number; y: number };
type GraphEdge = { from: string; to: string; label?: string; weight?: string };

const typeColors: Record<GraphNode["type"], { fill: string; stroke: string; text: string }> = {
  company: { fill: "#222222", stroke: "#222222", text: "#ffffff" },
  city: { fill: "#ffffff", stroke: "#3b82f6", text: "#1e40af" },
  segment: { fill: "#ffffff", stroke: "#16a34a", text: "#15803d" },
  theme: { fill: "#fffbeb", stroke: "#f59e0b", text: "#92400e" },
  warning: { fill: "#fff5f5", stroke: "#ef4444", text: "#991b1b" },
  strategy: { fill: "#f8f8f8", stroke: "#888888", text: "#333333" },
};

const typeLabels: Record<GraphNode["type"], string> = {
  company: "Company",
  city: "Revenue Market",
  segment: "Segment",
  theme: "Macro Theme",
  warning: "Risk Signal",
  strategy: "Strategy",
};

export function IndustryGraph({ graphNodes, graphEdges }: { graphNodes: GraphNode[]; graphEdges: GraphEdge[] }) {
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  const activeNode = selectedNode || hoveredNode;

  const activeEdges = activeNode
    ? graphEdges.filter((e) => e.from === activeNode || e.to === activeNode)
    : [];
  const activeNodeIds = activeNode
    ? new Set([activeNode, ...activeEdges.map((e) => e.from), ...activeEdges.map((e) => e.to)])
    : null;

  const svgWidth = 780;
  const svgHeight = 520;

  return (
    <div className="ed-section-ruled" id="industry-map">
      <div className="ed-container">
        <p className="kicker mb-2">Network Analysis</p>
        <h2 className="font-serif text-3xl lg:text-4xl text-[#222] leading-tight mb-6">Industry Map</h2>

        <p className="text-[15px] text-[#333] leading-[1.9] mb-8 max-w-3xl">
          How companies, markets, segments, and risks connect. Click any node to
          isolate its relationships. Revenue concentration creates shared vulnerability.
        </p>

        <div className="flex flex-wrap gap-4 mb-6 text-xs">
          {(Object.keys(typeColors) as GraphNode["type"][]).map((type) => (
            <div key={type} className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-full border-2" style={{ backgroundColor: typeColors[type].fill, borderColor: typeColors[type].stroke }} />
              <span className="text-[#888]">{typeLabels[type]}</span>
            </div>
          ))}
        </div>

        <div className="border border-[#e0e0e0] overflow-hidden" style={{ background: "#fafafa" }}>
          <svg viewBox={`0 0 ${svgWidth} ${svgHeight}`} className="w-full" style={{ height: "auto", maxHeight: 420 }}>
            {graphEdges.map((edge, i) => {
              const from = graphNodes.find((n) => n.id === edge.from);
              const to = graphNodes.find((n) => n.id === edge.to);
              if (!from || !to) return null;
              const isActive = !activeNodeIds || (activeNodeIds.has(edge.from) && activeNodeIds.has(edge.to));
              const isHighWeight = edge.weight === "high";
              return (
                <g key={i}>
                  <line
                    x1={from.x} y1={from.y} x2={to.x} y2={to.y}
                    stroke={isHighWeight ? "#ef4444" : "#ccc"}
                    strokeWidth={isHighWeight ? 2 : 1}
                    strokeDasharray={isHighWeight ? undefined : "4 4"}
                    opacity={isActive ? (isHighWeight ? 0.8 : 0.5) : 0.1}
                    className="transition-opacity duration-200"
                  />
                  {edge.label && isActive && (
                    <text x={(from.x + to.x) / 2} y={(from.y + to.y) / 2 - 6} textAnchor="middle" className="text-[9px]" fill="#888" style={{ fontFamily: "monospace" }}>
                      {edge.label}
                    </text>
                  )}
                </g>
              );
            })}
            {graphNodes.map((node) => {
              const colors = typeColors[node.type];
              const isActive = !activeNodeIds || activeNodeIds.has(node.id);
              const isSelected = node.id === activeNode;
              const radius = node.type === "company" ? 28 : node.type === "warning" ? 24 : 22;
              return (
                <g
                  key={node.id}
                  className="cursor-pointer transition-opacity duration-200"
                  opacity={isActive ? 1 : 0.15}
                  onClick={() => setSelectedNode(selectedNode === node.id ? null : node.id)}
                  onMouseEnter={() => setHoveredNode(node.id)}
                  onMouseLeave={() => setHoveredNode(null)}
                >
                  {isSelected && (
                    <circle cx={node.x} cy={node.y} r={radius + 6} fill="none" stroke={colors.stroke} strokeWidth={1} opacity={0.3} />
                  )}
                  <circle cx={node.x} cy={node.y} r={radius} fill={colors.fill} stroke={colors.stroke} strokeWidth={2} />
                  {node.label.includes("\n") ? (
                    node.label.split("\n").map((line, li) => (
                      <text key={li} x={node.x} y={node.y + (li - 0.5) * 11} textAnchor="middle" dominantBaseline="central" className="text-[9px] pointer-events-none" fill={colors.text} style={{ fontFamily: "system-ui" }}>
                        {line}
                      </text>
                    ))
                  ) : (
                    <text x={node.x} y={node.y} textAnchor="middle" dominantBaseline="central" className="text-[10px] pointer-events-none" fill={colors.text} style={{ fontFamily: "system-ui", fontWeight: node.type === "company" ? 600 : 400 }}>
                      {node.label}
                    </text>
                  )}
                </g>
              );
            })}
          </svg>
        </div>

        {activeNode && (
          <div className="mt-4 text-xs text-[#888]">
            <strong className="text-[#222]">{graphNodes.find((n) => n.id === activeNode)?.label}</strong>
            {" — "}{activeEdges.length} connection{activeEdges.length !== 1 ? "s" : ""}.
            {activeEdges.filter((e) => e.weight === "high").length > 0 && (
              <span className="text-red-600 ml-1">High-weight links indicate concentrated risk.</span>
            )}
          </div>
        )}

        <p className="text-xs text-[#bbb] mt-3">Source: Annual Reports FY24, DRHP filings, BSE disclosures.</p>
      </div>
    </div>
  );
}
