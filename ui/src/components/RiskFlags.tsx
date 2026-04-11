"use client";

import { RiskFlag } from "@/lib/data";
import { Citation } from "./Citation";

export function RiskFlags({ risks }: { risks: RiskFlag[] }) {
  return (
    <section className="max-w-2xl mx-auto px-6 py-12" id="risk-flags">
      <div className="border-t border-[#e2e8f0] mb-10" />

      <h2 className="text-xs tracking-[0.2em] uppercase text-[#94a3b8] font-medium mb-4">
        Risk Flags
      </h2>

      <p className="text-[15px] text-[#334155] leading-[1.85] mb-8">
        {risks.length} flags identified from annual reports, earnings transcripts, and competitive filings. 
        Sorted by severity.
      </p>

      {risks.map((risk, i) => {
        const severityStyle =
          risk.severity === "critical" ? "border-l-red-500" :
          risk.severity === "high" ? "border-l-orange-400" : "border-l-amber-400";

        const severityLabel =
          risk.severity === "critical" ? "text-red-700 bg-red-50" :
          risk.severity === "high" ? "text-orange-700 bg-orange-50" : "text-amber-700 bg-amber-50";

        return (
          <div key={risk.id} className={`border-l-[3px] ${severityStyle} pl-6 mb-8`}>
            <div className="flex items-baseline gap-3 mb-2">
              <h4 className="text-[15px] font-semibold text-[#0f172a]">{risk.category}</h4>
              <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${severityLabel}`}>
                {risk.severity}
              </span>
            </div>

            <p className="text-[15px] text-[#334155] leading-[1.85] mb-2">
              {risk.description}
            </p>

            {risk.verbatimQuote && (
              <blockquote className="text-sm text-[#64748b] italic leading-relaxed mb-2 pl-0 border-none">
                &ldquo;{risk.verbatimQuote}&rdquo;
              </blockquote>
            )}

            <p className="text-xs text-[#94a3b8]">
              <Citation source={risk.source} />
              <span className="ml-2">{risk.period}</span>
            </p>
          </div>
        );
      })}
    </section>
  );
}
