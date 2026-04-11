import { NextResponse } from "next/server";
import {
  getCompanies,
  getLatestAnnualFinancials,
  getScorecards,
} from "@/lib/db";

export const dynamic = "force-dynamic";

export async function GET() {
  const companies = await getCompanies();

  // Build comparison: for each company, get latest annual financials
  const comparison: Record<string, Record<string, number | null>> = {};
  const metricsToCompare = [
    "revenue", "operating_profit", "opm", "net_profit", "eps",
    "interest", "borrowings", "total_assets",
  ];

  for (const c of companies) {
    const latest = await getLatestAnnualFinancials(c.id);
    comparison[c.id] = {};
    for (const m of metricsToCompare) {
      comparison[c.id][m] = latest[m]?.value ?? null;
    }
    // Add interest coverage
    const opProfit = latest["operating_profit"]?.value ?? 0;
    const interest = latest["interest"]?.value ?? 0;
    comparison[c.id]["interest_coverage"] =
      interest > 0 ? Math.round((opProfit / interest) * 10) / 10 : null;
  }

  // Rankings from scorecards
  const allScorecards = await getScorecards();
  const rankings = [...allScorecards]
    .sort((a, b) => b.composite_score - a.composite_score)
    .map((s, i) => {
      const company = companies.find((c) => c.id === s.company_id);
      return {
        rank: i + 1,
        company_id: s.company_id,
        company_name: company?.name || s.company_id,
        composite_score: s.composite_score,
        dim_credibility: s.dim_credibility,
        dim_financial_quality: s.dim_financial_quality,
        dim_industry_position: s.dim_industry_position,
        dim_risk: s.dim_risk,
        period: s.period,
      };
    });

  return NextResponse.json({
    companies: companies.map((c) => ({ id: c.id, name: c.name })),
    metrics: metricsToCompare.concat(["interest_coverage"]),
    comparison,
    rankings,
  });
}
