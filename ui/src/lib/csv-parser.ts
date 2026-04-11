import fs from "fs";
import path from "path";

// Base path to the Raw Data Extraction folder (sibling of ui/)
const RAW_DATA_ROOT = path.resolve(process.cwd(), "..", "Raw Data Extraction");

// Company folder mapping
export const COMPANY_FOLDERS: Record<string, string> = {
  IHCL: "Indian_Hotels",
  CHALET: "Chalet_Hotels",
  LEMONTREE: "Lemon_Tree_Hotels",
  EIH: "EIH_Limited",
  JUNIPER: "Juniper_Hotels",
};

export const COMPANY_META: Record<
  string,
  {
    name: string;
    ticker: string;
    segment: string;
    strategy: string;
    brands: string[];
    keyMarkets: string[];
    color: string;
    infoFile: string;
  }
> = {
  IHCL: {
    name: "Indian Hotels Company Ltd",
    ticker: "INDHOTEL",
    segment: "Premium / Luxury",
    strategy: "Hybrid (Asset-Heavy + Management Contracts)",
    brands: ["Taj", "Vivanta", "SeleQtions", "Ginger"],
    keyMarkets: ["Mumbai", "Delhi", "Bengaluru", "Goa"],
    color: "#1e3a5f",
    infoFile: "info_ihcl.txt",
  },
  CHALET: {
    name: "Chalet Hotels Ltd",
    ticker: "CHALET",
    segment: "Upper Midscale / Business",
    strategy: "Asset-Heavy",
    brands: ["Marriott", "Westin", "Four Points", "Novotel"],
    keyMarkets: ["Mumbai", "Bengaluru", "Hyderabad", "Pune"],
    color: "#6b4c9a",
    infoFile: "info_chaletHotels.txt",
  },
  LEMONTREE: {
    name: "Lemon Tree Hotels Ltd",
    ticker: "LEMONTREE",
    segment: "Economy / Midscale",
    strategy: "Hybrid (Owned + Managed/Franchised)",
    brands: ["Aurika", "Lemon Tree Premier", "Lemon Tree", "Red Fox", "Keys"],
    keyMarkets: ["Delhi-NCR", "Hyderabad", "Mumbai", "Bengaluru"],
    color: "#2d8544",
    infoFile: "info_lemonTree.txt",
  },
  EIH: {
    name: "EIH Ltd (Oberoi Group)",
    ticker: "EIHOTEL",
    segment: "Luxury",
    strategy: "Asset-Heavy",
    brands: ["Oberoi", "Trident"],
    keyMarkets: ["Delhi", "Mumbai", "Udaipur", "Agra"],
    color: "#8b6914",
    infoFile: "info_eih.txt",
  },
  JUNIPER: {
    name: "Juniper Hotels Ltd",
    ticker: "JUNIPER",
    segment: "Luxury / Upper Upscale",
    strategy: "Asset-Heavy (Hyatt Affiliated)",
    brands: ["Grand Hyatt", "Andaz", "Hyatt Regency", "Hyatt Place"],
    keyMarkets: ["Mumbai", "Delhi", "Ahmedabad", "Lucknow"],
    color: "#1a6b6b",
    infoFile: "info_juniper.txt",
  },
};

/**
 * Parse a CSV file into an array of objects.
 * First row = headers, subsequent rows = data.
 */
export function parseCSV(filePath: string): Record<string, string>[] {
  if (!fs.existsSync(filePath)) return [];
  const raw = fs.readFileSync(filePath, "utf-8").trim();
  const lines = raw.split("\n").map((l) => l.trim()).filter((l) => l.length > 0);
  if (lines.length < 2) return [];

  const headers = lines[0].split(",").map((h) => h.trim());
  const rows: Record<string, string>[] = [];

  for (let i = 1; i < lines.length; i++) {
    const vals = lines[i].split(",").map((v) => v.trim());
    // Stop if we hit the "Additional Metrics" section
    if (vals[0] === "Additional Metrics") break;
    const row: Record<string, string> = {};
    headers.forEach((h, j) => {
      row[h] = vals[j] || "";
    });
    rows.push(row);
  }
  return rows;
}

/**
 * Parse the "Additional Metrics" section from profit_loss.csv
 */
export function parseAdditionalMetrics(filePath: string): Record<string, string> {
  if (!fs.existsSync(filePath)) return {};
  const raw = fs.readFileSync(filePath, "utf-8").trim();
  const lines = raw.split("\n").map((l) => l.trim()).filter((l) => l.length > 0);

  const metrics: Record<string, string> = {};
  let inAdditional = false;
  for (const line of lines) {
    if (line.startsWith("Additional Metrics")) {
      inAdditional = true;
      continue;
    }
    if (inAdditional) {
      const parts = line.split(",");
      if (parts.length >= 2 && parts[0].trim()) {
        metrics[parts[0].trim()] = parts[1].trim();
      }
    }
  }
  return metrics;
}

/**
 * Read company info text file
 */
export function readInfoFile(companyId: string): string {
  const folder = COMPANY_FOLDERS[companyId];
  const meta = COMPANY_META[companyId];
  if (!folder || !meta) return "";
  const filePath = path.join(RAW_DATA_ROOT, folder, meta.infoFile);
  if (!fs.existsSync(filePath)) return "";
  return fs.readFileSync(filePath, "utf-8");
}

/**
 * Get file path for a company's CSV
 */
export function getCompanyCSVPath(companyId: string, csvName: string): string {
  const folder = COMPANY_FOLDERS[companyId];
  if (!folder) return "";
  return path.join(RAW_DATA_ROOT, folder, csvName);
}

/**
 * Get the latest annual period column name from CSV headers
 * e.g., "Mar 2025" from profit_loss.csv
 */
export function getLatestAnnualPeriod(headers: string[]): string {
  // Filter for "Mar YYYY" columns (annual data), pick the latest
  const marCols = headers.filter((h) => h.startsWith("Mar "));
  if (marCols.length === 0) return headers[headers.length - 1];
  return marCols[marCols.length - 1];
}

/**
 * Parse a numeric value from CSV (handles %, commas, empty)
 */
export function parseNum(val: string | undefined): number | null {
  if (!val || val === "") return null;
  const cleaned = val.replace(/[%,]/g, "").trim();
  const num = parseFloat(cleaned);
  return isNaN(num) ? null : num;
}

/**
 * Calculate YoY change between two periods
 */
export function calcYoY(current: number | null, previous: number | null): number | null {
  if (current === null || previous === null || previous === 0) return null;
  return Math.round(((current - previous) / Math.abs(previous)) * 1000) / 10;
}

/**
 * Get list of available company IDs
 */
export function getAvailableCompanies(): string[] {
  return Object.keys(COMPANY_FOLDERS).filter((id) => {
    const folder = COMPANY_FOLDERS[id];
    const dirPath = path.join(RAW_DATA_ROOT, folder);
    return fs.existsSync(dirPath);
  });
}
