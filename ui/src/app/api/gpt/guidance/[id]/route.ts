import { NextRequest, NextResponse } from "next/server";
import { getCompany, getCompanies, getDeviations, getGuidanceClaims } from "@/lib/db";

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

  const [deviations, guidance] = await Promise.all([
    getDeviations(companyId),
    getGuidanceClaims(companyId),
  ]);

  if (deviations.length === 0) {
    return NextResponse.json({
      company: companyId,
      note: "No guidance tracking data available yet for this company. Data will appear once the PDF pipeline processes earnings transcripts.",
    });
  }

  const missCount = deviations.filter((d) => d.flag === "MISS").length;
  const beatCount = deviations.filter((d) => d.flag === "BEAT").length;
  const inlineCount = deviations.filter((d) => d.flag === "IN-LINE").length;
  const hitRate = Math.round(
    ((beatCount + inlineCount) / deviations.length) * 100
  );

  return NextResponse.json({
    company: companyId,
    summary: {
      total_claims: deviations.length,
      misses: missCount,
      beats: beatCount,
      in_line: inlineCount,
      hit_rate_pct: hitRate,
    },
    claims: deviations.map((d) => {
      const g = guidance.find((gc) => gc.id === d.guidance_id);
      return {
        metric: d.metric_type,
        check_type: d.check_type,
        target_period: d.period,
        guided_value: d.guided_value,
        actual_value: d.actual_value,
        delta: d.delta,
        flag: d.flag,
        severity: d.severity,
        verbatim_quote: g?.verbatim_quote || null,
        speaker: g?.speaker || null,
        confidence_language: g?.confidence_language || null,
        source_guidance: d.source_guidance,
        source_actual: d.source_actual,
        pattern: d.pattern || null,
      };
    }),
  });
}
