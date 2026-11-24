"""Curate extracted guidance, risk flags, credit ratings, and raw_data into Parquet."""

from typing import Any, Dict, List, Optional, Sequence, Tuple

from cloud.common.companies import normalize_company_id
from cloud.common.hashing import make_record_id
from cloud.common.manifest import utc_now_iso
from cloud.common.quarantine import QuarantineWriter
from cloud.common.storage import StorageBackend
from cloud.glue_jobs.lib.dq import deduplicate_rows, normalise_period, validate_curated_row
from cloud.glue_jobs.lib.spark_utils import (
    parse_job_args,
    resolve_storage_from_args,
    write_curated_parquet,
)

FACT_TABLES: Tuple[str, ...] = ("guidance_claims", "risk_flags", "credit_ratings", "raw_data")  # type: ignore[name-defined]


def _normalize_fact_row(table: str, raw: Dict[str, Any], ingested_at: str) -> Dict[str, Any]:
    row = dict(raw)
    company_id = normalize_company_id(str(row.get("company_id") or ""), default=None)
    if company_id:
        row["company_id"] = company_id
    if table == "guidance_claims":
        if row.get("statement_quarter"):
            row["statement_quarter"] = normalise_period(row["statement_quarter"])
        if row.get("target_period"):
            norm_tp = normalise_period(row["target_period"])
            if norm_tp.startswith(("FY", "Q1FY", "Q2FY", "Q3FY", "Q4FY")):
                row["target_period"] = norm_tp
    elif row.get("period"):
        norm_p = normalise_period(row["period"])
        if norm_p.startswith(("FY", "Q1FY", "Q2FY", "Q3FY", "Q4FY")):
            row["period"] = norm_p

    if not row.get("record_id") and company_id:
        row["record_id"] = make_record_id(
            company_id=company_id,
            table=table,
            key_fields={
                "source_document": row.get("source_document"),
                "source_page": row.get("source_page"),
                "key": row.get("verbatim_quote") or row.get("description") or row.get("rating_agency") or row.get("value_text"),
            },
        )
    row.setdefault("ingested_at", ingested_at)
    return row


def run(
    storage: StorageBackend,
    engine: str = "auto",
    tables: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    target_tables = tuple(tables) if tables else ("guidance_claims", "risk_flags", "credit_ratings", "raw_data")
    ingested_at = utc_now_iso()
    results: Dict[str, Any] = {}

    for table in target_tables:
        prefix = f"processed/facts/table={table}/"
        candidates: List[Dict[str, Any]] = []
        for key in storage.list_keys(prefix):
            if not key.endswith(".jsonl"):
                continue
            for raw_item in storage.read_jsonl(key):
                candidates.append(_normalize_fact_row(table, raw_item, ingested_at))

        valid_rows: List[Dict[str, Any]] = []
        bad_rows: List[Dict[str, Any]] = []
        for row in candidates:
            ok, err = validate_curated_row(table, row)
            if ok:
                valid_rows.append(row)
            else:
                bad_rows.append({"row": row, "error": err})

        if bad_rows:
            QuarantineWriter(storage).write(
                stage=f"curation/{table}",
                doc_id="batch",
                input_ref={"table": table, "candidate_count": len(candidates)},
                error={"invalid_count": len(bad_rows), "samples": bad_rows[:50]},
            )

        deduped = deduplicate_rows(valid_rows, key_col="record_id", ts_col="ingested_at")
        written_keys = write_curated_parquet(table, deduped, storage, engine=engine)
        results[table] = {
            "candidates": len(candidates),
            "valid": len(valid_rows),
            "deduplicated": len(deduped),
            "quarantined": len(bad_rows),
            "written_keys": written_keys,
        }

    return results


def main(argv: Optional[List[str]] = None) -> int:
    job_args = parse_job_args(argv)
    _, storage = resolve_storage_from_args(job_args)
    result = run(storage, engine=job_args["engine"])
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
