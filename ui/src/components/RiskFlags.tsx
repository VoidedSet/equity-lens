"use client";

import { Citation } from "./Citation";

type UIRiskFlag = {
  id: string; category: string; severity: string; description: string;
  verbatimQuote?: string; source: string; period: string;
};

const SEV: Record<string, string> = { critical: "CRITICAL", high: "HIGH", medium: "MEDIUM" };

export function RiskFlags({ risks }: { risks: UIRiskFlag[] }) {
  const critical = risks.filter((r) => r.severity === "critical").length;
  const high = risks.filter((r) => r.severity === "high").length;

  return (
    <div className="ed-section-ruled" id="risk-flags">
      <div className="ed-container">
        <div className="ed-grid">
          <div>
            <p className="kicker mb-2">Editor&apos;s Notes</p>
            <h2 className="font-serif text-3xl lg:text-4xl text-[#222] mb-6 leading-tight">Risk Flags</h2>

            <p className="text-[15px] text-[#333] leading-[1.9] mb-8">
              {risks.length} flags identified from annual reports, transcripts, and filings.
              {critical > 0 && <> <span className="highlight-red">{critical} critical</span>.</>}
              {high > 0 && <> {high} high severity.</>}
            </p>

            {risks.map((risk) => (
              <div key={risk.id} className="border-t border-[#e0e0e0] py-5">
                <div className="flex items-center gap-3 mb-2">
                  <span className="text-[9px] font-bold uppercase tracking-wider text-[#888]">
                    {SEV[risk.severity] || "MEDIUM"}
                  </span>
                  <h4 className="text-[15px] font-bold text-[#222]">{risk.category}</h4>
                </div>
                <p className="text-[14px] text-[#333] leading-[1.85] mb-2">{risk.description}</p>
                {risk.verbatimQuote && (
                  <blockquote className="pull-quote text-[14px] text-left">
                    &ldquo;{risk.verbatimQuote}&rdquo;
                  </blockquote>
                )}
                <div className="flex items-center gap-2 text-[11px] text-[#999]">
                  <Citation source={risk.source} company={risk.id.split("-")[0]} quote={risk.verbatimQuote} />
                  <span>&middot;</span>
                  <span>{risk.period}</span>
                </div>
              </div>
            ))}
          </div>

          <aside>
            <div className="sidebar-card" style={{ position: "sticky", top: "4rem" }}>
              <p className="kicker mb-3">Risk Summary</p>
              <div className="stat-big">{risks.length}</div>
              <p className="stat-label">Total Flags</p>
              <hr className="my-4 border-[#e0e0e0]" />
              {critical > 0 && (
                <div className="flex items-center justify-between py-2">
                  <span className="text-[12px] text-[#888]">Critical</span>
                  <span className="font-serif text-xl font-bold text-red-600">{critical}</span>
                </div>
              )}
              {high > 0 && (
                <div className="flex items-center justify-between py-2">
                  <span className="text-[12px] text-[#888]">High</span>
                  <span className="font-serif text-xl font-bold text-[#222]">{high}</span>
                </div>
              )}
              <div className="flex items-center justify-between py-2">
                <span className="text-[12px] text-[#888]">Medium</span>
                <span className="font-serif text-xl font-bold text-[#222]">{risks.length - critical - high}</span>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}
