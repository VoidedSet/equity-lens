"""Validated, idempotent batch synchronization from S3 curated/ + processed embeddings to Supabase."""

import argparse
import json
import math
import time
from typing import Any, Callable, Dict, List, Optional, Sequence

from cloud.common.config import CloudConfig, get_config
from cloud.common.llm import retry_with_backoff
from cloud.common.quarantine import QuarantineWriter
from cloud.common.storage import StorageBackend, get_storage
from cloud.glue_jobs.lib.dq import deduplicate_rows
from cloud.glue_jobs.lib.spark_utils import read_curated_parquet

COMPANY_SEED_ROWS: List[Dict[str, Any]] = [
    {
        "id": "IHCL",
        "name": "Indian Hotels Company Ltd",
        "ticker_nse": "INDHOTEL",
        "segment": "premium_luxury",
        "strategy": "hybrid",
        "brands": ["Taj", "Vivanta", "SeleQtions", "Ginger"],
        "key_markets": ["Mumbai", "Delhi", "Bengaluru", "Goa"],
    },
    {
        "id": "CHALET",
        "name": "Chalet Hotels Ltd",
        "ticker_nse": "CHALET",
        "segment": "upper_midscale",
        "strategy": "asset_heavy",
        "brands": ["Marriott", "Westin", "Renaissance", "Four Points"],
        "key_markets": ["Mumbai", "Bengaluru", "Hyderabad", "Pune"],
    },
    {
        "id": "LEMONTREE",
        "name": "Lemon Tree Hotels Ltd",
        "ticker_nse": "LEMONTREE",
        "segment": "economy_midscale",
        "strategy": "hybrid",
        "brands": ["Aurika", "Lemon Tree Premier", "Lemon Tree", "Red Fox", "Keys"],
        "key_markets": ["Delhi-NCR", "Hyderabad", "Mumbai", "Bengaluru"],
    },
    {
        "id": "EIH",
        "name": "EIH Ltd (Oberoi Group)",
        "ticker_nse": "EIHOTEL",
        "segment": "premium_luxury",
        "strategy": "asset_heavy",
        "brands": ["Oberoi", "Trident"],
        "key_markets": ["Delhi", "Mumbai", "Udaipur", "Agra"],
    },
    {
        "id": "JUNIPER",
        "name": "Juniper Hotels Ltd",
        "ticker_nse": "JUNIPER",
        "segment": "luxury_upper_upscale",
        "strategy": "asset_heavy",
        "brands": ["Grand Hyatt", "Andaz", "Hyatt Regency", "Hyatt Place"],
        "key_markets": ["Mumbai", "Delhi", "Ahmedabad", "Lucknow"],
    },
]

TABLE_SYNC_CONFIG: Dict[str, Dict[str, Any]] = {
    "financials": {
        "on_conflict": "record_id",
        "columns": [
            "record_id", "doc_id", "company_id", "period", "period_type", "metric",
            "value", "unit", "yoy_change", "source_document", "source_page",
            "source_timestamp", "period_label",
        ],
    },
    "guidance_claims": {
        "on_conflict": "record_id",
        "columns": [
            "record_id", "doc_id", "company_id", "statement_quarter", "statement_date",
            "target_period", "metric_type", "guidance_value_low", "guidance_value_high",
            "guidance_value_point", "unit", "verbatim_quote", "confidence_language",
            "speaker", "check_type", "source_document", "source_page", "source_timestamp",
        ],
    },
    "risk_flags": {
        "on_conflict": "record_id",
        "columns": [
            "record_id", "doc_id", "company_id", "period", "category", "check_type",
            "description", "severity", "subcategory", "verbatim_quote",
            "source_document", "source_page",
        ],
    },
    "credit_ratings": {
        "on_conflict": "record_id",
        "columns": [
            "record_id", "doc_id", "company_id", "period", "rating_agency",
            "rating_scale", "rating_outlook", "instrument", "rating_date",
            "rating_amount_crores", "previous_rating", "watch_status", "rationale",
            "source_document", "source_page",
        ],
    },
    "raw_data": {
        "on_conflict": "record_id",
        "columns": [
            "record_id", "doc_id", "company_id", "period", "data_type", "category",
            "key_name", "value_text", "value_numeric", "unit", "context",
            "source_document", "source_page", "source_timestamp",
        ],
    },
    "deviation_tracker": {
        "on_conflict": "record_id",
        "columns": [
            "record_id", "company_id", "period", "metric_type", "check_type",
            "guided_value", "actual_value", "delta", "delta_pct", "flag",
            "severity", "pattern", "insight", "source_guidance", "source_actual",
        ],
    },
    "credibility_scores": {
        "on_conflict": "company_id,period",
        "columns": [
            "company_id", "period", "overall_score", "check_1_revpar_score",
            "check_2_keys_score", "check_3_driver_score", "check_4_fnb_score",
            "check_5_debt_score", "check_6_supply_score", "hit_rate",
            "avg_deviation", "total_guidance_count", "total_matched_count",
            "consecutive_misses", "trend",
        ],
    },
    "document_chunks": {
        "on_conflict": "chunk_id",
        "columns": [
            "chunk_id", "doc_id", "company_id", "document_type", "period",
            "chunk_index", "section_name", "source_document", "source_page",
            "speaker", "embedding", "chunk_text",
        ],
    },
}


def _get_supabase_client(cfg: CloudConfig) -> Any:
    if not cfg.supabase_url or not cfg.supabase_service_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY are required for Supabase sync")
    from supabase import create_client

    return create_client(cfg.supabase_url, cfg.supabase_service_key)


def _is_retryable_supabase_error(exc: Exception) -> bool:
    status = getattr(exc, "status_code", None)
    if status in {429, 500, 502, 503, 504}:
        return True
    msg = f"{type(exc).__name__} {exc}".lower()
    return any(tok in msg for tok in ("429", "502", "503", "504", "timeout", "temporarily", "rate limit", "connection"))


def _sanitize_value(val: Any) -> Any:
    if isinstance(val, float) and not math.isfinite(val):
        return None
    return val


def _project_rows(rows: List[Dict[str, Any]], allowed_cols: Sequence[str]) -> List[Dict[str, Any]]:
    projected: List[Dict[str, Any]] = []
    for row in rows:
        item = {col: _sanitize_value(row.get(col)) for col in allowed_cols if col in row or row.get(col) is not None}
        for col in allowed_cols:
            item.setdefault(col, None)
        projected.append(item)
    return projected


def ensure_companies(supabase_client: Any) -> int:
    """Idempotently upsert canonical company master records."""
    supabase_client.table("companies").upsert(COMPANY_SEED_ROWS, on_conflict="id").execute()
    return len(COMPANY_SEED_ROWS)


def _load_document_chunks_for_sync(storage: StorageBackend) -> List[Dict[str, Any]]:
    emb_rows: List[Dict[str, Any]] = []
    for key in storage.list_keys("processed/embeddings/"):
        if key.endswith(".jsonl"):
            emb_rows.extend(storage.read_jsonl(key))

    if emb_rows:
        return deduplicate_rows(emb_rows, key_col="chunk_id", ts_col="ingested_at")

    return read_curated_parquet("document_chunks", storage)


def sync_curated_to_supabase(
    storage: StorageBackend,
    supabase_client: Any = None,
    config: Optional[CloudConfig] = None,
    tables: Optional[Sequence[str]] = None,
    batch_size: int = 200,
    dry_run: bool = False,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> Dict[str, Any]:
    """Upsert curated Parquet datasets (and processed embeddings) into Supabase idempotently."""
    cfg = config or get_config()
    target_tables = tuple(tables) if tables else tuple(TABLE_SYNC_CONFIG.keys())
    for t in target_tables:
        if t not in TABLE_SYNC_CONFIG:
            raise ValueError(f"Unsupported sync table: {t!r}")

    client = None if dry_run else (supabase_client or _get_supabase_client(cfg))
    if client is not None:
        ensure_companies(client)

    quarantine = QuarantineWriter(storage)
    summary: Dict[str, Any] = {"tables": {}, "total_upserted": 0, "total_errors": 0}

    for table in target_tables:
        spec = TABLE_SYNC_CONFIG[table]
        raw_rows = (
            _load_document_chunks_for_sync(storage)
            if table == "document_chunks"
            else read_curated_parquet(table, storage)
        )
        rows = _project_rows(raw_rows, spec["columns"])

        if dry_run or not rows:
            summary["tables"][table] = {
                "rows_read": len(rows),
                "upserted": 0 if dry_run else len(rows),
                "errors": 0,
            }
            continue

        table_upserted = 0
        table_errors = 0
        step = max(1, batch_size)
        for batch_idx, start in enumerate(range(0, len(rows), step)):
            batch = rows[start : start + step]

            def _upsert_batch() -> str:
                client.table(table).upsert(batch, on_conflict=spec["on_conflict"]).execute()
                return "ok"

            try:
                retry_with_backoff(
                    _upsert_batch,
                    is_retryable=_is_retryable_supabase_error,
                    max_attempts=4,
                    base_delay=1.0,
                    sleep_fn=sleep_fn,
                )
                table_upserted += len(batch)
            except Exception as exc:
                table_errors += len(batch)
                quarantine.write(
                    stage="sync",
                    doc_id=f"{table}_batch_{batch_idx}",
                    input_ref={"table": table, "batch_index": batch_idx, "row_count": len(batch)},
                    error={"type": type(exc).__name__, "message": str(exc), "rows": batch[:20]},
                )

        summary["tables"][table] = {
            "rows_read": len(rows),
            "upserted": table_upserted,
            "errors": table_errors,
        }
        summary["total_upserted"] += table_upserted
        summary["total_errors"] += table_errors

    return summary


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Idempotently sync curated lakehouse datasets to Supabase.")
    parser.add_argument("--tables", default="", help="Comma-separated subset of tables to sync.")
    parser.add_argument("--batch-size", type=int, default=200)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    cfg = get_config()
    storage = get_storage(cfg)
    table_list = [t.strip() for t in args.tables.split(",") if t.strip()] or None
    result = sync_curated_to_supabase(
        storage=storage,
        config=cfg,
        tables=table_list,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, indent=2))
    return 0 if result["total_errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
