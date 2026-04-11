"""
Deviation Computer — Said vs Delivered
Joins guidance_claims + financials → deviation_tracker
Computes: delta, delta_pct, BEAT/MISS/IN-LINE flag, severity, patterns
Run this AFTER ingestion of all transcripts + annual reports for a company.

Usage:
  python deviation_computer.py --company IHCL
  python deviation_computer.py --all
"""

import argparse
from typing import Dict, List, Optional
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_SERVICE_KEY, COMPANIES


def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


# ─────────────────────────────────────────────────────────────────
# MATCHING LOGIC
# Match guidance_claims to financials by (company, metric, period)
# ─────────────────────────────────────────────────────────────────

METRIC_ALIASES = {
    "revpar":          ["revpar", "rev par", "revenue per available room"],
    "adr":             ["adr", "average daily rate", "average room rate", "arr"],
    "occupancy":       ["occupancy", "occupancy rate", "occupancy %"],
    "revenue":         ["revenue", "total revenue", "total income"],
    "ebitda":          ["ebitda", "operating profit"],
    "ebitda_margin":   ["ebitda margin", "ebitda %", "operating margin"],
    "pat":             ["pat", "net profit", "profit after tax"],
    "debt":            ["debt", "borrowings", "total debt", "net debt"],
    "interest_coverage": ["interest coverage", "interest cover", "icr"],
    "room_count":      ["room_count", "rooms", "keys", "room additions", "new keys", "properties"],
    "fnb_share":       ["fnb share", "f&b share", "f&b revenue %"],
    "capex":           ["capex", "capital expenditure"],
}

# Map guidance metric_type → financials metric names
GUIDANCE_TO_FINANCIAL_METRIC = {
    "revpar":         "revpar",
    "adr":            "adr",
    "occupancy":      "occupancy",
    "revenue":        "revenue",
    "ebitda_margin":  "ebitda_margin",
    "rooms_keys":     "room_count",
    "capex":          "capex",
    "debt":           "debt",
    "interest_coverage": "interest_coverage",
    "fnb_revenue":    "fnb_share",
    "properties":     "room_count",
}

# In-line threshold: within ±5% of guided value = IN-LINE
INLINE_THRESHOLD_PCT = 5.0


def normalise_period(period: str) -> str:
    """Normalise period strings for matching: 'FY 2024' → 'FY24', 'Q2 FY24' → 'Q2FY24'."""
    if not period:
        return ""
    p = period.upper().strip()
    p = p.replace("FY 20", "FY").replace("FY20", "FY")
    p = p.replace(" ", "")
    return p


def compute_flag(guided: float, actual: float) -> tuple:
    """
    Returns (flag, delta, delta_pct, severity).
    flag: BEAT | MISS | IN-LINE
    """
    if guided == 0:
        return "IN-LINE", 0.0, 0.0, "none"

    delta = actual - guided
    delta_pct = (delta / abs(guided)) * 100

    if abs(delta_pct) <= INLINE_THRESHOLD_PCT:
        flag = "IN-LINE"
        severity = "none"
    elif delta_pct > 0:
        flag = "BEAT"
        severity = "none" if delta_pct < 10 else "minor"
    else:
        flag = "MISS"
        if abs(delta_pct) < 10:
            severity = "minor"
        elif abs(delta_pct) < 20:
            severity = "moderate"
        elif abs(delta_pct) < 35:
            severity = "major"
        else:
            severity = "critical"

    return flag, round(delta, 4), round(delta_pct, 2), severity


def detect_pattern(company_id: str, metric_type: str,
                   existing_deviations: List[Dict]) -> Optional[str]:
    """Look for consecutive MISS or BEAT patterns for the same metric."""
    relevant = [
        d for d in existing_deviations
        if d["company_id"] == company_id and d["metric_type"] == metric_type
    ]
    if len(relevant) < 2:
        return None

    # Sort by period
    relevant.sort(key=lambda x: x.get("period", ""))
    flags = [d["flag"] for d in relevant[-3:]]  # last 3

    if all(f == "MISS" for f in flags):
        return f"{len(flags)}rd consecutive MISS on {metric_type}" if len(flags) == 3 else f"{len(flags)} consecutive MISSes on {metric_type}"
    if all(f == "BEAT" for f in flags):
        return f"{len(flags)} consecutive BEATs on {metric_type}"

    return None


# ─────────────────────────────────────────────────────────────────
# MAIN COMPUTATION
# ─────────────────────────────────────────────────────────────────

def compute_deviations_for_company(company_id: str, supabase: Client) -> int:
    """
    Load all guidance_claims + financials for a company.
    Attempt to match them. Insert matched pairs into deviation_tracker.
    Returns count of deviations computed.
    """
    print(f"\n[Deviation] Computing for {company_id} ...")

    # Load guidance claims
    guid_resp = supabase.table("guidance_claims") \
        .select("*") \
        .eq("company_id", company_id) \
        .execute()
    guidance_rows = guid_resp.data or []

    # Load financials
    fin_resp = supabase.table("financials") \
        .select("*") \
        .eq("company_id", company_id) \
        .execute()
    financials_rows = fin_resp.data or []

    # Load existing deviations (for pattern detection)
    dev_resp = supabase.table("deviation_tracker") \
        .select("company_id, metric_type, period, flag") \
        .eq("company_id", company_id) \
        .execute()
    existing_devs = dev_resp.data or []

    print(f"  Guidance claims: {len(guidance_rows)}")
    print(f"  Financial rows : {len(financials_rows)}")

    # Build financials lookup: {(metric, normalised_period): row}
    fin_lookup: Dict = {}
    for fin in financials_rows:
        metric = fin.get("metric", "")
        period = normalise_period(fin.get("period", ""))
        fin_lookup[(metric, period)] = fin

    inserted = 0
    for guid in guidance_rows:
        metric_type = guid.get("metric_type", "")
        target_period = normalise_period(guid.get("target_period", ""))
        guided_val = guid.get("guidance_value_point")
        if guided_val is None:
            # Use midpoint of range if available
            lo = guid.get("guidance_value_low")
            hi = guid.get("guidance_value_high")
            if lo is not None and hi is not None:
                guided_val = (float(lo) + float(hi)) / 2
        if guided_val is None:
            continue  # can't compute without a number

        # Find matching financial metric
        fin_metric = GUIDANCE_TO_FINANCIAL_METRIC.get(metric_type)
        if not fin_metric:
            continue

        fin_row = fin_lookup.get((fin_metric, target_period))
        if not fin_row:
            continue  # no matching actual data yet

        actual_val = fin_row.get("value")
        if actual_val is None:
            continue

        guided_val = float(guided_val)
        actual_val = float(actual_val)

        flag, delta, delta_pct, severity = compute_flag(guided_val, actual_val)
        pattern = detect_pattern(company_id, metric_type, existing_devs)

        source_guidance = f"[{guid['source_document']} | {guid.get('source_timestamp') or 'p.' + str(guid.get('source_page', '?'))} | {guid.get('statement_quarter', '')}]"
        source_actual   = f"[{fin_row['source_document']} | p.{fin_row.get('source_page', '?')} | {fin_row.get('period', '')}]"

        deviation_row = {
            "guidance_id":       guid["id"],
            "actual_metric_id":  fin_row["id"],
            "company_id":        company_id,
            "period":            target_period,
            "metric_type":       metric_type,
            "check_type":        guid.get("check_type"),
            "guided_value":      guided_val,
            "actual_value":      actual_val,
            "delta":             delta,
            "delta_pct":         delta_pct,
            "flag":              flag,
            "severity":          severity,
            "pattern":           pattern,
            "source_guidance":   source_guidance,
            "source_actual":     source_actual,
        }

        try:
            supabase.table("deviation_tracker").insert(deviation_row).execute()
            inserted += 1
            # Track locally for pattern detection in same run
            existing_devs.append({
                "company_id": company_id,
                "metric_type": metric_type,
                "period": target_period,
                "flag": flag,
            })
        except Exception as e:
            print(f"  [Error] Insert deviation: {e}")

    print(f"  Deviations computed: {inserted}")
    return inserted


def compute_credibility_score(company_id: str, supabase: Client):
    """Compute and upsert credibility_scores for a company from deviation_tracker."""
    dev_resp = supabase.table("deviation_tracker") \
        .select("*") \
        .eq("company_id", company_id) \
        .execute()
    devs = dev_resp.data or []

    if not devs:
        print(f"  [Credibility] No deviations for {company_id} — skipping score.")
        return

    total = len(devs)
    inline_or_beat = sum(1 for d in devs if d.get("flag") in ("IN-LINE", "BEAT"))
    hit_rate = (inline_or_beat / total) * 100 if total else 0

    deltas = [abs(d.get("delta_pct", 0)) for d in devs if d.get("delta_pct") is not None]
    avg_deviation = sum(deltas) / len(deltas) if deltas else 0

    # Consecutive misses
    sorted_devs = sorted(devs, key=lambda x: x.get("period", ""))
    consecutive = 0
    max_consec = 0
    for d in sorted_devs:
        if d.get("flag") == "MISS":
            consecutive += 1
            max_consec = max(max_consec, consecutive)
        else:
            consecutive = 0

    # Per-check scores
    def check_score(check_id: str) -> Optional[float]:
        check_devs = [d for d in devs if d.get("check_type") == check_id]
        if not check_devs:
            return None
        hits = sum(1 for d in check_devs if d.get("flag") in ("IN-LINE", "BEAT"))
        return (hits / len(check_devs)) * 100

    # Overall score (0-100)
    consistency = max(0, 100 - avg_deviation)
    overall = (
        hit_rate * 0.35 +
        consistency * 0.25 +
        max(0, 100 - avg_deviation * 2) * 0.20 +
        (0 if max_consec >= 3 else 20) * 0.10 +  # pattern penalty
        min(100, total * 5) * 0.10               # data completeness bonus
    )
    overall = min(100, max(0, round(overall, 1)))

    trend = "stable"
    if len(devs) >= 4:
        first_half = devs[:len(devs)//2]
        second_half = devs[len(devs)//2:]
        first_hits = sum(1 for d in first_half if d.get("flag") in ("IN-LINE", "BEAT"))
        second_hits = sum(1 for d in second_half if d.get("flag") in ("IN-LINE", "BEAT"))
        if second_hits > first_hits:
            trend = "improving"
        elif second_hits < first_hits:
            trend = "declining"

    score_row = {
        "company_id":          company_id,
        "period":              "ALL",
        "overall_score":       overall,
        "check_1_revpar_score": check_score("check_1_revpar"),
        "check_2_keys_score":  check_score("check_2_keys"),
        "check_3_driver_score": check_score("check_3_driver"),
        "check_4_fnb_score":   check_score("check_4_fnb"),
        "check_5_debt_score":  check_score("check_5_debt"),
        "check_6_supply_score": check_score("check_6_supply"),
        "hit_rate":            round(hit_rate, 1),
        "avg_deviation":       round(avg_deviation, 2),
        "total_guidance_count": total,
        "total_matched_count":  total,
        "consecutive_misses":  max_consec,
        "trend":               trend,
    }

    try:
        supabase.table("credibility_scores").upsert(
            score_row, on_conflict="company_id,period"
        ).execute()
        print(f"  [Credibility] {company_id} score: {overall}/100 | "
              f"Hit rate: {hit_rate:.1f}% | Trend: {trend}")
    except Exception as e:
        print(f"  [Credibility] Error upserting score: {e}")


# ─────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Compute Said vs Delivered deviations"
    )
    parser.add_argument("--company", choices=COMPANIES + ["ALL"],
                        default="ALL", help="Company ID or ALL")
    args = parser.parse_args()

    supabase = get_supabase()
    targets = COMPANIES if args.company == "ALL" else [args.company]

    for company in targets:
        compute_deviations_for_company(company, supabase)
        compute_credibility_score(company, supabase)

    print("\n[Done] Deviation computation complete.")


if __name__ == "__main__":
    main()
