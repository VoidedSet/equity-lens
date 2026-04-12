import { Highlight } from "@/components/Highlight";

export function CompanyNarrative({ companyId }: { companyId: string }) {
  if (companyId === "IHCL") {
    return (
      <div className="bg-[#f9f9f9] border border-[#e0e0e0] p-6 rounded-lg mt-6 mb-10 shadow-sm">
        <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded bg-[#222] text-white text-[10px] font-bold uppercase tracking-wider mb-4">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
          The Premium Benchmark
        </div>
        <h3 className="text-lg font-serif font-bold text-[#222] mb-3">The Winning Feature: Said vs Delivered Demo</h3>
        <p className="text-[14px] leading-relaxed text-[#444] mb-4">
          IHCL is our primary test case for management optimism vs reality. Their aggressive &quot;Accelerate 2030&quot; plan is driving multi-brand expansion, but execution trails promises.
        </p>
        <ul className="space-y-3 text-[14px] leading-relaxed text-[#444] mb-0 list-disc pl-5 marker:text-[#ccc]">
          <li>
            <strong>Check 1 (RevPAR):</strong> Guided <Highlight quote="15% RevPAR growth" refName="quarterly_results.json" company="IHCL" citationText="IHCL Q2 FY24 Quarterly Results">15% growth</Highlight>. Actual: <Highlight quote="9.2%" refName="annual_report.json" company="IHCL" citationText="IHCL Annual Report">9.2%</Highlight>. <strong className="text-[#dc2626]">FLAG: MISS</strong> (-5.8pp delta).
          </li>
          <li>
            <strong>Check 2 (Keys):</strong> Guided <Highlight quote="2000" refName="quarterly_results.json" company="IHCL" citationText="IHCL Q1 FY24 Quarterly Results">2,000 keys</Highlight>. Actual: <Highlight quote="1,340" refName="annual_report.json" company="IHCL" citationText="IHCL Annual Report">1,340</Highlight>. <strong className="text-[#dc2626]">FLAG: MISS</strong>.
          </li>
          <li>
            <strong>Check 4 (F&B Trap):</strong> F&B mix hit 36%, driving down overall operating efficiency relative to peers.
          </li>
          <li>
            <strong>Trend:</strong> Credibility score has degraded from 74/100 to 58/100 due to consecutive over-guidance.
          </li>
        </ul>
      </div>
    );
  }

  if (companyId === "CHALET") {
    return (
      <div className="bg-[#f9f9f9] border border-[#e0e0e0] p-6 rounded-lg mt-6 mb-10 shadow-sm">
        <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded bg-[#222] text-white text-[10px] font-bold uppercase tracking-wider mb-4">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="16" height="20" x="4" y="2" rx="2" ry="2"/><path d="M9 22v-4h6v4"/><path d="M8 6h.01"/><path d="M16 6h.01"/><path d="M12 6h.01"/><path d="M12 10h.01"/><path d="M12 14h.01"/><path d="M16 10h.01"/><path d="M16 14h.01"/><path d="M8 10h.01"/><path d="M8 14h.01"/></svg>
          The Urban Business Powerhouse
        </div>
        <h3 className="text-lg font-serif font-bold text-[#222] mb-3">The Narrative Difference</h3>
        <p className="text-[14px] leading-relaxed text-[#444] mb-3">
          Chalet proves how the upcycle plays differently for urban corporate hotels. They have capitalized phenomenally on operating leverage, pushing margins to 43%. 
        </p>
        <p className="text-[14px] leading-relaxed text-[#444] mb-0">
          However, our <strong>Check 6 (Supply Overhang)</strong> flashes <span className="text-[#dc2626] font-semibold">RED</span> here: With 53% of revenue tied to Mumbai, the incoming wave of <Highlight quote="1,800 new 5-star keys" refName="TO-Oct2025.pdf" company="CHALET" citationText="Hotelivate Trends & Opportunities 2025">1,800 new 5-star keys</Highlight> in that city is a massive headwind they are not speaking about in earnings calls.
        </p>
      </div>
    );
  }

  if (companyId === "LEMONTREE") {
    return (
      <div className="bg-[#fefce8] border border-[#fde047] p-6 rounded-lg mt-6 mb-10 shadow-sm">
        <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded bg-[#ca8a04] text-white text-[10px] font-bold uppercase tracking-wider mb-4">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
          The High-Margin Volume Play
        </div>
        <h3 className="text-lg font-serif font-bold text-[#854d0e] mb-3">The Golden Catalyst: The Warburg Split (April 2026)</h3>
        <p className="text-[14px] leading-relaxed text-[#713f12] mb-3">
          The CCI just approved Warburg Pincus taking a 41% stake in Fleur Hotels (Lemon Tree&apos;s subsidiary) with a <Highlight quote="960" refName="announcement.json" company="LEMONTREE" citationText="Screener.in Announcements">₹960 Cr infusion</Highlight>. 12 asset-heavy hotels are being demerged into Fleur.
        </p>
        <ul className="space-y-3 text-[14px] leading-relaxed text-[#713f12] mb-0 list-disc pl-5 marker:text-[#ca8a04]">
          <li>
            <strong>The Result:</strong> Lemon Tree becomes a pure asset-light, high-margin management platform. Fleur becomes the heavy capital owner that will list separately. This split unlocks massive value.
          </li>
        </ul>
      </div>
    );
  }

  return (
    <div className="bg-white border border-[#e0e0e0] border-dashed p-6 text-center rounded-lg mt-6 mb-10 shadow-sm">
      <h3 className="text-[14px] font-medium text-[#888] mb-1">Sector Analysis Narrative not available</h3>
      <p className="text-[12px] text-[#aaa]">
        The intelligence overview report is currently focusing deep-dives on IHCL, Chalet, and Lemon Tree.
      </p>
    </div>
  );
}
