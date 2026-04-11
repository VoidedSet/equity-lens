import { NextRequest, NextResponse } from "next/server";
import {
  getCompany,
  getLatestAnnualFinancials,
  getFinancials,
  getScorecards,
  getDeviations,
  getRiskFlags,
  getCredibilityScores,
  getGuidanceClaims,
  getManagementTone,
  getGraph,
} from "@/lib/db";

export const dynamic = "force-dynamic";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const company = await getCompany(id);

  if (!company) {
    return NextResponse.json(
      { error: `Company '${id}' not found` },
      { status: 404 }
    );
  }

  const cid = company.id;
  const [latest, quarterly, scorecards, deviations, riskFlags, credibility, guidance, managementTone] = await Promise.all([
    getLatestAnnualFinancials(cid),
    getFinancials(cid, "quarterly"),
    getScorecards(cid),
    getDeviations(cid),
    getRiskFlags(cid),
    getCredibilityScores(cid),
    getGuidanceClaims(cid),
    getManagementTone(cid),
  ]);
  const graph = getGraph();

  // Build key metrics from latest annual
  const keyMetrics = Object.entries(latest).map(([metric, row]) => ({
    metric,
    value: row.value,
    unit: row.unit,
    yoy_change: row.yoy_change,
    period: row.period,
    source: row.source_document,
  }));

  return NextResponse.json({
    company,
    keyMetrics,
    quarterly,
    scorecards,
    deviations,
    riskFlags,
    credibility,
    guidance,
    managementTone,
    graph,
  });
}
