import { NextRequest, NextResponse } from "next/server";
import fs from "fs";
import path from "path";

export const dynamic = "force-dynamic";

type NewsItem = {
  title: string;
  url: string;
  source: string;
  published_date: string;
  summary_2line: string;
  company_tags: string[];
  dimension_primary: string;
  dimensions: string[];
  sentiment: string;
  market_scope: string;
  relevance_score: number;
  citation: string;
};

/* ── Hotel-sector relevance guard ────────────────────────── */
const HOTEL_KEYWORDS = [
  "hotel", "hotels", "hospitality", "revpar", "adr", "occupancy",
  "resort", "lodging", "ihcl", "taj hotel", "chalet hotel",
  "lemon tree", "eih", "oberoi", "juniper hotel",
  "marriott", "hyatt", "accor", "hilton",
  "hotelivate", "branded hotel", "hotel supply", "management contract",
  "asset light", "room night", "key addition", "hotel pipeline",
  "banquet", "f&b revenue", "room revenue", "hotel reit",
  "star hotel", "luxury hotel", "budget hotel",
];

const NOISE_PATTERNS = [
  "gold price", "silver price", "precious metal",
  "l&t ", " bel ", "defence stock", "solar industries",
  "tcs ceo", "infosys q", "wipro q", "f&o talk", "nifty's",
  "petrol", "diesel", "crude oil",
  "rupee's swing", "forex", "currency pair",
  "railway infra", "railway company",
  "cricket", "ipl", "bollywood", "viral video",
  "hindustan unilever", "hul q",
  "ibc", "insolvency code",
  "bitcoin", "cryptocurrency",
];

function isHotelRelevant(item: NewsItem): boolean {
  const combined = (item.title + " " + item.summary_2line).toLowerCase();
  // Hard-reject obvious off-topic noise
  if (NOISE_PATTERNS.some((p) => combined.includes(p))) return false;
  // Items with company tags are hotel-relevant (they passed pipeline detection)
  if (item.company_tags.length > 0) return true;
  // Non-company items must contain at least one hotel-sector keyword
  return HOTEL_KEYWORDS.some((k) => combined.includes(k));
}

function stripHtml(text: string): string {
  return (text || "").replace(/<[^>]*>/g, "").replace(/&nbsp;/g, " ").replace(/&amp;/g, "&").trim();
}

function normalizeCompanyId(id: string): string {
  if (id === "JUNIPERHOTELS") return "JUNIPER";
  return id;
}

export async function GET(request: NextRequest) {
  const digestPath = path.resolve(process.cwd(), "data", "news_digest.json");

  if (!fs.existsSync(digestPath)) {
    return NextResponse.json({ items: [], market_context: null, error: "No news digest available" });
  }

  try {
    const raw = JSON.parse(fs.readFileSync(digestPath, "utf-8"));
    const { searchParams } = new URL(request.url);
    const companyFilter = searchParams.get("company")?.toUpperCase();

    // Flatten all items
    const allItems: NewsItem[] = [];

    // Company items
    for (const [companyId, items] of Object.entries(raw.companies || {})) {
      const normalizedId = normalizeCompanyId(companyId);
      for (const item of items as Record<string, unknown>[]) {
        allItems.push({
          title: stripHtml(item.title as string),
          url: item.url as string,
          source: item.source as string,
          published_date: item.published_date as string,
          summary_2line: stripHtml((item.summary_2line || item.summary || "") as string),
          company_tags: ((item.company_tags || []) as string[]).map(normalizeCompanyId),
          dimension_primary: item.dimension_primary as string,
          dimensions: (item.dimensions || []) as string[],
          sentiment: item.sentiment as string,
          market_scope: "company",
          relevance_score: item.relevance_score as number,
          citation: item.citation as string,
        });
      }
    }

    // Sector items
    for (const item of (raw.sector_news || []) as Record<string, unknown>[]) {
      allItems.push({
        title: stripHtml(item.title as string),
        url: item.url as string,
        source: item.source as string,
        published_date: item.published_date as string,
        summary_2line: stripHtml((item.summary_2line || item.summary || "") as string),
        company_tags: ((item.company_tags || []) as string[]).map(normalizeCompanyId),
        dimension_primary: item.dimension_primary as string,
        dimensions: (item.dimensions || []) as string[],
        sentiment: item.sentiment as string,
        market_scope: "sector",
        relevance_score: item.relevance_score as number,
        citation: item.citation as string,
      });
    }

    // Global items
    for (const item of (raw.global_hospitality_news || []) as Record<string, unknown>[]) {
      allItems.push({
        title: stripHtml(item.title as string),
        url: item.url as string,
        source: item.source as string,
        published_date: item.published_date as string,
        summary_2line: stripHtml((item.summary_2line || item.summary || "") as string),
        company_tags: ((item.company_tags || []) as string[]).map(normalizeCompanyId),
        dimension_primary: item.dimension_primary as string,
        dimensions: (item.dimensions || []) as string[],
        sentiment: item.sentiment as string,
        market_scope: "global",
        relevance_score: item.relevance_score as number,
        citation: item.citation as string,
      });
    }

    // Deduplicate by URL
    const seen = new Set<string>();
    const deduped = allItems.filter((item) => {
      if (seen.has(item.url)) return false;
      seen.add(item.url);
      return true;
    });

    // Hotel-sector relevance gate + minimum quality score
    const hotelFiltered = deduped
      .filter(isHotelRelevant)
      .filter((item) => (item.relevance_score || 0) >= 4);

    // Filter by company if requested
    const filtered = companyFilter
      ? hotelFiltered.filter((item) => item.company_tags.includes(companyFilter) || item.market_scope !== "company")
      : hotelFiltered;

    // Sort by relevance
    filtered.sort((a, b) => (b.relevance_score || 0) - (a.relevance_score || 0));

    return NextResponse.json({
      items: filtered,
      market_context: raw.market_context,
      digest_date: raw.market_context?.as_of,
      total: filtered.length,
    });
  } catch (err) {
    console.error("[news] Error reading digest:", err);
    return NextResponse.json({ items: [], market_context: null, error: "Failed to parse digest" });
  }
}
