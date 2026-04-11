"use client";

import { Citation } from "./Citation";

type UICompany = { id: string; name: string; ticker: string; segment: string; strategy: string; brands: string[]; keyMarkets: string[] };
type UIKeyMetric = { label: string; value: string; unit: string; change: number | null; period: string; source: string };

export function CompanyHeader({ company, metrics }: { company: UICompany; metrics: UIKeyMetric[] }) {
  const m = (label: string) => metrics.find((x) => x.label === label);
  const rev = m("Revenue");
  const op = m("Operating Profit");
  const opm = m("OPM");
  const np = m("Net Profit");
  const eps = m("EPS");

  const allMetrics = [rev, op, opm, np, eps].filter(Boolean);

  return (
    <div className="ed-section" style={{ paddingTop: "3rem" }}>
      <div className="ed-container">
        {/* Top rule + meta */}
        <div className="flex items-center justify-between pb-3 mb-8 border-b border-[#e0e0e0]">
          <span className="kicker">Company Report &bull; {rev?.period ?? "FY24"}</span>
          <span className="kicker">NSE: {company.ticker}</span>
        </div>

        {/* BIG company name */}
        <h1 className="font-serif text-6xl sm:text-7xl lg:text-[6rem] font-bold leading-[0.92] tracking-tight text-[#222] mb-3">
          {company.name}
        </h1>
        <p className="text-[15px] text-[#888] leading-relaxed mb-6 max-w-xl">
          {company.segment} &mdash; {company.strategy}
        </p>

        {/* Key metrics — horizontal strip */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-6 py-5 border-t-2 border-b border-[#222] mb-10">
          {allMetrics.map((metric) => (
            <div key={metric!.label}>
              <p className="text-[10px] tracking-[0.15em] uppercase text-[#999] font-medium mb-1">{metric!.label}</p>
              <p className="font-serif text-2xl font-bold text-[#222]">
                {metric!.unit === "₹ Cr" && "₹"}{metric!.value}
                <span className="text-[13px] font-normal text-[#888] ml-1">
                  {metric!.unit === "₹ Cr" ? "Cr" : metric!.unit === "%" ? "%" : metric!.unit}
                </span>
              </p>
              {metric!.change != null && (
                <p className={`text-[11px] font-semibold mt-0.5 ${metric!.change > 0 ? "text-green-600" : metric!.change < 0 ? "text-red-600" : "text-[#888]"}`}>
                  {metric!.change > 0 ? "+" : ""}{metric!.change}% YoY
                </p>
              )}
            </div>
          ))}
        </div>

        {/* Visual pull quote */}
        <div className="max-w-3xl mx-auto my-12 py-8 border-t border-b border-[#e0e0e0]">
          <p className="text-center text-2xl font-serif leading-relaxed text-[#222]">
            {rev?.change != null && rev.change > 0
              ? `Revenue up ${rev.change}% YoY. `
              : rev?.change != null && rev.change < 0
              ? `Revenue down ${Math.abs(rev.change)}% YoY. `
              : ""}
            {opm && Number(opm.value) >= 20
              ? `Operating margin at ${opm.value}% signals pricing power.`
              : opm && Number(opm.value) >= 15
              ? `Operating margin at ${opm.value}% — room for expansion.`
              : "Margin compression requires attention."}
          </p>
        </div>

        {/* Brand portfolio */}
        <div className="grid grid-cols-2 gap-8 max-w-4xl mx-auto">
          <div>
            <p className="text-[10px] tracking-[0.15em] uppercase text-[#999] font-medium mb-2">Brand Portfolio</p>
            <p className="text-[14px] text-[#333] leading-relaxed">{company.brands.join(" • ")}</p>
          </div>
          <div>
            <p className="text-[10px] tracking-[0.15em] uppercase text-[#999] font-medium mb-2">Key Markets</p>
            <p className="text-[14px] text-[#333] leading-relaxed">{company.keyMarkets.join(" • ")}</p>
          </div>
        </div>

        <p className="mt-4 text-[12px] text-[#aaa]">
          <Citation source={rev?.source || "Screener.in"} company={company.id} />
        </p>
      </div>
    </div>
  );
}
