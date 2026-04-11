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

    // Filter by company if requested
    const filtered = companyFilter
      ? deduped.filter((item) => item.company_tags.includes(companyFilter) || item.market_scope !== "company")
      : deduped;

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
