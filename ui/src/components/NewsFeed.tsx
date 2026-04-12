"use client";

import { useState } from "react";

type NewsItem = {
  title: string;
  url: string;
  source: string;
  published_date: string;
  summary_2line: string;
  company_tags: string[];
  dimension_primary: string;
  sentiment: string;
  market_scope: string;
  relevance_score: number;
};

type NewsFeedProps = {
  items: NewsItem[];
  digestDate: string;
};

const SENTIMENT_COLORS: Record<string, { bg: string; text: string; dot: string }> = {
  Positive: { bg: "bg-emerald-50", text: "text-emerald-700", dot: "bg-emerald-500" },
  Negative: { bg: "bg-red-50", text: "text-red-700", dot: "bg-red-500" },
  Watch: { bg: "bg-amber-50", text: "text-amber-700", dot: "bg-amber-500" },
  Neutral: { bg: "bg-slate-50", text: "text-slate-600", dot: "bg-slate-400" },
};

const DIMENSION_LABELS: Record<string, string> = {
  check_1_revpar_guidance: "RevPAR & Guidance",
  check_2_room_additions: "Room Additions",
  check_3_occupancy_vs_adr: "Occupancy vs ADR",
  check_4_fnb_mix_margin: "F&B Mix & Margin",
  check_5_debt_coverage: "Debt & Coverage",
  check_6_supply_overhang: "Supply Overhang",
};

const SCOPE_LABELS: Record<string, string> = {
  company: "Company",
  sector: "Sector",
  global: "Global",
};

export function NewsFeed({ items, digestDate }: NewsFeedProps) {
  const [filter, setFilter] = useState<"all" | "company" | "sector" | "global">("all");
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  const filtered = filter === "all" ? items : items.filter((i) => i.market_scope === filter);
  const sentimentCounts = {
    Positive: items.filter((i) => i.sentiment === "Positive").length,
    Negative: items.filter((i) => i.sentiment === "Negative").length,
    Watch: items.filter((i) => i.sentiment === "Watch").length,
    Neutral: items.filter((i) => i.sentiment === "Neutral").length,
  };

  const toggle = (idx: number) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  return (
    <div className="ed-section-ruled" id="news">
      <div className="ed-container">
        <div className="flex items-start justify-between mb-6">
          <div>
            <p className="kicker mb-2">Wire Service</p>
            <h2 className="font-serif text-3xl lg:text-4xl text-[#222] leading-tight">News Intelligence</h2>
          </div>
          <span className="text-[11px] text-[#bbb] mt-2">{digestDate}</span>
        </div>

        <p className="text-[15px] text-[#333] leading-[1.9] mb-6 max-w-3xl">
          Automated daily digest from Google Alerts, RSS feeds, and news APIs.
          Each item tagged to a PRD check dimension and scored for materiality.
        </p>

        {/* Sentiment counts */}
        <div className="flex gap-4 mb-6 text-[12px]">
          {Object.entries(sentimentCounts).map(([sentiment, count]) => {
            if (count === 0) return null;
            return (
              <span key={sentiment} className="text-[#888]">
                <strong className="text-[#222]">{count}</strong> {sentiment}
              </span>
            );
          })}
        </div>

        {/* Filter tabs */}
        <div className="flex gap-1 mb-8">
          {(["all", "company", "sector", "global"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setFilter(tab)}
              className={`px-3 py-1.5 text-[11px] font-semibold tracking-wider uppercase transition-all cursor-pointer ${
                filter === tab ? "border-b-2 border-[#222] text-[#222]" : "text-[#999] hover:text-[#222]"
              }`}
            >
              {tab === "all" ? `All (${items.length})` : `${SCOPE_LABELS[tab]} (${items.filter((i) => i.market_scope === tab).length})`}
            </button>
          ))}
        </div>

        {/* ── Lead story ── */}
        {filtered.length > 0 && (() => {
          const lead = filtered[0];
          const sc = SENTIMENT_COLORS[lead.sentiment] || SENTIMENT_COLORS.Neutral;
          return (
            <div className="border-t-2 border-[#222] pt-5 mb-8">
              <div className="ed-grid">
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`inline-block w-2 h-2 rounded-full ${sc.dot}`} />
                    <span className="kicker">{DIMENSION_LABELS[lead.dimension_primary] || lead.dimension_primary}</span>
                    {lead.company_tags.length > 0 && (
                      <span className="kicker text-[#bbb]">· {lead.company_tags.join(", ")}</span>
                    )}
                  </div>
                  <a href={lead.url} target="_blank" rel="noopener noreferrer"
                    className="font-serif text-2xl font-bold text-[#222] leading-snug hover:underline underline-offset-4 decoration-1 block mb-3">
                    {lead.title}
                  </a>
                  {lead.summary_2line && (
                    <p className="text-[14px] text-[#555] leading-[1.85] mb-3">{lead.summary_2line}</p>
                  )}
                  <span className="text-[11px] text-[#bbb]">{lead.source} &middot; {lead.published_date}</span>
                </div>
                <aside>
                  <div className="sidebar-card">
                    <p className="kicker mb-3">Signal Breakdown</p>
                    <div className="space-y-2">
                      {(["Positive","Negative","Watch","Neutral"] as const).map((s) => {
                        const n = sentimentCounts[s];
                        if (!n) return null;
                        const sc2 = SENTIMENT_COLORS[s];
                        return (
                          <div key={s} className="flex items-center justify-between text-[12px]">
                            <span className={`flex items-center gap-1.5 ${sc2.text}`}>
                              <span className={`w-1.5 h-1.5 rounded-full ${sc2.dot}`} />
                              {s}
                            </span>
                            <span className="font-mono font-semibold text-[#222]">{n}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </aside>
              </div>
            </div>
          );
        })()}

        {/* ── Column grid (remaining items) ── */}
        {filtered.length > 1 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-0 border-t border-[#e0e0e0]">
            {filtered.slice(1, 19).map((item, idx) => {
              const isExpanded = expanded.has(idx + 1);
              const sc = SENTIMENT_COLORS[item.sentiment] || SENTIMENT_COLORS.Neutral;
              return (
                <div key={idx}
                  className="py-4 pr-5 border-b border-[#f0f0f0] lg:border-r lg:last-of-type:border-r-0 [&:nth-child(3n)]:border-r-0">
                  <div className="flex items-center gap-1.5 mb-1.5">
                    <span className={`inline-block w-1.5 h-1.5 rounded-full shrink-0 ${sc.dot}`} />
                    <span className="kicker truncate">{DIMENSION_LABELS[item.dimension_primary] || item.dimension_primary}</span>
                  </div>
                  <a href={item.url} target="_blank" rel="noopener noreferrer"
                    className="text-[13px] font-semibold text-[#222] hover:underline underline-offset-2 leading-snug block mb-1.5">
                    {item.title}
                  </a>
                  {isExpanded && item.summary_2line && (
                    <p className="text-[12px] text-[#666] leading-relaxed mb-1.5">{item.summary_2line}</p>
                  )}
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-[#bbb]">{item.source} &middot; {item.published_date}</span>
                    {item.summary_2line && (
                      <button onClick={() => toggle(idx + 1)}
                        className="text-[10px] text-[#bbb] hover:text-[#555] cursor-pointer shrink-0 ml-2">
                        {isExpanded ? "▲" : "▼"}
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {filtered.length === 0 && <p className="text-[13px] text-[#999] text-center py-8">No news items for this filter.</p>}
      </div>
    </div>
  );
}
