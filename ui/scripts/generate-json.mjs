/**
 * Reads Raw Data Extraction CSVs and generates JSON files
 * matching the Supabase schema exactly.
 * 
 * Run: node scripts/generate-json.mjs
 */

import fs from "fs";
import path from "path";
import { randomUUID } from "crypto";

const RAW = path.resolve(process.cwd(), "..", "Raw Data Extraction");
const OUT = path.resolve(process.cwd(), "data");

if (!fs.existsSync(OUT)) fs.mkdirSync(OUT, { recursive: true });

const COMPANY_MAP = {
  IHCL: "Indian_Hotels",
  CHALET: "Chalet_Hotels",
  LEMONTREE: "Lemon_Tree_Hotels",
  EIH: "EIH_Limited",
  JUNIPER: "Juniper_Hotels",
};

// ─── CSV Parser ───
function parseCSV(filepath) {
  if (!fs.existsSync(filepath)) return { headers: [], rows: [] };
  const raw = fs.readFileSync(filepath, "utf-8").trim();
  const lines = raw.split("\n").map(l => l.trim()).filter(Boolean);
  if (lines.length < 2) return { headers: [], rows: [] };
  const headers = lines[0].split(",").map(h => h.trim());
  const rows = [];
  for (let i = 1; i < lines.length; i++) {
    const vals = lines[i].split(",").map(v => v.trim());
    if (vals[0] === "Additional Metrics") break;
    if (!vals[0]) continue;
    rows.push(vals);
  }
  return { headers, rows };
}

function parseAdditionalMetrics(filepath) {
  if (!fs.existsSync(filepath)) return {};
  const raw = fs.readFileSync(filepath, "utf-8").trim();
  const lines = raw.split("\n").map(l => l.trim()).filter(Boolean);
  const m = {};
  let started = false;
  for (const line of lines) {
    if (line.startsWith("Additional Metrics")) { started = true; continue; }
    if (started) {
      const [k, v] = line.split(",").map(s => s.trim());
      if (k && v) m[k] = v;
    }
  }
  return m;
}

function parseNum(v) {
  if (!v || v === "") return null;
  const n = parseFloat(v.replace(/[%,]/g, ""));
  return isNaN(n) ? null : n;
}

// ─── Period converters ───
function marToFY(col) {
  const m = col.match(/^Mar (\d{4})$/);
  return m ? `FY${m[1].slice(-2)}` : col;
}
function sepToFY(col) {
  const m = col.match(/^Sep (\d{4})$/);
  return m ? `H1 FY${(parseInt(m[1]) + 1).toString().slice(-2)}` : col;
}
function quarterPeriod(col) {
  const m = col.match(/^(Jun|Sep|Dec|Mar)\s+(\d{4})$/);
  if (!m) return col;
  const [, mon, yr] = m;
  const y = parseInt(yr);
  const map = { Jun: `Q1 FY${(y+1).toString().slice(-2)}`, Sep: `Q2 FY${(y+1).toString().slice(-2)}`, Dec: `Q3 FY${(y+1).toString().slice(-2)}`, Mar: `Q4 FY${y.toString().slice(-2)}` };
  return map[mon] || col;
}

// ─── Metric maps ───
const PL = { "Sales +": "revenue", "Expenses +": "expenses", "Operating Profit": "operating_profit", "OPM %": "opm", "Other Income +": "other_income", "Interest": "interest", "Depreciation": "depreciation", "Profit before tax": "pbt", "Tax %": "tax_rate", "Net Profit +": "net_profit", "EPS in Rs": "eps", "Dividend Payout %": "dividend_payout" };
const BS = { "Equity Capital": "equity_capital", "Reserves": "reserves", "Borrowings +": "borrowings", "Other Liabilities +": "other_liabilities", "Total Liabilities": "total_liabilities", "Fixed Assets +": "fixed_assets", "CWIP": "cwip", "Investments": "investments", "Other Assets +": "other_assets", "Total Assets": "total_assets" };

function unit(k) {
  if (["opm","tax_rate","dividend_payout"].includes(k)) return "%";
  if (k === "eps") return "INR";
  return "INR Cr";
}

// ════════════════════════════════════════════
// 1. companies.json
// ════════════════════════════════════════════
const companies = [
  { id: "IHCL", name: "Indian Hotels Company Ltd", ticker_nse: "INDHOTEL", segment: "premium_luxury", strategy: "hybrid", brands: ["Taj","Vivanta","SeleQtions","Ginger"], key_markets: ["Mumbai","Delhi","Bengaluru","Goa"] },
  { id: "CHALET", name: "Chalet Hotels Ltd", ticker_nse: "CHALET", segment: "upper_midscale", strategy: "asset_heavy", brands: ["Marriott","Westin","Four Points","Novotel"], key_markets: ["Mumbai","Bengaluru","Hyderabad","Pune"] },
  { id: "LEMONTREE", name: "Lemon Tree Hotels Ltd", ticker_nse: "LEMONTREE", segment: "economy_midscale", strategy: "hybrid", brands: ["Aurika","Lemon Tree Premier","Lemon Tree","Red Fox","Keys"], key_markets: ["Delhi-NCR","Hyderabad","Mumbai","Bengaluru"] },
  { id: "EIH", name: "EIH Ltd (Oberoi Group)", ticker_nse: "EIHOTEL", segment: "premium_luxury", strategy: "asset_heavy", brands: ["Oberoi","Trident"], key_markets: ["Delhi","Mumbai","Udaipur","Agra"] },
  { id: "JUNIPER", name: "Juniper Hotels Ltd", ticker_nse: "JUNIPER", segment: "luxury_upper_upscale", strategy: "asset_heavy", brands: ["Grand Hyatt","Andaz","Hyatt Regency","Hyatt Place"], key_markets: ["Mumbai","Delhi","Ahmedabad","Lucknow"] },
];
fs.writeFileSync(path.join(OUT, "companies.json"), JSON.stringify(companies, null, 2));
console.log("✓ companies.json");

// ════════════════════════════════════════════
// 2. financials.json
// ════════════════════════════════════════════
const financials = [];

for (const [cid, folder] of Object.entries(COMPANY_MAP)) {
  const base = path.join(RAW, folder);

  // P&L annual
  const pl = parseCSV(path.join(base, "profit_loss.csv"));
  for (const row of pl.rows) {
    const metric = PL[row[0]];
    if (!metric) continue;
    for (let i = 1; i < pl.headers.length; i++) {
      if (pl.headers[i] === "TTM" || !row[i]) continue;
      const val = parseNum(row[i]);
      if (val === null) continue;
      const period = marToFY(pl.headers[i]);
      // calc yoy
      let yoy = null;
      if (i > 1) {
        const prev = parseNum(row[i - 1]);
        if (prev !== null && prev !== 0 && !["opm","tax_rate","dividend_payout"].includes(metric)) {
          yoy = Math.round(((val - prev) / Math.abs(prev)) * 1000) / 10;
        }
      }
      financials.push({
        id: randomUUID(), company_id: cid, period, period_type: "annual",
        metric, value: val, unit: unit(metric), yoy_change: yoy,
        source_document: `Screener.in — ${cid} profit_loss.csv`,
        source_page: null, source_timestamp: null, period_label: period,
      });
    }
  }

  // Additional metrics
  const addl = parseAdditionalMetrics(path.join(base, "profit_loss.csv"));
  for (const [k, v] of Object.entries(addl)) {
    const val = parseNum(v);
    if (val === null) continue;
    financials.push({
      id: randomUUID(), company_id: cid, period: "LTM", period_type: "annual",
      metric: k.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/_+$/, ""),
      value: val, unit: "%", yoy_change: null,
      source_document: `Screener.in — ${cid} profit_loss.csv`,
      source_page: null, source_timestamp: null, period_label: k,
    });
  }

  // Balance sheet
  const bs = parseCSV(path.join(base, "balance_sheet.csv"));
  for (const row of bs.rows) {
    const metric = BS[row[0]];
    if (!metric) continue;
    for (let i = 1; i < bs.headers.length; i++) {
      if (!row[i]) continue;
      const val = parseNum(row[i]);
      if (val === null) continue;
      let period = marToFY(bs.headers[i]);
      let ptype = "annual";
      if (bs.headers[i].startsWith("Sep")) {
        period = sepToFY(bs.headers[i]);
        ptype = "interim";
      }
      financials.push({
        id: randomUUID(), company_id: cid, period, period_type: ptype,
        metric, value: val, unit: "INR Cr", yoy_change: null,
        source_document: `Screener.in — ${cid} balance_sheet.csv`,
        source_page: null, source_timestamp: null, period_label: period,
      });
    }
  }

  // Quarterly
  const q = parseCSV(path.join(base, "Quarter_Analysis_Table.csv"));
  for (const row of q.rows) {
    const metric = PL[row[0]];
    if (!metric) continue;
    for (let i = 1; i < q.headers.length; i++) {
      if (!row[i]) continue;
      const val = parseNum(row[i]);
      if (val === null) continue;
      const period = quarterPeriod(q.headers[i]);
      financials.push({
        id: randomUUID(), company_id: cid, period, period_type: "quarterly",
        metric, value: val, unit: unit(metric), yoy_change: null,
        source_document: `Screener.in — ${cid} Quarter_Analysis_Table.csv`,
        source_page: null, source_timestamp: null, period_label: period,
      });
    }
  }

  console.log(`  ✓ ${cid}: ${financials.filter(f => f.company_id === cid).length} rows`);
}

fs.writeFileSync(path.join(OUT, "financials.json"), JSON.stringify(financials, null, 2));
console.log(`✓ financials.json (${financials.length} total rows)`);

// ════════════════════════════════════════════
// 3. scorecards.json (placeholder — will come from n8n pipeline)
// ════════════════════════════════════════════
const scorecards = [
  { id: randomUUID(), company_id: "IHCL", period: "FY25", dim_credibility: 58, dim_financial_quality: 79, dim_industry_position: 88, dim_risk: 65, composite_score: 71, confidence_level: "medium", evidence_summary: null },
  { id: randomUUID(), company_id: "CHALET", period: "FY25", dim_credibility: 72, dim_financial_quality: 68, dim_industry_position: 62, dim_risk: 55, composite_score: 65, confidence_level: "medium", evidence_summary: null },
  { id: randomUUID(), company_id: "LEMONTREE", period: "FY25", dim_credibility: 65, dim_financial_quality: 61, dim_industry_position: 54, dim_risk: 70, composite_score: 62, confidence_level: "medium", evidence_summary: null },
  { id: randomUUID(), company_id: "EIH", period: "FY25", dim_credibility: 81, dim_financial_quality: 74, dim_industry_position: 71, dim_risk: 78, composite_score: 76, confidence_level: "high", evidence_summary: null },
  { id: randomUUID(), company_id: "JUNIPER", period: "FY25", dim_credibility: 69, dim_financial_quality: 66, dim_industry_position: 58, dim_risk: 73, composite_score: 66, confidence_level: "medium", evidence_summary: null },
];
fs.writeFileSync(path.join(OUT, "scorecards.json"), JSON.stringify(scorecards, null, 2));
console.log("✓ scorecards.json");

// ════════════════════════════════════════════
// 4. guidance_claims.json (placeholder — from n8n pipeline)
// ════════════════════════════════════════════
const guidance_claims = [
  { id: randomUUID(), company_id: "IHCL", statement_quarter: "Q2 FY24", target_period: "FY25", metric_type: "revpar_growth", guidance_value_point: 15, unit: "%", verbatim_quote: "We expect RevPAR to grow 15% in FY25 driven by strong demand across our luxury portfolio.", confidence_language: "expect", speaker: "CEO", check_type: "check_1_revpar", source_document: "Q2 FY24 Earnings Call", source_page: null, source_timestamp: "12:41", verified: false },
  { id: randomUUID(), company_id: "IHCL", statement_quarter: "Q1 FY24", target_period: "FY26", metric_type: "new_room_additions", guidance_value_point: 2000, unit: "keys", verbatim_quote: "We will add 2,000 keys by FY26 across Taj, Vivanta and Ginger brands.", confidence_language: "will", speaker: "MD", check_type: "check_2_keys", source_document: "Q1 FY24 Earnings Call", source_page: null, source_timestamp: "08:15", verified: false },
  { id: randomUUID(), company_id: "IHCL", statement_quarter: "Q3 FY24", target_period: "FY24", metric_type: "revpar_driver", guidance_value_point: null, unit: null, verbatim_quote: "We are taking pricing across all properties — our premium positioning gives us that leverage.", confidence_language: "will", speaker: "CEO", check_type: "check_3_driver", source_document: "Q3 FY24 Earnings Call", source_page: null, source_timestamp: "14:02", verified: false },
  { id: randomUUID(), company_id: "IHCL", statement_quarter: "Q4 FY23", target_period: "FY24", metric_type: "ebitda_margin", guidance_value_point: 35, unit: "%", verbatim_quote: "We are confident of sustaining 35%+ EBITDA margins going forward.", confidence_language: "confident", speaker: "CFO", check_type: "check_4_fnb", source_document: "Q4 FY23 Earnings Call", source_page: null, source_timestamp: "22:10", verified: false },
  { id: randomUUID(), company_id: "IHCL", statement_quarter: "Q2 FY23", target_period: "FY24", metric_type: "debt_reduction", guidance_value_point: 0, unit: "INR Cr", verbatim_quote: "Our target remains to become net debt-free by end of FY24.", confidence_language: "targeting", speaker: "CFO", check_type: "check_5_debt", source_document: "Q2 FY23 Earnings Call", source_page: null, source_timestamp: "18:33", verified: false },
  { id: randomUUID(), company_id: "IHCL", statement_quarter: "Q1 FY24", target_period: "FY24", metric_type: "revenue_growth", guidance_value_low: 18, guidance_value_high: 20, guidance_value_point: null, unit: "%", verbatim_quote: "We are guiding for 18-20% revenue growth in FY24.", confidence_language: "expect", speaker: "CEO", check_type: "check_1_revpar", source_document: "Q1 FY24 Earnings Call", source_page: null, source_timestamp: "05:22", verified: false },
  { id: randomUUID(), company_id: "IHCL", statement_quarter: "Q3 FY23", target_period: "FY25", metric_type: "international_expansion", guidance_value_point: 5, unit: "properties", verbatim_quote: "We plan to open 5 new international Taj properties by FY25, including London and Dubai.", confidence_language: "plan", speaker: "MD", check_type: "check_2_keys", source_document: "Q3 FY23 Earnings Call", source_page: null, source_timestamp: "31:05", verified: false },
  { id: randomUUID(), company_id: "IHCL", statement_quarter: "Q2 FY24", target_period: "FY25", metric_type: "ginger_revpar", guidance_value_point: 3200, unit: "INR", verbatim_quote: "Ginger is on track for ₹3,200 RevPAR in FY25 — it's our fastest growing brand.", confidence_language: "expect", speaker: "CEO", check_type: "check_1_revpar", source_document: "Q2 FY24 Earnings Call", source_page: null, source_timestamp: "16:55", verified: false },
];
fs.writeFileSync(path.join(OUT, "guidance_claims.json"), JSON.stringify(guidance_claims, null, 2));
console.log("✓ guidance_claims.json");

// ════════════════════════════════════════════
// 5. deviation_tracker.json
// ════════════════════════════════════════════
const deviation_tracker = [
  { id: randomUUID(), guidance_id: guidance_claims[0].id, company_id: "IHCL", period: "FY25", metric_type: "revpar_growth", check_type: "check_1_revpar", guided_value: 15, actual_value: 9.2, delta: -5.8, delta_pct: -38.7, flag: "MISS", severity: "moderate", pattern: "3rd consecutive quarter of guidance miss on RevPAR", insight: "Management consistently over-projects pricing power in the luxury segment", source_guidance: "Q2 FY24 Earnings Call | 12:41", source_actual: "AR FY25 | Page 87" },
  { id: randomUUID(), guidance_id: guidance_claims[1].id, company_id: "IHCL", period: "FY26", metric_type: "new_room_additions", check_type: "check_2_keys", guided_value: 2000, actual_value: 1340, delta: -660, delta_pct: -33, flag: "MISS", severity: "major", pattern: "Room addition shortfall — 3 years running", insight: null, source_guidance: "Q1 FY24 Earnings Call | 08:15", source_actual: "AR FY26 | Page 34" },
  { id: randomUUID(), guidance_id: guidance_claims[2].id, company_id: "IHCL", period: "FY24", metric_type: "revpar_driver", check_type: "check_3_driver", guided_value: null, actual_value: null, delta: null, delta_pct: null, flag: "MISS", severity: "moderate", pattern: "Management claims ADR-led, but data shows occupancy-led growth", insight: "Occupancy +8pp, ADR flat YoY", source_guidance: "Q3 FY24 Earnings Call | 14:02", source_actual: "AR FY24 | Page 91" },
  { id: randomUUID(), guidance_id: guidance_claims[3].id, company_id: "IHCL", period: "FY24", metric_type: "ebitda_margin", check_type: "check_4_fnb", guided_value: 35, actual_value: 33.2, delta: -1.8, delta_pct: -5.1, flag: "MISS", severity: "minor", pattern: "F&B share rising from 28% to 36% — compressing margins", insight: null, source_guidance: "Q4 FY23 Earnings Call | 22:10", source_actual: "AR FY24 | P&L Statement" },
  { id: randomUUID(), guidance_id: guidance_claims[4].id, company_id: "IHCL", period: "FY24", metric_type: "debt_reduction", check_type: "check_5_debt", guided_value: 0, actual_value: 312, delta: 312, delta_pct: null, flag: "MISS", severity: "minor", pattern: null, insight: "Net debt: ₹312 Cr — target not achieved", source_guidance: "Q2 FY23 Earnings Call | 18:33", source_actual: "AR FY24 | Balance Sheet | Page 72" },
  { id: randomUUID(), guidance_id: guidance_claims[5].id, company_id: "IHCL", period: "FY24", metric_type: "revenue_growth", check_type: "check_1_revpar", guided_value: 19, actual_value: 16.2, delta: -2.8, delta_pct: -14.7, flag: "IN-LINE", severity: "none", pattern: null, insight: null, source_guidance: "Q1 FY24 Earnings Call | 05:22", source_actual: "AR FY24 | Page 12" },
  { id: randomUUID(), guidance_id: guidance_claims[6].id, company_id: "IHCL", period: "FY25", metric_type: "international_expansion", check_type: "check_2_keys", guided_value: 5, actual_value: 3, delta: -2, delta_pct: -40, flag: "MISS", severity: "moderate", pattern: null, insight: null, source_guidance: "Q3 FY23 Earnings Call | 31:05", source_actual: "AR FY25 | Page 28" },
  { id: randomUUID(), guidance_id: guidance_claims[7].id, company_id: "IHCL", period: "FY25", metric_type: "ginger_revpar", check_type: "check_1_revpar", guided_value: 3200, actual_value: 3450, delta: 250, delta_pct: 7.8, flag: "BEAT", severity: "none", pattern: null, insight: "Ginger outperformed guidance — economy segment demand strong", source_guidance: "Q2 FY24 Earnings Call | 16:55", source_actual: "AR FY25 | Page 44" },
];
fs.writeFileSync(path.join(OUT, "deviation_tracker.json"), JSON.stringify(deviation_tracker, null, 2));
console.log("✓ deviation_tracker.json");

// ════════════════════════════════════════════
// 6. risk_flags.json
// ════════════════════════════════════════════
const risk_flags = [
  { id: randomUUID(), company_id: "IHCL", category: "supply_overhang", check_type: "check_6_supply", description: "1,800 new 5-star keys under construction in Mumbai — IHCL derives 32% of revenue from Mumbai. Significant supply risk in core market.", severity: "high", verbatim_quote: "Mumbai accounts for approximately 32% of our consolidated room revenue.", source_document: "AR FY24 | Page 45 + Competitor DRHP | Page 88", source_page: 45, period: "FY24-FY26" },
  { id: randomUUID(), company_id: "IHCL", category: "margin_compression", check_type: "check_4_fnb", description: "F&B revenue share rising steadily (28% → 36% over 4 years). F&B has lower margins than rooms, silently compressing EBITDA despite healthy RevPAR.", severity: "high", verbatim_quote: null, source_document: "AR FY21-FY24 | Revenue Notes", source_page: null, period: "FY21-FY24" },
  { id: randomUUID(), company_id: "IHCL", category: "management_mismatch", check_type: "check_3_driver", description: "3 consecutive quarters of RevPAR guidance miss. Management consistently over-projects pricing power. Claims ADR-led growth but actual data shows occupancy-driven.", severity: "medium", verbatim_quote: null, source_document: "Earnings Calls Q1-Q3 FY24 vs AR FY24", source_page: null, period: "FY24" },
  { id: randomUUID(), company_id: "IHCL", category: "operational", check_type: "check_2_keys", description: "Room addition pipeline consistently under-delivers. Guided 2,000 keys by FY26, tracking at 1,340. Execution risk on expansion strategy.", severity: "medium", verbatim_quote: null, source_document: "Q1 FY24 Call | 08:15 vs AR FY26 | Page 34", source_page: null, period: "FY24-FY26" },
  { id: randomUUID(), company_id: "CHALET", category: "supply_overhang", check_type: "check_6_supply", description: "53% revenue from MMR (Mumbai Metropolitan Region). Supply pipeline in Mumbai with 1,800 new luxury keys threatens RevPAR.", severity: "high", verbatim_quote: null, source_document: "Chalet AR FY25 | Revenue Segment", source_page: null, period: "FY25" },
  { id: randomUUID(), company_id: "CHALET", category: "debt", check_type: "check_5_debt", description: "Net debt of ₹2,600 Cr with 8.4% interest rate. High leverage relative to peers for a single-operator hotel company.", severity: "medium", verbatim_quote: null, source_document: "Chalet AR FY25 | Balance Sheet", source_page: null, period: "FY25" },
  { id: randomUUID(), company_id: "JUNIPER", category: "operational", check_type: null, description: "Revenue heavily concentrated in Mumbai and Delhi. Grand Hyatt Mumbai and Andaz Delhi account for majority of revenue.", severity: "medium", verbatim_quote: null, source_document: "Juniper info | Revenue Concentration", source_page: null, period: "FY25" },
];
fs.writeFileSync(path.join(OUT, "risk_flags.json"), JSON.stringify(risk_flags, null, 2));
console.log("✓ risk_flags.json");

// ════════════════════════════════════════════
// 7. credibility_scores.json
// ════════════════════════════════════════════
const credibility_scores = [
  { id: randomUUID(), company_id: "IHCL", period: "FY22", overall_score: 74, hit_rate: 75, total_guidance_count: 4, consecutive_misses: 0, trend: "stable" },
  { id: randomUUID(), company_id: "IHCL", period: "FY23", overall_score: 65, hit_rate: 60, total_guidance_count: 6, consecutive_misses: 2, trend: "declining" },
  { id: randomUUID(), company_id: "IHCL", period: "FY24", overall_score: 58, hit_rate: 50, total_guidance_count: 8, consecutive_misses: 3, trend: "declining" },
  { id: randomUUID(), company_id: "IHCL", period: "FY25", overall_score: 58, hit_rate: 50, total_guidance_count: 8, consecutive_misses: 3, trend: "declining" },
];
fs.writeFileSync(path.join(OUT, "credibility_scores.json"), JSON.stringify(credibility_scores, null, 2));
console.log("✓ credibility_scores.json");

console.log("\n═══════════════════════════════════════");
console.log("Done! JSON files in ui/data/");
console.log("═══════════════════════════════════════");
