"""Data quality checks, Screener CSV metric maps, deviation helpers, and deduplication."""

import math
import re
from typing import Any, Dict, List, Optional, Tuple

from cloud.common.companies import CANONICAL_COMPANIES, normalize_company_id

PL_METRIC_MAP: Dict[str, str] = {
    "Sales +": "revenue",
    "Expenses +": "expenses",
    "Operating Profit": "operating_profit",
    "OPM %": "opm",
    "Other Income +": "other_income",
    "Interest": "interest",
    "Depreciation": "depreciation",
    "Profit before tax": "pbt",
    "Tax %": "tax_rate",
    "Net Profit +": "net_profit",
    "EPS in Rs": "eps",
    "Dividend Payout %": "dividend_payout",
}

BS_METRIC_MAP: Dict[str, str] = {
    "Equity Capital": "equity_capital",
    "Reserves": "reserves",
    "Borrowings +": "borrowings",
    "Other Liabilities +": "other_liabilities",
    "Total Liabilities": "total_liabilities",
    "Fixed Assets +": "fixed_assets",
    "CWIP": "cwip",
    "Investments": "investments",
    "Other Assets +": "other_assets",
    "Total Assets": "total_assets",
}

GUIDANCE_TO_FINANCIAL_METRIC: Dict[str, Optional[str]] = {
    "revpar": "revpar",
    "RevPAR Growth": "revpar",
    "adr": "adr",
    "occupancy": "occupancy",
    "revenue": "revenue",
    "Revenue Growth": "revenue",
    "ebitda_margin": "ebitda_margin",
    "EBITDA Margin": "opm",
    "OPM": "opm",
    "rooms_keys": "room_count",
    "New Room Additions": "room_count",
    "Room Additions": "room_count",
    "capex": "capex",
    "debt": "debt",
    "Debt Reduction": "debt",
    "interest_coverage": "interest_coverage",
    "fnb_revenue": "fnb_share",
    "properties": "room_count",
    "International Expansion": None,
}
_GUIDANCE_METRIC_LOWER = {k.lower(): v for k, v in GUIDANCE_TO_FINANCIAL_METRIC.items()}

INLINE_THRESHOLD_PCT = 5.0

ALLOWED_PERIOD_TYPES = {"quarterly", "annual"}
ALLOWED_RISK_CATEGORIES = {
    "debt",
    "governance",
    "operational",
    "regulatory",
    "auditor",
    "supply_overhang",
    "margin_compression",
    "management_mismatch",
    "key_person",
}
ALLOWED_RISK_SEVERITIES = {"critical", "high", "medium"}
ALLOWED_DEV_FLAGS = {"BEAT", "MISS", "IN-LINE"}
ALLOWED_DEV_SEVERITIES = {"none", "minor", "moderate", "major", "critical"}
ALLOWED_TRENDS = {"improving", "stable", "declining"}


def normalise_text(value: str) -> str:
    """Replace non-breaking/zero-width spaces and collapse surrounding whitespace."""
    return value.replace("\xa0", " ").replace("\u200b", "").strip()


def mar_to_fy(col: str) -> str:
    """Convert 'Mar 2025' -> 'FY25'."""
    parts = normalise_text(col).split()
    if len(parts) == 2 and parts[0].lower() == "mar" and parts[1].isdigit():
        return f"FY{parts[1][-2:]}"
    return normalise_text(col)


def quarter_to_period(col: str) -> str:
    """Convert 'Dec 2024' -> 'Q3 FY25' (matching upload_screener_data.py)."""
    parts = normalise_text(col).split()
    if len(parts) != 2 or not parts[1].isdigit():
        return normalise_text(col)
    month, year = parts[0].capitalize(), int(parts[1])
    quarter_map = {
        "Jun": f"Q1 FY{str(year + 1)[-2:]}",
        "Sep": f"Q2 FY{str(year + 1)[-2:]}",
        "Dec": f"Q3 FY{str(year + 1)[-2:]}",
        "Mar": f"Q4 FY{str(year)[-2:]}",
    }
    return quarter_map.get(month, normalise_text(col))


def parse_numeric(val: Any) -> Optional[float]:
    """Parse Screener/numeric values safely, stripping %, commas, and rejecting NaN/Inf."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        num = float(val)
        return num if math.isfinite(num) else None
    cleaned = normalise_text(str(val)).replace("%", "").replace(",", "")
    if not cleaned or cleaned in ("-", "--", "NA", "N/A", "null", "None"):
        return None
    try:
        num = float(cleaned)
        return num if math.isfinite(num) else None
    except ValueError:
        return None


def get_financial_unit(metric_key: str) -> str:
    if metric_key in ("opm", "tax_rate", "dividend_payout"):
        return "%"
    if metric_key == "eps":
        return "INR"
    if metric_key in (
        "equity_capital",
        "reserves",
        "borrowings",
        "other_liabilities",
        "total_liabilities",
        "fixed_assets",
        "cwip",
        "investments",
        "other_assets",
        "total_assets",
        "revenue",
        "expenses",
        "operating_profit",
        "other_income",
        "interest",
        "depreciation",
        "pbt",
        "net_profit",
    ):
        return "INR Cr"
    return ""


def normalise_period(period: Optional[str]) -> str:
    """Normalize period strings for deterministic matching: 'FY 2024' -> 'FY24', 'Q2 FY24' -> 'Q2FY24'."""
    if not period:
        return ""
    p = str(period).upper().strip()
    p = p.replace("FY 20", "FY").replace("FY20", "FY")
    p = re.sub(r"\s+", "", p)
    return p


def resolve_financial_metric(metric_type: str) -> Optional[str]:
    if not metric_type:
        return None
    if metric_type in GUIDANCE_TO_FINANCIAL_METRIC:
        return GUIDANCE_TO_FINANCIAL_METRIC[metric_type]
    return _GUIDANCE_METRIC_LOWER.get(metric_type.strip().lower())


def compute_flag(guided: float, actual: float) -> Tuple[str, float, float, str]:
    """Return (flag, delta, delta_pct, severity) using deviation_computer thresholds."""
    if guided == 0:
        return "IN-LINE", 0.0, 0.0, "none"

    delta = actual - guided
    delta_pct = (delta / abs(guided)) * 100.0

    if abs(delta_pct) <= INLINE_THRESHOLD_PCT:
        flag = "IN-LINE"
        severity = "none"
    elif delta_pct > 0:
        flag = "BEAT"
        severity = "none" if delta_pct < 10 else "minor"
    else:
        flag = "MISS"
        abs_pct = abs(delta_pct)
        if abs_pct < 10:
            severity = "minor"
        elif abs_pct < 20:
            severity = "moderate"
        elif abs_pct < 35:
            severity = "major"
        else:
            severity = "critical"

    return flag, round(delta, 4), round(delta_pct, 2), severity


def detect_pattern(
    company_id: str,
    metric_type: str,
    existing_deviations: List[Dict[str, Any]],
) -> Optional[str]:
    """Detect consecutive MISS or BEAT runs for (company_id, metric_type)."""
    relevant = [
        d
        for d in existing_deviations
        if d.get("company_id") == company_id and d.get("metric_type") == metric_type
    ]
    if len(relevant) < 2:
        return None

    relevant.sort(key=lambda x: str(x.get("period") or ""))
    flags = [d.get("flag") for d in relevant[-3:]]

    if all(f == "MISS" for f in flags):
        if len(flags) == 3:
            return f"3rd consecutive MISS on {metric_type}"
        return f"{len(flags)} consecutive MISSes on {metric_type}"
    if all(f == "BEAT" for f in flags):
        return f"{len(flags)} consecutive BEATs on {metric_type}"
    return None


def _is_non_empty(val: Any) -> bool:
    return isinstance(val, str) and bool(val.strip())


def _is_finite_number(val: Any) -> bool:
    return isinstance(val, (int, float)) and not isinstance(val, bool) and math.isfinite(float(val))


def validate_curated_row(table: str, row: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Validate canonical company_id, required fields, enums, and finite numbers for a curated row."""
    raw_company = row.get("company_id")
    company_id = normalize_company_id(str(raw_company or ""), default=None)
    if company_id not in CANONICAL_COMPANIES:
        return False, f"Invalid company_id: {raw_company!r}"
    row["company_id"] = company_id

    if table == "document_chunks":
        if not _is_non_empty(row.get("chunk_id")):
            return False, "chunk_id is required"
        if not _is_non_empty(row.get("chunk_text")):
            return False, "chunk_text is required"
        if not _is_non_empty(row.get("source_document")):
            return False, "source_document is required"
        return True, None

    if not _is_non_empty(row.get("record_id")):
        return False, "record_id is required"

    if table == "financials":
        for field in ("period", "metric", "source_document"):
            if not _is_non_empty(row.get(field)):
                return False, f"{field} is required"
        if row.get("period_type") not in ALLOWED_PERIOD_TYPES:
            return False, f"Invalid period_type: {row.get('period_type')!r}"
        if not _is_finite_number(row.get("value")):
            return False, f"value must be a finite number, got {row.get('value')!r}"
        if row.get("yoy_change") is not None and not _is_finite_number(row.get("yoy_change")):
            return False, f"yoy_change must be finite, got {row.get('yoy_change')!r}"
        return True, None

    if table == "guidance_claims":
        for field in ("metric_type", "verbatim_quote", "source_document"):
            if not _is_non_empty(row.get(field)):
                return False, f"{field} is required"
        for bound in ("guidance_value_low", "guidance_value_high", "guidance_value_point"):
            if row.get(bound) is not None and not _is_finite_number(row.get(bound)):
                return False, f"{bound} must be finite"
        return True, None

    if table == "risk_flags":
        for field in ("description", "source_document"):
            if not _is_non_empty(row.get(field)):
                return False, f"{field} is required"
        if row.get("category") not in ALLOWED_RISK_CATEGORIES:
            return False, f"Invalid risk category: {row.get('category')!r}"
        if row.get("severity") not in ALLOWED_RISK_SEVERITIES:
            return False, f"Invalid risk severity: {row.get('severity')!r}"
        return True, None

    if table == "credit_ratings":
        for field in ("rating_agency", "source_document"):
            if not _is_non_empty(row.get(field)):
                return False, f"{field} is required"
        if row.get("rating_amount_crores") is not None and not _is_finite_number(row.get("rating_amount_crores")):
            return False, "rating_amount_crores must be finite"
        return True, None

    if table == "raw_data":
        for field in ("value_text", "source_document"):
            if not _is_non_empty(row.get(field)):
                return False, f"{field} is required"
        return True, None

    if table == "deviation_tracker":
        for field in ("period", "metric_type", "source_guidance", "source_actual"):
            if not _is_non_empty(row.get(field)):
                return False, f"{field} is required"
        if row.get("flag") not in ALLOWED_DEV_FLAGS:
            return False, f"Invalid deviation flag: {row.get('flag')!r}"
        if row.get("severity") not in ALLOWED_DEV_SEVERITIES:
            return False, f"Invalid deviation severity: {row.get('severity')!r}"
        return True, None

    if table == "credibility_scores":
        if not _is_non_empty(row.get("period")):
            return False, "period is required"
        if not _is_finite_number(row.get("overall_score")):
            return False, "overall_score must be finite"
        if row.get("trend") not in ALLOWED_TRENDS:
            return False, f"Invalid trend: {row.get('trend')!r}"
        return True, None

    return False, f"Unsupported table for validation: {table!r}"


def deduplicate_rows(
    rows: List[Dict[str, Any]],
    key_col: str = "record_id",
    ts_col: str = "ingested_at",
) -> List[Dict[str, Any]]:
    """Collapse duplicates deterministically by key_col, keeping the latest ts_col."""
    winners: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        key = str(row.get(key_col) or "")
        if not key:
            continue
        existing = winners.get(key)
        if existing is None or str(row.get(ts_col) or "") >= str(existing.get(ts_col) or ""):
            winners[key] = row
    return sorted(winners.values(), key=lambda r: str(r.get(key_col) or ""))
