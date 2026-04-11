/**
 * Transforms API response data into the shapes our UI components expect.
 * This is the adapter layer — when Supabase replaces JSON files,
 * only db.ts changes. Components + this file stay the same.
 */

import type { CompanyData, CompareData, Deviation, RiskFlag, CredibilityScore, Scorecard } from "./hooks";

// ─── Types that components expect ───

export type UICompany = {
  id: string;
  name: string;
  ticker: string;
  segment: string;
  strategy: string;
  brands: string[];
  keyMarkets: string[];
  color: string;
};

export type UIKeyMetric = {
  label: string;
  value: string;
  unit: string;
  change: number | null;
  period: string;
  source: string;
};

export type UIDeviation = {
  id: string;
  metric: string;
  checkType: string;
  statementQuarter: string;
  targetPeriod: string;
  guidedValue: string;
  actualValue: string;
  delta: string;
  flag: "BEAT" | "MISS" | "IN-LINE";
  severity: string;
  verbatimQuote: string;
  speaker: string;
  confidenceLanguage: string;
  sourceGuidance: string;
  sourceActual: string;
  pattern?: string;
  crossRef?: string;
};

export type UIScorecard = {
  companyId: string;
  period: string;
  credibility: number;
  financialQuality: number;
  industryPosition: number;
  risk: number;
  composite: number;
};

export type UIRiskFlag = {
  id: string;
  category: string;
  severity: string;
  description: string;
  verbatimQuote?: string;
  source: string;
  period: string;
};

export type UICredibilityPoint = {
  period: string;
  score: number;
};

// Color map for companies
const COMPANY_COLORS: Record<string, string> = {
  IHCL: "#1e3a5f",
  CHALET: "#6b4c9a",
  LEMONTREE: "#2d8544",
  EIH: "#8b6914",
  JUNIPER: "#1a6b6b",
};

// Metric label map
const METRIC_LABELS: Record<string, string> = {
  revenue: "Revenue",
  operating_profit: "Operating Profit",
  opm: "OPM",
  net_profit: "Net Profit",
  eps: "EPS",
  interest: "Interest",
  borrowings: "Total Debt",
  total_assets: "Total Assets",
  interest_coverage: "Interest Coverage",
  depreciation: "Depreciation",
  pbt: "Profit Before Tax",
};

// ─── Transformers ───

export function toUICompany(c: CompanyData["company"]): UICompany {
  return {
    id: c.id,
    name: c.name,
    ticker: c.ticker_nse,
    segment: c.segment.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase()),
    strategy: c.strategy.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase()),
    brands: c.brands,
    keyMarkets: c.key_markets,
    color: COMPANY_COLORS[c.id] || "#334155",
  };
}

export function toUIKeyMetrics(metrics: CompanyData["keyMetrics"]): UIKeyMetric[] {
  return metrics
    .filter((m) => METRIC_LABELS[m.metric])
    .map((m) => ({
      label: METRIC_LABELS[m.metric] || m.metric,
      value: m.unit === "%" ? `${m.value}` : m.value.toLocaleString("en-IN"),
      unit: m.unit,
      change: m.yoy_change,
      period: m.period,
      source: m.source,
    }));
}

export function toUIDeviations(
  deviations: Deviation[],
  guidance: CompanyData["guidance"]
): UIDeviation[] {
  return deviations.map((d, i) => {
    const g = guidance.find((gc) => gc.id === d.guidance_id);
    return {
      id: String(i + 1),
      metric: d.metric_type.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase()),
      checkType: d.check_type || "",
      statementQuarter: g?.statement_quarter || "",
      targetPeriod: d.period,
      guidedValue: d.guided_value !== null ? String(d.guided_value) + (g?.unit ? ` ${g.unit}` : "") : "Qualitative",
      actualValue: d.actual_value !== null ? String(d.actual_value) + (g?.unit ? ` ${g.unit}` : "") : (d.insight || "See pattern"),
      delta: d.delta !== null ? String(d.delta) + (d.delta_pct !== null ? `pp` : "") : (d.insight || "Mismatch"),
      flag: d.flag,
      severity: d.severity,
      verbatimQuote: g?.verbatim_quote || "",
      speaker: g?.speaker || "",
      confidenceLanguage: g?.confidence_language || "expect",
      sourceGuidance: d.source_guidance,
      sourceActual: d.source_actual,
      pattern: d.pattern || undefined,
    };
  });
}

export function toUIScorecard(sc: Scorecard): UIScorecard {
  return {
    companyId: sc.company_id,
    period: sc.period,
    credibility: sc.dim_credibility,
    financialQuality: sc.dim_financial_quality,
    industryPosition: sc.dim_industry_position,
    risk: sc.dim_risk,
    composite: sc.composite_score,
  };
}

export function toUIRiskFlags(flags: RiskFlag[]): UIRiskFlag[] {
  return flags.map((f) => ({
    id: f.id,
    category: f.category.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase()),
    severity: f.severity,
    description: f.description,
    verbatimQuote: f.verbatim_quote || undefined,
    source: f.source_document,
    period: f.period,
  }));
}

export function toUICredibility(scores: CredibilityScore[]): UICredibilityPoint[] {
  return scores.map((s) => ({
    period: s.period,
    score: s.overall_score,
  }));
}

// For CompanyCompare — builds the comparison table from API data
export function toUICompareTable(data: CompareData) {
  const metricLabels: Record<string, { label: string; unit: string }> = {
    revenue: { label: "Revenue", unit: "₹ Cr" },
    operating_profit: { label: "Operating Profit", unit: "₹ Cr" },
    opm: { label: "OPM", unit: "%" },
    net_profit: { label: "Net Profit", unit: "₹ Cr" },
    eps: { label: "EPS", unit: "₹" },
    interest_coverage: { label: "Interest Coverage", unit: "x" },
    borrowings: { label: "Total Debt", unit: "₹ Cr" },
  };

  const rows = Object.entries(metricLabels)
    .filter(([key]) => data.metrics.includes(key))
    .map(([key, meta]) => {
      const row: Record<string, string> = {
        metric: meta.label,
        unit: meta.unit,
      };
      for (const c of data.companies) {
        const val = data.comparison[c.id]?.[key];
        row[c.id] = val !== null && val !== undefined
          ? meta.unit === "%" ? `${val}%` : val.toLocaleString("en-IN")
          : "N/A";
      }
      return row;
    });

  const rankings = data.rankings.map((r) => ({
    companyId: r.company_id,
    name: r.company_name,
    composite: r.composite_score,
    segment: "",
  }));

  return { rows, rankings, companyIds: data.companies.map((c) => c.id), companyNames: data.companies };
}
