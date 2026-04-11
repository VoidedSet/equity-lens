"use client";

import { useState, useEffect } from "react";

// ─── Types matching API responses ───

export type Company = {
  id: string;
  name: string;
  ticker_nse: string;
  segment: string;
  strategy: string;
  brands: string[];
  key_markets: string[];
};

export type KeyMetric = {
  metric: string;
  value: number;
  unit: string;
  yoy_change: number | null;
  period: string;
  source: string;
};

export type Scorecard = {
  company_id: string;
  period: string;
  dim_credibility: number;
  dim_financial_quality: number;
  dim_industry_position: number;
  dim_risk: number;
  composite_score: number;
};

export type Deviation = {
  id: string;
  guidance_id: string;
  company_id: string;
  period: string;
  metric_type: string;
  check_type: string;
  guided_value: number | null;
  actual_value: number | null;
  delta: number | null;
  delta_pct: number | null;
  flag: "BEAT" | "MISS" | "IN-LINE";
  severity: string;
  pattern: string | null;
  insight: string | null;
  source_guidance: string;
  source_actual: string;
};

export type GuidanceClaim = {
  id: string;
  company_id: string;
  statement_quarter: string;
  target_period: string;
  metric_type: string;
  guidance_value_point: number | null;
  unit: string | null;
  verbatim_quote: string;
  confidence_language: string;
  speaker: string;
  check_type: string;
  source_document: string;
  source_timestamp: string | null;
};

export type RiskFlag = {
  id: string;
  company_id: string;
  category: string;
  description: string;
  severity: string;
  verbatim_quote: string | null;
  source_document: string;
  period: string;
};

export type CredibilityScore = {
  company_id: string;
  period: string;
  overall_score: number;
  hit_rate: number;
  total_guidance_count: number;
  consecutive_misses: number;
  trend: string;
};

export type FinancialRow = {
  company_id: string;
  period: string;
  period_type: string;
  metric: string;
  value: number;
  unit: string;
  yoy_change: number | null;
  source_document: string;
  period_label: string;
};

export type ManagementToneItem = {
  company_id: string;
  quarter: string;
  overall_sentiment: string;
  confidence_score: number;
  key_phrases: string[];
  hedging_count: number;
  commitment_count: number;
  source: string;
};

export type GraphNode = {
  id: string;
  label: string;
  type: string;
  x: number;
  y: number;
};

export type GraphEdge = {
  from: string;
  to: string;
  label?: string;
  weight?: string;
};

export type CompanyData = {
  company: Company;
  keyMetrics: KeyMetric[];
  quarterly: FinancialRow[];
  scorecards: Scorecard[];
  deviations: Deviation[];
  riskFlags: RiskFlag[];
  credibility: CredibilityScore[];
  guidance: GuidanceClaim[];
  managementTone: ManagementToneItem[];
  graph: { nodes: GraphNode[]; edges: GraphEdge[] };
};

export type CompareData = {
  companies: { id: string; name: string }[];
  metrics: string[];
  comparison: Record<string, Record<string, number | null>>;
  rankings: {
    rank: number;
    company_id: string;
    company_name: string;
    composite_score: number;
    dim_credibility: number;
    dim_financial_quality: number;
    dim_industry_position: number;
    dim_risk: number;
    period: string;
  }[];
};

// ─── Hooks ───

export function useCompanies() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/data/companies")
      .then((r) => r.json())
      .then((data) => setCompanies(data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return { companies, loading };
}

export function useCompanyData(companyId: string | null) {
  const [data, setData] = useState<CompanyData | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!companyId) {
      setData(null);
      return;
    }
    setLoading(true);
    fetch(`/api/data/company/${companyId}`)
      .then((r) => r.json())
      .then((d) => setData(d))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [companyId]);

  return { data, loading };
}

export function useCompare() {
  const [data, setData] = useState<CompareData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/data/compare")
      .then((r) => r.json())
      .then((d) => setData(d))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return { data, loading };
}

// ─── News Feed ───

export type NewsItem = {
  title: string;
  url: string;
  source: string;
  published_date: string;
  summary_2line: string;
  company_tags: string[];
  dimension_primary: string;
  sentiment: string;
  market_scope: string;
  relevance_score: number;
};

export type NewsData = {
  items: NewsItem[];
  market_context: {
    as_of: string;
    total_items: number;
    sentiment_distribution: Record<string, number>;
  } | null;
  digest_date: string;
  total: number;
};

export function useNews(companyId?: string | null) {
  const [data, setData] = useState<NewsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const url = companyId ? `/api/data/news?company=${companyId}` : "/api/data/news";
    fetch(url)
      .then((r) => r.json())
      .then((d) => setData(d))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [companyId]);

  return { data, loading };
}
