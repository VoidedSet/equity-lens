"use client";

import { useState } from "react";
import { Citation } from "./Citation";

type UIDeviation = {
  id: string; metric: string; checkType: string; statementQuarter: string;
  targetPeriod: string; guidedValue: string; actualValue: string; delta: string;
  flag: "BEAT" | "MISS" | "IN-LINE"; severity: string; verbatimQuote: string;
  speaker: string; confidenceLanguage: string; sourceGuidance: string;
  sourceActual: string; pattern?: string; crossRef?: string;
};

const confidenceMeta: Record<string, { label: string; color: string; description: string }> = {
  will: { label: "WILL", color: "text-red-600 bg-red-50 border-red-200", description: "Hard commitment" },
  expect: { label: "EXPECT", color: "text-amber-700 bg-amber-50 border-amber-200", description: "Moderate confidence" },
  confident: { label: "CONFIDENT", color: "text-red-700 bg-red-50 border-red-200", description: "Assertive" },
  targeting: { label: "TARGETING", color: "text-blue-700 bg-blue-50 border-blue-200", description: "Aspirational" },
  plan: { label: "PLAN", color: "text-blue-600 bg-blue-50 border-blue-200", description: "Intent, not commitment" },
  hope: { label: "HOPE", color: "text-slate-600 bg-slate-50 border-slate-200", description: "Low conviction" },
};

function ExhibitBlock({ claim, index, allClaims }: { claim: UIDeviation; index: number; allClaims: UIDeviation[] }) {
  const flagColor =
    claim.flag === "BEAT" ? "border-l-emerald-500" :
    claim.flag === "MISS" ? "border-l-red-400" : "border-l-blue-400";

  const flagLabel =
    claim.flag === "BEAT" ? "text-emerald-700 bg-emerald-50" :
    claim.flag === "MISS" ? "text-red-700 bg-red-50" : "text-blue-700 bg-blue-50";

  const conf = confidenceMeta[claim.confidenceLanguage.toLowerCase()] || { label: claim.confidenceLanguage, color: "text-slate-600 bg-slate-50 border-slate-200", description: "Stated" };

  // Get cross-referenced claims
  const crossRefIds = claim.crossRef?.split(",").map((s) => s.trim()) ?? [];
  const crossRefs = crossRefIds
    .map((id) => allClaims.find((c) => c.id === id))
    .filter(Boolean) as UIDeviation[];

  return (
    <div className={`border-l-[3px] ${flagColor} pl-6 py-1 mb-12`} id={`exhibit-${claim.id}`}>
      {/* Exhibit number + metric */}
      <div className="flex items-baseline gap-3 mb-1">
        <span className="text-[11px] font-mono text-[#bbb] uppercase tracking-wider">
          Exhibit {String.fromCharCode(64 + index)}
        </span>
        <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded border ${flagLabel}`}>
          {claim.flag}
        </span>
        {/* Confidence language tag */}
        <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${conf.color}`} title={conf.description}>
          {conf.label}
        </span>
      </div>

      <h4 className="text-lg font-semibold text-[#222] mb-4">{claim.metric}</h4>

      {/* Two-column: What they said | What happened */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
        {/* Left: What they said */}
        <div className="p-4 border-t-2 border-[#222]">
          <p className="text-[10px] tracking-[0.15em] uppercase text-[#999] font-medium mb-2">
            What they said
          </p>
          <blockquote className="text-[14px] text-[#333] italic leading-[1.75] mb-2">
            &ldquo;{claim.verbatimQuote}&rdquo;
          </blockquote>
          <p className="text-[11px] text-[#999]">
            — {claim.speaker}, {claim.statementQuarter}
          </p>
          <div className="mt-2">
            <Citation source={claim.sourceGuidance} quote={claim.verbatimQuote} />
          </div>
        </div>

        {/* Right: What happened */}
        <div className="p-4 border-t border-[#e0e0e0]">
          <p className="text-[10px] tracking-[0.15em] uppercase text-[#999] font-medium mb-2">
            What happened
          </p>
          <div className="space-y-2 text-[14px]">
            <div className="flex justify-between">
              <span className="text-[#999]">Guided</span>
              <span className="font-mono font-semibold text-[#222]">{claim.guidedValue}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[#999]">Actual</span>
              <span className="font-mono font-semibold text-[#222]">{claim.actualValue}</span>
            </div>
            <div className="border-t border-[#eee] pt-2 flex justify-between">
              <span className="text-[#999]">Delta</span>
              <span className={`font-mono font-bold ${
                claim.flag === "BEAT" ? "text-emerald-700" :
                claim.flag === "MISS" ? "text-red-600" : "text-blue-600"
              }`}>{claim.delta}</span>
            </div>
          </div>
          <div className="mt-2">
            <Citation source={claim.sourceActual} quote={claim.verbatimQuote} />
          </div>
        </div>
      </div>

      {/* Pattern warning */}
      {claim.pattern && (
        <p className="text-[13px] text-[#333] border-l-2 border-[#222] pl-3 py-1 mb-3 leading-relaxed">
          <span className="font-semibold">Pattern:</span> {claim.pattern}
        </p>
      )}

      {/* Cross-references */}
      {crossRefs.length > 0 && (
        <div className="text-xs text-[#999]">
          <span className="font-medium">See also:</span>{" "}
          {crossRefs.map((cr, ci) => (
            <span key={cr.id}>
              <a href={`#exhibit-${cr.id}`} className="text-[#222] underline underline-offset-2 hover:text-[#000]">
                Exhibit {String.fromCharCode(64 + allClaims.indexOf(cr) + 1)} ({cr.metric})
              </a>
              {ci < crossRefs.length - 1 && ", "}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export function SaidVsDelivered({ deviations }: { deviations: UIDeviation[] }) {
  const [filter, setFilter] = useState<"ALL" | "BEAT" | "MISS" | "IN-LINE">("ALL");

  const filtered = filter === "ALL" ? deviations : deviations.filter(d => d.flag === filter);
  const missCount = deviations.filter(d => d.flag === "MISS").length;
  const beatCount = deviations.filter(d => d.flag === "BEAT").length;
  const inlineCount = deviations.filter(d => d.flag === "IN-LINE").length;
  const hitRate = Math.round(((beatCount + inlineCount) / deviations.length) * 100);

  // Confidence language stats
  const hardCommits = deviations.filter(d => d.confidenceLanguage === "will" || d.confidenceLanguage === "confident").length;
  const softLanguage = deviations.filter(d => d.confidenceLanguage === "plan" || d.confidenceLanguage === "hope" || d.confidenceLanguage === "targeting").length;

  return (
    <div className="ed-section-ruled" id="said-vs-delivered">
      <div className="ed-container">
        <div className="ed-grid">
          <div>
            <p className="kicker mb-2">Said vs Delivered</p>
            <h2 className="font-serif text-3xl lg:text-4xl text-[#222] mb-6 leading-tight">Guidance Tracker</h2>

            <p className="text-[15px] text-[#333] leading-[1.9] mb-4">
              Of <span className="highlight">{deviations.length} tracked guidance claims</span>,
              management missed on <span className="highlight-red">{missCount}</span>,
              delivered on <span className="highlight-green">{beatCount}</span>,
              and came in-line on <strong>{inlineCount}</strong>.
              That&apos;s a <span className={hitRate >= 70 ? "highlight-green" : "highlight-red"}>{hitRate}% hit rate</span>.
            </p>

            <p className="text-[14px] text-[#888] leading-[1.85] mb-8">
              <strong className="text-[#333]">Language analysis:</strong>{" "}
              {hardCommits} claims used hard commitment language (&ldquo;will&rdquo;, &ldquo;confident&rdquo;) —
              of those, most were misses. When management uses definitive language, be skeptical.
              {softLanguage > 0 && ` ${softLanguage} claims used softer language ("plan", "targeting"), signaling lower internal conviction.`}
            </p>

            {/* Filter */}
            <div className="flex items-center gap-2 mb-10">
              {(["ALL", "MISS", "BEAT", "IN-LINE"] as const).map((f) => {
                const count = f === "ALL" ? deviations.length : f === "MISS" ? missCount : f === "BEAT" ? beatCount : inlineCount;
                const active = filter === f;
                return (
                  <button
                    key={f}
                    onClick={() => setFilter(f)}
                    className={`px-3 py-1.5 text-[11px] font-semibold tracking-wider uppercase transition-all cursor-pointer ${
                      active
                        ? "border-b-2 border-[#222] text-[#222]"
                        : "text-[#999] hover:text-[#222]"
                    }`}
                  >
                    {f === "ALL" ? "All" : f === "IN-LINE" ? "In-Line" : f.charAt(0) + f.slice(1).toLowerCase()} ({count})
                  </button>
                );
              })}
            </div>

            {filtered.map((claim, i) => (
              <ExhibitBlock key={claim.id} claim={claim} index={i + 1} allClaims={deviations} />
            ))}
          </div>

          <aside>
            <div className="sidebar-card" style={{ position: "sticky", top: "4rem" }}>
              <p className="kicker mb-4">Verdict</p>
              <div className="stat-big">{hitRate}%</div>
              <p className="stat-label">Hit Rate</p>
              <hr className="my-4 border-[#e0e0e0]" />
              <div className="grid grid-cols-3 gap-3 text-center">
                <div>
                  <p className="font-serif text-2xl font-bold text-red-600">{missCount}</p>
                  <p className="text-[10px] uppercase tracking-wider text-[#999] mt-1">Missed</p>
                </div>
                <div>
                  <p className="font-serif text-2xl font-bold text-green-600">{beatCount}</p>
                  <p className="text-[10px] uppercase tracking-wider text-[#999] mt-1">Beat</p>
                </div>
                <div>
                  <p className="font-serif text-2xl font-bold text-[#222]">{inlineCount}</p>
                  <p className="text-[10px] uppercase tracking-wider text-[#999] mt-1">In-Line</p>
                </div>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}
