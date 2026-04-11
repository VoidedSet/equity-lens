"""
Entity Extractor
================
Dictionary-based entity extraction from text chunks.
Extracts: topics, brands, locations, strategies, metrics, people, time periods.
Detects co-occurrences within same paragraph for edge creation.
"""

import re
from collections import defaultdict


# ============================================================
# ENTITY DICTIONARIES
# ============================================================

TOPIC_KEYWORDS = {
    # Financial metrics
    "Revenue": ["revenue", "sales", "top line", "topline", "income from operations"],
    "EBITDA": ["ebitda", "operating profit", "ebitda margin"],
    "Net Profit": ["net profit", "pat", "profit after tax", "bottom line", "net income"],
    "Operating Margin": ["operating margin", "opm", "op margin"],
    "Occupancy": ["occupancy", "occupancy rate", "occupancy level"],
    "RevPAR": ["revpar", "rev par", "revenue per available room"],
    "ADR": ["adr", "average daily rate", "average room rate", "arr"],
    "Debt": ["debt", "borrowing", "leverage", "net debt", "gross debt"],
    "Interest Coverage": ["interest coverage", "icr", "debt service"],
    "ROE": ["roe", "return on equity"],
    "ROCE": ["roce", "return on capital employed"],
    "Cash Flow": ["cash flow", "free cash flow", "fcf", "operating cash flow", "cash generation"],
    "Dividend": ["dividend", "payout", "dividend yield"],
    "EPS": ["eps", "earnings per share"],
    "Book Value": ["book value", "net worth", "shareholders equity"],
    "Working Capital": ["working capital", "current assets", "current liabilities"],
    "Capex": ["capex", "capital expenditure", "capital spend"],
    "Depreciation": ["depreciation", "amortization", "d&a"],

    # Business metrics
    "Room Inventory": ["room inventory", "keys", "number of rooms", "total rooms", "hotel rooms"],
    "New Openings": ["new openings", "new hotels", "new properties", "opened", "launched"],
    "Pipeline": ["pipeline", "upcoming", "under development", "under construction"],
    "F&B": ["food and beverage", "f&b", "restaurant", "dining", "banquet", "catering"],
    "MICE": ["mice", "meetings", "incentives", "conferences", "exhibitions"],
    "Weddings": ["wedding", "social events", "celebrations"],
    "Loyalty Program": ["loyalty", "membership", "rewards program", "frequent guest"],
    "Digital": ["digital", "online", "app", "technology", "website", "direct booking"],
    "Customer Satisfaction": ["guest satisfaction", "nps", "guest experience", "service quality"],

    # Strategic themes
    "Expansion": ["expansion", "growth strategy", "scale up", "new markets"],
    "Acquisition": ["acquisition", "acquire", "takeover", "buyout", "merge"],
    "Asset Light": ["asset light", "management contract", "franchise", "managed hotels"],
    "Brand Portfolio": ["brand", "portfolio", "brand architecture", "rebrand"],
    "Sustainability": ["sustainability", "esg", "green", "carbon", "environment", "renewable"],
    "International": ["international", "global", "overseas", "foreign", "export"],
    "Premium Segment": ["luxury", "premium", "upscale", "five star", "5 star"],
    "Budget Segment": ["budget", "economy", "mid-scale", "affordable", "value"],
    "Renovation": ["renovation", "refurbishment", "upgrade", "modernization"],
    "Cost Optimization": ["cost optimization", "cost reduction", "efficiency", "cost control"],
    "Tourism": ["tourism", "travel", "domestic tourism", "inbound tourism", "outbound"],
    "Government Policy": ["government", "policy", "regulation", "gst", "tax", "subsidy"],
    "Competition": ["competition", "competitor", "market share", "competitive"],
    "Risk": ["risk", "challenge", "headwind", "uncertainty", "threat"],
    "Guidance": ["guidance", "outlook", "forecast", "target", "vision"],
    "Credit Rating": ["credit rating", "rating", "upgrade", "downgrade", "icra", "crisil", "fitch"],
}

BRAND_KEYWORDS = {
    # IHCL brands
    "Taj": ["taj hotels", "taj ", "the taj"],
    "Vivanta": ["vivanta"],
    "SeleQtions": ["seleqtions"],
    "Ginger": ["ginger hotels", "ginger"],
    "amã Stays": ["ama stays", "amã", "ama stays & trails"],
    "TajSATS": ["tajsats", "taj sats"],
    "Qmin": ["qmin"],

    # EIH brands
    "Oberoi": ["oberoi", "the oberoi"],
    "Trident": ["trident"],

    # Lemon Tree brands
    "Lemon Tree Premier": ["lemon tree premier"],
    "Lemon Tree": ["lemon tree hotel"],
    "Red Fox": ["red fox"],
    "Keys Hotels": ["keys hotel", "keys prima", "keys select", "keys lite"],
    "Aurika": ["aurika"],

    # Chalet brands
    "Marriott": ["marriott", "jw marriott"],
    "Westin": ["westin"],
    "Renaissance": ["renaissance"],
    "Four Points": ["four points"],
    "Novotel": ["novotel"],
    "Dukes Retreat": ["dukes retreat"],

    # Juniper brands
    "Hyatt": ["hyatt", "hyatt regency", "grand hyatt"],
    "Hyatt Centric": ["hyatt centric"],
}

LOCATION_KEYWORDS = {
    "Mumbai": ["mumbai", "bombay"],
    "Delhi": ["delhi", "new delhi", "ncr", "gurugram", "gurgaon", "noida"],
    "Bengaluru": ["bengaluru", "bangalore"],
    "Chennai": ["chennai", "madras"],
    "Kolkata": ["kolkata", "calcutta"],
    "Hyderabad": ["hyderabad"],
    "Pune": ["pune"],
    "Goa": ["goa"],
    "Jaipur": ["jaipur", "rajasthan"],
    "Udaipur": ["udaipur"],
    "Kochi": ["kochi", "kerala", "trivandrum"],
    "Ahmedabad": ["ahmedabad", "gujarat"],
    "Varanasi": ["varanasi"],
    "Agra": ["agra"],
    "Lucknow": ["lucknow"],
    "London": ["london"],
    "Dubai": ["dubai", "uae"],
    "New York": ["new york"],
    "San Francisco": ["san francisco"],
    "Singapore": ["singapore"],
    "Sri Lanka": ["sri lanka", "colombo"],
    "Nepal": ["nepal", "kathmandu"],
    "Maldives": ["maldives"],
    "Thailand": ["thailand", "bangkok"],
    "Cape Town": ["cape town"],
}

STRATEGY_KEYWORDS = {
    "Asset Light Model": ["asset light", "management contract", "franchise model"],
    "Premiumization": ["premiumization", "move upscale", "luxury focus", "premium positioning"],
    "Digital Transformation": ["digital transformation", "tech stack", "digitization", "digital first"],
    "Cost Leadership": ["cost leadership", "lowest cost", "cost advantage"],
    "Aggressive Expansion": ["aggressive expansion", "rapid growth", "fast track", "accelerate growth"],
    "Debt Reduction": ["deleveraging", "debt reduction", "reduce debt", "pay down debt"],
    "Brand Consolidation": ["brand consolidation", "brand rationalization", "portfolio optimization"],
    "International Expansion": ["international expansion", "global footprint", "overseas growth"],
    "Brownfield Development": ["brownfield", "renovation", "asset renovation"],
    "Greenfield Development": ["greenfield", "new build", "ground up"],
    "Strategic Partnership": ["strategic partnership", "joint venture", "jv", "collaboration", "tie-up"],
    "Divestment": ["divestment", "divest", "sell off", "exit"],
}

# Map company codes to display names
COMPANY_NAMES = {
    "CHALET": "Chalet Hotels",
    "EIH": "EIH Limited",
    "IHCL": "Indian Hotels",
    "JUNIPER": "Juniper Hotels",
    "LEMONTREE": "Lemon Tree Hotels",
}


# ============================================================
# TIME PERIOD EXTRACTION
# ============================================================

TIME_PATTERNS = [
    r'FY\s*\'?\d{2,4}',           # FY24, FY'24, FY2024
    r'Q[1-4]\s*FY\s*\'?\d{2,4}',  # Q3 FY25
    r'H[12]\s*FY\s*\'?\d{2,4}',   # H1 FY2024
    r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}',  # Mar 2025
    r'\d{4}-\d{2,4}',              # 2024-25
]


def extract_time_periods(text: str) -> list:
    """Extract fiscal/calendar time references."""
    periods = set()
    for pattern in TIME_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for m in matches:
            periods.add(m.strip())
    return list(periods)


# ============================================================
# NUMERIC METRIC EXTRACTION
# ============================================================

METRIC_PATTERNS = [
    # INR X crore/crores
    (r'(?:INR|Rs\.?|₹)\s*([\d,]+\.?\d*)\s*(?:crore|crores|cr)', "amount_crore"),
    # X% or X percent
    (r'(\d+\.?\d*)\s*(?:%|percent|basis points|bps)', "percentage"),
    # X rooms/keys
    (r'([\d,]+)\s*(?:rooms|keys|properties|hotels)', "count"),
]


def extract_metrics(text: str) -> list:
    """Extract numeric metrics with context."""
    metrics = []
    for pattern, mtype in METRIC_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            value = match.group(1).replace(',', '')
            # Get surrounding context (30 chars before and after)
            start = max(0, match.start() - 40)
            end = min(len(text), match.end() + 40)
            context = text[start:end].strip()
            metrics.append({
                "value": value,
                "type": mtype,
                "context": context,
                "position": match.start(),
            })
    return metrics


# ============================================================
# ENTITY EXTRACTION CORE
# ============================================================

def extract_entities_from_chunk(chunk: dict) -> dict:
    """
    Extract all entities from a single text chunk.
    Returns: {entity_type: [(entity_name, metadata), ...]}
    """
    text = chunk.get("text", "")
    text_lower = text.lower()
    company = chunk.get("company", "")

    entities = defaultdict(list)

    # Add company as entity
    if company in COMPANY_NAMES:
        entities["COMPANY"].append((COMPANY_NAMES[company], {"code": company}))

    # Extract topics
    for topic, keywords in TOPIC_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                entities["TOPIC"].append((topic, {"keyword": kw}))
                break  # one match per topic enough

    # Extract brands
    for brand, keywords in BRAND_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                entities["BRAND"].append((brand, {"keyword": kw}))
                break

    # Extract locations
    for loc, keywords in LOCATION_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                entities["LOCATION"].append((loc, {"keyword": kw}))
                break

    # Extract strategies
    for strat, keywords in STRATEGY_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                entities["STRATEGY"].append((strat, {"keyword": kw}))
                break

    # Extract time periods
    time_refs = extract_time_periods(text)
    for t in time_refs:
        entities["TIME_PERIOD"].append((t, {}))

    # Extract speakers (from transcripts)
    speaker = chunk.get("speaker", "")
    if speaker and speaker != "Unknown" and len(speaker) < 80:
        # Filter out non-person speaker fields
        if not any(x in speaker.lower() for x in ["http", "page", "bse", "nse", "limited"]):
            entities["PERSON"].append((speaker, {"role": "speaker"}))

    # Extract numeric metrics
    metrics = extract_metrics(text)
    for m in metrics:
        entities["METRIC"].append((f"{m['value']} ({m['type']})", m))

    return dict(entities)


def extract_cooccurrences(entities: dict) -> list:
    """
    Generate co-occurrence edges from entities found in same chunk.
    Each pair of non-same-type entities = potential edge.
    """
    edges = []
    all_entities = []
    for etype, elist in entities.items():
        for ename, emeta in elist:
            all_entities.append((etype, ename))

    # Create edges between entities of different types
    seen = set()
    for i, (type1, name1) in enumerate(all_entities):
        for j, (type2, name2) in enumerate(all_entities):
            if i >= j:
                continue
            if type1 == type2 and type1 == "METRIC":
                continue  # skip metric-metric edges (too noisy)
            edge_key = tuple(sorted([(type1, name1), (type2, name2)]))
            if edge_key not in seen:
                seen.add(edge_key)
                edges.append({
                    "source": (type1, name1),
                    "target": (type2, name2),
                })
    return edges


def get_recency_score(period: str) -> float:
    """Score how recent a period is (higher = more recent)."""
    period_lower = period.lower() if period else ""
    if "2026" in period_lower or "fy27" in period_lower:
        return 1.0
    elif "2025" in period_lower or "fy26" in period_lower:
        return 0.9
    elif "2024" in period_lower or "fy25" in period_lower:
        return 0.8
    elif "2023" in period_lower or "fy24" in period_lower:
        return 0.7
    elif "2022" in period_lower or "fy23" in period_lower:
        return 0.6
    else:
        return 0.4


if __name__ == "__main__":
    # Quick test
    test_chunk = {
        "text": "IHCL delivered record performance with 29% revenue growth and EBITDA margin expansion to 39.4% in Q3 FY25. The company opened 5 new hotels including a Taj in Goa and Vivanta in Bengaluru. We expect occupancy to remain at 78-80% going forward.",
        "company": "IHCL",
        "speaker": "Puneet Chhatwal",
        "period": "Feb 2025",
        "doc_type": "call_transcript",
    }
    entities = extract_entities_from_chunk(test_chunk)
    for etype, elist in entities.items():
        print(f"\n{etype}:")
        for name, meta in elist:
            print(f"  - {name}")

    edges = extract_cooccurrences(entities)
    print(f"\nCo-occurrence edges: {len(edges)}")
