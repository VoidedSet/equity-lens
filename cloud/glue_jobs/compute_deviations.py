"""Compute Said-vs-Delivered deviations and credibility scores from curated Parquet tables."""

from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from cloud.common.hashing import make_record_id
from cloud.common.manifest import utc_now_iso
from cloud.common.storage import StorageBackend
from cloud.glue_jobs.lib.dq import (
    compute_flag,
    deduplicate_rows,
    detect_pattern,
    normalise_period,
    resolve_financial_metric,
    validate_curated_row,
)
from cloud.glue_jobs.lib.spark_utils import (
    parse_job_args,
    read_curated_parquet,
    resolve_storage_from_args,
    write_curated_parquet,
)


def _compute_company_credibility(
    company_id: str,
    devs: List[Dict[str, Any]],
    ingested_at: str,
) -> Dict[str, Any]:
    total = len(devs)
    inline_or_beat = sum(1 for d in devs if d.get("flag") in ("IN-LINE", "BEAT"))
    hit_rate = (inline_or_beat / total) * 100.0 if total else 0.0

    deltas = [abs(float(d["delta_pct"])) for d in devs if d.get("delta_pct") is not None]
    avg_deviation = sum(deltas) / len(deltas) if deltas else 0.0

    sorted_devs = sorted(devs, key=lambda x: str(x.get("period") or ""))
    consecutive = 0
    max_consec = 0
    for d in sorted_devs:
        if d.get("flag") == "MISS":
            consecutive += 1
            max_consec = max(max_consec, consecutive)
        else:
            consecutive = 0

    def check_score(check_id: str) -> Optional[float]:
        check_devs = [d for d in devs if d.get("check_type") == check_id]
        if not check_devs:
            return None
        hits = sum(1 for d in check_devs if d.get("flag") in ("IN-LINE", "BEAT"))
        return round((hits / len(check_devs)) * 100.0, 2)

    consistency = max(0.0, 100.0 - avg_deviation)
    overall = (
        hit_rate * 0.35
        + consistency * 0.25
        + max(0.0, 100.0 - avg_deviation * 2.0) * 0.20
        + (0.0 if max_consec >= 3 else 20.0) * 0.10
        + min(100.0, total * 5.0) * 0.10
    )
    overall = min(100.0, max(0.0, round(overall, 1)))

    trend = "stable"
    if len(sorted_devs) >= 4:
        mid = len(sorted_devs) // 2
        first_hits = sum(1 for d in sorted_devs[:mid] if d.get("flag") in ("IN-LINE", "BEAT"))
        second_hits = sum(1 for d in sorted_devs[mid:] if d.get("flag") in ("IN-LINE", "BEAT"))
        if second_hits > first_hits:
            trend = "improving"
        elif second_hits < first_hits:
            trend = "declining"

    return {
        "record_id": make_record_id(company_id, "credibility_scores", {"period": "ALL"}),
        "company_id": company_id,
        "period": "ALL",
        "overall_score": overall,
        "check_1_revpar_score": check_score("check_1_revpar"),
        "check_2_keys_score": check_score("check_2_keys"),
        "check_3_driver_score": check_score("check_3_driver"),
        "check_4_fnb_score": check_score("check_4_fnb"),
        "check_5_debt_score": check_score("check_5_debt"),
        "check_6_supply_score": check_score("check_6_supply"),
        "hit_rate": round(hit_rate, 1),
        "avg_deviation": round(avg_deviation, 2),
        "total_guidance_count": total,
        "total_matched_count": total,
        "consecutive_misses": max_consec,
        "trend": trend,
        "ingested_at": ingested_at,
    }


def run(storage: StorageBackend, engine: str = "auto") -> Dict[str, Any]:
    """Join curated guidance_claims + financials into curated deviation_tracker & credibility_scores."""
    ingested_at = utc_now_iso()
    guidance_rows = read_curated_parquet("guidance_claims", storage)
    financial_rows = read_curated_parquet("financials", storage)

    # Index actuals by (company_id, metric, normalised_period); prefer latest ingested_at
    fin_lookup: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for fin in sorted(financial_rows, key=lambda r: str(r.get("ingested_at") or "")):
        cid = str(fin.get("company_id") or "")
        metric = str(fin.get("metric") or "")
        norm_p = normalise_period(fin.get("period"))
        if cid and metric and norm_p:
            fin_lookup[(cid, metric, norm_p)] = fin

    # Sort guidance deterministically by (company_id, target_period, record_id) for consistent pattern runs
    ordered_guidance = sorted(
        guidance_rows,
        key=lambda g: (
            str(g.get("company_id") or ""),
            normalise_period(g.get("target_period")),
            str(g.get("record_id") or ""),
        ),
    )

    deviations: List[Dict[str, Any]] = []
    history_by_company: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for guid in ordered_guidance:
        company_id = str(guid.get("company_id") or "")
        metric_type = str(guid.get("metric_type") or "")
        target_period = normalise_period(guid.get("target_period"))
        if not company_id or not target_period:
            continue

        guided_val = guid.get("guidance_value_point")
        if guided_val is None:
            lo = guid.get("guidance_value_low")
            hi = guid.get("guidance_value_high")
            if lo is not None and hi is not None:
                guided_val = (float(lo) + float(hi)) / 2.0
        if guided_val is None:
            continue

        fin_metric = resolve_financial_metric(metric_type)
        if not fin_metric:
            continue

        fin_row = fin_lookup.get((company_id, fin_metric, target_period))
        if not fin_row or fin_row.get("value") is None:
            continue

        guided_f = float(guided_val)
        actual_f = float(fin_row["value"])
        flag, delta, delta_pct, severity = compute_flag(guided_f, actual_f)
        pattern = detect_pattern(company_id, metric_type, history_by_company[company_id])

        src_page_guid = guid.get("source_page")
        loc_guid = guid.get("source_timestamp") or (f"p.{src_page_guid}" if src_page_guid is not None else "p.?")
        source_guidance = (
            f"[{guid.get('source_document')} | {loc_guid} | {guid.get('statement_quarter') or ''}]"
        )
        src_page_fin = fin_row.get("source_page")
        loc_fin = f"p.{src_page_fin}" if src_page_fin is not None else "p.?"
        source_actual = f"[{fin_row.get('source_document')} | {loc_fin} | {fin_row.get('period') or ''}]"

        dev_record_id = make_record_id(
            company_id=company_id,
            table="deviation_tracker",
            key_fields={
                "guidance_record_id": guid.get("record_id"),
                "period": target_period,
                "metric_type": metric_type,
            },
        )
        dev_row = {
            "record_id": dev_record_id,
            "guidance_record_id": guid.get("record_id"),
            "actual_record_id": fin_row.get("record_id"),
            "company_id": company_id,
            "period": target_period,
            "metric_type": metric_type,
            "check_type": guid.get("check_type"),
            "guided_value": guided_f,
            "actual_value": actual_f,
            "delta": delta,
            "delta_pct": delta_pct,
            "flag": flag,
            "severity": severity,
            "pattern": pattern,
            "insight": None,
            "source_guidance": source_guidance,
            "source_actual": source_actual,
            "ingested_at": ingested_at,
        }
        ok, _ = validate_curated_row("deviation_tracker", dev_row)
        if ok:
            deviations.append(dev_row)
            history_by_company[company_id].append(dev_row)

    dedup_devs = deduplicate_rows(deviations, key_col="record_id", ts_col="ingested_at")
    dev_keys = write_curated_parquet("deviation_tracker", dedup_devs, storage, engine=engine)

    cred_rows: List[Dict[str, Any]] = []
    grouped_devs: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for d in dedup_devs:
        grouped_devs[d["company_id"]].append(d)

    for company_id, comp_devs in sorted(grouped_devs.items()):
        score_row = _compute_company_credibility(company_id, comp_devs, ingested_at)
        ok, _ = validate_curated_row("credibility_scores", score_row)
        if ok:
            cred_rows.append(score_row)

    cred_keys = write_curated_parquet("credibility_scores", cred_rows, storage, engine=engine)
    return {
        "guidance_count": len(guidance_rows),
        "financial_count": len(financial_rows),
        "deviations_count": len(dedup_devs),
        "credibility_count": len(cred_rows),
        "deviation_keys": dev_keys,
        "credibility_keys": cred_keys,
    }


def main(argv: Optional[List[str]] = None) -> int:
    job_args = parse_job_args(argv)
    _, storage = resolve_storage_from_args(job_args)
    result = run(storage, engine=job_args["engine"])
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
