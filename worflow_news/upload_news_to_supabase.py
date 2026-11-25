"""
Upload news digest JSON to Supabase news_items table.
Creates the table if it doesn't exist, then inserts today's digest.

Usage: python upload_news_to_supabase.py
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

# Load env from parent pipeline dir
load_dotenv(Path(__file__).parent.parent / "pdf extraction pipeline" / ".env")

try:
    from supabase import create_client
except ImportError:
    create_client = None  # type: ignore[assignment]

OUTPUT_DIR = Path(__file__).parent / "output"

# Company ID normalization (pipeline uses JUNIPERHOTELS, legacy uses ITCHOTELS, DB uses JUNIPER)
COMPANY_ID_MAP = {
    "JUNIPERHOTELS": "JUNIPER",
    "ITCHOTELS": "JUNIPER",
    "IHCL": "IHCL",
    "CHALET": "CHALET",
    "LEMONTREE": "LEMONTREE",
    "EIH": "EIH",
}


def get_supabase():
    """Lazily create Supabase client from environment variables."""
    if create_client is None:
        raise ImportError("supabase package is required for news upload")
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables are required")
    return create_client(url, key)


def create_news_table(supabase_client=None):
    """Create news_items table via Supabase SQL."""
    supabase_client = supabase_client or get_supabase()
    sql = """
    CREATE TABLE IF NOT EXISTS news_items (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        title TEXT NOT NULL,
        url TEXT,
        source TEXT,
        published_date DATE,
        summary TEXT,
        company_tags TEXT[],
        dimension_primary TEXT,
        dimensions TEXT[],
        sentiment TEXT CHECK (sentiment IN ('Positive', 'Negative', 'Neutral', 'Watch')),
        investment_impact TEXT,
        relevance_score FLOAT,
        citation TEXT,
        market_scope TEXT,
        bucket TEXT,
        digest_date DATE,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    """
    try:
        supabase_client.rpc("exec_sql", {"query": sql}).execute()
        print("  Created news_items table via RPC")
    except Exception as e:
        # RPC might not exist - try direct insert to test if table exists
        print(f"  Note: RPC not available ({e}). Table may already exist or needs manual creation.")
        print(f"  Run this SQL in Supabase SQL Editor:\n{sql}")


def load_latest_digest():
    """Find and load the most recent digest JSON."""
    jsons = sorted(OUTPUT_DIR.glob("daily_digest_*.json"), reverse=True)
    if not jsons:
        print("No digest files found in output/")
        return None, None
    latest = jsons[0]
    date_str = latest.stem.replace("daily_digest_", "")
    print(f"  Loading: {latest.name}")
    with open(latest, "r", encoding="utf-8") as f:
        return json.load(f), date_str


def normalize_company_tags(tags):
    """Map JUNIPERHOTELS / ITCHOTELS → JUNIPER etc."""
    return [COMPANY_ID_MAP.get(t, t) for t in (tags or [])]


def extract_digest_items(digest: dict) -> list:
    """Extract and deduplicate items from both current and legacy digest JSON layouts."""
    raw_items = list(digest.get("all_items") or [])
    if not raw_items:
        for section in (
            "companies",
            "sector_news",
            "global_hospitality_news",
            "company_sections",
            "sector_items",
            "global_items",
        ):
            items = digest.get(section, [])
            if isinstance(items, dict):
                for company_items in items.values():
                    if isinstance(company_items, list):
                        raw_items.extend(company_items)
            elif isinstance(items, list):
                raw_items.extend(items)

    deduped = []
    seen = set()
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        dedup_key = (str(item.get("url") or "").strip().lower(), str(item.get("title") or "").strip().lower())
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        deduped.append(item)
    return deduped


def upload_digest(digest, digest_date, supabase_client=None):
    """Upload all items from a digest to Supabase."""
    supabase_client = supabase_client or get_supabase()
    all_items = extract_digest_items(digest)

    if not all_items:
        print("  No items found in digest")
        return 0

    print(f"  Found {len(all_items)} items to upload")

    # Clear old news for this date
    try:
        supabase_client.table("news_items").delete().eq("digest_date", digest_date).execute()
        print(f"  Cleared old items for {digest_date}")
    except Exception as e:
        print(f"  Note clearing old items: {e}")

    inserted = 0
    for item in all_items:
        row = {
            "title": (item.get("title") or "")[:500],
            "url": item.get("url"),
            "source": item.get("source"),
            "published_date": item.get("published_date"),
            "summary": (item.get("summary_2line") or item.get("summary") or "")[:1000],
            "company_tags": normalize_company_tags(item.get("company_tags", [])),
            "dimension_primary": item.get("dimension_primary"),
            "dimensions": item.get("dimensions", []),
            "sentiment": item.get("sentiment", "Neutral"),
            "investment_impact": item.get("investment_impact_sentiment", item.get("sentiment", "Neutral")),
            "relevance_score": item.get("relevance_score"),
            "citation": item.get("citation"),
            "market_scope": item.get("market_scope"),
            "bucket": item.get("bucket"),
            "digest_date": digest_date,
        }
        try:
            supabase_client.table("news_items").insert(row).execute()
            inserted += 1
        except Exception as e:
            print(f"  Error inserting: {e}")

    return inserted


def main():
    print("=" * 60)
    print("EquityLens AI — News Digest → Supabase Upload")
    print("=" * 60)

    client = get_supabase()

    # Step 1: Try to create table
    print("\n[1] Ensuring news_items table exists...")
    create_news_table(client)

    # Step 2: Load latest digest
    print("\n[2] Loading latest digest...")
    digest, digest_date = load_latest_digest()
    if not digest:
        sys.exit(1)

    # Step 3: Upload
    print(f"\n[3] Uploading to Supabase (date: {digest_date})...")
    count = upload_digest(digest, digest_date, supabase_client=client)
    print(f"\n  Done! {count} news items uploaded.")


if __name__ == "__main__":
    main()
