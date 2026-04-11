"""
Scorecard Computer — 4-Dimension Scoring
Computes scorecards from: credibility_scores + financials + risk_flags + raw_data
Run this AFTER deviation_computer.py has populated credibility_scores.

Usage:
  python scorecard_computer.py --company IHCL
  python scorecard_computer.py --all
"""

import argparse
from typing import Dict, Optional
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_SERVICE_KEY, COMPANIES


def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def compute_financial_quality(company_id: str, supabase: Client) -> float:
    """Score 0-100 based on financial metrics: revenue growth, margins, debt ratios."""
    fin_resp = supabase.table("financials") \
        .select("metric, value, period, period_type") \
        .eq("company_id", company_id) \
        .eq("period_type", "annual") \
        .execute()
    rows = fin_resp.data or []

    if not rows:
        return 50.0  # neutral default

    # Build latest values by metric
    by_metric: Dict[str, list] = {}
    for r in rows:
        m = r["metric"]
        if m not in by_metric:
            by_metric[m] = []
        by_metric[m].append(r)

    def latest_value(metric: str) -> Optional[float]:
        if metric not in by_metric:
            return None
        sorted_rows = sorted(by_metric[metric], key=lambda x: x["period"], reverse=True)
        fy_rows = [r for r in sorted_rows if r["period"].startswith("FY")]
        return fy_rows[0]["value"] if fy_rows else None

    score = 50.0  # start neutral
    adjustments = 0

    # Revenue growth (YoY)
    rev = latest_value("revenue")
    rev_prev = None
    if "revenue" in by_metric:
        fy_sorted = sorted(
            [r for r in by_metric["revenue"] if r["period"].startswith("FY")],
            key=lambda x: x["period"], reverse=True
        )
        if len(fy_sorted) >= 2:
            rev_prev = fy_sorted[1]["value"]
    if rev and rev_prev and rev_prev > 0:
        growth = ((rev - rev_prev) / rev_prev) * 100
        if growth > 20:
            score += 15
        elif growth > 10:
            score += 10
        elif growth > 0:
            score += 5
        elif growth > -10:
            score -= 5
        else:
            score -= 15
        adjustments += 1

    # OPM (Operating Profit Margin)
    opm = latest_value("opm")
    if opm is not None:
        if opm > 25:
            score += 15
        elif opm > 15:
            score += 10
        elif opm > 10:
            score += 5
        else:
            score -= 5
        adjustments += 1

    # Interest coverage
    op_profit = latest_value("operating_profit")
    interest = latest_value("interest")
    if op_profit and interest and interest > 0:
        icr = op_profit / interest
        if icr > 5:
            score += 10
        elif icr > 3:
            score += 5
        elif icr > 1.5:
            score += 0
        else:
            score -= 10
        adjustments += 1

    # Net profit positive
    np_val = latest_value("net_profit")
    if np_val is not None:
        if np_val > 0:
            score += 5
        else:
            score -= 10
        adjustments += 1

    return max(0, min(100, round(score, 1)))


def compute_industry_position(company_id: str, supabase: Client) -> float:
    """Score based on relative operating profit size and segment positioning."""
    # Get all companies' latest operating profit (revenue not available from Screener)
    all_fin = supabase.table("financials") \
        .select("company_id, metric, value, period") \
        .eq("metric", "operating_profit") \
        .eq("period_type", "annual") \
        .execute()
    rows = all_fin.data or []

    # Latest operating profit per company
    rev_by_company: Dict[str, float] = {}
    for r in rows:
        cid = r["company_id"]
        period = r.get("period", "")
        if cid not in rev_by_company or period > rev_by_company.get(f"{cid}_period", ""):
            rev_by_company[cid] = r["value"] or 0
            rev_by_company[f"{cid}_period"] = period

    # Clean up period keys
    revenues = {k: v for k, v in rev_by_company.items() if not k.endswith("_period")}

    if not revenues or company_id not in revenues:
        return 50.0

    # Rank by revenue
    sorted_companies = sorted(revenues.items(), key=lambda x: x[1], reverse=True)
    rank = next((i + 1 for i, (cid, _) in enumerate(sorted_companies) if cid == company_id), len(sorted_companies))
    total = len(sorted_companies)

    # Score: top company gets ~85, bottom gets ~30
    if total <= 1:
        return 70.0
    percentile = 1 - ((rank - 1) / (total - 1))
    return round(30 + percentile * 55, 1)


def compute_risk_score(company_id: str, supabase: Client) -> float:
    """Score 0-100 where HIGHER = LESS risky (inverse of risk count/severity)."""
    risk_resp = supabase.table("risk_flags") \
        .select("severity") \
        .eq("company_id", company_id) \
        .execute()
    risks = risk_resp.data or []

    if not risks:
        return 75.0  # no risk flags = decent score

    # Weight by severity
    severity_weights = {"critical": 15, "high": 10, "medium": 5}
    total_penalty = sum(severity_weights.get(r.get("severity", "medium"), 5) for r in risks)

    return max(0, min(100, round(100 - total_penalty, 1)))


def compute_scorecard(company_id: str, supabase: Client):
    """Compute and upsert a 4-dimension scorecard for a company."""
    print(f"\n[Scorecard] Computing for {company_id}...")

    # Dimension 1: Credibility (from credibility_scores table)
    cred_resp = supabase.table("credibility_scores") \
        .select("overall_score") \
        .eq("company_id", company_id) \
        .limit(1) \
        .execute()
    cred_rows = cred_resp.data or []
    dim_credibility = cred_rows[0]["overall_score"] if cred_rows else 50.0

    # Dimension 2: Financial Quality
    dim_financial = compute_financial_quality(company_id, supabase)

    # Dimension 3: Industry Position
    dim_industry = compute_industry_position(company_id, supabase)

    # Dimension 4: Risk (inverse)
    dim_risk = compute_risk_score(company_id, supabase)

    # Composite: weighted average
    composite = round(
        dim_credibility * 0.30 +
        dim_financial * 0.30 +
        dim_industry * 0.20 +
        dim_risk * 0.20,
        1
    )

    # Confidence level based on data availability
    data_points = 0
    for table in ["financials", "guidance_claims", "risk_flags", "document_chunks"]:
        resp = supabase.table(table).select("id", count="exact").eq("company_id", company_id).execute()
        if resp.count and resp.count > 0:
            data_points += 1
    confidence = "high" if data_points >= 3 else "medium" if data_points >= 2 else "low"

    scorecard_row = {
        "company_id": company_id,
        "period": "FY25",
        "dim_credibility": dim_credibility,
        "dim_financial_quality": dim_financial,
        "dim_industry_position": dim_industry,
        "dim_risk": dim_risk,
        "composite_score": composite,
        "confidence_level": confidence,
        "evidence_summary": {
            "credibility_source": "deviation_tracker analysis",
            "financial_source": "Screener.in financials",
            "industry_source": "revenue-based ranking",
            "risk_source": "LLM-extracted risk flags",
        },
    }

    try:
        supabase.table("scorecards").upsert(
            scorecard_row, on_conflict="company_id,period"
        ).execute()
        print(f"  Credibility: {dim_credibility} | Financial: {dim_financial} | "
              f"Industry: {dim_industry} | Risk: {dim_risk}")
        print(f"  Composite: {composite}/100 | Confidence: {confidence}")
    except Exception as e:
        print(f"  [Error] Upsert scorecard: {e}")


def main():
    parser = argparse.ArgumentParser(description="Compute 4-Dimension Scorecards")
    parser.add_argument("--company", choices=COMPANIES + ["ALL"], default="ALL")
    args = parser.parse_args()

    supabase = get_supabase()
    targets = COMPANIES if args.company == "ALL" else [args.company]

    for company in targets:
        compute_scorecard(company, supabase)

    print("\n[Done] Scorecard computation complete.")


if __name__ == "__main__":
    main()
