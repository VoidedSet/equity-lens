import hashlib
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import feedparser
import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
from dotenv import load_dotenv
from rapidfuzz import fuzz


# -----------------------------
# Configuration
# -----------------------------

COMPANIES: Dict[str, List[str]] = {
    "IHCL": ["ihcl", "indhotel", "indian hotels company", "taj hotels", "vivanta", "ginger hotels"],
    "CHALET": ["chalet hotels", "chalet hotels ltd", "chalet"],
    "LEMONTREE": ["lemon tree hotels", "lemontree", "red fox hotels", "keys select", "lemon tree"],
    "EIH": ["eih", "eih ltd", "eihotel", "oberoi hotels", "trident hotels", "oberoi"],
    "JUNIPERHOTELS": ["juniper hotels", "juniper", "juniper hotels ltd", "juniperhotels"],
}

SECTOR_KEYWORDS = [
    "indian hospitality",
    "india hotel sector",
    "revpar",
    "occupancy",
    "adr",
    "hotel pipeline",
    "new keys",
    "tourism policy",
    "mice",
]

GLOBAL_KEYWORDS = [
    "global hotel",
    "international hospitality",
    "marriott",
    "hilton",
    "hyatt",
    "ihg",
    "accor",
    "travel demand",
    "interest rates",
]

# PRD checks: each retained item must map to at least one check dimension.
DIMENSION_KEYWORDS: Dict[str, List[str]] = {
    "check_1_revpar_guidance": ["revpar", "guidance", "actual", "miss", "beat", "outlook"],
    "check_2_room_additions": ["room additions", "new keys", "hotel opening", "expansion", "pipeline", "greenfield"],
    "check_3_occupancy_vs_adr": ["occupancy", "adr", "average daily rate", "pricing", "demand driver"],
    "check_4_fnb_mix_margin": ["f&b", "food and beverage", "banquet", "mix", "ebitda margin", "margin pressure"],
    "check_5_debt_coverage": ["debt", "interest coverage", "finance cost", "leverage", "refinancing", "borrowings"],
    "check_6_supply_overhang": ["new supply", "pipeline", "city supply", "oversupply", "new rooms", "market share pressure"],
}

# Secondary mapping so broader market events are still anchored to PRD checks.
DIMENSION_RULE_MAP: Dict[str, List[str]] = {
    "check_1_revpar_guidance": ["earnings", "results", "guidance", "outlook", "estimate"],
    "check_2_room_additions": ["opening", "launch", "expansion", "pipeline", "new hotel", "new property"],
    "check_3_occupancy_vs_adr": ["demand", "pricing", "premium", "occupancy", "adr", "travel demand"],
    "check_4_fnb_mix_margin": ["margin", "profitability", "f&b", "banquet", "food and beverage"],
    "check_5_debt_coverage": ["debt", "borrowings", "finance cost", "interest", "leverage", "refinancing"],
    "check_6_supply_overhang": ["policy", "regulatory", "sebi", "city supply", "new supply", "oversupply", "tourism policy"],
}

MATERIAL_EVENT_KEYWORDS = [
    "earnings",
    "results",
    "guidance",
    "management commentary",
    "analyst",
    "rating",
    "downgrade",
    "upgrade",
    "merger",
    "acquisition",
    "m&a",
    "regulatory",
    "sebi",
    "exchange filing",
]

EXCLUDE_PATTERNS = [
    "press release",
    "pr newswire",
    "business wire",
    "globenewswire",
    "sponsored",
    "advertorial",
]

POSITIVE_TERMS = [
    "beat",
    "upgrade",
    "strong",
    "growth",
    "expansion",
    "improved",
    "record",
    "outperform",
    "higher",
    "upside",
]

NEGATIVE_TERMS = [
    "miss",
    "downgrade",
    "weak",
    "decline",
    "fall",
    "cut",
    "risk",
    "concern",
    "pressure",
    "default",
]

WATCH_TERMS = [
    "investigation",
    "regulatory",
    "audit",
    "pledge",
    "contingent",
    "litigation",
    "governance",
]

MANDATORY_EVIDENCE_FIELDS = [
    "title",
    "source",
    "url",
    "published_date",
    "dimension_primary",
    "citation",
]

STATE_DIR = Path("./.state")
IR_SNAPSHOT_FILE = STATE_DIR / "ir_snapshots.json"

GOOGLE_ALERT_RSS_URLS = {
    
    "IHCL": ["https://www.google.com/alerts/feeds/04191294896868538319/8586775691101841511"],
    "CHALET": ["https://www.google.com/alerts/feeds/04191294896868538319/13259870219700882078"],
    "LEMONTREE": ["https://www.google.com/alerts/feeds/04191294896868538319/6548937527860729422"],
    "EIH": ["https://www.google.com/alerts/feeds/04191294896868538319/17349074703165784150"],
    "JUNIPERHOTELS": ["https://www.google.co.in/alerts/feeds/04191294896868538319/6548937527860729577"],
    "SECTOR": ["https://www.google.com/alerts/feeds/04191294896868538319/6548937527860731455"],
    "GLOBAL": ["https://www.google.co.in/alerts/feeds/04191294896868538319/9092356338574221853"],

}

PUBLISHER_RSS_FEEDS = [
    "https://economictimes.indiatimes.com/industry/services/hotels-/-restaurants/rssfeeds/13359484.cms",
    "https://www.business-standard.com/rss/companies-101.rss",
    "https://www.livemint.com/rss/companies",
    "https://www.moneycontrol.com/rss/business.xml",
]

# Exchange/disclosure focused channels.
EXCHANGE_AND_DISCLOSURE_FEEDS = [
    "https://www.moneycontrol.com/rss/results.xml",
    "https://www.moneycontrol.com/rss/business.xml",
]

# Credit/rating watch channels for leverage and refinancing signal.
RATING_AND_CREDIT_FEEDS = [
    "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "https://www.business-standard.com/rss/finance-103.rss",
]

# Policy and regulation channels affecting hospitality demand/supply/margins.
POLICY_AND_REGULATION_FEEDS = [
    "https://pib.gov.in/rss.aspx?mincode=31",  # Ministry of Tourism PIB releases
    "https://economictimes.indiatimes.com/news/economy/policy/rssfeeds/1715249553.cms",
]

# Tourism and travel demand channels.
TOURISM_AND_DEMAND_FEEDS = [
    "https://economictimes.indiatimes.com/industry/transportation/airlines-/-aviation/rssfeeds/134466308.cms",
    "https://www.moneycontrol.com/rss/economy.xml",
]

# Hotel supply and city pipeline channels.
SUPPLY_INTELLIGENCE_FEEDS = [
    "https://economictimes.indiatimes.com/industry/services/property-/-cstruction/rssfeeds/8153388.cms",
    "https://www.business-standard.com/rss/companies-101.rss",
]

# Global hospitality channels for macro and peer signal.
GLOBAL_HOSPITALITY_FEEDS = [
    "https://news.marriott.com/rss.xml",
    "https://stories.hilton.com/rss",
    "https://www.traveldailynews.com/feed/",
    "https://skift.com/feed/",
]

# Company IR URLs for change-detection (new decks/transcripts/announcements).
IR_MONITOR_URLS: Dict[str, List[str]] = {
    "IHCL": [
        "https://www.ihcltata.com/investors",
    ],
    "CHALET": [
        "https://www.chalethotels.com/investor-relations/",
    ],
    "LEMONTREE": [
        "https://www.lemontreehotels.com/investors",
    ],
    "EIH": [
        "https://www.eihltd.com/investors",
    ],
    "JUNIPERHOTELS": [
        "https://www.juniperhotels.com/investor-relations",
    ],
}

FALLBACK_SCRAPE_URLS = [
    "https://www.moneycontrol.com/news/business/companies/",
    "https://economictimes.indiatimes.com/industry/services/hotels-/-restaurants",
]

NEWSAPI_ENDPOINT = "https://newsapi.org/v2/everything"
BING_DEFAULT_ENDPOINT = "https://api.bing.microsoft.com/v7.0/news/search"


# -----------------------------
# Utilities
# -----------------------------


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def normalize_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url.strip())

    # Google feeds often wrap real links in /url?url=... or /url?q=...
    if "google.com" in parsed.netloc and parsed.path == "/url":
        raw_qs = dict(parse_qsl(parsed.query, keep_blank_values=True))
        candidate = raw_qs.get("url") or raw_qs.get("q")
        if candidate:
            parsed = urlparse(candidate)

    query_pairs = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if not k.lower().startswith("utm_")]
    clean_query = urlencode(query_pairs)
    normalized = parsed._replace(fragment="", query=clean_query)
    clean = urlunparse(normalized)
    if clean.endswith("/"):
        clean = clean[:-1]
    return clean.lower()


def safe_parse_date(value: str) -> str:
    if not value:
        return datetime.now(timezone.utc).date().isoformat()
    try:
        dt = date_parser.parse(value)
        return dt.date().isoformat()
    except Exception:
        return datetime.now(timezone.utc).date().isoformat()


def request_with_retry(url: str, params: Optional[dict] = None, headers: Optional[dict] = None, timeout: int = 20, retries: int = 3) -> Optional[requests.Response]:
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=timeout)
            if resp.status_code >= 500:
                raise requests.HTTPError(f"Server error {resp.status_code}")
            return resp
        except Exception as exc:
            last_error = exc
            backoff = 1.5 * attempt
            print(f"[warn] request failed ({attempt}/{retries}) for {url}: {exc}")
            if attempt < retries:
                time.sleep(backoff)
    print(f"[error] source unavailable after retries: {url}. last_error={last_error}")
    return None


def get_user_agent() -> str:
    return os.getenv("USER_AGENT", "EquityLensNewsBot/1.0 (+contact: team@equitylens.local)")


def load_ir_snapshots() -> Dict[str, dict]:
    if not IR_SNAPSHOT_FILE.exists():
        return {}
    try:
        with IR_SNAPSHOT_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception as exc:
        print(f"[warn] could not read IR snapshot state: {exc}")
    return {}


def save_ir_snapshots(snapshots: Dict[str, dict]) -> None:
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        with IR_SNAPSHOT_FILE.open("w", encoding="utf-8") as f:
            json.dump(snapshots, f, indent=2, ensure_ascii=False)
    except Exception as exc:
        print(f"[warn] could not persist IR snapshot state: {exc}")


def text_for_scoring(item: dict) -> str:
    return " ".join(
        [
            item.get("title", ""),
            item.get("summary", ""),
            item.get("content", ""),
            item.get("source", ""),
        ]
    ).lower()


def detect_companies(text: str) -> List[str]:
    found = []
    for code, aliases in COMPANIES.items():
        if any(alias in text for alias in aliases):
            found.append(code)
    return found


def score_dimensions(text: str) -> Tuple[List[str], int]:
    scores = {}
    for dim, words in DIMENSION_KEYWORDS.items():
        hits = sum(1 for w in words if w in text)
        if hits > 0:
            scores[dim] = hits

    # Add softer rule mapping when direct check keywords are sparse.
    for dim, words in DIMENSION_RULE_MAP.items():
        rule_hits = sum(1 for w in words if w in text)
        if rule_hits > 0:
            scores[dim] = scores.get(dim, 0) + rule_hits

    ordered = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    dims = [k for k, _ in ordered]
    return dims, sum(scores.values())


def score_materiality(text: str) -> int:
    return sum(1 for k in MATERIAL_EVENT_KEYWORDS if k in text)


def is_press_release_like(text: str) -> bool:
    return any(p in text for p in EXCLUDE_PATTERNS)


def classify_linguistic_sentiment(text: str) -> str:
    pos = sum(1 for t in POSITIVE_TERMS if t in text)
    neg = sum(1 for t in NEGATIVE_TERMS if t in text)
    watch = sum(1 for t in WATCH_TERMS if t in text)

    if watch > 0 and abs(pos - neg) <= 1:
        return "Watch"
    if pos - neg >= 2:
        return "Positive"
    if neg - pos >= 2:
        return "Negative"
    return "Neutral"


def classify_investment_impact(text: str, dimensions: List[str], linguistic_sentiment: str) -> str:
    # Hard risk override for governance/regulatory/debt stress signals.
    hard_risk_terms = [
        "investigation",
        "forensic",
        "fraud",
        "governance",
        "audit qualification",
        "default",
        "debt stress",
        "pledged",
        "downgrade",
    ]
    if any(t in text for t in hard_risk_terms):
        return "Watch"

    # Debt and coverage headlines tend to be downside unless explicitly improving.
    if "check_5_debt_coverage" in dimensions:
        if any(t in text for t in ["reduction in debt", "improved coverage", "refinanced at lower cost"]):
            return "Neutral"
        if any(t in text for t in ["higher finance cost", "rising debt", "coverage pressure", "leverage concern"]):
            return "Negative"

    # Positive investment impact for strong operational + guidance signals.
    if any(t in text for t in ["guidance raised", "beat estimates", "strong demand", "occupancy improvement", "adr growth"]):
        return "Positive"

    # Supply overhang tends to be cautionary.
    if "check_6_supply_overhang" in dimensions and any(t in text for t in ["new supply", "pipeline", "oversupply"]):
        return "Watch"

    return linguistic_sentiment


def two_line_summary(text: str, max_len: int = 280) -> str:
    clean = normalize_whitespace(text)
    if not clean:
        return "No summary available from source payload."
    if len(clean) <= max_len:
        return clean
    clipped = clean[: max_len - 3].rstrip()
    return f"{clipped}..."


def citation(item: dict) -> str:
    return f"[{item['source']} | {item['url']} | {item['published_date']}]"


def item_hash(item: dict) -> str:
    key = f"{normalize_url(item.get('url', ''))}|{normalize_whitespace(item.get('title', '')).lower()}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()


def content_signature(item: dict) -> str:
    # Signature is useful for cross-source syndicated duplicates.
    title = normalize_whitespace(item.get("title", "")).lower()
    summary = normalize_whitespace(item.get("summary", "")).lower()
    pub_date = item.get("published_date", "")
    base = f"{title}|{summary[:140]}|{pub_date}"
    return hashlib.sha1(base.encode("utf-8")).hexdigest()


def stage_two_relevance_check(item: dict, text: str, dimensions: List[str], dim_score: int, materiality: int, companies: List[str]) -> Tuple[bool, float, str]:
    # Stage-2 classifier (deterministic) to reduce noisy headlines after stage-1 keyword pass.
    hard_signal = dim_score + materiality + len(companies)
    noise = 2 if is_press_release_like(text) else 0
    specificity = 2 if any(k in text for k in ["revpar", "occupancy", "adr", "ebitda", "debt", "guidance"]) else 0
    confidence = max(0.0, min(1.0, (hard_signal + specificity - noise) / 10.0))

    if not dimensions:
        return False, confidence, "no_dimension_mapping"
    if confidence < 0.35:
        return False, confidence, "low_stage2_confidence"
    return True, confidence, "accepted"


def collect_rss_channel_items(feed_urls: List[str], channel_name: str, bucket: str) -> List[dict]:
    items = []
    for rss_url in feed_urls:
        feed = feedparser.parse(rss_url)
        if feed.bozo:
            print(f"[warn] {channel_name} rss parse issue: {rss_url}")
        for entry in feed.entries:
            source_name = channel_name
            if getattr(entry, "source", None) and isinstance(entry.source, dict):
                source_name = entry.source.get("title", source_name)
            items.append(
                {
                    "title": normalize_whitespace(getattr(entry, "title", "")),
                    "url": getattr(entry, "link", ""),
                    "source": source_name,
                    "published_date": safe_parse_date(getattr(entry, "published", "")),
                    "summary": normalize_whitespace(getattr(entry, "summary", "")),
                    "content": normalize_whitespace(getattr(entry, "summary", "")),
                    "bucket": bucket,
                }
            )
    return items


# -----------------------------
# Source adapters
# -----------------------------


def collect_google_alert_items() -> List[dict]:
    items = []
    for bucket, urls in GOOGLE_ALERT_RSS_URLS.items():
        for rss_url in urls:
            feed = feedparser.parse(rss_url)
            if feed.bozo:
                print(f"[warn] google alert rss parse issue: {rss_url}")
            for entry in feed.entries:
                items.append(
                    {
                        "title": normalize_whitespace(getattr(entry, "title", "")),
                        "url": getattr(entry, "link", ""),
                        "source": "Google Alerts RSS",
                        "published_date": safe_parse_date(getattr(entry, "published", "")),
                        "summary": normalize_whitespace(getattr(entry, "summary", "")),
                        "content": normalize_whitespace(getattr(entry, "summary", "")),
                        "bucket": bucket,
                    }
                )
    return items


def collect_publisher_rss_items() -> List[dict]:
    items = []
    for rss_url in PUBLISHER_RSS_FEEDS:
        feed = feedparser.parse(rss_url)
        if feed.bozo:
            print(f"[warn] publisher rss parse issue: {rss_url}")
        for entry in feed.entries:
            source_name = "RSS"
            if getattr(entry, "source", None) and isinstance(entry.source, dict):
                source_name = entry.source.get("title", "RSS")
            items.append(
                {
                    "title": normalize_whitespace(getattr(entry, "title", "")),
                    "url": getattr(entry, "link", ""),
                    "source": source_name,
                    "published_date": safe_parse_date(getattr(entry, "published", "")),
                    "summary": normalize_whitespace(getattr(entry, "summary", "")),
                    "content": normalize_whitespace(getattr(entry, "summary", "")),
                    "bucket": "PUBLISHER_RSS",
                }
            )
    return items


def collect_newsapi_items(newsapi_key: str) -> List[dict]:
    if not newsapi_key:
        print("[info] NEWSAPI_KEY missing, skipping NewsAPI source")
        return []

    query = '("IHCL" OR "Chalet Hotels" OR "Lemon Tree Hotels" OR "EIH" OR "Juniper Hotels" OR "Indian hospitality" OR "hotel sector India")'
    params = {
        "q": query,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 100,
    }
    headers = {"X-Api-Key": newsapi_key}
    resp = request_with_retry(NEWSAPI_ENDPOINT, params=params, headers=headers)
    if not resp:
        return []

    try:
        payload = resp.json()
    except Exception:
        print("[warn] invalid JSON from NewsAPI")
        return []

    articles = payload.get("articles", [])
    items = []
    for a in articles:
        items.append(
            {
                "title": normalize_whitespace(a.get("title", "")),
                "url": a.get("url", ""),
                "source": (a.get("source") or {}).get("name", "NewsAPI"),
                "published_date": safe_parse_date(a.get("publishedAt", "")),
                "summary": normalize_whitespace(a.get("description", "")),
                "content": normalize_whitespace(a.get("content", "")),
                "bucket": "NEWSAPI",
            }
        )
    return items


def collect_bing_items(bing_key: str, bing_endpoint: str) -> List[dict]:
    if not bing_key:
        print("[info] BING_NEWS_API_KEY missing, skipping Bing source")
        return []

    query = "IHCL OR Chalet Hotels OR Lemon Tree Hotels OR EIH OR Juniper Hotels OR Indian hospitality hotel sector"
    params = {
        "q": query,
        "count": 50,
        "mkt": "en-IN",
        "safeSearch": "Moderate",
        "sortBy": "Date",
    }
    headers = {"Ocp-Apim-Subscription-Key": bing_key}
    resp = request_with_retry(bing_endpoint, params=params, headers=headers)
    if not resp:
        return []

    try:
        payload = resp.json()
    except Exception:
        print("[warn] invalid JSON from Bing")
        return []

    items = []
    for a in payload.get("value", []):
        provider = "Bing News"
        providers = a.get("provider") or []
        if providers and isinstance(providers, list):
            provider = providers[0].get("name", provider)
        items.append(
            {
                "title": normalize_whitespace(a.get("name", "")),
                "url": a.get("url", ""),
                "source": provider,
                "published_date": safe_parse_date(a.get("datePublished", "")),
                "summary": normalize_whitespace(a.get("description", "")),
                "content": normalize_whitespace(a.get("description", "")),
                "bucket": "BING",
            }
        )
    return items


def collect_fallback_scrape_items() -> List[dict]:
    items = []
    for page_url in FALLBACK_SCRAPE_URLS:
        resp = request_with_retry(page_url)
        if not resp:
            continue
        soup = BeautifulSoup(resp.text, "html.parser")
        links = soup.find_all("a", href=True)
        for a in links[:250]:
            title = normalize_whitespace(a.get_text(" ", strip=True))
            href = a["href"].strip()
            if not title or len(title) < 25:
                continue
            if href.startswith("/"):
                parsed = urlparse(page_url)
                href = f"{parsed.scheme}://{parsed.netloc}{href}"
            text = title.lower()
            if not any(k in text for k in ["hotel", "hospitality", "tourism", "revpar", "occupancy", "adr"]):
                continue
            items.append(
                {
                    "title": title,
                    "url": href,
                    "source": f"Scrape:{urlparse(page_url).netloc}",
                    "published_date": datetime.now(timezone.utc).date().isoformat(),
                    "summary": title,
                    "content": title,
                    "bucket": "SCRAPE",
                }
            )
    return items


def collect_exchange_disclosure_items() -> List[dict]:
    return collect_rss_channel_items(EXCHANGE_AND_DISCLOSURE_FEEDS, "Exchange/Disclosure", "EXCHANGE_DISCLOSURE")


def collect_rating_credit_items() -> List[dict]:
    return collect_rss_channel_items(RATING_AND_CREDIT_FEEDS, "Rating/Credit", "RATING_CREDIT")


def collect_policy_regulation_items() -> List[dict]:
    return collect_rss_channel_items(POLICY_AND_REGULATION_FEEDS, "Policy/Regulation", "POLICY_REGULATION")


def collect_tourism_demand_items() -> List[dict]:
    return collect_rss_channel_items(TOURISM_AND_DEMAND_FEEDS, "Tourism/Demand", "TOURISM_DEMAND")


def collect_supply_intelligence_items() -> List[dict]:
    return collect_rss_channel_items(SUPPLY_INTELLIGENCE_FEEDS, "Supply Intelligence", "SUPPLY_INTEL")


def collect_global_hospitality_items() -> List[dict]:
    return collect_rss_channel_items(GLOBAL_HOSPITALITY_FEEDS, "Global Hospitality", "GLOBAL_HOSPITALITY")


def collect_ir_change_items() -> List[dict]:
    snapshots = load_ir_snapshots()
    updated_snapshots = dict(snapshots)
    items: List[dict] = []

    headers = {"User-Agent": get_user_agent()}
    today = datetime.now(timezone.utc).date().isoformat()

    for company, urls in IR_MONITOR_URLS.items():
        for ir_url in urls:
            resp = request_with_retry(ir_url, headers=headers, timeout=20, retries=2)
            if not resp:
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            page_title = normalize_whitespace(soup.title.text if soup.title else company)
            text_blob = normalize_whitespace(soup.get_text(" ", strip=True))[:5000]
            html_hash = hashlib.sha1(text_blob.encode("utf-8")).hexdigest()

            key = f"{company}|{ir_url}"
            prev = snapshots.get(key, {})
            prev_hash = prev.get("hash")

            updated_snapshots[key] = {
                "hash": html_hash,
                "last_seen_utc": utc_now_iso(),
                "url": ir_url,
                "company": company,
            }

            # Emit only if baseline already existed and content changed.
            if prev_hash and prev_hash != html_hash:
                items.append(
                    {
                        "title": f"{company} IR update detected: {page_title}",
                        "url": ir_url,
                        "source": "IR Change Monitor",
                        "published_date": today,
                        "summary": "Investor relations page content changed since previous run. Review for new transcript/deck/filing links.",
                        "content": text_blob[:800],
                        "bucket": "IR_CHANGE",
                    }
                )

    save_ir_snapshots(updated_snapshots)
    return items


# -----------------------------
# Processing pipeline
# -----------------------------


def enrich_and_filter(raw_items: List[dict]) -> Tuple[List[dict], dict]:
    processed = []
    stats = {
        "input_items": len(raw_items),
        "dropped_missing_title_or_url": 0,
        "dropped_press_release": 0,
        "dropped_no_dimension": 0,
        "dropped_low_relevance": 0,
        "dropped_stage2": 0,
        "accepted": 0,
    }
    for item in raw_items:
        title = normalize_whitespace(item.get("title", ""))
        url = normalize_url(item.get("url", ""))
        if not title or not url:
            stats["dropped_missing_title_or_url"] += 1
            continue

        doc_text = text_for_scoring(item)
        if is_press_release_like(doc_text):
            stats["dropped_press_release"] += 1
            continue

        companies = detect_companies(doc_text)
        dimensions, dim_score = score_dimensions(doc_text)
        materiality = score_materiality(doc_text)

        # Each retained item must map to at least one PRD check.
        if not dimensions:
            stats["dropped_no_dimension"] += 1
            continue

        relevance_score = dim_score * 2 + materiality + (2 if companies else 0)
        if relevance_score < 3:
            stats["dropped_low_relevance"] += 1
            continue

        keep_stage2, stage2_confidence, stage2_reason = stage_two_relevance_check(
            item=item,
            text=doc_text,
            dimensions=dimensions,
            dim_score=dim_score,
            materiality=materiality,
            companies=companies,
        )
        if not keep_stage2:
            stats["dropped_stage2"] += 1
            continue

        market_scope = "company" if companies else "sector"
        if any(k in doc_text for k in GLOBAL_KEYWORDS):
            market_scope = "global"
        elif any(k in doc_text for k in SECTOR_KEYWORDS):
            market_scope = "sector"

        linguistic = classify_linguistic_sentiment(doc_text)
        investment = classify_investment_impact(doc_text, dimensions, linguistic)

        merged = {
            **item,
            "title": title,
            "url": url,
            "published_date": safe_parse_date(item.get("published_date", "")),
            "company_tags": companies,
            "dimensions": dimensions,
            "dimension_primary": dimensions[0],
            "relevance_score": relevance_score,
            "stage2_confidence": round(stage2_confidence, 3),
            "stage2_reason": stage2_reason,
            "linguistic_sentiment": linguistic,
            "investment_impact_sentiment": investment,
            "sentiment": investment,
            "market_scope": market_scope,
        }
        merged["summary_2line"] = two_line_summary(merged.get("summary", "") or merged.get("content", ""))
        merged["citation"] = citation(merged)
        merged["uid"] = item_hash(merged)
        merged["content_signature"] = content_signature(merged)
        processed.append(merged)
        stats["accepted"] += 1

    return processed, stats


def deduplicate(items: List[dict]) -> Tuple[List[dict], dict]:
    # Step 1: exact dedupe by normalized URL + title hash
    seen = set()
    exact = []
    exact_dupe_count = 0
    for item in items:
        if item["uid"] in seen:
            exact_dupe_count += 1
            continue
        seen.add(item["uid"])
        exact.append(item)

    # Step 2: content-signature dedupe for syndicated rewrites on same date.
    sig_seen = set()
    signature_dedupe = []
    signature_dupe_count = 0
    for item in exact:
        key = f"{item.get('published_date','')}|{item.get('content_signature','')}"
        if key in sig_seen:
            signature_dupe_count += 1
            continue
        sig_seen.add(key)
        signature_dedupe.append(item)

    # Step 3: fuzzy title dedupe on same publication date
    deduped: List[dict] = []
    fuzzy_dupe_count = 0
    for item in signature_dedupe:
        duplicate = False
        for kept in deduped:
            if item["published_date"] != kept["published_date"]:
                continue
            title_sim = fuzz.token_set_ratio(item["title"], kept["title"])
            if title_sim >= 92:
                duplicate = True
                break
        if not duplicate:
            deduped.append(item)
        else:
            fuzzy_dupe_count += 1

    stats = {
        "input_items": len(items),
        "exact_duplicates_removed": exact_dupe_count,
        "signature_duplicates_removed": signature_dupe_count,
        "fuzzy_duplicates_removed": fuzzy_dupe_count,
        "output_items": len(deduped),
    }
    return deduped, stats


def enforce_evidence_gate(items: List[dict]) -> Tuple[List[dict], dict]:
    valid_items = []
    dropped = Counter()

    for item in items:
        missing = [f for f in MANDATORY_EVIDENCE_FIELDS if not str(item.get(f, "")).strip()]
        if not item.get("dimensions"):
            missing.append("dimensions")

        if missing:
            dropped["missing_required_fields"] += 1
            for field in missing:
                dropped[f"missing_{field}"] += 1
            continue

        valid_items.append(item)

    return valid_items, dict(dropped)


def build_digest(items: List[dict], as_of_date: str) -> dict:
    company_sections = {k: [] for k in COMPANIES.keys()}
    sector_section = []
    global_section = []

    for item in sorted(items, key=lambda x: (x["published_date"], x["relevance_score"]), reverse=True):
        if item["company_tags"]:
            for company in item["company_tags"]:
                company_sections[company].append(item)
        elif item["market_scope"] == "global":
            global_section.append(item)
        else:
            sector_section.append(item)

    sentiment_counts = Counter(i["sentiment"] for i in items)
    market_context = {
        "as_of": as_of_date,
        "total_items": len(items),
        "sentiment_distribution": dict(sentiment_counts),
        "top_dimensions": dict(Counter(d for i in items for d in i["dimensions"]).most_common(6)),
    }

    digest = {
        "market_context": market_context,
        "companies": company_sections,
        "sector_news": sector_section,
        "global_hospitality_news": global_section,
        "metadata": {
            "generated_at_utc": utc_now_iso(),
            "citation_format": "[Source | URL | Date]",
            "check_dimensions": list(DIMENSION_KEYWORDS.keys()),
        },
    }
    return digest


def render_markdown(digest: dict) -> str:
    mc = digest["market_context"]
    lines = []
    lines.append(f"# EquityLens Daily News Digest - {mc['as_of']}")
    lines.append("")
    lines.append("## Market Context")
    lines.append(f"- Total material items: {mc['total_items']}")
    lines.append(f"- Sentiment mix: {mc['sentiment_distribution']}")
    lines.append(f"- Top PRD dimensions: {mc['top_dimensions']}")
    lines.append("")

    lines.append("## Company Coverage")
    for company, items in digest["companies"].items():
        lines.append("")
        lines.append(f"### {company}")
        if not items:
            lines.append("- No material items found today.")
            continue
        for item in items[:12]:
            lines.append(
                f"- {item['title']} | Sentiment: {item['sentiment']} | Dimension: {item['dimension_primary']} | {item['citation']}"
            )
            lines.append(f"  Summary: {item['summary_2line']}")

    lines.append("")
    lines.append("## Sector News")
    if not digest["sector_news"]:
        lines.append("- No material sector items found today.")
    else:
        for item in digest["sector_news"][:15]:
            lines.append(
                f"- {item['title']} | Sentiment: {item['sentiment']} | Dimension: {item['dimension_primary']} | {item['citation']}"
            )
            lines.append(f"  Summary: {item['summary_2line']}")

    lines.append("")
    lines.append("## Global Hospitality")
    if not digest["global_hospitality_news"]:
        lines.append("- No material global items found today.")
    else:
        for item in digest["global_hospitality_news"][:15]:
            lines.append(
                f"- {item['title']} | Sentiment: {item['sentiment']} | Dimension: {item['dimension_primary']} | {item['citation']}"
            )
            lines.append(f"  Summary: {item['summary_2line']}")

    return "\n".join(lines)


def write_outputs(digest: dict, output_dir: Path, as_of_date: str) -> Tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"daily_digest_{as_of_date}.json"
    md_path = output_dir / f"daily_digest_{as_of_date}.md"

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(digest, f, indent=2, ensure_ascii=False)

    with md_path.open("w", encoding="utf-8") as f:
        f.write(render_markdown(digest))

    return json_path, md_path


def write_health_report(health: dict, output_dir: Path, as_of_date: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    health_path = output_dir / f"pipeline_health_{as_of_date}.json"
    with health_path.open("w", encoding="utf-8") as f:
        json.dump(health, f, indent=2, ensure_ascii=False)
    return health_path


# -----------------------------
# Entrypoint
# -----------------------------


def run_pipeline() -> int:
    load_dotenv()

    newsapi_key = os.getenv("NEWSAPI_KEY", "").strip()
    bing_key = os.getenv("BING_NEWS_API_KEY", "").strip()
    bing_endpoint = os.getenv("BING_NEWS_ENDPOINT", BING_DEFAULT_ENDPOINT).strip() or BING_DEFAULT_ENDPOINT

    as_of_date = datetime.now(timezone.utc).date().isoformat()
    output_dir = Path(os.getenv("OUTPUT_DIR", "./output"))

    all_items: List[dict] = []
    source_stats = {}

    # Independent source failures should not block the pipeline.
    source_collectors = [
        ("google_alerts", collect_google_alert_items),
        ("publisher_rss", collect_publisher_rss_items),
        ("exchange_disclosure", collect_exchange_disclosure_items),
        ("rating_credit", collect_rating_credit_items),
        ("policy_regulation", collect_policy_regulation_items),
        ("tourism_demand", collect_tourism_demand_items),
        ("supply_intel", collect_supply_intelligence_items),
        ("global_hospitality", collect_global_hospitality_items),
        ("ir_change_monitor", collect_ir_change_items),
        ("newsapi", lambda: collect_newsapi_items(newsapi_key)),
        ("bing", lambda: collect_bing_items(bing_key, bing_endpoint)),
        ("fallback_scrape", collect_fallback_scrape_items),
    ]

    for source_name, collector in source_collectors:
        start = time.time()
        try:
            items = collector()
            all_items.extend(items)
            source_stats[source_name] = {
                "status": "ok",
                "items": len(items),
                "duration_sec": round(time.time() - start, 3),
            }
            print(f"[info] collected {len(items)} raw items from {source_name}")
        except Exception as exc:
            source_stats[source_name] = {
                "status": "failed",
                "items": 0,
                "duration_sec": round(time.time() - start, 3),
                "error": str(exc),
            }
            print(f"[error] source failed ({source_name}) but pipeline continues: {exc}")

    if not all_items:
        print("[warn] no raw items collected from any source")

    raw_bucket_counts = dict(Counter(i.get("bucket", "UNKNOWN") for i in all_items))

    filtered, filter_stats = enrich_and_filter(all_items)
    deduped, dedupe_stats = deduplicate(filtered)
    evidence_safe, evidence_drop_stats = enforce_evidence_gate(deduped)

    final_bucket_counts = dict(Counter(i.get("bucket", "UNKNOWN") for i in evidence_safe))

    digest = build_digest(evidence_safe, as_of_date)
    json_path, md_path = write_outputs(digest, output_dir, as_of_date)

    health_report = {
        "as_of_date": as_of_date,
        "generated_at_utc": utc_now_iso(),
        "source_stats": source_stats,
        "bucket_counts_raw": raw_bucket_counts,
        "bucket_counts_final": final_bucket_counts,
        "filter_stats": filter_stats,
        "dedupe_stats": dedupe_stats,
        "evidence_gate_drops": evidence_drop_stats,
        "counts": {
            "raw": len(all_items),
            "filtered": len(filtered),
            "deduped": len(deduped),
            "evidence_safe": len(evidence_safe),
        },
    }
    health_path = write_health_report(health_report, output_dir, as_of_date)

    print(
        f"[done] raw={len(all_items)} filtered={len(filtered)} deduped={len(deduped)} evidence_safe={len(evidence_safe)}"
    )
    print(f"[done] json: {json_path}")
    print(f"[done] markdown: {md_path}")
    print(f"[done] health: {health_path}")

    return 0


if __name__ == "__main__":
    sys.exit(run_pipeline())
