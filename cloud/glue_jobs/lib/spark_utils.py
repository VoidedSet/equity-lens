"""Glue/CLI argument parsing and dual PyArrow + PySpark Parquet I/O utilities."""

import argparse
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import unquote

import pyarrow as pa
import pyarrow.parquet as pq

from cloud.common.config import CloudConfig, get_config
from cloud.common.storage import LocalStorage, S3Storage, StorageBackend, get_storage
from cloud.glue_jobs.lib.schemas import (
    PARTITION_COLUMNS,
    TABLE_FIELD_SPECS,
    get_parquet_data_schema,
    get_spark_schema,
)


def parse_job_args(argv: Optional[List[str]] = None) -> Dict[str, str]:
    """Parse arguments from AWS Glue getResolvedOptions or local CLI flags."""
    raw_argv = argv if argv is not None else sys.argv[1:]
    if "--JOB_NAME" in raw_argv:
        from awsglue.utils import getResolvedOptions  # type: ignore[import-not-found]

        resolved = getResolvedOptions(sys.argv, ["JOB_NAME", "S3_BUCKET", "AWS_REGION"])
        return {
            "job_name": resolved["JOB_NAME"],
            "s3_bucket": resolved["S3_BUCKET"],
            "aws_region": resolved["AWS_REGION"],
            "datalake_root": "",
            "engine": "spark",
        }

    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--datalake-root", default="", help="Override local_datalake directory.")
    parser.add_argument("--s3-bucket", default="", help="Override S3 bucket (switches backend to s3).")
    parser.add_argument("--aws-region", default="", help="Override AWS region.")
    parser.add_argument("--engine", choices=["auto", "spark", "pyarrow"], default="auto")
    parsed = parser.parse_args(raw_argv)
    return {
        "job_name": "local",
        "datalake_root": parsed.datalake_root,
        "s3_bucket": parsed.s3_bucket,
        "aws_region": parsed.aws_region,
        "engine": parsed.engine,
    }


def resolve_storage_from_args(job_args: Dict[str, str]) -> Tuple[CloudConfig, StorageBackend]:
    """Build CloudConfig & StorageBackend honoring CLI/Glue overrides."""
    cfg = get_config()
    updates: Dict[str, Any] = {}
    if job_args.get("s3_bucket"):
        updates["storage_backend"] = "s3"
        updates["s3_bucket"] = job_args["s3_bucket"]
    if job_args.get("aws_region"):
        updates["aws_region"] = job_args["aws_region"]
    if job_args.get("datalake_root"):
        updates["storage_backend"] = "local"
        updates["local_datalake_dir"] = Path(job_args["datalake_root"]).resolve()
    if updates:
        cfg = cfg.model_copy(update=updates)
    return cfg, get_storage(cfg)


def resolve_engine(requested: str = "auto") -> str:
    """Use PySpark when available (or fail if explicitly forced without pyspark); else PyArrow."""
    req = (requested or "auto").strip().lower()
    if req == "pyarrow":
        return "pyarrow"

    try:
        import pyspark  # noqa: F401
        return "spark"
    except ImportError as exc:
        if req == "spark":
            raise ImportError("pyspark is required when --engine=spark is specified") from exc
        return "pyarrow"


def _safe_partition_val(val: Any) -> str:
    text = str(val if val is not None else "UNKNOWN").strip()
    return text.replace("/", "_").replace("\\", "_") or "UNKNOWN"


def _coerce_value(val: Any, dtype: str) -> Any:
    if val is None:
        return None
    if isinstance(val, float) and not math.isfinite(val):
        return None
    if dtype == "string":
        return str(val)
    if dtype == "float64":
        return float(val)
    if dtype == "int32":
        return int(val)
    return val


def _rows_to_pa_table(table_name: str, rows: List[Dict[str, Any]], exclude_cols: set[str]) -> pa.Table:
    data_schema = get_parquet_data_schema(table_name)
    specs = [spec for spec in TABLE_FIELD_SPECS[table_name] if spec[0] not in exclude_cols]
    columns: Dict[str, List[Any]] = {name: [] for name, _ in specs}
    for row in rows:
        for name, dtype in specs:
            columns[name].append(_coerce_value(row.get(name), dtype))
    return pa.table(columns, schema=data_schema)


def _write_with_pyarrow(table_name: str, rows: List[Dict[str, Any]], storage: StorageBackend) -> List[str]:
    if not rows:
        return []

    part_cols = PARTITION_COLUMNS[table_name]
    part_col_set = set(part_cols)
    grouped: Dict[Tuple[str, ...], List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        part_key = tuple(_safe_partition_val(row.get(col)) for col in part_cols)
        grouped[part_key].append(row)

    written_keys: List[str] = []
    for part_vals, group_rows in sorted(grouped.items()):
        part_segments = "/".join(f"{col}={val}" for col, val in zip(part_cols, part_vals))
        part_prefix = f"curated/{table_name}/{part_segments}/"

        if isinstance(storage, LocalStorage):
            part_dir = storage.root / part_prefix
            if part_dir.exists():
                for old_file in part_dir.glob("*.parquet"):
                    old_file.unlink()

        pa_table = _rows_to_pa_table(table_name, group_rows, exclude_cols=part_col_set)
        sink = pa.BufferOutputStream()
        pq.write_table(pa_table, sink, compression="snappy")
        out_key = f"{part_prefix}part-00000.parquet"
        storage.write_bytes(out_key, sink.getvalue().to_pybytes(), content_type="application/octet-stream")
        written_keys.append(out_key)

    return written_keys


def _write_with_spark(table_name: str, rows: List[Dict[str, Any]], storage: StorageBackend) -> List[str]:
    from pyspark.sql import SparkSession

    part_cols = PARTITION_COLUMNS[table_name]
    spark = (
        SparkSession.builder.appName(f"equity-lens-{table_name}")
        .config("spark.sql.sources.partitionOverwriteMode", "dynamic")
        .getOrCreate()
    )
    spark_schema = get_spark_schema(table_name)
    specs = TABLE_FIELD_SPECS[table_name]
    normalized_rows = [
        {name: _coerce_value(row.get(name), dtype) for name, dtype in specs}
        for row in rows
    ]
    df = spark.createDataFrame(normalized_rows, schema=spark_schema)

    if isinstance(storage, S3Storage):
        target = f"s3://{storage.bucket}/curated/{table_name}"
    elif isinstance(storage, LocalStorage):
        target = str((storage.root / "curated" / table_name).resolve())
    else:
        raise TypeError(f"Unsupported storage backend for Spark writes: {type(storage).__name__}")

    (
        df.write.mode("overwrite")
        .option("compression", "snappy")
        .partitionBy(*part_cols)
        .parquet(target)
    )
    return storage.list_keys(f"curated/{table_name}/")


def write_curated_parquet(
    table_name: str,
    rows: List[Dict[str, Any]],
    storage: StorageBackend,
    engine: str = "auto",
) -> List[str]:
    """Write rows as Hive-partitioned Snappy Parquet under curated/<table_name>/."""
    if table_name not in TABLE_FIELD_SPECS:
        raise ValueError(f"Unknown curated table: {table_name!r}")
    if not rows:
        return []

    chosen = resolve_engine(engine)
    if chosen == "spark":
        return _write_with_spark(table_name, rows, storage)
    return _write_with_pyarrow(table_name, rows, storage)


def _clean_read_row(row: Dict[str, Any]) -> Dict[str, Any]:
    cleaned: Dict[str, Any] = {}
    for k, v in row.items():
        if isinstance(v, float) and not math.isfinite(v):
            cleaned[k] = None
        else:
            cleaned[k] = v
    return cleaned


def read_curated_parquet(table_name: str, storage: StorageBackend) -> List[Dict[str, Any]]:
    """Read all Hive-partitioned Parquet files for a curated table, restoring partition columns."""
    if table_name not in TABLE_FIELD_SPECS:
        raise ValueError(f"Unknown curated table: {table_name!r}")

    prefix = f"curated/{table_name}/"
    part_cols = set(PARTITION_COLUMNS[table_name])
    rows: List[Dict[str, Any]] = []

    for key in storage.list_keys(prefix):
        if not key.endswith(".parquet"):
            continue
        part_values: Dict[str, str] = {}
        for segment in key[len(prefix) :].split("/")[:-1]:
            if "=" in segment:
                col_name, raw_val = segment.split("=", 1)
                if col_name in part_cols:
                    part_values[col_name] = unquote(raw_val)

        raw_bytes = storage.read_bytes(key)
        pa_table = pq.read_table(pa.BufferReader(raw_bytes))
        for item in pa_table.to_pylist():
            merged = {**item, **part_values}
            rows.append(_clean_read_row(merged))

    return rows
