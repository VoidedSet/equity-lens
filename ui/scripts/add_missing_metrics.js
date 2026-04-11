/**
 * One-time script: Extract sales + net_profit from Screener CSVs
 * and append to financials.json
 */
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

const RAW_DIR = path.resolve(__dirname, "../../Raw Data Extraction");
const FIN_PATH = path.resolve(__dirname, "../data/financials.json");
console.log("RAW_DIR:", RAW_DIR, "exists:", fs.existsSync(RAW_DIR));
console.log("FIN_PATH:", FIN_PATH, "exists:", fs.existsSync(FIN_PATH));

const COMPANIES = [
  { dir: "Indian_Hotels", id: "IHCL" },
  { dir: "Chalet_Hotels", id: "CHALET" },
  { dir: "Lemon_Tree_Hotels", id: "LEMONTREE" },
  { dir: "EIH_Limited", id: "EIH" },
  { dir: "Juniper_Hotels", id: "JUNIPER" },
];

function parseCSVRow(header, row) {
  const headerCols = header.split(",");
  const dataCols = row.split(",");
  const metricName = dataCols[0].trim();
  const entries = [];
  for (let i = 1; i < headerCols.length; i++) {
    const periodRaw = headerCols[i].trim();
    const valRaw = dataCols[i]?.trim();
    if (!valRaw || valRaw === "") continue;
    // Parse value — remove commas, handle percentages
    let value = parseFloat(valRaw.replace(/,/g, "").replace(/%/g, ""));
    if (isNaN(value)) continue;
    entries.push({ period: periodRaw, value });
  }
  return { metricName, entries };
}

function periodToFY(p) {
  if (p === "TTM") return "TTM";
  // "Mar 2024" -> "FY24"
  const m = p.match(/Mar (\d{4})/);
  if (m) return `FY${m[1].slice(2)}`;
  return p;
}

const existing = JSON.parse(fs.readFileSync(FIN_PATH, "utf-8"));
const newRows = [];

for (const co of COMPANIES) {
  const csvPath = path.join(RAW_DIR, co.dir, "profit_loss.csv");
  if (!fs.existsSync(csvPath)) { console.log(`SKIP ${co.id} — ${csvPath}`); continue; }
  console.log(`Processing ${co.id} from ${csvPath}`);
  const lines = fs.readFileSync(csvPath, "utf-8").split("\n").filter(l => l.trim());
  const header = lines[0];

  // Find Sales and Net Profit rows
  for (const line of lines.slice(1)) {
    const label = line.split(",")[0].replace(/\u00A0/g, " ").trim().toLowerCase();
    let metric = null;
    let unit = "INR Cr";
    if (label === "sales +" || label === "sales") metric = "revenue";
    else if (label === "net profit +" || label === "net profit") metric = "net_profit";
    else continue;

    const { entries } = parseCSVRow(header, line);
    // Sort by period for YoY calc
    const sorted = entries
      .map(e => ({ ...e, fy: periodToFY(e.period) }))
      .filter(e => e.fy !== "TTM");

    for (let i = 0; i < sorted.length; i++) {
      const e = sorted[i];
      let yoyChange = null;
      if (i > 0 && sorted[i - 1].value !== 0) {
        yoyChange = Math.round(((e.value - sorted[i - 1].value) / Math.abs(sorted[i - 1].value)) * 1000) / 10;
      }

      // Check if already exists
      const dup = existing.find(r => r.company_id === co.id && r.metric === metric && r.period === e.fy);
      if (dup) continue;

      newRows.push({
        id: crypto.randomUUID(),
        company_id: co.id,
        period: e.fy,
        period_type: "annual",
        metric,
        value: e.value,
        unit,
        yoy_change: yoyChange,
        source_document: `Screener.in — ${co.id} profit_loss.csv`,
        source_page: null,
        source_timestamp: null,
        period_label: e.fy,
      });
    }
  }
}

console.log(`Adding ${newRows.length} new rows (revenue + net_profit)`);
const merged = [...existing, ...newRows];
fs.writeFileSync(FIN_PATH, JSON.stringify(merged, null, 2));
console.log("Done. financials.json updated.");
