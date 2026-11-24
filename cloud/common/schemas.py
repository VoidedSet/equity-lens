"""Pydantic validation schemas and deterministic record IDs for lakehouse outputs."""

import math
from typing import Any, Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from cloud.common.companies import normalize_company_id
from cloud.common.hashing import make_record_id

TABLE_NAME_MAP: Dict[str, str] = {
    "HOTEL_OPS_METRIC": "financials",
    "hotel_ops_metric": "financials",
    "FINANCIAL_METRIC": "financials",
    "financial_metric": "financials",
    "financials": "financials",
    "GUIDANCE_CLAIM": "guidance_claims",
    "guidance_claim": "guidance_claims",
    "guidance_claims": "guidance_claims",
    "RISK_FLAG": "risk_flags",
    "risk_flag": "risk_flags",
    "risk_flags": "risk_flags",
    "CREDIT_RATING": "credit_ratings",
    "credit_rating": "credit_ratings",
    "credit_ratings": "credit_ratings",
    "RAW_DATA": "raw_data",
    "raw_data": "raw_data",
}


def _clean_optional_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


class ChunkRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    chunk_id: str
    doc_id: str
    company_id: str
    document_type: str
    period: str
    chunk_index: int
    section_name: str = "general"
    source_document: str
    source_page: Optional[int] = None
    speaker: Optional[str] = None
    source_timestamp: Optional[str] = None
    chunk_text: str = Field(min_length=1)
    ingested_at: str

    @field_validator("company_id", mode="before")
    @classmethod
    def _norm_company(cls, v: Any) -> str:
        return normalize_company_id(v)


class EmbeddingRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    chunk_id: str
    doc_id: str
    company_id: str
    document_type: str
    period: str
    chunk_index: int
    section_name: str = "general"
    source_document: str
    source_page: Optional[int] = None
    speaker: Optional[str] = None
    chunk_text: str = Field(min_length=1)
    embedding: List[float]
    embedding_model: str
    ingested_at: str

    @field_validator("company_id", mode="before")
    @classmethod
    def _norm_company(cls, v: Any) -> str:
        return normalize_company_id(v)


class _FactBase(BaseModel):
    model_config = ConfigDict(extra="ignore")

    company_id: str
    source_document: str = Field(min_length=1)
    source_page: Optional[int] = None
    period: Optional[str] = None

    @field_validator("company_id", mode="before")
    @classmethod
    def _norm_company(cls, v: Any) -> str:
        return normalize_company_id(v)

    @field_validator("source_document", mode="before")
    @classmethod
    def _strip_doc(cls, v: Any) -> str:
        text = _clean_optional_str(v)
        if not text:
            raise ValueError("source_document cannot be empty")
        return text


class FinancialFact(_FactBase):
    period: str = Field(min_length=1)
    period_type: Literal["quarterly", "annual"] = "annual"
    metric: str = Field(min_length=1)
    value: float
    unit: Optional[str] = None
    yoy_change: Optional[float] = None
    source_timestamp: Optional[str] = None
    period_label: Optional[str] = None

    @field_validator("period", "metric", mode="before")
    @classmethod
    def _non_empty_str(cls, v: Any) -> str:
        text = _clean_optional_str(v)
        if not text:
            raise ValueError("field cannot be empty")
        return text

    @field_validator("value")
    @classmethod
    def _finite_value(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError("value must be finite")
        return v


class GuidanceClaimFact(_FactBase):
    statement_quarter: Optional[str] = None
    statement_date: Optional[str] = None
    target_period: Optional[str] = None
    metric_type: str = "other"
    guidance_value_low: Optional[float] = None
    guidance_value_high: Optional[float] = None
    guidance_value_point: Optional[float] = None
    unit: Optional[str] = None
    verbatim_quote: str = Field(min_length=1)
    confidence_language: Optional[str] = None
    speaker: Optional[str] = None
    check_type: Optional[str] = None
    source_timestamp: Optional[str] = None

    @field_validator("verbatim_quote", mode="before")
    @classmethod
    def _quote_non_empty(cls, v: Any) -> str:
        text = _clean_optional_str(v)
        if not text:
            raise ValueError("verbatim_quote cannot be empty")
        return text

    @field_validator("metric_type", mode="before")
    @classmethod
    def _metric_type_default(cls, v: Any) -> str:
        return _clean_optional_str(v) or "other"


class RiskFlagFact(_FactBase):
    category: Literal[
        "debt",
        "governance",
        "operational",
        "regulatory",
        "auditor",
        "supply_overhang",
        "margin_compression",
        "management_mismatch",
        "key_person",
    ]
    check_type: Optional[str] = None
    description: str = Field(min_length=1)
    severity: Literal["critical", "high", "medium"] = "medium"
    subcategory: Optional[str] = None
    verbatim_quote: Optional[str] = None

    @field_validator("description", mode="before")
    @classmethod
    def _desc_non_empty(cls, v: Any) -> str:
        text = _clean_optional_str(v)
        if not text:
            raise ValueError("description cannot be empty")
        return text

    @field_validator("category", "severity", mode="before")
    @classmethod
    def _lower_enum(cls, v: Any) -> Any:
        return v.strip().lower() if isinstance(v, str) else v


class CreditRatingFact(_FactBase):
    rating_agency: str = Field(min_length=1)
    rating_scale: Optional[str] = None
    rating_outlook: Optional[str] = None
    instrument: Optional[str] = None
    rating_date: Optional[str] = None
    rating_amount_crores: Optional[float] = None
    previous_rating: Optional[str] = None
    watch_status: Optional[str] = None
    rationale: Optional[str] = None

    @field_validator("rating_agency", mode="before")
    @classmethod
    def _agency_non_empty(cls, v: Any) -> str:
        text = _clean_optional_str(v)
        if not text:
            raise ValueError("rating_agency cannot be empty")
        return text


class RawDataFact(_FactBase):
    data_type: Optional[str] = "qualitative"
    category: Optional[str] = "other"
    key_name: Optional[str] = None
    value_text: str = Field(min_length=1)
    value_numeric: Optional[float] = None
    unit: Optional[str] = None
    context: Optional[str] = None
    source_timestamp: Optional[str] = None

    @field_validator("value_text", mode="before")
    @classmethod
    def _text_non_empty(cls, v: Any) -> str:
        text = _clean_optional_str(v)
        if not text:
            raise ValueError("value_text cannot be empty")
        return text


_TABLE_MODEL_MAP = {
    "financials": FinancialFact,
    "guidance_claims": GuidanceClaimFact,
    "risk_flags": RiskFlagFact,
    "credit_ratings": CreditRatingFact,
    "raw_data": RawDataFact,
}


def _record_key_fields(table: str, cleaned: Dict[str, Any]) -> Dict[str, Any]:
    if table == "financials":
        return {
            "period": cleaned.get("period"),
            "period_type": cleaned.get("period_type"),
            "metric": cleaned.get("metric"),
            "source_document": cleaned.get("source_document"),
            "source_page": cleaned.get("source_page"),
        }
    if table == "guidance_claims":
        return {
            "statement_quarter": cleaned.get("statement_quarter"),
            "target_period": cleaned.get("target_period"),
            "metric_type": cleaned.get("metric_type"),
            "verbatim_quote": cleaned.get("verbatim_quote"),
            "source_document": cleaned.get("source_document"),
            "source_page": cleaned.get("source_page"),
        }
    if table == "risk_flags":
        return {
            "period": cleaned.get("period"),
            "category": cleaned.get("category"),
            "description": cleaned.get("description"),
            "source_document": cleaned.get("source_document"),
            "source_page": cleaned.get("source_page"),
        }
    if table == "credit_ratings":
        return {
            "period": cleaned.get("period"),
            "rating_agency": cleaned.get("rating_agency"),
            "rating_scale": cleaned.get("rating_scale"),
            "instrument": cleaned.get("instrument"),
            "source_document": cleaned.get("source_document"),
            "source_page": cleaned.get("source_page"),
        }
    return {
        "period": cleaned.get("period"),
        "category": cleaned.get("category"),
        "key_name": cleaned.get("key_name"),
        "value_text": cleaned.get("value_text"),
        "source_document": cleaned.get("source_document"),
        "source_page": cleaned.get("source_page"),
    }


def validate_fact(
    raw_item: Dict[str, Any],
    doc_id: str,
    ingested_at: str,
) -> Tuple[Optional[str], Optional[Dict[str, Any]], Optional[str]]:
    """Validate an extracted item and attach deterministic record_id, doc_id, and ingested_at."""
    if not isinstance(raw_item, dict):
        return None, None, f"Extracted item must be a dict, got {type(raw_item).__name__}"

    raw_table = str(raw_item.get("table", "")).strip()
    table = TABLE_NAME_MAP.get(raw_table)
    model_cls = _TABLE_MODEL_MAP.get(table or "")
    if not table or model_cls is None:
        return raw_table or None, None, f"Unsupported table: {raw_table!r}"

    candidate = dict(raw_item)
    if table == "guidance_claims" and not candidate.get("statement_quarter"):
        candidate["statement_quarter"] = candidate.get("period")
    if table == "financials" and not candidate.get("period_label"):
        candidate["period_label"] = candidate.get("period")

    try:
        validated = model_cls.model_validate(candidate)
    except ValidationError as exc:
        return table, None, str(exc)

    row = validated.model_dump(mode="json")
    if table == "guidance_claims":
        row.pop("period", None)

    row["record_id"] = make_record_id(
        company_id=row["company_id"],
        table=table,
        key_fields=_record_key_fields(table, row),
    )
    row["doc_id"] = doc_id
    row["ingested_at"] = ingested_at
    return table, row, None
