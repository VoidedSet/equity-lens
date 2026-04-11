"use client";

import { useState } from "react";
import { GuidanceClaim } from "@/lib/data";
import { Citation } from "./Citation";

function ClaimBlock({ claim }: { claim: GuidanceClaim }) {
  const flagColor =
    claim.flag === "BEAT" ? "border-l-emerald-500" :
    claim.flag === "MISS" ? "border-l-red-400" : "border-l-blue-400";

  const flagLabel =
    claim.flag === "BEAT" ? "text-emerald-700 bg-emerald-50" :
    claim.flag === "MISS" ? "text-red-700 bg-red-50" : "text-blue-700 bg-blue-50";

  return (
    <div className={`border-l-[3px] ${flagColor} pl-6 py-1 mb-10`}>
      {/* Claim header — metric + verdict */}
      <div className="flex items-baseline gap-3 mb-3">
        <h4 className="text-[15px] font-semibold text-[#0f172a]">{claim.metric}</h4>
        <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${flagLabel}`}>
          {claim.flag}
        </span>
      </div>

      {/* The quote — what they said */}
      <blockquote className="text-[15px] text-[#334155] italic leading-[1.85] mb-2 border-none pl-0">
        &ldquo;{claim.verbatimQuote}&rdquo;
      </blockquote>
      <p className="text-xs text-[#94a3b8] mb-5">
        — {claim.speaker}, {claim.statementQuarter} &nbsp;
        <Citation source={claim.sourceGuidance} />
      </p>

      {/* The evidence — what actually happened */}
      <div className="text-[15px] text-[#334155] leading-[1.85] mb-2">
        <span className="text-[#94a3b8]">Guided:</span>{" "}
        <strong className="text-[#0f172a]">{claim.guidedValue}</strong>
        <span className="mx-3 text-[#cbd5e1]">&rarr;</span>
        <span className="text-[#94a3b8]">Actual:</span>{" "}
        <strong className="text-[#0f172a]">{claim.actualValue}</strong>
        <span className="mx-3 text-[#cbd5e1]">&rarr;</span>
        <span className="text-[#94a3b8]">Delta:</span>{" "}
        <strong className={
          claim.flag === "BEAT" ? "text-emerald-700" :
          claim.flag === "MISS" ? "text-red-600" : "text-blue-600"
        }>{claim.delta}</strong>
      </div>

      <p className="text-xs text-[#94a3b8] mb-1">
        <Citation source={claim.sourceActual} />
      </p>

      {/* Pattern — if exists */}
      {claim.pattern && (
        <p className="text-sm text-amber-800 bg-amber-50 border border-amber-100 rounded-md px-3 py-2 mt-4 leading-relaxed">
          {claim.pattern}
        </p>
      )}
    </div>
  );
}

export function SaidVsDelivered({ deviations }: { deviations: GuidanceClaim[] }) {
  const [filter, setFilter] = useState<"ALL" | "BEAT" | "MISS" | "IN-LINE">("ALL");

  const filtered = filter === "ALL" ? deviations : deviations.filter(d => d.flag === filter);
  const missCount = deviations.filter(d => d.flag === "MISS").length;
  const beatCount = deviations.filter(d => d.flag === "BEAT").length;
  const inlineCount = deviations.filter(d => d.flag === "IN-LINE").length;
  const hitRate = Math.round(((beatCount + inlineCount) / deviations.length) * 100);

  return (
    <section className="max-w-2xl mx-auto px-6 py-12" id="said-vs-delivered">
      <div className="border-t border-[#e2e8f0] mb-10" />

      <h2 className="text-xs tracking-[0.2em] uppercase text-[#94a3b8] font-medium mb-4">
        Said vs Delivered
      </h2>

      {/* Verdict — one clear sentence */}
      <p className="text-[15px] text-[#334155] leading-[1.85] mb-8">
        Of <strong className="text-[#0f172a]">{deviations.length} tracked guidance claims</strong>,
        management delivered on <strong className="text-[#0f172a]">{beatCount + inlineCount}</strong> and
        missed on <strong className="text-red-600">{missCount}</strong>.
        That&apos;s a <strong className="text-[#0f172a]">{hitRate}% hit rate</strong>.
      </p>

      {/* Minimal filter */}
      <div className="flex items-center gap-2 mb-10">
        {(["ALL", "MISS", "BEAT", "IN-LINE"] as const).map((f) => {
          const count = f === "ALL" ? deviations.length : f === "MISS" ? missCount : f === "BEAT" ? beatCount : inlineCount;
          const active = filter === f;
          return (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1 text-xs font-medium rounded-full transition-all cursor-pointer ${
                active
                  ? "bg-[#0f172a] text-white"
                  : "text-[#94a3b8] hover:text-[#334155]"
              }`}
            >
              {f === "ALL" ? "All" : f === "IN-LINE" ? "In-Line" : f.charAt(0) + f.slice(1).toLowerCase()} ({count})
            </button>
          );
        })}
      </div>

      {/* Claims — editorial blocks */}
      {filtered.map((claim) => (
        <ClaimBlock key={claim.id} claim={claim} />
      ))}
    </section>
  );
}
