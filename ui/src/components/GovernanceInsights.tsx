"use client";

import { Citation } from "./Citation";

/* ── Static data extracted from governance/hotel_sector_analysis.md ── */
const SECTOR_METRICS = [
  { company: "Lemon Tree", revenue: "₹1,286 Cr", opm: "49%", opmFy22: "30%", revpar: "~₹2,800", story: "Volume-driven economy play maximising high fixed-cost leverage." },
  { company: "Chalet",     revenue: "₹1,718 Cr", opm: "43%", opmFy22: "19%", revpar: "~₹6,200", story: "Urban business hubs pushing ADRs — flow-through to margins is massive." },
  { company: "IHCL",       revenue: "₹8,335 Cr", opm: "33%", opmFy22: "13%", revpar: "~₹8,500", story: "Huge revenue leap, but OPM trails peers. Rising F&B mix is the silent drag." },
  { company: "EIH",        revenue: "₹2,743 Cr", opm: "37%", opmFy22: "-3%", revpar: "~₹9,100", story: "Recovered from deep COVID losses to stable premium margins." },
  { company: "Juniper",    revenue: "₹944 Cr",   opm: "36%", opmFy22: "22%", revpar: "~₹4,400", story: "Solid margins, but slight recent compression from 41% in FY23." },
];

const CORE_CHECKS = [
  {
    id: 1, label: "RevPAR Guidance vs Actual",
    what: "Did they hit aggressive RevPAR targets?",
    finding: "MISS", findingColor: "text-red-600",
    detail: "IHCL missed RevPAR guidance three quarters running. Guided 15% growth, actual 9.2%.",
  },
  {
    id: 2, label: "New Room Additions",
    what: "Do they actually open the keys they promised?",
    finding: "MISS", findingColor: "text-red-600",
    detail: "IHCL guided 2,000 keys by FY26, delivered 1,340. Execution risk is structural.",
  },
  {
    id: 3, label: "Occupancy vs ADR",
    what: "Is growth pricing-led or volume-led?",
    finding: "MISMATCH", findingColor: "text-amber-600",
    detail: "Premium leaders claim ADR-led growth. Data shows occupancy doing the heavy lifting.",
  },
  {
    id: 4, label: "F&B Margin Trap",
    what: "Is low-margin F&B cannibalising EBITDA?",
    finding: "HIGH RISK", findingColor: "text-red-600",
    detail: "IHCL's F&B share grew from 28% to 36%. Lower margins than rooms erode RevPAR gains.",
  },
  {
    id: 5, label: "Debt & Interest Coverage",
    what: "EBITDA / Interest — danger if < 2×",
    finding: "WATCH", findingColor: "text-amber-600",
    detail: "Chalet has ₹2,600 Cr net debt at 8.4%. Highly leveraged for a single operator.",
  },
  {
    id: 6, label: "Supply Overhang",
    what: "Is new competitor supply flooding a core city?",
    finding: "CRITICAL", findingColor: "text-red-700",
    detail: "Mumbai: 53% of Chalet revenue, 32% of IHCL. 1,800 new luxury keys under construction there.",
  },
];

const INVESTMENT_OPPORTUNITIES = [
  {
    title: "The Asset-Light Pivot",
    body: "Lemon Tree is the template. Moving to management contracts and franchises minimises capital risk and drives Return on Equity through the roof.",
  },
  {
    title: "Economy Segment Scale",
    body: "Mid-market/economy penetration in India is under 15% of branded inventory. Converting unbranded local hotels to Ginger or Red Fox flags is the highest volume opportunity.",
  },
  {
    title: "Exploiting the Tier 1 Squeeze",
    body: "Real ADR growth (+8.3%) remains trapped in Tier 1 cities where fresh supply is only trickling in (3.4% growth). Assets holding Tier 1 fortresses benefit disproportionately.",
  },
];

const INVESTOR_RISKS = [
  {
    title: "The 1,00,000 Room Avalanche",
    body: "Over the next five years, supply will surge 58%. If MICE and domestic tourism demand falters, occupancy drops below the 60% operating leverage threshold, instantly crushing 40%+ EBITDA margins.",
  },
  {
    title: "The F&B Margin Illusion",
    body: "Look past RevPAR. If a hotel's F&B revenue share balloons beyond 30–35%, the cost required to generate that revenue will quietly erode bottom-line profits.",
  },
  {
    title: "The Micro-Market Supply Threat (Check #6)",
    body: "Ignore national averages. If your company makes 40% of its cash in Mumbai, and Mumbai gets 1,800 new rooms, your RevPAR is dead regardless of India's GDP. Only DRHP cross-checking reveals this.",
  },
];

type Props = { companyId?: string };

export function GovernanceInsights({ companyId }: Props) {
  return (
    <section className="ed-section-ruled" id="governance">
      <div className="ed-container">

        {/* Header */}
        <p className="kicker mb-2">Sector Intelligence</p>
        <h2 className="font-serif text-3xl lg:text-4xl text-[#222] leading-tight mb-6">
          The Six Checks & Sector Reality
        </h2>

        {/* Lead paragraph */}
        <div className="ed-two-col mb-10">
          <p className="text-[15px] text-[#333] leading-[1.9] text-justify mb-0 drop-cap">
            India's hotel market is heading toward <strong>$27–28 billion by 2026</strong>. Nationwide RevPAR
            jumped 5.7% and for the first time in over a decade, the branded hotel ADR crossed the{" "}
            <strong>US$100 threshold</strong>. But blended averages lie. The gap between frontrunners and
            the midfield is widening — top-4 urban markets carrying ADR growth of +8.3%, while
            Tier 2 &amp; 3 cities see only modest +3.2% gains because supply is growing too fast
            (14.8% growth vs Tier 1's 3.4%). For the first time, India's proposed pipeline crossed{" "}
            <span className="highlight">1,00,000 rooms</span> — a 58% surge planned over five years.
            The operating leverage story that rewarded investors over the past three years is now
            entering its most fragile phase.
          </p>
          <p className="text-[15px] text-[#333] leading-[1.9] text-justify mb-0">
            Our system runs <strong>six strict checks</strong> against every management claim. Each check
            is programmatically enforced against filed data — annual reports, investor presentations,
            earnings transcripts, and DRHP filings. The following table summarises what we found at
            the sector level. Individual company reports show the same checks applied to verbatim
            management quotes with source citations.{" "}
            <Citation source="hotel_companies_governance.pdf" company={companyId} quote="governance analysis source" />
          </p>
        </div>

        {/* Core Checks table */}
        <div className="mb-12">
          <p className="kicker mb-4">The 6 Core Checks — Sector-Wide Findings</p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-t-2 border-[#222]">
              <thead>
                <tr className="border-b border-[#e0e0e0]">
                  <th className="text-left py-2.5 pr-4 text-[10px] uppercase tracking-wider text-[#999] font-semibold w-6">#</th>
                  <th className="text-left py-2.5 pr-6 text-[10px] uppercase tracking-wider text-[#999] font-semibold">Check</th>
                  <th className="text-left py-2.5 pr-6 text-[10px] uppercase tracking-wider text-[#999] font-semibold hidden sm:table-cell">What We Look For</th>
                  <th className="text-left py-2.5 pr-4 text-[10px] uppercase tracking-wider text-[#999] font-semibold">Result</th>
                  <th className="text-left py-2.5 text-[10px] uppercase tracking-wider text-[#999] font-semibold hidden md:table-cell">Sector Finding</th>
                </tr>
              </thead>
              <tbody>
                {CORE_CHECKS.map((c) => (
                  <tr key={c.id} className="border-b border-[#f0f0f0] hover:bg-[#fafafa] transition-colors">
                    <td className="py-3 pr-4 text-[12px] font-mono text-[#bbb]">{c.id}</td>
                    <td className="py-3 pr-6 text-[13px] font-semibold text-[#222]">{c.label}</td>
                    <td className="py-3 pr-6 text-[12px] text-[#666] hidden sm:table-cell">{c.what}</td>
                    <td className="py-3 pr-4">
                      <span className={`text-[11px] font-bold uppercase tracking-wider ${c.findingColor}`}>
                        {c.finding}
                      </span>
                    </td>
                    <td className="py-3 text-[12px] text-[#555] leading-relaxed hidden md:table-cell">{c.detail}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Revenue & margin table */}
        <div className="mb-12">
          <p className="kicker mb-4">Revenue &amp; Operating Margin — FY22 to FY25</p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-t-2 border-[#222]">
              <thead>
                <tr className="border-b border-[#e0e0e0]">
                  {["Company", "FY25 Revenue", "Current OPM", "OPM (FY22)", "RevPAR", "The Leverage Story"].map((h) => (
                    <th key={h} className="text-left py-2.5 pr-6 text-[10px] uppercase tracking-wider text-[#999] font-semibold">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {SECTOR_METRICS.map((r) => {
                  const isActive = !companyId || r.company.toUpperCase().includes(companyId);
                  return (
                    <tr
                      key={r.company}
                      className={`border-b border-[#f0f0f0] transition-colors ${isActive ? "hover:bg-[#fafafa]" : "opacity-40"}`}
                    >
                      <td className="py-3 pr-6 text-[13px] font-semibold text-[#222]">{r.company}</td>
                      <td className="py-3 pr-6 font-mono text-[13px] text-[#222]">{r.revenue}</td>
                      <td className="py-3 pr-6 font-mono text-[13px] font-bold text-emerald-700">{r.opm}</td>
                      <td className="py-3 pr-6 font-mono text-[12px] text-[#888]">{r.opmFy22}</td>
                      <td className="py-3 pr-6 font-mono text-[12px] text-[#555]">{r.revpar}</td>
                      <td className="py-3 text-[12px] text-[#666] leading-relaxed">{r.story}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="text-[11px] text-[#bbb] mt-2">
            Source: <Citation source="Screener.in — profit_loss" company={companyId} quote="FY25 revenue operating margin" />
          </p>
        </div>

        {/* Investment & Risk — two column */}
        <div className="ed-grid">
          {/* Opportunities */}
          <div>
            <p className="kicker mb-4">Investment Opportunities</p>
            <div className="space-y-6">
              {INVESTMENT_OPPORTUNITIES.map((o, i) => (
                <div key={i} className="border-l-[3px] border-emerald-500 pl-5">
                  <p className="text-[13px] font-bold text-[#222] mb-1.5">{o.title}</p>
                  <p className="text-[13px] text-[#555] leading-[1.85] text-justify">{o.body}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Risks sidebar */}
          <aside>
            <div className="sidebar-card">
              <p className="kicker mb-4">Investor Risk Watch</p>
              <div className="space-y-5">
                {INVESTOR_RISKS.map((r, i) => (
                  <div key={i}>
                    <p className="text-[12px] font-bold text-red-700 mb-1">{r.title}</p>
                    <p className="text-[12px] text-[#555] leading-[1.8]">{r.body}</p>
                    {i < INVESTOR_RISKS.length - 1 && <hr className="mt-4 border-[#f0f0f0]" />}
                  </div>
                ))}
              </div>
            </div>

            {/* Market stat callout */}
            <div className="sidebar-card mt-0">
              <p className="kicker mb-2">Market Size 2026</p>
              <p className="stat-big">$27B</p>
              <p className="stat-label">India Hotel Market Estimate</p>
              <hr className="my-4 border-[#e0e0e0]" />
              <div className="space-y-2 text-[12px] text-[#666]">
                <div className="flex justify-between">
                  <span>Nationwide RevPAR growth</span>
                  <span className="font-mono font-semibold text-[#222]">+5.7%</span>
                </div>
                <div className="flex justify-between">
                  <span>ADR crossed</span>
                  <span className="font-mono font-semibold text-[#222]">US$100</span>
                </div>
                <div className="flex justify-between">
                  <span>Nationwide occupancy</span>
                  <span className="font-mono font-semibold text-[#222]">68.0%</span>
                </div>
                <div className="flex justify-between">
                  <span>Pipeline (5yr rooms)</span>
                  <span className="font-mono font-semibold text-red-600">1,00,000+</span>
                </div>
              </div>
              <p className="text-[10px] text-[#bbb] mt-3">Source: Hotelivate India Hotel Market Trends 2025</p>
            </div>
          </aside>
        </div>

      </div>
    </section>
  );
}
