"""
Scorecard Computer - Deep Analytical Reasoning Engine

Computes scorecards from extracted data and persists to Supabase.

Implemented analytical depth:
1) Causal decomposition for each score dimension
2) Multi-scenario stress matrix with probability weighting
3) Management truthfulness intelligence
4) Forward-looking early warning risk probabilities
5) Peer-normalized z-scores and percentile ranks
6) Confidence calibration with uncertainty bands
7) Citation graph for auditable UI rendering

Usage:
    python scorecard_computer.py --company IHCL
    python scorecard_computer.py --company ALL
"""

import argparse
from statistics import mean, pstdev
from typing import Any, Dict, List, Optional, Tuple

from supabase import Client, create_client

from config import COMPANIES, SUPABASE_SERVICE_KEY, SUPABASE_URL


def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def _clamp(val: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, round(val, 1)))


def _metric_family(metric_type: str) -> str:
    m = (metric_type or "").lower()
    if any(k in m for k in ["revpar", "adr", "occupancy"]):
        return "demand"
    if any(k in m for k in ["room", "key", "properties", "expansion"]):
        return "expansion"
    if any(k in m for k in ["debt", "interest", "coverage", "capex"]):
        return "balance_sheet"
    if any(k in m for k in ["margin", "ebitda", "revenue", "pat", "profit"]):
        return "profitability"
    return "other"


def _latest_annual_metric_rows(company_id: str, supabase: Client) -> Dict[str, List[Dict[str, Any]]]:
    fin_resp = (
        supabase.table("financials")
        .select("metric, value, period, period_type, source_document, source_page")
        .eq("company_id", company_id)
        .eq("period_type", "annual")
        .execute()
    )
    rows = fin_resp.data or []
    by_metric: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows:
        metric = r.get("metric")
        if not metric:
            continue
        by_metric.setdefault(metric, []).append(r)
    return by_metric


def _latest_row(by_metric: Dict[str, List[Dict[str, Any]]], metric: str) -> Optional[Dict[str, Any]]:
    rows = by_metric.get(metric, [])
    if not rows:
        return None
    fy_rows = [r for r in rows if str(r.get("period", "")).startswith("FY")]
    if not fy_rows:
        return None
    fy_rows.sort(key=lambda x: x.get("period", ""), reverse=True)
    return fy_rows[0]


def _latest_value(by_metric: Dict[str, List[Dict[str, Any]]], metric: str) -> Optional[float]:
    row = _latest_row(by_metric, metric)
    if not row:
        return None
    v = row.get("value")
    return float(v) if v is not None else None


def _previous_value(by_metric: Dict[str, List[Dict[str, Any]]], metric: str) -> Optional[float]:
    rows = by_metric.get(metric, [])
    fy_rows = [r for r in rows if str(r.get("period", "")).startswith("FY")]
    fy_rows.sort(key=lambda x: x.get("period", ""), reverse=True)
    if len(fy_rows) < 2:
        return None
    v = fy_rows[1].get("value")
    return float(v) if v is not None else None


def compute_financial_quality_detail(company_id: str, supabase: Client) -> Tuple[float, Dict[str, Any]]:
    by_metric = _latest_annual_metric_rows(company_id, supabase)
    if not by_metric:
        return 50.0, {"drivers": {"baseline": 50.0}, "raw": {}, "citations": []}

    score = 50.0
    drivers: Dict[str, float] = {"baseline": 50.0}
    raw: Dict[str, Any] = {}
    citations: List[Dict[str, Any]] = []

    def add_citation(metric_name: str) -> None:
        row = _latest_row(by_metric, metric_name)
        if row:
            citations.append(
                {
                    "dimension": "financial_quality",
                    "metric": metric_name,
                    "source_document": row.get("source_document"),
                    "source_page": row.get("source_page"),
                    "period": row.get("period"),
                }
            )

    # Revenue growth contribution
    rev = _latest_value(by_metric, "revenue")
    rev_prev = _previous_value(by_metric, "revenue")
    growth_pts = 0.0
    if rev is not None and rev_prev is not None and rev_prev > 0:
        growth = ((rev - rev_prev) / rev_prev) * 100
        raw["revenue_growth_pct"] = round(growth, 2)
        if growth > 20:
            growth_pts = 15
        elif growth > 10:
            growth_pts = 10
        elif growth > 0:
            growth_pts = 5
        elif growth > -10:
            growth_pts = -5
        else:
            growth_pts = -15
        score += growth_pts
        drivers["revenue_growth_points"] = growth_pts
        add_citation("revenue")

    # Margin contribution
    opm = _latest_value(by_metric, "opm")
    margin_pts = 0.0
    if opm is not None:
        raw["opm"] = round(opm, 2)
        if opm > 25:
            margin_pts = 15
        elif opm > 15:
            margin_pts = 10
        elif opm > 10:
            margin_pts = 5
        else:
            margin_pts = -5
        score += margin_pts
        drivers["margin_points"] = margin_pts
        add_citation("opm")

    # Coverage contribution
    op_profit = _latest_value(by_metric, "operating_profit")
    interest = _latest_value(by_metric, "interest")
    coverage_pts = 0.0
    if op_profit is not None and interest is not None and interest > 0:
        icr = op_profit / interest
        raw["interest_coverage_ratio"] = round(icr, 2)
        if icr > 5:
            coverage_pts = 10
        elif icr > 3:
            coverage_pts = 5
        elif icr > 1.5:
            coverage_pts = 0
        else:
            coverage_pts = -10
        score += coverage_pts
        drivers["coverage_points"] = coverage_pts
        add_citation("operating_profit")
        add_citation("interest")

    # Profitability floor contribution
    np_val = _latest_value(by_metric, "net_profit")
    np_pts = 0.0
    if np_val is not None:
        raw["net_profit"] = round(np_val, 2)
        np_pts = 5 if np_val > 0 else -10
        score += np_pts
        drivers["net_profit_points"] = np_pts
        add_citation("net_profit")

    return _clamp(score), {"drivers": drivers, "raw": raw, "citations": citations}


def compute_industry_position(company_id: str, supabase: Client) -> Tuple[float, Dict[str, Any]]:
    all_fin = (
        supabase.table("financials")
        .select("company_id, metric, value, period, source_document, source_page")
        .eq("metric", "operating_profit")
        .eq("period_type", "annual")
        .execute()
    )
    rows = all_fin.data or []

    by_company: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        cid = r.get("company_id")
        if not cid:
            continue
        current = by_company.get(cid)
        if not current or (r.get("period", "") > current.get("period", "")):
            by_company[cid] = r

    if company_id not in by_company:
        return 50.0, {"rank": None, "total": len(by_company), "citations": []}

    ranking = sorted(
        [(cid, row.get("value") or 0.0) for cid, row in by_company.items()],
        key=lambda x: x[1],
        reverse=True,
    )
    rank = next((i + 1 for i, (cid, _) in enumerate(ranking) if cid == company_id), len(ranking))
    total = len(ranking)

    if total <= 1:
        score = 70.0
    else:
        percentile = 1 - ((rank - 1) / (total - 1))
        score = 30 + percentile * 55

    citations = []
    for cid, _ in ranking:
        row = by_company[cid]
        citations.append(
            {
                "dimension": "industry_position",
                "company_id": cid,
                "source_document": row.get("source_document"),
                "source_page": row.get("source_page"),
                "period": row.get("period"),
            }
        )

    return round(score, 1), {
        "rank": rank,
        "total": total,
        "percentile": round((1 - (rank - 1) / max(1, total - 1)) * 100, 1) if total > 1 else 100.0,
        "citations": citations,
    }


def compute_risk_score(company_id: str, supabase: Client) -> Tuple[float, Dict[str, Any]]:
    risk_resp = (
        supabase.table("risk_flags")
        .select("category, severity, source_document, source_page, period")
        .eq("company_id", company_id)
        .execute()
    )
    risks = risk_resp.data or []

    if not risks:
        return 75.0, {"severity_counts": {"critical": 0, "high": 0, "medium": 0}, "citations": []}

    severity_weights = {"critical": 15, "high": 10, "medium": 5}
    total_penalty = sum(severity_weights.get(r.get("severity", "medium"), 5) for r in risks)

    counts = {"critical": 0, "high": 0, "medium": 0}
    citations: List[Dict[str, Any]] = []
    for r in risks:
        sev = r.get("severity", "medium")
        if sev in counts:
            counts[sev] += 1
        citations.append(
            {
                "dimension": "risk_identification",
                "category": r.get("category"),
                "severity": sev,
                "source_document": r.get("source_document"),
                "source_page": r.get("source_page"),
                "period": r.get("period"),
            }
        )

    return _clamp(100 - total_penalty), {"severity_counts": counts, "total_penalty": total_penalty, "citations": citations}


def compute_truthfulness_intelligence(company_id: str, supabase: Client) -> Dict[str, Any]:
    dev_resp = (
        supabase.table("deviation_tracker")
        .select("guidance_id, metric_type, flag, period")
        .eq("company_id", company_id)
        .execute()
    )
    devs = dev_resp.data or []

    guid_resp = (
        supabase.table("guidance_claims")
        .select("id, confidence_language, source_document, source_page, statement_quarter")
        .eq("company_id", company_id)
        .execute()
    )
    guidance = guid_resp.data or []
    g_by_id = {g["id"]: g for g in guidance if g.get("id")}

    if not devs:
        return {
            "truthfulness_score": 50.0,
            "overall_miss_rate": None,
            "family_miss_rates": {},
            "language_inflation_penalty": 0.0,
            "trend_penalty": 0.0,
            "citations": [],
        }

    total = len(devs)
    misses = sum(1 for d in devs if d.get("flag") == "MISS")
    overall_miss_rate = misses / total

    # Family miss rates
    families: Dict[str, List[str]] = {}
    for d in devs:
        fam = _metric_family(d.get("metric_type", ""))
        families.setdefault(fam, []).append(d.get("flag", "IN-LINE"))

    family_miss_rates: Dict[str, float] = {}
    for fam, flags in families.items():
        miss_rate = sum(1 for f in flags if f == "MISS") / len(flags)
        family_miss_rates[fam] = round(miss_rate, 3)

    # Trend penalty: compare first vs second half misses
    sorted_devs = sorted(devs, key=lambda x: x.get("period", ""))
    mid = len(sorted_devs) // 2
    first_half = sorted_devs[:mid] or sorted_devs
    second_half = sorted_devs[mid:] or sorted_devs
    first_miss = sum(1 for d in first_half if d.get("flag") == "MISS") / max(1, len(first_half))
    second_miss = sum(1 for d in second_half if d.get("flag") == "MISS") / max(1, len(second_half))
    trend_penalty = max(0.0, second_miss - first_miss) * 25

    # Language inflation: hard language with poor delivery
    hard_words = {"will", "confident", "expect"}
    hard_total = 0
    hard_miss = 0
    citations = []
    for d in devs:
        gid = d.get("guidance_id")
        g = g_by_id.get(gid)
        if not g:
            continue
        lang = (g.get("confidence_language") or "").strip().lower()
        if lang in hard_words:
            hard_total += 1
            if d.get("flag") == "MISS":
                hard_miss += 1
            citations.append(
                {
                    "dimension": "management_truthfulness",
                    "guidance_id": gid,
                    "confidence_language": lang,
                    "source_document": g.get("source_document"),
                    "source_page": g.get("source_page"),
                    "statement_quarter": g.get("statement_quarter"),
                }
            )

    hard_miss_rate = (hard_miss / hard_total) if hard_total else 0.0
    language_inflation_penalty = hard_miss_rate * 20

    truthfulness_score = 100 - (overall_miss_rate * 60) - trend_penalty - language_inflation_penalty

    return {
        "truthfulness_score": _clamp(truthfulness_score),
        "overall_miss_rate": round(overall_miss_rate, 3),
        "family_miss_rates": family_miss_rates,
        "hard_language_miss_rate": round(hard_miss_rate, 3),
        "language_inflation_penalty": round(language_inflation_penalty, 2),
        "trend_penalty": round(trend_penalty, 2),
        "citations": citations,
    }


def compute_management_credibility(company_id: str, supabase: Client) -> Tuple[float, Dict[str, Any]]:
    cred_resp = (
        supabase.table("credibility_scores")
        .select("overall_score, hit_rate, avg_deviation, consecutive_misses, trend, created_at")
        .eq("company_id", company_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    cred_rows = cred_resp.data or []

    if not cred_rows:
        base = 50.0
        hit_rate = 50.0
        avg_dev = 20.0
        consecutive_misses = 0
        trend = "stable"
    else:
        row = cred_rows[0]
        base = float(row.get("overall_score") or 50.0)
        hit_rate = float(row.get("hit_rate") or 50.0)
        avg_dev = float(row.get("avg_deviation") or 20.0)
        consecutive_misses = int(row.get("consecutive_misses") or 0)
        trend = row.get("trend") or "stable"

    risk_resp = (
        supabase.table("risk_flags")
        .select("category, severity, source_document, source_page, period")
        .eq("company_id", company_id)
        .in_("category", ["governance", "management_mismatch", "key_person"])
        .execute()
    )
    mgmt_risks = risk_resp.data or []

    truth = compute_truthfulness_intelligence(company_id, supabase)

    severity_weight = {"critical": 10, "high": 6, "medium": 3}
    mgmt_penalty = sum(severity_weight.get(r.get("severity", "medium"), 3) for r in mgmt_risks)

    trend_bonus = 4 if trend == "improving" else -4 if trend == "declining" else 0
    miss_penalty = min(12, consecutive_misses * 4)

    score = (
        base * 0.45
        + hit_rate * 0.20
        + max(0, 100 - avg_dev) * 0.15
        + float(truth["truthfulness_score"]) * 0.20
        + trend_bonus
        - miss_penalty
        - mgmt_penalty
    )

    citations = [
        {
            "dimension": "management_credibility",
            "source_table": "credibility_scores",
            "company_id": company_id,
        }
    ]
    for r in mgmt_risks:
        citations.append(
            {
                "dimension": "management_credibility",
                "source_table": "risk_flags",
                "category": r.get("category"),
                "source_document": r.get("source_document"),
                "source_page": r.get("source_page"),
                "period": r.get("period"),
            }
        )
    citations.extend(truth.get("citations", []))

    detail = {
        "base_credibility": round(base, 2),
        "hit_rate": round(hit_rate, 2),
        "avg_deviation": round(avg_dev, 2),
        "consecutive_misses": consecutive_misses,
        "trend": trend,
        "management_risk_penalty": mgmt_penalty,
        "truthfulness": truth,
        "citations": citations,
    }
    return _clamp(score), detail


def _icr_to_score(icr: Optional[float]) -> float:
    if icr is None:
        return 50.0
    if icr >= 4:
        return 90.0
    if icr >= 2.5:
        return 70.0
    if icr >= 1.5:
        return 45.0
    return 20.0


def compute_stress_test_resilience(company_id: str, supabase: Client) -> Tuple[float, Dict[str, Any]]:
    by_metric = _latest_annual_metric_rows(company_id, supabase)

    opm = _latest_value(by_metric, "opm")
    op_profit = _latest_value(by_metric, "operating_profit")
    interest = _latest_value(by_metric, "interest")
    debt = _latest_value(by_metric, "debt")

    base_icr = None
    if op_profit is not None and interest is not None and interest > 0:
        base_icr = op_profit / interest

    demand_levels = [
        ("mild", 0.95, 0.50),
        ("base", 0.90, 0.35),
        ("severe", 0.80, 0.15),
    ]
    rate_levels = [
        ("mild", 1.05, 0.45),
        ("base", 1.15, 0.35),
        ("severe", 1.30, 0.20),
    ]

    matrix = []
    weighted_score = 0.0
    weighted_icr = 0.0
    breach_prob = 0.0

    for d_name, d_mult, d_prob in demand_levels:
        for r_name, r_mult, r_prob in rate_levels:
            prob = d_prob * r_prob
            stressed_icr = (base_icr * d_mult / r_mult) if base_icr is not None else None
            cell_score = _icr_to_score(stressed_icr)
            weighted_score += cell_score * prob
            if stressed_icr is not None:
                weighted_icr += stressed_icr * prob
                if stressed_icr < 1.5:
                    breach_prob += prob
            matrix.append(
                {
                    "demand_scenario": d_name,
                    "rate_scenario": r_name,
                    "probability": round(prob, 4),
                    "stressed_icr": round(stressed_icr, 3) if stressed_icr is not None else None,
                    "cell_score": round(cell_score, 2),
                }
            )

    score = weighted_score

    # Structural buffers/penalties
    if opm is not None:
        if opm >= 25:
            score += 8
        elif opm >= 15:
            score += 4
        elif opm < 10:
            score -= 8

    if debt is not None:
        if debt <= 500:
            score += 6
        elif debt > 3000:
            score -= 8

    risk_resp = (
        supabase.table("risk_flags")
        .select("category, severity, source_document, source_page, period")
        .eq("company_id", company_id)
        .in_("category", ["debt", "margin_compression", "supply_overhang", "operational"])
        .execute()
    )
    cyclical_risks = risk_resp.data or []
    sev_penalty = {"critical": 8, "high": 5, "medium": 2}
    score -= sum(sev_penalty.get(r.get("severity", "medium"), 2) for r in cyclical_risks)

    citations = []
    for m in ["operating_profit", "interest", "opm", "debt"]:
        row = _latest_row(by_metric, m)
        if row:
            citations.append(
                {
                    "dimension": "stress_test_resilience",
                    "metric": m,
                    "source_document": row.get("source_document"),
                    "source_page": row.get("source_page"),
                    "period": row.get("period"),
                }
            )
    for r in cyclical_risks:
        citations.append(
            {
                "dimension": "stress_test_resilience",
                "risk_category": r.get("category"),
                "source_document": r.get("source_document"),
                "source_page": r.get("source_page"),
                "period": r.get("period"),
            }
        )

    summary = {
        "base_icr": round(base_icr, 3) if base_icr is not None else None,
        "weighted_stressed_icr": round(weighted_icr, 3) if base_icr is not None else None,
        "breach_probability_icr_lt_1_5": round(breach_prob, 4),
        "matrix": matrix,
        "citations": citations,
    }

    return _clamp(score), summary


def compute_forward_risk(
    company_id: str,
    supabase: Client,
    stress_detail: Dict[str, Any],
    truth_detail: Dict[str, Any],
    financial_score: float,
    risk_score: float,
) -> Dict[str, Any]:
    risk_resp = (
        supabase.table("risk_flags")
        .select("category, severity")
        .eq("company_id", company_id)
        .execute()
    )
    risks = risk_resp.data or []

    sev_weight = {"critical": 1.0, "high": 0.6, "medium": 0.3}
    weighted_risk_count = sum(sev_weight.get(r.get("severity", "medium"), 0.3) for r in risks)

    breach_prob = float(stress_detail.get("breach_probability_icr_lt_1_5", 0.0) or 0.0)
    miss_rate = float(truth_detail.get("overall_miss_rate") or 0.0)

    p_margin = min(0.95, max(0.05, 0.12 + 0.10 * weighted_risk_count + 0.35 * breach_prob + (70 - financial_score) / 200))
    p_guidance_miss = min(0.95, max(0.05, 0.10 + 0.65 * miss_rate + (65 - risk_score) / 220))
    p_liquidity = min(0.95, max(0.03, 0.08 + 0.55 * breach_prob + (75 - risk_score) / 250))

    return {
        "next_2q_margin_compression_prob": round(p_margin, 3),
        "next_2q_guidance_miss_prob": round(p_guidance_miss, 3),
        "next_2q_liquidity_stress_prob": round(p_liquidity, 3),
        "method": "heuristic blended probabilities from stress, risk, and delivery behavior",
    }


def _infer_latest_period(company_id: str, supabase: Client) -> str:
    resp = (
        supabase.table("financials")
        .select("period")
        .eq("company_id", company_id)
        .eq("period_type", "annual")
        .order("period", desc=True)
        .limit(1)
        .execute()
    )
    rows = resp.data or []
    if not rows:
        return "FY25"
    return rows[0].get("period") or "FY25"


def _dimension_snapshot(company_id: str, supabase: Client) -> Dict[str, float]:
    dim_industry, _ = compute_industry_position(company_id, supabase)
    dim_financial, _ = compute_financial_quality_detail(company_id, supabase)
    dim_management, _ = compute_management_credibility(company_id, supabase)
    dim_risk, _ = compute_risk_score(company_id, supabase)
    dim_stress, _ = compute_stress_test_resilience(company_id, supabase)
    composite = round(
        dim_industry * 0.20
        + dim_financial * 0.25
        + dim_management * 0.20
        + dim_risk * 0.20
        + dim_stress * 0.15,
        1,
    )
    return {
        "industry_position": dim_industry,
        "financial_quality": dim_financial,
        "management_credibility": dim_management,
        "risk_identification": dim_risk,
        "stress_test_resilience": dim_stress,
        "composite": composite,
    }


def compute_peer_normalization(company_id: str, current_snapshot: Dict[str, float], supabase: Client) -> Dict[str, Any]:
    peers = []
    for cid in COMPANIES:
        if cid == company_id:
            peers.append({"company_id": cid, **current_snapshot})
        else:
            peers.append({"company_id": cid, **_dimension_snapshot(cid, supabase)})

    dimensions = [
        "industry_position",
        "financial_quality",
        "management_credibility",
        "risk_identification",
        "stress_test_resilience",
        "composite",
    ]

    normalized: Dict[str, Any] = {}
    for d in dimensions:
        vals = [float(p[d]) for p in peers]
        mu = mean(vals)
        sigma = pstdev(vals) if len(vals) > 1 else 0.0
        x = float(current_snapshot[d])
        z = 0.0 if sigma == 0 else (x - mu) / sigma
        rank = 1 + sum(1 for v in vals if v > x)
        percentile = round((1 - (rank - 1) / max(1, len(vals) - 1)) * 100, 1) if len(vals) > 1 else 100.0
        normalized[d] = {
            "value": round(x, 2),
            "peer_mean": round(mu, 2),
            "peer_std": round(sigma, 3),
            "z_score": round(z, 3),
            "percentile": percentile,
            "rank": rank,
            "total": len(vals),
        }

    return {"dimensions": normalized}


def compute_uncertainty_band(
    composite: float,
    confidence_level: str,
    data_points: int,
    dimension_values: List[float],
) -> Dict[str, Any]:
    spread = pstdev(dimension_values) if len(dimension_values) > 1 else 0.0
    base_width = 6.0 if confidence_level == "high" else 9.0 if confidence_level == "medium" else 13.0
    missing_penalty = max(0.0, 4 - data_points) * 1.2
    spread_penalty = spread * 0.08
    width = round(base_width + missing_penalty + spread_penalty, 2)
    return {
        "composite": round(composite, 1),
        "band_low": _clamp(composite - width),
        "band_high": _clamp(composite + width),
        "band_width": width,
        "confidence_level": confidence_level,
        "method": "coverage + cross-dimension dispersion calibrated band",
    }


def compute_scorecard(company_id: str, supabase: Client) -> None:
    print(f"\n[Scorecard] Computing for {company_id}...")

    # Delivery credibility from existing table (kept for continuity)
    cred_resp = (
        supabase.table("credibility_scores")
        .select("overall_score")
        .eq("company_id", company_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    cred_rows = cred_resp.data or []
    dim_delivery_credibility = float(cred_rows[0]["overall_score"]) if cred_rows else 50.0

    dim_financial, financial_detail = compute_financial_quality_detail(company_id, supabase)
    dim_industry, industry_detail = compute_industry_position(company_id, supabase)
    dim_risk, risk_detail = compute_risk_score(company_id, supabase)
    dim_management, management_detail = compute_management_credibility(company_id, supabase)
    dim_stress, stress_detail = compute_stress_test_resilience(company_id, supabase)

    composite = round(
        dim_industry * 0.20
        + dim_financial * 0.25
        + dim_management * 0.20
        + dim_risk * 0.20
        + dim_stress * 0.15,
        1,
    )

    data_points = 0
    for table in ["financials", "guidance_claims", "risk_flags", "document_chunks"]:
        resp = supabase.table(table).select("id", count="exact").eq("company_id", company_id).execute()
        if resp.count and resp.count > 0:
            data_points += 1

    confidence = "high" if data_points >= 3 else "medium" if data_points >= 2 else "low"

    current_snapshot = {
        "industry_position": dim_industry,
        "financial_quality": dim_financial,
        "management_credibility": dim_management,
        "risk_identification": dim_risk,
        "stress_test_resilience": dim_stress,
        "composite": composite,
    }

    peer_norm = compute_peer_normalization(company_id, current_snapshot, supabase)
    forward_risk = compute_forward_risk(
        company_id,
        supabase,
        stress_detail,
        management_detail.get("truthfulness", {}),
        dim_financial,
        dim_risk,
    )
    uncertainty = compute_uncertainty_band(
        composite,
        confidence,
        data_points,
        [dim_industry, dim_financial, dim_management, dim_risk, dim_stress],
    )

    latest_period = _infer_latest_period(company_id, supabase)

    citation_graph = {
        "financial_quality": financial_detail.get("citations", []),
        "industry_position": industry_detail.get("citations", []),
        "management_credibility": management_detail.get("citations", []),
        "risk_identification": risk_detail.get("citations", []),
        "stress_test_resilience": stress_detail.get("citations", []),
    }

    scorecard_row = {
        "company_id": company_id,
        "period": latest_period,
        "dim_credibility": dim_delivery_credibility,
        "dim_financial_quality": dim_financial,
        "dim_industry_position": dim_industry,
        "dim_risk": dim_risk,
        "composite_score": composite,
        "confidence_level": confidence,
        "evidence_summary": {
            "dimension_scores": {
                "industry_position": dim_industry,
                "financial_quality": dim_financial,
                "management_credibility": dim_management,
                "risk_identification": dim_risk,
                "stress_test_resilience": dim_stress,
                "delivery_credibility": dim_delivery_credibility,
            },
            "decomposition": {
                "financial_quality": financial_detail,
                "industry_position": industry_detail,
                "management_credibility": management_detail,
                "risk_identification": risk_detail,
            },
            "stress_test": {
                "summary": stress_detail,
                "assumptions": {
                    "demand_shock_levels": ["mild:-5%", "base:-10%", "severe:-20%"],
                    "rate_shock_levels": ["mild:+5%", "base:+15%", "severe:+30%"],
                },
            },
            "forward_risk": forward_risk,
            "peer_normalized": peer_norm,
            "uncertainty": uncertainty,
            "citation_graph": citation_graph,
        },
    }

    try:
        supabase.table("scorecards").upsert(scorecard_row, on_conflict="company_id,period").execute()
        print(
            f"  Industry: {dim_industry} | Financial: {dim_financial} | "
            f"Management: {dim_management} | Risk: {dim_risk} | Stress: {dim_stress}"
        )
        print(f"  Composite: {composite}/100 | Confidence: {confidence}")
    except Exception as e:
        print(f"  [Error] Upsert scorecard: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute deep analytical scorecards")
    parser.add_argument("--company", choices=COMPANIES + ["ALL"], default="ALL")
    args = parser.parse_args()

    supabase = get_supabase()
    targets = COMPANIES if args.company == "ALL" else [args.company]

    for company in targets:
        compute_scorecard(company, supabase)

    print("\n[Done] Scorecard computation complete.")


if __name__ == "__main__":
    main()
