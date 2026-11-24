"""Curate Screener CSV JSONLs + Bedrock/Gemma financial facts into curated/financials/ Parquet."""

import re
from collections import defaultdict
from typing import Any, Dict, List, Optional

from cloud.common.companies import normalize_company_id
from cloud.common.hashing import make_record_id
from cloud.common.manifest import utc_now_iso
from cloud.common.quarantine import QuarantineWriter
from cloud.common.storage import StorageBackend
from cloud.glue_jobs.lib.dq import (
    BS_METRIC_MAP,
    PL_METRIC_MAP,
    deduplicate_rows,
    get_financial_unit,
    mar_to_fy,
    parse_numeric,
    quarter_to_period,
    validate_curated_row,
)
from cloud.glue_jobs.lib.spark_utils import (
    parse_job_args,
    resolve_storage_from_args,
    write_curated_parquet,
)

_FY_RE = re.compile(r"^FY(\d{2})$")


def _screener_rows_to_financials(screener_rows: List[Dict[str, Any]], ingested_at: str) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    skip_until_next_doc: Optional[str] = None

    # Sort deterministically by doc_id and row_index so Additional Metrics boundary holds per CSV file
    ordered = sorted(screener_rows, key=lambda r: (str(r.get("doc_id") or ""), int(r.get("row_index") or 0)))

    for entry in ordered:
        doc_id = str(entry.get("doc_id") or "")
        if skip_until_next_doc == doc_id:
            continue

        metric_raw = str(entry.get("metric_name") or "").strip()
        if metric_raw == "Additional Metrics":
            skip_until_next_doc = doc_id
            continue

        doc_type = str(entry.get("doc_type") or "")
        company_id = normalize_company_id(str(entry.get("company_id") or ""), default=None)
        if not company_id:
            continue

        if doc_type in ("profit_loss", "profit_loss_enriched"):
            metric_key = PL_METRIC_MAP.get(metric_raw)
            period_type = "annual"
        elif doc_type in ("balance_sheet", "balance_sheet_enriched"):
            metric_key = BS_METRIC_MAP.get(metric_raw)
            period_type = "annual"
        elif doc_type in ("quarter_analysis", "quarter_analysis_enriched"):
            metric_key = PL_METRIC_MAP.get(metric_raw)
            period_type = "quarterly"
        else:
            continue

        if not metric_key:
            continue

        filename = str(entry.get("filename") or f"{doc_type}.csv")
        source_document = f"Screener.in — {company_id} {filename}"
        values = entry.get("values") or {}
        row_ingested_at = str(entry.get("ingested_at") or ingested_at)

        for col_name, raw_val in values.items():
            col_clean = str(col_name).strip()
            if not col_clean or col_clean.upper() == "TTM":
                continue
            if doc_type.startswith("balance_sheet") and not col_clean.startswith("Mar"):
                continue

            val = parse_numeric(raw_val)
            if val is None:
                continue

            period = mar_to_fy(col_clean) if period_type == "annual" else quarter_to_period(col_clean)
            record_id = make_record_id(
                company_id=company_id,
                table="financials",
                key_fields={
                    "period": period,
                    "period_type": period_type,
                    "metric": metric_key,
                    "source_document": source_document,
                    "source_page": None,
                },
            )
            records.append(
                {
                    "record_id": record_id,
                    "doc_id": doc_id,
                    "company_id": company_id,
                    "period": period,
                    "period_type": period_type,
                    "metric": metric_key,
                    "value": val,
                    "unit": get_financial_unit(metric_key),
                    "yoy_change": None,
                    "source_document": source_document,
                    "source_page": None,
                    "source_timestamp": None,
                    "period_label": period,
                    "ingested_at": row_ingested_at,
                }
            )

    return records


def _compute_annual_yoy(rows: List[Dict[str, Any]]) -> None:
    by_series: Dict[tuple[str, str], Dict[int, Dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        if row.get("period_type") != "annual":
            continue
        match = _FY_RE.match(str(row.get("period") or ""))
        if not match:
            continue
        fy_num = int(match.group(1))
        by_series[(row["company_id"], row["metric"])][fy_num] = row

    for series in by_series.values():
        for fy_num, row in series.items():
            if row.get("yoy_change") is not None:
                continue
            prev = series.get(fy_num - 1)
            if prev is None:
                continue
            prev_val = prev.get("value")
            cur_val = row.get("value")
            if prev_val in (None, 0) or cur_val is None:
                continue
            row["yoy_change"] = round(((float(cur_val) - float(prev_val)) / abs(float(prev_val))) * 100.0, 2)


def run(storage: StorageBackend, engine: str = "auto") -> Dict[str, Any]:
    """Read processed/screener and processed/facts/table=financials, validate, dedup, and curate."""
    ingested_at = utc_now_iso()
    candidates: List[Dict[str, Any]] = []

    screener_rows: List[Dict[str, Any]] = []
    for key in storage.list_keys("processed/screener/"):
        if key.endswith(".jsonl"):
            screener_rows.extend(storage.read_jsonl(key))
    candidates.extend(_screener_rows_to_financials(screener_rows, ingested_at))

    for key in storage.list_keys("processed/facts/table=financials/"):
        if not key.endswith(".jsonl"):
            continue
        for row in storage.read_jsonl(key):
            item = dict(row)
            company_id = normalize_company_id(str(item.get("company_id") or ""), default=None)
            if company_id:
                item["company_id"] = company_id
            if not item.get("record_id") and company_id:
                item["record_id"] = make_record_id(
                    company_id=company_id,
                    table="financials",
                    key_fields={
                        "period": item.get("period"),
                        "period_type": item.get("period_type", "annual"),
                        "metric": item.get("metric"),
                        "source_document": item.get("source_document"),
                        "source_page": item.get("source_page"),
                    },
                )
            item.setdefault("ingested_at", ingested_at)
            candidates.append(item)

    valid_rows: List[Dict[str, Any]] = []
    bad_rows: List[Dict[str, Any]] = []
    for row in candidates:
        ok, err = validate_curated_row("financials", row)
        if ok:
            valid_rows.append(row)
        else:
            bad_rows.append({"row": row, "error": err})

    if bad_rows:
        QuarantineWriter(storage).write(
            stage="curation/financials",
            doc_id="batch",
            input_ref={"table": "financials", "candidate_count": len(candidates)},
            error={"invalid_count": len(bad_rows), "samples": bad_rows[:50]},
        )

    deduped = deduplicate_rows(valid_rows, key_col="record_id", ts_col="ingested_at")
    _compute_annual_yoy(deduped)
    written_keys = write_curated_parquet("financials", deduped, storage, engine=engine)

    return {
        "table": "financials",
        "candidates": len(candidates),
        "valid": len(valid_rows),
        "deduplicated": len(deduped),
        "quarantined": len(bad_rows),
        "written_keys": written_keys,
    }


def main(argv: Optional[List[str]] = None) -> int:
    job_args = parse_job_args(argv)
    _, storage = resolve_storage_from_args(job_args)
    result = run(storage, engine=job_args["engine"])
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
