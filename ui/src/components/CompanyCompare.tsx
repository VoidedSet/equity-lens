"use client";

import { companyCompare, revparTrend, allScorecards, companies } from "@/lib/data";

export function CompanyCompare() {
  const sorted = [...allScorecards].sort((a, b) => b.composite - a.composite);

  return (
    <section className="max-w-2xl mx-auto px-6 py-12" id="compare">
      <div className="border-t border-[#e2e8f0] mb-10" />

      <h2 className="text-xs tracking-[0.2em] uppercase text-[#94a3b8] font-medium mb-4">
        Peer Comparison
      </h2>

      {/* Narrative intro */}
      <p className="text-[15px] text-[#334155] leading-[1.85] mb-8">
        Five Indian hotel companies rode the same post-COVID upcycle. But the same RevPAR
        tailwind produced very different credibility outcomes. EIH (Oberoi) leads with a composite
        score of <strong className="text-[#0f172a]">76</strong> — they guide conservatively and
        deliver. IHCL&apos;s superior market position (<strong className="text-[#0f172a]">88</strong>)
        is offset by weak credibility (<strong className="text-red-600">58</strong>).
      </p>

      {/* Ranking — editorial list */}
      <div className="mb-10">
        <h3 className="text-[15px] font-semibold text-[#0f172a] mb-4">Composite Ranking</h3>
        <div className="bg-white rounded-lg border border-[#e2e8f0] overflow-hidden">
          {sorted.map((sc, i) => {
            const c = companies.find((x) => x.id === sc.companyId);
            return (
              <div
                key={sc.companyId}
                className="flex items-baseline justify-between px-5 py-3 border-b border-[#f1f5f9] last:border-b-0"
              >
                <div className="flex items-baseline gap-3">
                  <span className="text-sm text-[#b0b8c4] font-mono w-4">{i + 1}</span>
                  <span className="text-[15px] text-[#0f172a] font-medium">{c?.name ?? sc.companyId}</span>
                  <span className="text-xs text-[#94a3b8]">{c?.segment}</span>
                </div>
                <span className="text-lg font-semibold font-mono text-[#0f172a]">{sc.composite}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* RevPAR trajectory — clean table */}
      <div className="mb-10">
        <h3 className="text-[15px] font-semibold text-[#0f172a] mb-2">RevPAR Trajectory</h3>
        <p className="text-sm text-[#64748b] mb-4">
          Same upcycle, different unit economics. Luxury (EIH, IHCL) vs Economy (Lemon Tree).
        </p>
        <div className="bg-white rounded-lg border border-[#e2e8f0] overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#f1f5f9]">
                <th className="text-left py-2.5 px-4 text-xs text-[#94a3b8] font-medium uppercase tracking-wider">Company</th>
                {revparTrend.map((r) => (
                  <th key={r.period} className="text-right py-2.5 px-4 text-xs text-[#94a3b8] font-medium">{r.period}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(["IHCL", "EIH", "ITCHOTELS", "CHALET", "LEMONTREE"] as const).map((id) => (
                <tr key={id} className="border-b border-[#f1f5f9] last:border-b-0">
                  <td className="py-2.5 px-4 text-[#334155] font-medium">{id}</td>
                  {revparTrend.map((r) => (
                    <td key={r.period} className="text-right py-2.5 px-4 font-mono text-[#0f172a]">
                      ₹{(r[id] as number).toLocaleString()}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Full comparison table */}
      <div>
        <h3 className="text-[15px] font-semibold text-[#0f172a] mb-2">Key Metrics (FY24)</h3>
        <div className="bg-white rounded-lg border border-[#e2e8f0] overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#f1f5f9]">
                <th className="text-left py-2.5 px-4 text-xs text-[#94a3b8] font-medium uppercase tracking-wider">Metric</th>
                <th className="text-right py-2.5 px-4 text-xs text-[#94a3b8] font-medium">IHCL</th>
                <th className="text-right py-2.5 px-4 text-xs text-[#94a3b8] font-medium">Chalet</th>
                <th className="text-right py-2.5 px-4 text-xs text-[#94a3b8] font-medium">Lemon Tree</th>
                <th className="text-right py-2.5 px-4 text-xs text-[#94a3b8] font-medium">EIH</th>
                <th className="text-right py-2.5 px-4 text-xs text-[#94a3b8] font-medium">ITC</th>
              </tr>
            </thead>
            <tbody>
              {companyCompare.map((row) => (
                <tr key={row.metric} className="border-b border-[#f1f5f9] last:border-b-0">
                  <td className="py-2.5 px-4 text-[#334155]">
                    {row.metric} <span className="text-[#b0b8c4] text-xs">({row.unit})</span>
                  </td>
                  <td className="text-right py-2.5 px-4 font-mono text-[#0f172a] font-medium">{row.ihcl}</td>
                  <td className="text-right py-2.5 px-4 font-mono text-[#0f172a]">{row.chalet}</td>
                  <td className="text-right py-2.5 px-4 font-mono text-[#0f172a]">{row.lemonTree}</td>
                  <td className="text-right py-2.5 px-4 font-mono text-[#0f172a]">{row.eih}</td>
                  <td className="text-right py-2.5 px-4 font-mono text-[#0f172a]">{row.itcHotels}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
