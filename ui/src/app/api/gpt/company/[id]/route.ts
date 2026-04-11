import { NextRequest, NextResponse } from "next/server";
import {
  getCompany,
  getCompanies,
  getLatestAnnualFinancials,
  getScorecards,
  getRiskFlags,
  getManagementTone,
  getCredibilityScores,
} from "@/lib/db";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const companyId = id.toUpperCase();
  const company = await getCompany(companyId);

  if (!company) {
    const allCompanies = await getCompanies();
    return NextResponse.json(
      {
        error: `Company '${companyId}' not found`,
        available: allCompanies.map((c) => c.id),
      },
      { status: 404 }
    );
  }

  const [scorecards, latest, riskFlags, tones, credibility] = await Promise.all([
    getScorecards(companyId),
    getLatestAnnualFinancials(companyId),
    getRiskFlags(companyId),
    getManagementTone(companyId),
    getCredibilityScores(companyId),
  ]);
  const sc = scorecards[0];

  const keyMetrics = Object.entries(latest).map(([metric, row]) => ({
    label: metric,
    value: row.value,
    unit: row.unit,
    yoy_change_pct: row.yoy_change,
    period: row.period,
    source: row.source_document,
  }));

  return NextResponse.json({
    company: {
      id: company.id,
      name: company.name,
      ticker: company.ticker_nse,
      segment: company.segment,
      strategy: company.strategy,
      brands: company.brands,
      key_markets: company.key_markets,
    },
    key_metrics: keyMetrics,
    scorecard: sc
      ? {
          composite: sc.composite_score,
          credibility: sc.dim_credibility,
          financial_quality: sc.dim_financial_quality,
          industry_position: sc.dim_industry_position,
          risk: sc.dim_risk,
          period: sc.period,
          source: "EquityLens 4-Dimension Scoring Model",
        }
      : null,
    risk_flags: riskFlags.map((r) => ({
      category: r.category,
      severity: r.severity,
      description: r.description,
      source: r.source_document,
      period: r.period,
    })),
    management_tone: tones.map((t) => ({
      quarter: t.quarter,
      sentiment: t.overall_sentiment,
      confidence_score: t.confidence_score,
      hedging_count: t.hedging_count,
      commitment_count: t.commitment_count,
      key_phrases: t.key_phrases,
      source: t.source,
    })),
    credibility_trend: credibility.map((c) => ({
      period: c.period,
      score: c.overall_score,
      source: "EquityLens Credibility Model",
    })),
  });
}
