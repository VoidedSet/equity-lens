"""
Promise Verifier
================
Deterministically compares extracted management promises against the
local enriched CSV financial data and writes promise_scorecard.json.
"""

import json
import math
import os
import re
import sys
from collections import defaultdict
from typing import Dict, Optional, Tuple

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from agent.data_loader import CSV_FILES, load_company_data, resolve_company

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
PROMISES_JSON_PATH = os.path.join(OUTPUT_DIR, "promises.json")
SCORECARD_JSON_PATH = os.path.join(OUTPUT_DIR, "promise_scorecard.json")

STATUSES = ["EXCEEDED", "KEPT", "PARTIAL", "BROKEN", "PENDING"]
SCORE_BY_STATUS = {
    "EXCEEDED": 1.2,
    "KEPT": 1.0,
    "PARTIAL": 0.5,
    "BROKEN": -0.5,
    "PENDING": 0.0,
}

FOLDER_TO_CODE = {
    "Chalet_Hotels": "CHALET",
    "EIH_Limited": "EIH",
    "Indian_Hotels": "IHCL",
    "Juniper_Hotels": "JUNIPER",
    "Lemon_Tree_Hotels": "LEMONTREE",
}

QUARTER_TO_MONTH = {
    "Q1": "Jun",
    "Q2": "Sep",
    "Q3": "Dec",
    "Q4": "Mar",
}


def company_code(company: str) -> str:
    canonical = resolve_company(company)
    return FOLDER_TO_CODE.get(canonical, company.upper())


def actual_data_file(company: str, source: str) -> str:
    canonical = resolve_company(company)
    filename = CSV_FILES.get(source, "")
    if not filename:
        return ""
    return os.path.join(PROJECT_ROOT, "Raw Data Extraction", canonical, filename)


def read_promises() -> list:
    if not os.path.exists(PROMISES_JSON_PATH):
        raise FileNotFoundError("promises.json not found. Run promises/extract_promises.py first.")
    with open(PROMISES_JSON_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json_atomic(path: str, payload) -> None:
    """Write JSON via replace so the scorecard is never left half-written."""
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    os.replace(tmp_path, path)


def numeric(value) -> Optional[float]:
    if value is None:
        return None
    try:
        if isinstance(value, str):
            value = value.replace(",", "").strip()
            if not value or value.lower() in {"nan", "none"}:
                return None
        result = float(value)
        if math.isnan(result):
            return None
        return result
    except (TypeError, ValueError):
        return None


def target_year(target_period: str) -> Optional[int]:
    match = re.search(r"FY\s*'?(\d{2,4})", target_period or "", re.I)
    if not match:
        return None
    year = int(match.group(1))
    return 2000 + year if year < 100 else year


def target_column(target_period: str, source: str) -> Optional[str]:
    """Map FY/QFY target labels to CSV column names."""
    if not target_period or target_period == "Unknown":
        return None

    quarter_match = re.search(r"\b(Q[1-4])\s+FY\s*'?(\d{2,4})\b", target_period, re.I)
    if quarter_match:
        quarter = quarter_match.group(1).upper()
        fy = target_year(target_period)
        if fy is None:
            return None
        month = QUARTER_TO_MONTH[quarter]
        calendar_year = fy if quarter == "Q4" else fy - 1
        return f"{month} {calendar_year}"

    fy = target_year(target_period)
    if fy is None:
        return None
    return f"Mar {fy}"


def period_key(period: str) -> Optional[Tuple[int, int]]:
    parts = str(period or "").split()
    if len(parts) != 2:
        return None
    month_num = {
        "Mar": 3,
        "Jun": 6,
        "Sep": 9,
        "Dec": 12,
        "Jan": 1,
        "Feb": 2,
        "Apr": 4,
        "May": 5,
        "Jul": 7,
        "Aug": 8,
        "Oct": 10,
        "Nov": 11,
    }.get(parts[0][:3])
    if month_num is None:
        return None
    try:
        return (int(parts[1]), month_num)
    except ValueError:
        return None


def source_period_key(source_period: str) -> Optional[Tuple[int, int]]:
    if not source_period:
        return None
    q_col = target_column(source_period, "quarter_analysis_enriched")
    if q_col:
        return period_key(q_col)
    fy_col = target_column(source_period, "profit_loss_enriched")
    if fy_col:
        return period_key(fy_col)
    return period_key(source_period)


def latest_period_for(df) -> Optional[str]:
    columns = [col for col in df.columns if str(col).upper() != "TTM"]
    return columns[-1] if columns else None


def period_is_after_available(target_period_name: str, latest_period_name: str) -> bool:
    target_key = period_key(target_period_name)
    latest_key = period_key(latest_period_name)
    if target_key is None or latest_key is None:
        return False
    return target_key > latest_key


def select_verification_metric(promise: dict) -> Optional[dict]:
    metric = promise.get("primary_metric") or (promise.get("metrics") or [""])[0]
    text = promise.get("text", "").lower()
    target = promise.get("target_value", {})
    unit = str(target.get("unit", "")).lower()
    target_period = promise.get("target_period", "")
    is_quarter = bool(re.search(r"\bQ[1-4]\s+FY", target_period or "", re.I))
    is_undated_near_term = target_period == "Unknown" and promise.get("doc_type") in {
        "call_transcript",
        "quarterly_results",
        "announcement",
    }
    period_source = "quarter_analysis_enriched" if is_quarter else "profit_loss_enriched"
    if is_undated_near_term:
        period_source = "quarter_analysis_enriched"

    growth_words = re.search(r"\bgrow|growth|increase|higher|up|surpass|exceed|improve\b", text)
    is_percent = unit in {"%", "percent", "percentage", "bps", "basis points"}

    if metric == "Revenue":
        if is_percent:
            return {
                "source": period_source,
                "row": "YoY Sales Growth %",
                "direction": "up",
                "kind": "percentage_growth",
            }
        return {"source": period_source, "row": "Sales +", "direction": "up", "kind": "currency"}

    if metric == "EBITDA Margin":
        if is_percent or "margin" in text:
            return {
                "source": period_source,
                "row": "EBITDA Margin %",
                "direction": "up",
                "kind": "percentage_level",
            }
        return {"source": period_source, "row": "EBITDA", "direction": "up", "kind": "currency"}

    if metric == "Net Profit":
        if is_percent:
            return {
                "source": period_source,
                "row": "YoY Net Profit Growth %",
                "direction": "up",
                "kind": "percentage_growth",
            }
        return {"source": period_source, "row": "Net Profit +", "direction": "up", "kind": "currency"}

    if metric == "Debt":
        if "debt-to-equity" in text or "debt equity" in text or unit in {"x", "times"}:
            return {
                "source": "balance_sheet_enriched",
                "row": "Debt-to-Equity Ratio",
                "direction": "down",
                "kind": "ratio",
            }
        if re.search(r"\brepayment|pay down|repay|reduction|reduce by|bring down by\b", text):
            return {
                "source": "balance_sheet_enriched",
                "row": "Borrowings +",
                "direction": "up",
                "kind": "debt_reduction",
            }
        return {
            "source": "balance_sheet_enriched",
            "row": "Borrowings +",
            "direction": "down",
            "kind": "currency",
        }

    return None


def target_to_comparable_value(target: dict, verification: dict) -> Optional[Tuple[float, Optional[float]]]:
    unit = str(target.get("unit", "")).lower()
    low = numeric(target.get("low"))
    high = numeric(target.get("high"))
    if low is None:
        return None

    kind = verification["kind"]

    if unit in {"rooms", "keys", "hotels", "properties", "sqft", "square feet"}:
        return None

    if unit in {"bps", "basis points"}:
        return (low / 100.0, high / 100.0 if high is not None else None)

    if kind.startswith("percentage"):
        return (low, high)

    if kind == "ratio":
        return (low, high)

    if kind in {"currency", "debt_reduction"}:
        multiplier = {
            "crore": 1.0,
            "crores": 1.0,
            "cr": 1.0,
            "currency": 1.0,
            "million": 0.1,
            "mn": 0.1,
            "billion": 100.0,
            "bn": 100.0,
            "lakh": 0.01,
            "lakhs": 0.01,
            "": 1.0,
        }.get(unit)
        if multiplier is None:
            return None
        return (low * multiplier, high * multiplier if high is not None else None)

    return None


def choose_window_actual(df, row: str, promise: dict, verification: dict) -> Optional[dict]:
    """For undated promises, use a reasonable future reported window."""
    source_key = source_period_key(promise.get("source_period", ""))
    if source_key is None:
        return None

    candidates = []
    for col in df.columns:
        if str(col).upper() == "TTM":
            continue
        key = period_key(col)
        if key is None or key <= source_key:
            continue
        value = numeric(df.loc[row, col])
        if value is None:
            continue
        candidates.append((key, col, value))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0])
    window_size = 4 if verification["source"] == "quarter_analysis_enriched" else 2
    window = candidates[:window_size]
    if not window:
        return None

    direction = promise.get("direction") or verification["direction"]
    if verification["direction"] == "down":
        direction = "down"
    if verification["kind"] == "debt_reduction":
        direction = "up"

    if direction == "down":
        chosen = min(window, key=lambda item: item[2])
    else:
        chosen = max(window, key=lambda item: item[2])

    return {
        "period": chosen[1],
        "value": chosen[2],
        "window_periods": [item[1] for item in window],
    }


def prior_period_for_source(df, source_period: str) -> Optional[str]:
    source_key = source_period_key(source_period)
    if source_key is None:
        return None
    candidates = []
    for col in df.columns:
        if str(col).upper() == "TTM":
            continue
        key = period_key(col)
        if key is not None and key <= source_key:
            candidates.append((key, col))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    return candidates[-1][1]


def classify(actual: float, low: float, high: Optional[float], direction: str, comparator: str) -> str:
    comparator = comparator or ""
    has_range = high is not None

    if direction == "down":
        target_max = high if has_range else low
        if actual <= target_max * 0.9:
            return "EXCEEDED"
        if actual <= target_max * 1.05:
            return "KEPT"
        if actual <= target_max * 1.2:
            return "PARTIAL"
        return "BROKEN"

    if has_range:
        if actual > high * 1.05:
            return "EXCEEDED"
        if low <= actual <= high * 1.05:
            return "KEPT"
        if actual >= low * 0.85:
            return "PARTIAL"
        return "BROKEN"

    if any(word in comparator for word in ["less than", "below", "under", "up to", "upto"]):
        if actual < low * 0.9:
            return "EXCEEDED"
        if actual <= low * 1.05:
            return "KEPT"
        if actual <= low * 1.2:
            return "PARTIAL"
        return "BROKEN"

    if actual >= low * 1.05:
        return "EXCEEDED"
    if actual >= low * 0.95:
        return "KEPT"
    if actual >= low * 0.8:
        return "PARTIAL"
    return "BROKEN"


def verify_one(promise: dict) -> Optional[dict]:
    code = company_code(promise.get("company", ""))
    result = dict(promise)
    result["company"] = code

    verification = select_verification_metric(promise)
    if verification is None:
        return None

    target_period = promise.get("target_period", "")
    if target_period == "Unknown" and promise.get("target_period_basis") == "unknown":
        return None

    period_col = target_column(target_period, verification["source"])

    data = load_company_data(code)
    df = data.get(verification["source"])
    if df is None or df.empty:
        return None

    latest = latest_period_for(df)
    row = verification["row"]
    if row not in df.index:
        return None

    window_actual = None
    if period_col is None:
        window_actual = choose_window_actual(df, row, promise, verification)
        if window_actual is None:
            result.update({
                "status": "PENDING",
                "score": SCORE_BY_STATUS["PENDING"],
                "verification_metric": row,
                "verification_source": verification["source"],
                "verification_source_file": actual_data_file(code, verification["source"]),
                "rationale": (
                    "No explicit target period was found and there are no later reported "
                    "periods to form a verification window."
                ),
            })
            return result
        period_col = window_actual["period"]

    if period_col not in df.columns:
        rationale = f"Actual data for {period_col} is not available."
        if latest and period_is_after_available(period_col, latest):
            rationale = f"Actual data only runs through {latest}; {period_col} is still pending."
        result.update({
            "status": "PENDING",
            "score": SCORE_BY_STATUS["PENDING"],
            "verification_metric": verification["row"],
            "verification_source": verification["source"],
            "verification_source_file": actual_data_file(code, verification["source"]),
            "actual_period": period_col,
            "latest_available_period": latest,
            "rationale": rationale,
        })
        return result

    actual = window_actual["value"] if window_actual else numeric(df.loc[row, period_col])
    base_period = None
    base_value = None
    ending_value = actual
    if verification["kind"] == "debt_reduction":
        base_period = prior_period_for_source(df, promise.get("source_period", ""))
        if base_period is None:
            return None
        base_value = numeric(df.loc[row, base_period])
        if base_value is None or ending_value is None:
            return None
        actual = base_value - ending_value
    comparable = target_to_comparable_value(promise.get("target_value", {}), verification)
    if actual is None or comparable is None:
        return None

    low, high = comparable
    direction = promise.get("direction") or verification["direction"]
    if verification["direction"] == "down":
        direction = "down"

    status = classify(
        actual=actual,
        low=low,
        high=high,
        direction=direction,
        comparator=promise.get("target_value", {}).get("comparator", ""),
    )

    target_display = f"{low:g}" if high is None else f"{low:g}-{high:g}"
    rationale = (
        f"{row} in {period_col} was {actual:g} versus comparable target "
        f"{target_display}; classified as {status}."
    )
    if verification["kind"] == "debt_reduction":
        rationale = (
            f"{row} fell from {base_value:g} in {base_period} to {ending_value:g} in "
            f"{period_col}, a reduction of {actual:g} versus target reduction "
            f"{target_display}; classified as {status}."
        )
    if window_actual:
        rationale = (
            f"No explicit target date was stated, so checked the next reported window "
            f"({', '.join(window_actual['window_periods'])}); best comparable {row} "
            f"was {actual:g} in {period_col} versus target {target_display}; "
            f"classified as {status}."
        )

    result.update({
        "status": status,
        "score": SCORE_BY_STATUS[status],
        "verification_metric": row,
        "verification_source": verification["source"],
        "verification_source_file": actual_data_file(code, verification["source"]),
        "actual_period": period_col,
        "actual_value": actual,
        "base_period": base_period or "",
        "base_value": base_value if base_value is not None else "",
        "ending_value": ending_value if verification["kind"] == "debt_reduction" else "",
        "comparable_target": target_display,
        "evidence": {
            "promise_source": {
                "document_type": promise.get("doc_type", ""),
                "source_file": promise.get("source_file", ""),
                "source_period": promise.get("source_period", ""),
                "speaker": promise.get("speaker", ""),
                "text": promise.get("text", ""),
            },
            "actual_source": {
                "csv_file": actual_data_file(code, verification["source"]),
                "csv_key": verification["source"],
                "metric": row,
                "period": period_col,
                "value": actual,
                "base_period": base_period or "",
                "base_value": base_value if base_value is not None else "",
                "ending_value": ending_value if verification["kind"] == "debt_reduction" else "",
            },
            "method": "future_window_csv" if window_actual else "exact_period_csv",
            "window_periods": window_actual["window_periods"] if window_actual else [],
        },
        "rationale": rationale,
    })
    return result


def aggregate(details: list) -> dict:
    by_status = {status: 0 for status in STATUSES}
    company_scores: Dict[str, dict] = defaultdict(lambda: {
        "total": 0,
        "EXCEEDED": 0,
        "KEPT": 0,
        "PARTIAL": 0,
        "BROKEN": 0,
        "PENDING": 0,
        "resolved": 0,
        "credibility_score": 50,
    })

    for item in details:
        status = item.get("status", "PENDING")
        company = item.get("company", "UNKNOWN")
        by_status[status] = by_status.get(status, 0) + 1
        stats = company_scores[company]
        stats["total"] += 1
        stats[status] += 1
        if status != "PENDING":
            stats["resolved"] += 1

    for stats in company_scores.values():
        resolved = stats["resolved"]
        if resolved:
            raw = (
                stats["EXCEEDED"] * 1.2
                + stats["KEPT"]
                + stats["PARTIAL"] * 0.5
                - stats["BROKEN"] * 0.5
            ) / resolved
            stats["credibility_score"] = int(max(0, min(100, round(raw * 100))))

    return {
        "total_promises": len(details),
        "by_status": by_status,
        "company_scores": dict(sorted(company_scores.items())),
    }


def verify_promises() -> dict:
    print("=" * 60)
    print("  Promise Verifier")
    print("=" * 60)

    promises = read_promises()
    print(f"Loaded {len(promises)} promises.")

    details = [verified for promise in promises if (verified := verify_one(promise)) is not None]
    scorecard = {
        "summary": aggregate(details),
        "details": details,
    }

    write_json_atomic(SCORECARD_JSON_PATH, scorecard)

    print("Summary by status:")
    for status, count in scorecard["summary"]["by_status"].items():
        print(f"  {status}: {count}")
    print(f"Saved scorecard to {SCORECARD_JSON_PATH}")
    return scorecard


# Backward-compatible entry point used by older scripts.
def verify_agentic() -> dict:
    return verify_promises()


if __name__ == "__main__":
    verify_promises()
