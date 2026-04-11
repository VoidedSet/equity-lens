"use client";

import { ScoreCard } from "@/lib/data";

function DimensionLine({ label, weight, value }: { label: string; weight: string; value: number }) {
  const assessment =
    value >= 80 ? "Strong" : value >= 65 ? "Adequate" : value >= 50 ? "Concerning" : "Weak";
  const color =
    value >= 80 ? "text-emerald-700" : value >= 65 ? "text-[#0f172a]" : value >= 50 ? "text-amber-700" : "text-red-600";

  return (
    <div className="flex items-baseline justify-between py-3 border-b border-[#f1f5f9] last:border-b-0">
      <div>
        <span className="text-[15px] text-[#334155]">{label}</span>
        <span className="text-xs text-[#b0b8c4] ml-2">({weight})</span>
      </div>
      <div className="flex items-baseline gap-3">
        <span className={`text-sm font-medium ${color}`}>{assessment}</span>
        <span className="text-lg font-semibold font-mono text-[#0f172a] w-8 text-right">{value}</span>
      </div>
    </div>
  );
}

export function Scorecard({ scorecard }: { scorecard: ScoreCard }) {
  const compositeLabel =
    scorecard.composite >= 80 ? "Strong" :
    scorecard.composite >= 65 ? "Adequate" :
    scorecard.composite >= 50 ? "Concerning" : "Weak";

  return (
    <section className="max-w-2xl mx-auto px-6 py-12" id="scorecard">
      <div className="border-t border-[#e2e8f0] mb-10" />

      <h2 className="text-xs tracking-[0.2em] uppercase text-[#94a3b8] font-medium mb-4">
        Scorecard
      </h2>

      {/* The verdict — large, clear */}
      <div className="mb-8">
        <div className="flex items-baseline gap-4 mb-2">
          <span className="text-5xl font-serif text-[#0f172a]">{scorecard.composite}</span>
          <span className="text-lg text-[#64748b]">/ 100</span>
        </div>
        <p className="text-[15px] text-[#334155] leading-[1.85]">
          Composite rating: <strong className="text-[#0f172a]">{compositeLabel}</strong>.
          Credibility drags the score — financial quality and market position are strengths,
          but management&apos;s track record of over-promising limits overall confidence.
        </p>
      </div>

      {/* Dimension breakdown — clean list, no charts */}
      <div className="bg-white rounded-lg border border-[#e2e8f0] px-5">
        <DimensionLine label="Credibility" weight="40%" value={scorecard.credibility} />
        <DimensionLine label="Financial Quality" weight="25%" value={scorecard.financialQuality} />
        <DimensionLine label="Industry Position" weight="20%" value={scorecard.industryPosition} />
        <DimensionLine label="Risk Profile" weight="15%" value={scorecard.risk} />
      </div>
    </section>
  );
}
