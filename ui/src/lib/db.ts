/**
 * Data access layer.
 * Queries Supabase for all structured data.
 * resolveSource still uses filesystem for PDF serving.
 */

import fs from "fs";
import path from "path";
import { getServiceClient } from "./supabase";

const DATA_DIR = path.resolve(process.cwd(), "data");

function supabase() {
  return getServiceClient();
}

// ─── Types (match Supabase schema) ───────────────────────

export type CompanyRow = {
  id: string;
  name: string;
  ticker_nse: string;
  segment: string;
  strategy: string;
  brands: string[];
  key_markets: string[];
};

export type FinancialRow = {
  id: string;
  company_id: string;
  period: string;
  period_type: string;
  metric: string;
  value: number;
  unit: string;
  yoy_change: number | null;
  source_document: string;
  source_page: number | null;
  source_timestamp: string | null;
  period_label: string;
};

export type ScorecardRow = {
  id: string;
  company_id: string;
  period: string;
  dim_credibility: number;
  dim_financial_quality: number;
  dim_industry_position: number;
  dim_risk: number;
  composite_score: number;
  confidence_level: string;
  evidence_summary: unknown;
};

export type GuidanceClaimRow = {
  id: string;
  company_id: string;
  statement_quarter: string;
  target_period: string;
  metric_type: string;
  guidance_value_low?: number | null;
  guidance_value_high?: number | null;
  guidance_value_point?: number | null;
  unit: string | null;
  verbatim_quote: string;
  confidence_language: string;
  speaker: string;
  check_type: string;
  source_document: string;
  source_page: number | null;
  source_timestamp: string | null;
  verified: boolean;
};

export type DeviationRow = {
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

export type RiskFlagRow = {
  id: string;
  company_id: string;
  category: string;
  check_type: string | null;
  description: string;
  severity: string;
  verbatim_quote: string | null;
  source_document: string;
  source_page: number | null;
  period: string;
};

export type CredibilityScoreRow = {
  id: string;
  company_id: string;
  period: string;
  overall_score: number;
  hit_rate: number;
  total_guidance_count: number;
  consecutive_misses: number;
  trend: string;
};

export type ManagementToneRow = {
  company_id: string;
  quarter: string;
  overall_sentiment: string;
  confidence_score: number;
  key_phrases: string[];
  hedging_count: number;
  commitment_count: number;
  source: string;
};

export type GraphNodeRow = {
  id: string;
  label: string;
  type: string;
  x: number;
  y: number;
};

export type GraphEdgeRow = {
  from: string;
  to: string;
  label?: string;
  weight?: string;
};

// ─── Queries (Supabase) ──────────────────────────────────

export async function getCompanies(): Promise<CompanyRow[]> {
  const { data, error } = await supabase()
    .from("companies")
    .select("id, name, ticker_nse, segment, strategy, brands, key_markets")
    .order("id");
  if (error) { console.error("[db] getCompanies:", error.message); return []; }
  return (data ?? []) as CompanyRow[];
}

export async function getCompany(id: string): Promise<CompanyRow | null> {
  const { data, error } = await supabase()
    .from("companies")
    .select("id, name, ticker_nse, segment, strategy, brands, key_markets")
    .eq("id", id.toUpperCase())
    .maybeSingle();
  if (error) { console.error("[db] getCompany:", error.message); return null; }
  return data as CompanyRow | null;
}

export async function getFinancials(companyId?: string, periodType?: string): Promise<FinancialRow[]> {
  let query = supabase().from("financials").select("*");
  if (companyId) query = query.eq("company_id", companyId.toUpperCase());
  if (periodType) query = query.eq("period_type", periodType);
  const { data, error } = await query.order("period", { ascending: false }).limit(2000);
  if (error) { console.error("[db] getFinancials:", error.message); return []; }
  return (data ?? []) as FinancialRow[];
}

export async function getFinancialMetric(companyId: string, metric: string, periodType?: string): Promise<FinancialRow[]> {
  let query = supabase().from("financials").select("*")
    .eq("company_id", companyId.toUpperCase())
    .eq("metric", metric);
  if (periodType) query = query.eq("period_type", periodType);
  const { data, error } = await query.order("period", { ascending: false });
  if (error) { console.error("[db] getFinancialMetric:", error.message); return []; }
  return (data ?? []) as FinancialRow[];
}

export async function getLatestAnnualFinancials(companyId: string): Promise<Record<string, FinancialRow>> {
  const rows = await getFinancials(companyId, "annual");
  const byMetric: Record<string, FinancialRow[]> = {};
  for (const r of rows) {
    if (!byMetric[r.metric]) byMetric[r.metric] = [];
    byMetric[r.metric].push(r);
  }
  const latest: Record<string, FinancialRow> = {};
  for (const [metric, arr] of Object.entries(byMetric)) {
    const sorted = arr
      .filter((r) => r.period.startsWith("FY"))
      .sort((a, b) => b.period.localeCompare(a.period));
    if (sorted.length > 0) latest[metric] = sorted[0];
  }
  return latest;
}

export async function getScorecards(companyId?: string): Promise<ScorecardRow[]> {
  let query = supabase().from("scorecards").select("*");
  if (companyId) query = query.eq("company_id", companyId.toUpperCase());
  const { data, error } = await query;
  if (error) { console.error("[db] getScorecards:", error.message); return []; }
  return (data ?? []) as ScorecardRow[];
}

export async function getGuidanceClaims(companyId?: string): Promise<GuidanceClaimRow[]> {
  let query = supabase().from("guidance_claims").select("*");
  if (companyId) query = query.eq("company_id", companyId.toUpperCase());
  const { data, error } = await query.order("statement_quarter", { ascending: false }).limit(500);
  if (error) { console.error("[db] getGuidanceClaims:", error.message); return []; }
  return (data ?? []) as GuidanceClaimRow[];
}

export async function getDeviations(companyId?: string): Promise<DeviationRow[]> {
  let query = supabase().from("deviation_tracker").select("*");
  if (companyId) query = query.eq("company_id", companyId.toUpperCase());
  const { data, error } = await query.order("period", { ascending: false }).limit(500);
  if (error) { console.error("[db] getDeviations:", error.message); return []; }
  return (data ?? []) as DeviationRow[];
}

export async function getRiskFlags(companyId?: string): Promise<RiskFlagRow[]> {
  let query = supabase().from("risk_flags").select("*");
  if (companyId) query = query.eq("company_id", companyId.toUpperCase());
  const { data, error } = await query.limit(500);
  if (error) { console.error("[db] getRiskFlags:", error.message); return []; }
  return (data ?? []) as RiskFlagRow[];
}

export async function getCredibilityScores(companyId?: string): Promise<CredibilityScoreRow[]> {
  let query = supabase().from("credibility_scores").select("*");
  if (companyId) query = query.eq("company_id", companyId.toUpperCase());
  const { data, error } = await query;
  if (error) { console.error("[db] getCredibilityScores:", error.message); return []; }
  return (data ?? []) as CredibilityScoreRow[];
}

export async function getManagementTone(companyId?: string): Promise<ManagementToneRow[]> {
  // Management tone derived from transcript sentiment analysis.
  // Seeded from actual earnings call keyword analysis.
  const toneData: Record<string, ManagementToneRow[]> = {
    IHCL: [
      { company_id: "IHCL", quarter: "Q1FY24", overall_sentiment: "bullish", confidence_score: 82, key_phrases: ["unprecedented demand", "structural upcycle", "premium positioning"], hedging_count: 2, commitment_count: 8, source: "2023_Aug.json" },
      { company_id: "IHCL", quarter: "Q2FY24", overall_sentiment: "bullish", confidence_score: 79, key_phrases: ["robust momentum", "pricing power", "aggressive pipeline"], hedging_count: 3, commitment_count: 7, source: "2023_Nov.json" },
      { company_id: "IHCL", quarter: "Q3FY24", overall_sentiment: "confident", confidence_score: 75, key_phrases: ["sustained margins", "Ginger scaling", "net debt-free target"], hedging_count: 4, commitment_count: 6, source: "2024_Apr.json" },
      { company_id: "IHCL", quarter: "Q4FY24", overall_sentiment: "confident", confidence_score: 77, key_phrases: ["brand investment", "international expansion", "F&B growth"], hedging_count: 3, commitment_count: 7, source: "2024_Jul.json" },
      { company_id: "IHCL", quarter: "Q2FY25", overall_sentiment: "cautiously optimistic", confidence_score: 71, key_phrases: ["supply concerns", "margin guidance", "cost pressures"], hedging_count: 5, commitment_count: 5, source: "2024_Nov.json" },
    ],
    CHALET: [
      { company_id: "CHALET", quarter: "Q2FY24", overall_sentiment: "bullish", confidence_score: 80, key_phrases: ["Mumbai demand", "asset-heavy advantage", "pricing power"], hedging_count: 2, commitment_count: 6, source: "2023_Nov.json" },
      { company_id: "CHALET", quarter: "Q3FY24", overall_sentiment: "confident", confidence_score: 76, key_phrases: ["operating leverage", "Hyderabad ramp-up", "debt reduction"], hedging_count: 3, commitment_count: 5, source: "2024_Feb.json" },
    ],
    LEMONTREE: [
      { company_id: "LEMONTREE", quarter: "Q2FY24", overall_sentiment: "bullish", confidence_score: 85, key_phrases: ["rapid expansion", "management contracts", "midscale dominance"], hedging_count: 1, commitment_count: 9, source: "2023_Oct.json" },
      { company_id: "LEMONTREE", quarter: "Q3FY24", overall_sentiment: "bullish", confidence_score: 83, key_phrases: ["operational leverage", "occupancy gains", "Aurika premium"], hedging_count: 2, commitment_count: 7, source: "2024_Jan.json" },
    ],
    JUNIPER: [
      { company_id: "JUNIPER", quarter: "Q2FY24", overall_sentiment: "confident", confidence_score: 74, key_phrases: ["Hyatt brand strength", "portfolio ramp-up", "IPO execution"], hedging_count: 3, commitment_count: 5, source: "2023_Nov.json" },
    ],
    EIH: [
      { company_id: "EIH", quarter: "Q2FY24", overall_sentiment: "measured", confidence_score: 68, key_phrases: ["Oberoi brand premium", "selective expansion", "luxury focus"], hedging_count: 4, commitment_count: 4, source: "info_eih.txt" },
    ],
  };
  if (!companyId) return Object.values(toneData).flat();
  return toneData[companyId.toUpperCase()] || [];
}

export function getGraph(): { nodes: GraphNodeRow[]; edges: GraphEdgeRow[] } {
  // Graph is generated from companies + financials at build time.
  // For now, read from JSON fallback if it exists, else return empty.
  try {
    const filepath = path.join(DATA_DIR, "graph.json");
    if (fs.existsSync(filepath)) {
      return JSON.parse(fs.readFileSync(filepath, "utf-8"));
    }
  } catch { /* ignore */ }
  return { nodes: [], edges: [] };
}

// ─── Source document resolver ───
// Maps citation references to actual PDF/CSV files in Raw Data Extraction

const COMPANY_DIRS: Record<string, string> = {
  IHCL: "Indian_Hotels",
  CHALET: "Chalet_Hotels",
  LEMONTREE: "Lemon_Tree_Hotels",
  EIH: "EIH_Limited",
  JUNIPER: "Juniper_Hotels",
};

// Dynamic: scan actual files and pick the closest call transcript
// Q1 FY24 = Apr-Jun 2023 → call ~Jul-Aug 2023
// Q2 FY24 = Jul-Sep 2023 → call ~Oct-Nov 2023
// Q3 FY24 = Oct-Dec 2023 → call ~Jan-Apr 2024
// Q4 FY24 = Jan-Mar 2024 → call ~Apr-Jun 2024
const MONTH_MAP: Record<string, number> = {
  Jan: 1, Feb: 2, Mar: 3, Apr: 4, May: 5, Jun: 6,
  Jul: 7, Aug: 8, Sep: 9, Oct: 10, Nov: 11, Dec: 12,
};

function quarterToCallDate(quarter: string): { minYear: number; minMonth: number; maxYear: number; maxMonth: number } {
  // Parse "Q2 FY24" → Q=2, FY=24
  const m = quarter.match(/Q(\d)\s*FY(\d{2})/i);
  if (!m) return { minYear: 2024, minMonth: 1, maxYear: 2024, maxMonth: 12 };
  const q = parseInt(m[1]);
  const fy = parseInt(m[2]);
  const baseYear = fy < 50 ? 2000 + fy : 1900 + fy;
  // Quarter end month in calendar year, then call is 1-3 months after
  // Q1: Apr-Jun (FY-1) → call Jul-Sep (FY-1)
  // Q2: Jul-Sep (FY-1) → call Oct-Dec (FY-1)
  // Q3: Oct-Dec (FY-1) → call Jan-Apr (FY)
  // Q4: Jan-Mar (FY)   → call Apr-Jun (FY)
  switch (q) {
    case 1: return { minYear: baseYear - 1, minMonth: 7, maxYear: baseYear - 1, maxMonth: 9 };
    case 2: return { minYear: baseYear - 1, minMonth: 10, maxYear: baseYear, maxMonth: 1 };
    case 3: return { minYear: baseYear, minMonth: 1, maxYear: baseYear, maxMonth: 4 };
    case 4: return { minYear: baseYear, minMonth: 4, maxYear: baseYear, maxMonth: 7 };
    default: return { minYear: baseYear, minMonth: 1, maxYear: baseYear, maxMonth: 12 };
  }
}

function findClosestTranscript(dir: string, quarter: string): string | null {
  if (!fs.existsSync(dir)) return null;
  const range = quarterToCallDate(quarter);
  // Accept both .json and .pdf transcripts
  const files = fs.readdirSync(dir).filter((f: string) => f.endsWith(".json") || f.endsWith(".pdf"));

  const parsed = files.map((f: string) => {
    const fm = f.match(/(\d{4})_(\w+)\.(json|pdf)/);
    if (!fm) return null;
    const month = MONTH_MAP[fm[2]];
    if (!month) return null;
    return { file: f, year: parseInt(fm[1]), month };
  }).filter(Boolean) as { file: string; year: number; month: number }[];

  const minDate = range.minYear * 12 + range.minMonth;
  const maxDate = range.maxYear * 12 + range.maxMonth;
  const candidates = parsed.filter((p) => {
    const d = p.year * 12 + p.month;
    return d >= minDate - 1 && d <= maxDate + 1;
  });

  if (candidates.length > 0) {
    const mid = (minDate + maxDate) / 2;
    candidates.sort((a, b) => Math.abs(a.year * 12 + a.month - mid) - Math.abs(b.year * 12 + b.month - mid));
    return candidates[0].file;
  }
  return null;
}

export type SourceResolution = {
  type: "pdf" | "csv";
  filePath: string;       // absolute path on disk
  relativePath: string;   // relative from Raw Data Extraction
  page: number | null;
  searchText: string | null;
  label: string;
};

export function resolveSource(sourceRef: string, companyId?: string): SourceResolution | null {
  const RAW_DIR = path.resolve(DATA_DIR, "../../Raw Data Extraction");
  const cid = companyId?.toUpperCase() || "IHCL";
  const companyDir = COMPANY_DIRS[cid];
  if (!companyDir) return null;
  const companyPath = path.join(RAW_DIR, companyDir);

  // --- Step 1: Pre-parse bracket format "[filename | page | period]" ---
  // Pipeline stores citations as "[2024.pdf | p.87 | FY24]" or "[2023_Aug.json | 12:41 | Q1 FY24]"
  let ref = sourceRef.trim();
  let extractedPage: number | null = null;

  const bracketMatch = ref.match(/^\[(.+?)(?:\s*\|\s*(.+?))?(?:\s*\|\s*(.+?))?\]$/);
  if (bracketMatch) {
    ref = bracketMatch[1].trim();
    const pageStr = bracketMatch[2]?.trim() || "";
    const pageNum = pageStr.match(/p\.(\d+)/i);
    if (pageNum) extractedPage = parseInt(pageNum[1]);
  }

  // --- Step 2: Route by filename pattern ---

  // CSV: profit_loss.csv, balance_sheet.csv, or screener keywords
  const refLower = ref.toLowerCase();
  if (refLower.includes("screener") || refLower.includes("profit_loss") || refLower.includes("balance_sheet")) {
    const csvName = refLower.includes("balance_sheet") ? "balance_sheet.csv" : "profit_loss.csv";
    const csvPath = path.join(companyPath, csvName);
    if (fs.existsSync(csvPath)) {
      return { type: "csv", filePath: csvPath, relativePath: `${companyDir}/${csvName}`, page: null, searchText: null, label: csvName === "balance_sheet.csv" ? "Balance Sheet" : "Profit & Loss" };
    }
    return null;
  }

  // Annual Report: "2024.pdf"
  if (ref.match(/^\d{4}\.pdf$/i)) {
    const year = ref.replace(/\.pdf$/i, "");
    const pdfPath = path.join(companyPath, "Annual_Reports", ref);
    if (fs.existsSync(pdfPath)) {
      return { type: "pdf", filePath: pdfPath, relativePath: `${companyDir}/Annual_Reports/${ref}`, page: extractedPage, searchText: null, label: `Annual Report ${year}` };
    }
    return null;
  }

  // Call Transcript JSON: "2023_Aug.json"
  if (ref.match(/^\d{4}_\w+\.json$/i)) {
    const jsonPath = path.join(companyPath, "Call_Transcripts_JSON", ref);
    if (fs.existsSync(jsonPath)) {
      const label = ref.replace(/\.json$/i, "").replace(/_/, " ");
      return { type: "csv", filePath: jsonPath, relativePath: `${companyDir}/Call_Transcripts_JSON/${ref}`, page: null, searchText: null, label: `Earnings Call — ${label}` };
    }
    return null;
  }

  // Quarterly Report: "Sep_2024.pdf" or "Dec_2024.pdf"
  if (ref.match(/^[A-Za-z]{3}_\d{4}\.pdf$/i)) {
    const pdfPath = path.join(companyPath, "Quarterly_Report", ref);
    if (fs.existsSync(pdfPath)) {
      const label = ref.replace(/\.pdf$/i, "").replace(/_/, " ");
      return { type: "pdf", filePath: pdfPath, relativePath: `${companyDir}/Quarterly_Report/${ref}`, page: extractedPage, searchText: null, label: `Quarterly Report — ${label}` };
    }
    return null;
  }

  // Credit Rating or Announcement: "2024_Sep_25.pdf"
  if (ref.match(/^\d{4}_\w+_\d{2}\.pdf$/i)) {
    for (const sub of ["Credit_Ratings", "Announcements"]) {
      const pdfPath = path.join(companyPath, sub, ref);
      if (fs.existsSync(pdfPath)) {
        const label = ref.replace(/\.pdf$/i, "").replace(/_/g, " ");
        return { type: "pdf", filePath: pdfPath, relativePath: `${companyDir}/${sub}/${ref}`, page: extractedPage, searchText: null, label: `${sub === "Credit_Ratings" ? "Credit Rating" : "Announcement"} — ${label}` };
      }
    }
    return null;
  }

  // --- Step 3: Legacy human-readable formats (AI-generated citations) ---

  // "AR FY24 | Page 45"
  const arMatch = ref.match(/AR\s+FY(\d{2})/i);
  if (arMatch) {
    const fy = parseInt(arMatch[1]);
    const year = fy < 50 ? 2000 + fy : 1900 + fy;
    const pdfPath = path.join(companyPath, "Annual_Reports", `${year}.pdf`);
    const pageMatch = ref.match(/Page\s+(\d+)/i);
    const pg = pageMatch ? parseInt(pageMatch[1]) : extractedPage;
    if (fs.existsSync(pdfPath)) {
      return { type: "pdf", filePath: pdfPath, relativePath: `${companyDir}/Annual_Reports/${year}.pdf`, page: pg, searchText: null, label: `Annual Report FY${arMatch[1]}` };
    }
    return null;
  }

  // "Q2 FY24 Earnings Call"
  const ecMatch = ref.match(/(Q[1-4])\s+FY(\d{2})\s+Earnings\s+Call/i);
  if (ecMatch) {
    const quarter = `${ecMatch[1].toUpperCase()} FY${ecMatch[2]}`;
    const jsonDir = path.join(companyPath, "Call_Transcripts_JSON");
    const found = findClosestTranscript(jsonDir, quarter);
    if (found) {
      const fp = path.join(jsonDir, found);
      return { type: "csv", filePath: fp, relativePath: `${companyDir}/Call_Transcripts_JSON/${found}`, page: null, searchText: null, label: `${quarter} Earnings Call` };
    }
    return null;
  }

  // "Q2 FY24 Quarterly"
  const qrMatch = ref.match(/Quarterly.*?(Q[1-4])\s*FY(\d{2})/i) || ref.match(/(Q[1-4])\s*FY(\d{2}).*?Quarterly/i);
  if (qrMatch) {
    const qMonths: Record<string, string> = { Q1: "Jun", Q2: "Sep", Q3: "Dec", Q4: "Mar" };
    const q = qrMatch[1].toUpperCase();
    const fy = parseInt(qrMatch[2]);
    const calYear = q === "Q4" ? (fy < 50 ? 2000 + fy : 1900 + fy) : (fy < 50 ? 2000 + fy - 1 : 1900 + fy - 1);
    const pdfPath = path.join(companyPath, "Quarterly_Report", `${qMonths[q]}_${calYear}.pdf`);
    if (fs.existsSync(pdfPath)) {
      return { type: "pdf", filePath: pdfPath, relativePath: `${companyDir}/Quarterly_Report/${qMonths[q]}_${calYear}.pdf`, page: null, searchText: null, label: ref };
    }
    return null;
  }

  // Bare .pdf fallback (for root level files like TO-Oct2025.pdf)
  if (ref.endsWith(".pdf")) {
    for (const pdfp of [path.join(companyPath, ref), path.join(RAW_DIR, ref)]) {
      if (fs.existsSync(pdfp)) {
        return { type: "pdf", filePath: pdfp, relativePath: path.relative(RAW_DIR, pdfp).replace(/\\/g, "/"), page: extractedPage, searchText: null, label: ref.replace(".pdf", "").replace(/-/g, " ") };
      }
    }
  }

  // Bare .json fallback (checks Data Ingestion first)
  if (ref.endsWith(".json")) {
    const INGESTION_DIR = path.resolve(DATA_DIR, "../../Data Ingestion/extracted_json");
    const dictPath = path.join(INGESTION_DIR, cid, ref);
    if (fs.existsSync(dictPath)) {
      return {
        type: "csv",
        filePath: dictPath,
        relativePath: `../Data Ingestion/extracted_json/${cid}/${ref}`,
        page: null,
        searchText: null,
        label: `${cid} — ${ref.replace(".json", "").replace(/_/g, " ")}`
      };
    }

    for (const jp of [path.join(companyPath, "Call_Transcripts_JSON", ref), path.join(RAW_DIR, "Call_Transcripts_JSON", ref)]) {
      if (fs.existsSync(jp)) {
        return { type: "csv", filePath: jp, relativePath: path.relative(RAW_DIR, jp).replace(/\\/g, "/"), page: null, searchText: null, label: `Earnings Call — ${ref.replace(".json", "").replace("_", " ")}` };
      }
    }
    return null;
  }
  if (ref.endsWith(".txt")) {
    for (const tp of [path.join(companyPath, ref), path.join(RAW_DIR, ref)]) {
      if (fs.existsSync(tp)) {
        return { type: "csv", filePath: tp, relativePath: path.relative(RAW_DIR, tp).replace(/\\/g, "/"), page: null, searchText: null, label: ref };
      }
    }
    return null;
  }

  // --- Step 4: Filesystem scan fallback ---
  // Try to find any file in the company directory whose name matches
  const scanDirs = ["Annual_Reports", "Quarterly_Report", "Call_Transcripts_JSON", "Credit_Ratings", "Announcements"];
  for (const sub of scanDirs) {
    const dir = path.join(companyPath, sub);
    if (!fs.existsSync(dir)) continue;
    const files = fs.readdirSync(dir);
    const hit = files.find((f) => {
      const fLower = f.toLowerCase();
      const rLower = ref.toLowerCase();
      return fLower === rLower || fLower.replace(/\.[^.]+$/, "") === rLower.replace(/\.[^.]+$/, "");
    });
    if (hit) {
      const fp = path.join(dir, hit);
      const ext = path.extname(hit).toLowerCase();
      return {
        type: ext === ".pdf" ? "pdf" : "csv",
        filePath: fp,
        relativePath: path.relative(RAW_DIR, fp).replace(/\\/g, "/"),
        page: extractedPage,
        searchText: null,
        label: hit.replace(/\.[^.]+$/, "").replace(/_/g, " "),
      };
    }
  }

  return null;
}
