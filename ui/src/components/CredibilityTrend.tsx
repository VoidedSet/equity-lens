"use client";

import { credibilityTrend, fnbShareTrend } from "@/lib/data";

export function CredibilityTrend() {
  return (
    <section className="max-w-2xl mx-auto px-6 py-12" id="trends">
      <div className="border-t border-[#e2e8f0] mb-10" />

      <h2 className="text-xs tracking-[0.2em] uppercase text-[#94a3b8] font-medium mb-4">
        Patterns
      </h2>

      {/* Credibility decline — written as narrative */}
      <div className="mb-10">
        <h3 className="text-[15px] font-semibold text-[#0f172a] mb-3">Credibility is declining</h3>
        <p className="text-[15px] text-[#334155] leading-[1.85] mb-4">
          Management&apos;s guidance accuracy has eroded steadily over four years. The credibility
          score fell from <strong className="text-[#0f172a]">74</strong> in FY21 to{" "}
          <strong className="text-red-600">58</strong> in FY24 — a 16-point decline driven by
          repeated over-guidance on RevPAR and room additions.
        </p>

        {/* Simple inline data table — not a chart */}
        <div className="bg-white rounded-lg border border-[#e2e8f0] overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#f1f5f9]">
                <th className="text-left py-2.5 px-4 text-xs text-[#94a3b8] font-medium uppercase tracking-wider">Period</th>
                {credibilityTrend.map((r) => (
                  <th key={r.period} className="text-right py-2.5 px-4 text-xs text-[#94a3b8] font-medium">{r.period}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="py-2.5 px-4 text-[#334155]">Credibility Score</td>
                {credibilityTrend.map((r, i) => (
                  <td key={r.period} className={`text-right py-2.5 px-4 font-mono font-semibold ${
                    i === credibilityTrend.length - 1 ? "text-red-600" : "text-[#0f172a]"
                  }`}>
                    {r.score}
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* F&B margin compression — written as narrative */}
      <div>
        <h3 className="text-[15px] font-semibold text-[#0f172a] mb-3">F&B mix is compressing margins</h3>
        <p className="text-[15px] text-[#334155] leading-[1.85] mb-4">
          Food &amp; beverage revenue share has risen from{" "}
          <strong className="text-[#0f172a]">28%</strong> (FY21) to{" "}
          <strong className="text-[#0f172a]">36%</strong> (FY24). F&B earns lower margins than
          rooms — so even when RevPAR grows, this compositional shift quietly compresses EBITDA.
          Management guided 35%+ margins but delivered 33.2%.
        </p>

        <div className="bg-white rounded-lg border border-[#e2e8f0] overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#f1f5f9]">
                <th className="text-left py-2.5 px-4 text-xs text-[#94a3b8] font-medium uppercase tracking-wider">Metric</th>
                {fnbShareTrend.map((r) => (
                  <th key={r.period} className="text-right py-2.5 px-4 text-xs text-[#94a3b8] font-medium">{r.period}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-[#f1f5f9]">
                <td className="py-2.5 px-4 text-[#334155]">F&B Revenue Share</td>
                {fnbShareTrend.map((r) => (
                  <td key={r.period} className="text-right py-2.5 px-4 font-mono font-medium text-[#0f172a]">{r.fnbShare}%</td>
                ))}
              </tr>
              <tr>
                <td className="py-2.5 px-4 text-[#334155]">EBITDA Margin</td>
                {fnbShareTrend.map((r) => (
                  <td key={r.period} className="text-right py-2.5 px-4 font-mono font-medium text-[#0f172a]">{r.ebitdaMargin}%</td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
