"use client";

type Ranking = { companyId: string; name: string; composite: number; segment: string };
type CompareRow = Record<string, string>;
type CompanyName = { id: string; name: string };

export function CompanyCompare({
  rankings, rows, companyIds, companyNames,
}: {
  rankings: Ranking[]; rows: CompareRow[]; companyIds: string[]; companyNames: CompanyName[];
}) {
  const sorted = [...rankings].sort((a, b) => b.composite - a.composite);
  const nameOf = (id: string) => companyNames.find((c) => c.id === id)?.name || id;

  return (
    <div className="ed-section-ruled" id="compare">
      <div className="ed-container">
        <p className="kicker mb-2">Peer Comparison</p>
        <h2 className="font-serif text-3xl lg:text-4xl text-[#222] mb-6 leading-tight">Industry Benchmarks</h2>

        <p className="text-[15px] text-[#333] leading-[1.9] mb-10 max-w-3xl">
          Five Indian hotel companies in focus. Financial metrics sourced from Screener.in,
          scorecards computed from guidance accuracy. Rankings based on composite scores.
        </p>

        {/* Ranking strip */}
        <div className="grid grid-cols-5 gap-0 border-t-2 border-[#222] mb-12">
          {sorted.map((sc, i) => (
            <div key={sc.companyId} className="border-r border-[#e0e0e0] last:border-r-0 py-4 pr-4">
              <span className="text-[10px] font-mono text-[#bbb] block mb-1">#{i + 1}</span>
              <span className="font-serif text-2xl font-bold text-[#222] block mb-1">{sc.composite}</span>
              <span className="text-[12px] font-medium text-[#888]">{sc.name}</span>
            </div>
          ))}
        </div>

        {/* Full comparison table */}
        <h3 className="font-serif text-xl text-[#222] mb-2">Key Metrics (Latest FY)</h3>
        <p className="text-[12px] text-[#999] mb-4">Source: Screener.in financials</p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-t-2 border-b border-[#222]">
            <thead>
              <tr className="border-b border-[#e0e0e0]">
                <th className="text-left py-3 pr-4 text-[10px] text-[#999] font-semibold uppercase tracking-[0.15em]">Metric</th>
                {companyIds.map((id) => (
                  <th key={id} className="text-right py-3 px-3 text-[10px] text-[#999] font-semibold uppercase tracking-wider">{nameOf(id).split(" ")[0]}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.metric} className="border-b border-[#eee] last:border-b-0">
                  <td className="py-2.5 pr-4 text-[#333] font-medium">
                    {row.metric} <span className="text-[#bbb] text-xs ml-1">({row.unit})</span>
                  </td>
                  {companyIds.map((id) => (
                    <td key={id} className="text-right py-2.5 px-3 font-mono text-[#222]">{row[id] || "—"}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
