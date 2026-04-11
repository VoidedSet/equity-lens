import { NextResponse } from "next/server";
import { getCompanies, getScorecards, getLatestAnnualFinancials } from "@/lib/db";

export async function GET() {
  const [companies, allScorecards] = await Promise.all([
    getCompanies(),
    getScorecards(),
  ]);

  const rankings = [...allScorecards]
    .sort((a, b) => b.composite_score - a.composite_score)
    .map((s, i) => {
      const company = companies.find((c) => c.id === s.company_id);
      return {
        rank: i + 1,
        company_id: s.company_id,
        company_name: company?.name || s.company_id,
        composite_score: s.composite_score,
        credibility: s.dim_credibility,
        financial_quality: s.dim_financial_quality,
        industry_position: s.dim_industry_position,
        risk: s.dim_risk,
        period: s.period,
        source: "EquityLens 4-Dimension Scoring Model",
      };
    });

  // Build comparison from latest financials
  const metrics = ["revenue", "operating_profit", "opm", "net_profit", "eps"];
  const comparison: Record<string, Record<string, number | null>> = {};
  for (const c of companies) {
    const latest = await getLatestAnnualFinancials(c.id);
    comparison[c.id] = {};
    for (const m of metrics) {
      comparison[c.id][m] = latest[m]?.value ?? null;
    }
  }

  return NextResponse.json({
    companies: companies.map((c) => ({ id: c.id, name: c.name })),
    metrics,
    comparison,
    rankings,
    source: "Screener.in financials, EquityLens Scoring Model",
  });
}
