"use client";

import { Company, KeyMetric } from "@/lib/data";
import { Citation } from "./Citation";

export function CompanyHeader({ company, metrics }: { company: Company; metrics: KeyMetric[] }) {
  const m = (label: string) => metrics.find((x) => x.label === label);

  return (
    <section className="max-w-2xl mx-auto px-6 pt-20 pb-12" id="company-header">
      {/* Publication-style header */}
      <p className="text-[11px] tracking-[0.35em] uppercase text-[#94a3b8] mb-6 font-medium">
        EquityLens AI &mdash; Company Report
      </p>

      <h1 className="text-3xl sm:text-4xl font-serif font-normal text-[#0f172a] leading-snug mb-3">
        {company.name}
      </h1>

      <p className="text-sm text-[#94a3b8] mb-10">
        NSE: {company.ticker} &middot; {company.segment} &middot; {company.strategy}
      </p>

      {/* Thin rule */}
      <div className="border-t border-[#e2e8f0] mb-10" />

      {/* Executive summary — prose, not cards */}
      <h2 className="text-xs tracking-[0.2em] uppercase text-[#94a3b8] font-medium mb-4">
        Executive Summary
      </h2>

      <div className="text-[15px] text-[#334155] leading-[1.85] space-y-4">
        <p>
          {company.name} reported revenue of{" "}
          <strong className="text-[#0f172a]">₹{m("Revenue")?.value} Cr</strong>{" "}
          in FY24, up {m("Revenue")?.change}% year-on-year. The company operates{" "}
          <strong className="text-[#0f172a]">{m("Room Count")?.value} keys</strong>{" "}
          across its {company.brands.join(", ")} brands, with primary revenue
          concentration in {company.keyMarkets.join(", ")}.
        </p>

        <p>
          RevPAR stood at{" "}
          <strong className="text-[#0f172a]">₹{m("RevPAR")?.value}</strong>{" "}
          (+{m("RevPAR")?.change}% YoY), driven by occupancy of{" "}
          <strong className="text-[#0f172a]">{m("Occupancy")?.value}%</strong>{" "}
          and an average daily rate of{" "}
          <strong className="text-[#0f172a]">₹{m("ADR")?.value}</strong>.
          EBITDA margin was{" "}
          <strong className="text-[#0f172a]">{m("EBITDA Margin")?.value}%</strong>{" "}
          — a figure management had guided above 35%.
        </p>

        <p className="text-sm text-[#64748b]">
          <Citation source="AR FY24 | Pages 12, 45, 87, 91" />
        </p>
      </div>
    </section>
  );
}
