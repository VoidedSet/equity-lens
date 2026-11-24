"""Curate document chunk metadata into curated/document_chunks/ Parquet."""

from typing import Any, Dict, List, Optional

from cloud.common.companies import normalize_company_id
from cloud.common.manifest import utc_now_iso
from cloud.common.quarantine import QuarantineWriter
from cloud.common.storage import StorageBackend
from cloud.glue_jobs.lib.dq import deduplicate_rows, validate_curated_row
from cloud.glue_jobs.lib.spark_utils import (
    parse_job_args,
    resolve_storage_from_args,
    write_curated_parquet,
)


def run(storage: StorageBackend, engine: str = "auto") -> Dict[str, Any]:
    ingested_at = utc_now_iso()
    candidates: List[Dict[str, Any]] = []

    for key in storage.list_keys("processed/chunks/"):
        if not key.endswith(".jsonl"):
            continue
        for raw_row in storage.read_jsonl(key):
            row = dict(raw_row)
            company_id = normalize_company_id(str(row.get("company_id") or ""), default=None)
            if company_id:
                row["company_id"] = company_id
            row.setdefault("ingested_at", ingested_at)
            candidates.append(row)

    valid_rows: List[Dict[str, Any]] = []
    bad_rows: List[Dict[str, Any]] = []
    for row in candidates:
        ok, err = validate_curated_row("document_chunks", row)
        if ok:
            valid_rows.append(row)
        else:
            bad_rows.append({"row": row, "error": err})

    if bad_rows:
        QuarantineWriter(storage).write(
            stage="curation/document_chunks",
            doc_id="batch",
            input_ref={"table": "document_chunks", "candidate_count": len(candidates)},
            error={"invalid_count": len(bad_rows), "samples": bad_rows[:50]},
        )

    deduped = deduplicate_rows(valid_rows, key_col="chunk_id", ts_col="ingested_at")
    written_keys = write_curated_parquet("document_chunks", deduped, storage, engine=engine)
    return {
        "table": "document_chunks",
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
