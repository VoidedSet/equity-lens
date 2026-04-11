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

        {/* News items */}
        <div className="space-y-0">
          {filtered.slice(0, 20).map((item, idx) => {
            const isExpanded = expanded.has(idx);
            return (
              <div key={idx} className="border-t border-[#e0e0e0] py-4">
                <div className="flex items-center gap-2 mb-1 text-[10px] text-[#999]">
                  <span className="font-semibold uppercase tracking-wider">{item.sentiment}</span>
                  {item.dimension_primary && (
                    <><span>&middot;</span><span>{DIMENSION_LABELS[item.dimension_primary] || item.dimension_primary}</span></>
                  )}
                  {item.company_tags.length > 0 && (
                    <><span>&middot;</span><span>{item.company_tags.join(", ")}</span></>
                  )}
                </div>
                <a href={item.url} target="_blank" rel="noopener noreferrer" className="text-[14px] font-semibold text-[#222] hover:underline leading-snug block mb-1">
                  {item.title}
                </a>
                <div className="flex items-center gap-2 text-[11px] text-[#999]">
                  <span>{item.source}</span><span>&middot;</span><span>{item.published_date}</span>
                </div>
                {isExpanded && item.summary_2line && <p className="text-[13px] text-[#888] leading-relaxed mt-2">{item.summary_2line}</p>}
                <button onClick={() => toggle(idx)} className="text-[11px] text-[#bbb] hover:text-[#222] mt-1 cursor-pointer">
                  {isExpanded ? "Less" : "More"}
                </button>
              </div>
            );
          })}
        </div>

        {filtered.length === 0 && <p className="text-[13px] text-[#999] text-center py-8">No news items for this filter.</p>}
      </div>
    </div>
  );
}
