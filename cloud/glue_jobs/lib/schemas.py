"""Canonical curated table schemas (PyArrow + lazy PySpark) and Hive partition specs."""

from typing import Dict, List, Tuple

import pyarrow as pa

FieldSpec = Tuple[str, str]  # (column_name, "string" | "float64" | "int32")

TABLE_FIELD_SPECS: Dict[str, List[FieldSpec]] = {
    "financials": [
        ("record_id", "string"),
        ("doc_id", "string"),
        ("company_id", "string"),
        ("period", "string"),
        ("period_type", "string"),
        ("metric", "string"),
        ("value", "float64"),
        ("unit", "string"),
        ("yoy_change", "float64"),
        ("source_document", "string"),
        ("source_page", "int32"),
        ("source_timestamp", "string"),
        ("period_label", "string"),
        ("ingested_at", "string"),
    ],
    "guidance_claims": [
        ("record_id", "string"),
        ("doc_id", "string"),
        ("company_id", "string"),
        ("statement_quarter", "string"),
        ("statement_date", "string"),
        ("target_period", "string"),
        ("metric_type", "string"),
        ("guidance_value_low", "float64"),
        ("guidance_value_high", "float64"),
        ("guidance_value_point", "float64"),
        ("unit", "string"),
        ("verbatim_quote", "string"),
        ("confidence_language", "string"),
        ("speaker", "string"),
        ("check_type", "string"),
        ("source_document", "string"),
        ("source_page", "int32"),
        ("source_timestamp", "string"),
        ("ingested_at", "string"),
    ],
    "risk_flags": [
        ("record_id", "string"),
        ("doc_id", "string"),
        ("company_id", "string"),
        ("period", "string"),
        ("category", "string"),
        ("check_type", "string"),
        ("description", "string"),
        ("severity", "string"),
        ("subcategory", "string"),
        ("verbatim_quote", "string"),
        ("source_document", "string"),
        ("source_page", "int32"),
        ("ingested_at", "string"),
    ],
    "credit_ratings": [
        ("record_id", "string"),
        ("doc_id", "string"),
        ("company_id", "string"),
        ("period", "string"),
        ("rating_agency", "string"),
        ("rating_scale", "string"),
        ("rating_outlook", "string"),
        ("instrument", "string"),
        ("rating_date", "string"),
        ("rating_amount_crores", "float64"),
        ("previous_rating", "string"),
        ("watch_status", "string"),
        ("rationale", "string"),
        ("source_document", "string"),
        ("source_page", "int32"),
        ("ingested_at", "string"),
    ],
    "raw_data": [
        ("record_id", "string"),
        ("doc_id", "string"),
        ("company_id", "string"),
        ("period", "string"),
        ("data_type", "string"),
        ("category", "string"),
        ("key_name", "string"),
        ("value_text", "string"),
        ("value_numeric", "float64"),
        ("unit", "string"),
        ("context", "string"),
        ("source_document", "string"),
        ("source_page", "int32"),
        ("source_timestamp", "string"),
        ("ingested_at", "string"),
    ],
    "document_chunks": [
        ("chunk_id", "string"),
        ("doc_id", "string"),
        ("company_id", "string"),
        ("document_type", "string"),
        ("period", "string"),
        ("chunk_index", "int32"),
        ("section_name", "string"),
        ("source_document", "string"),
        ("source_page", "int32"),
        ("speaker", "string"),
        ("source_timestamp", "string"),
        ("chunk_text", "string"),
        ("ingested_at", "string"),
    ],
    "deviation_tracker": [
        ("record_id", "string"),
        ("guidance_record_id", "string"),
        ("actual_record_id", "string"),
        ("company_id", "string"),
        ("period", "string"),
        ("metric_type", "string"),
        ("check_type", "string"),
        ("guided_value", "float64"),
        ("actual_value", "float64"),
        ("delta", "float64"),
        ("delta_pct", "float64"),
        ("flag", "string"),
        ("severity", "string"),
        ("pattern", "string"),
        ("insight", "string"),
        ("source_guidance", "string"),
        ("source_actual", "string"),
        ("ingested_at", "string"),
    ],
    "credibility_scores": [
        ("record_id", "string"),
        ("company_id", "string"),
        ("period", "string"),
        ("overall_score", "float64"),
        ("check_1_revpar_score", "float64"),
        ("check_2_keys_score", "float64"),
        ("check_3_driver_score", "float64"),
        ("check_4_fnb_score", "float64"),
        ("check_5_debt_score", "float64"),
        ("check_6_supply_score", "float64"),
        ("hit_rate", "float64"),
        ("avg_deviation", "float64"),
        ("total_guidance_count", "int32"),
        ("total_matched_count", "int32"),
        ("consecutive_misses", "int32"),
        ("trend", "string"),
        ("ingested_at", "string"),
    ],
}

PARTITION_COLUMNS: Dict[str, List[str]] = {
    "financials": ["company_id", "period_type"],
    "guidance_claims": ["company_id"],
    "risk_flags": ["company_id"],
    "credit_ratings": ["company_id"],
    "raw_data": ["company_id"],
    "document_chunks": ["company_id", "document_type"],
    "deviation_tracker": ["company_id"],
    "credibility_scores": ["company_id"],
}

_PA_TYPES = {
    "string": pa.string(),
    "float64": pa.float64(),
    "int32": pa.int32(),
}


def _build_pa_schema(specs: List[FieldSpec]) -> pa.Schema:
    return pa.schema([pa.field(name, _PA_TYPES[dtype], nullable=True) for name, dtype in specs])


CURATED_SCHEMAS: Dict[str, pa.Schema] = {
    table: _build_pa_schema(specs) for table, specs in TABLE_FIELD_SPECS.items()
}


def get_parquet_data_schema(table: str) -> pa.Schema:
    """Return PyArrow schema excluding Hive partition columns (written in S3/directory path)."""
    part_cols = set(PARTITION_COLUMNS[table])
    specs = [spec for spec in TABLE_FIELD_SPECS[table] if spec[0] not in part_cols]
    return _build_pa_schema(specs)


def get_spark_schema(table: str):
    """Lazily build PySpark StructType matching CURATED_SCHEMAS[table]."""
    from pyspark.sql.types import DoubleType, IntegerType, StringType, StructField, StructType

    spark_types = {
        "string": StringType(),
        "float64": DoubleType(),
        "int32": IntegerType(),
    }
    return StructType(
        [StructField(name, spark_types[dtype], nullable=True) for name, dtype in TABLE_FIELD_SPECS[table]]
    )
