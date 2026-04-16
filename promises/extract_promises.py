"""
Promise Extractor
=================
Extracts forward-looking, measurable management statements from the
text corpus and writes them to promises.json.
"""

import hashlib
import json
import os
import re
import sys
from typing import Dict, Iterable, List, Optional, Tuple

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from graph.text_preprocessor import clean_text, load_all_data

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
PROMISES_JSON_PATH = os.path.join(OUTPUT_DIR, "promises.json")


FORWARD_PATTERN = re.compile(
    r"\b("
    r"expect(?:s|ed|ing)?|anticipat(?:e|es|ed|ing)|target(?:s|ed|ing)?|"
    r"aim(?:s|ed|ing)?|plan(?:s|ning)?|guidance|outlook|"
    r"forecast(?:s|ed|ing)?|projecting|going forward|likely to|poised to|"
    r"committed to|on track|confident|aspire|vision|pipeline|should see|"
    r"hope to|intend(?:s|ed|ing)?|strategy is to|roadmap|"
    r"will\s+(?:achieve|deliver|grow|expand|increase|maintain|improve|"
    r"reduce|open|add|reach|be|have|cross|commission|complete)"
    r")\b",
    re.IGNORECASE,
)

NEGATIVE_BOILERPLATE = [
    "limited review",
    "ind as",
    "listing regulations",
    "our conclusion is not modified",
    "according to the information and explanations",
    "auditor",
    "board of directors",
    "statement includes the results",
    "results have not been reviewed",
    "digitally signed",
]

NON_MANAGEMENT_SPEAKERS = [
    "moderator",
    "operator",
    "participant",
    "analyst",
    "investor",
]

METRIC_KEYWORDS: Dict[str, List[str]] = {
    "Revenue": ["revenue", "sales", "top line", "topline", "income"],
    "Occupancy": ["occupancy", "occupancy rate"],
    "RevPAR": ["revpar", "rev par", "revenue per available room"],
    "ADR": ["adr", "average daily rate", "average rate", "arr"],
    "EBITDA Margin": [
        "ebitda margin",
        "operating margin",
        "opm",
        "margin expansion",
        "ebitda",
        "gop",
    ],
    "Net Profit": ["pat", "profit after tax", "net profit", "bottom line", "profit"],
    "Debt": ["debt", "leverage", "borrowing", "net debt", "deleverag"],
    "Expansion": [
        "rooms",
        "keys",
        "properties",
        "hotels",
        "new openings",
        "pipeline",
        "portfolio",
    ],
    "Capex": ["capex", "capital expenditure", "investment", "cwip"],
}

VERIFIABLE_METRICS = {"Revenue", "EBITDA Margin", "Net Profit", "Debt"}
NON_FINANCIAL_UNITS = {"rooms", "keys", "hotels", "properties", "sqft", "square feet"}

TARGET_PATTERN = re.compile(
    r"(?P<prefix>Rs\.?|INR|rupees|rs\.|inr)?\s*"
    r"(?P<comparator>at least|atleast|minimum|min|not less than|more than|over|above|"
    r"greater than|less than|below|under|up to|upto|around|approximately|"
    r"approx\.?|about|nearly|close to|between|exceed|exceeds|surpass|north of)?\s*"
    r"(?P<low>\d[\d,]*(?:\.\d+)?)"
    r"(?:\s*(?:-|to|and)\s*(?P<high>\d[\d,]*(?:\.\d+)?))?\s*"
    r"(?P<unit>%|percent|percentage|bps|basis points|crore|crores|cr|"
    r"million|mn|billion|bn|lakh|lakhs|x|times|rooms|keys|hotels|properties|"
    r"sqft|square feet)?",
    re.IGNORECASE,
)

FY_PATTERN = re.compile(
    r"\b(?:Q(?P<q>[1-4])\s*)?FY\s*['-]?(?P<fy>\d{2,4})\b|"
    r"\b(?:financial year|fiscal year)\s*(?P<fy_long>\d{2,4})\b|"
    r"\b(?:by|in|for|before|end of)\s+(?P<calendar>20[2-3]\d)\b",
    re.IGNORECASE,
)

FY_RANGE_PATTERN = re.compile(
    r"\b(?:FY|financial year|fiscal year)\s*'?(?:20)?(?P<start>\d{2})\s*[-/]\s*(?:20)?(?P<end>\d{2})\b",
    re.IGNORECASE,
)

MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

QUARTER_TO_MONTH = {
    "Q1": 6,
    "Q2": 9,
    "Q3": 12,
    "Q4": 3,
}

NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
}


def split_into_sentences(text: str) -> List[str]:
    """Split long transcript turns into manageable statements."""
    cleaned = clean_text(text)
    if not cleaned:
        return []
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(\-])", cleaned)
    sentences: List[str] = []
    for part in parts:
        part = part.strip()
        if len(part) <= 1200:
            sentences.append(part)
            continue
        subparts = re.split(r"\s+(?=(?:We|The company|This|Our|At|By)\b)", part)
        sentences.extend(s.strip() for s in subparts if s.strip())
    return [s for s in sentences if len(s.split()) >= 8]


def is_management_chunk(chunk: dict) -> bool:
    """Avoid extracting analyst questions as management promises."""
    if chunk.get("doc_type") != "call_transcript":
        return True
    speaker = chunk.get("speaker", "").strip().lower()
    if not speaker or speaker == "unknown":
        return False
    return not any(marker in speaker for marker in NON_MANAGEMENT_SPEAKERS)


def is_forward_statement(text: str) -> bool:
    """Return True for genuine forward-looking language."""
    text_lower = text.lower()
    if any(bp in text_lower for bp in NEGATIVE_BOILERPLATE):
        return False
    if text.strip().endswith("?") or (
        "?" in text and re.search(r"\b(would|could|do|does|can|should|if)\s+you\b", text_lower)
    ):
        return False
    return bool(FORWARD_PATTERN.search(text))


def is_company_scoped(text: str) -> bool:
    """Filter out broad macro forecasts that are not company promises."""
    text_lower = f" {text.lower()} "
    scope_terms = [
        " we ",
        " our ",
        " us ",
        " company",
        " management",
        " portfolio",
        " hotel",
        " hotels",
        " room",
        " rooms",
        " property",
        " properties",
        " business",
        " revenue",
        " ebitda",
        " debt",
        " capex",
        " ihcl",
        " chalet",
        " eih",
        " juniper",
        " lemon tree",
        " lemontree",
    ]
    return any(term in text_lower for term in scope_terms)


def map_to_metrics(text: str) -> List[str]:
    text_lower = text.lower()
    matched = []
    for metric, keywords in METRIC_KEYWORDS.items():
        if any(keyword in text_lower for keyword in keywords):
            matched.append(metric)
    return matched


def _normalize_number(value: str) -> float:
    return float(value.replace(",", ""))


def _target_candidate_score(text_lower: str, match: re.Match, metrics: List[str]) -> int:
    """Rank numeric candidates by closeness to metric and forward keywords."""
    score = 0
    start = match.start()
    window = text_lower[max(0, start - 90): min(len(text_lower), match.end() + 90)]

    for metric in metrics:
        for keyword in METRIC_KEYWORDS[metric]:
            positions = [m.start() for m in re.finditer(re.escape(keyword), text_lower)]
            if not positions:
                continue
            closest = min(abs(pos - start) for pos in positions)
            if closest <= 140:
                score += max(1, int(12 - closest / 15))
            else:
                score += 1

    if FORWARD_PATTERN.search(window):
        score += 4
    if re.search(r"\b(yield|contribute|add|deliver|north of|exceed|target|guidance)\b", window):
        score += 3
    if re.search(r"\b(capital work|cwip|capex|spent|investment|cost)\b", window):
        score -= 4

    unit = (match.group("unit") or "").lower()
    prefix = match.group("prefix")
    if unit:
        score += 2
    if prefix:
        score += 2
    if match.group("high"):
        score += 2
    return score


def extract_target(text: str, metrics: List[str]) -> Optional[dict]:
    """Pick the target number most likely attached to the promise."""
    text_lower = text.lower()
    candidates = []
    first_forward = FORWARD_PATTERN.search(text_lower)
    first_forward_pos = first_forward.start() if first_forward else 0

    for match in TARGET_PATTERN.finditer(text):
        if match.start() < first_forward_pos:
            continue
        unit = (match.group("unit") or "").lower()
        prefix = match.group("prefix")
        low = _normalize_number(match.group("low"))
        high = _normalize_number(match.group("high")) if match.group("high") else None

        if not unit and not prefix:
            continue

        raw = match.group(0).strip()
        context = text_lower[max(0, match.start() - 30): min(len(text_lower), match.end() + 30)]
        if re.search(r"\b(confidence|confident|sure|certainty|guarantee)\b", context):
            continue
        if re.search(r"\b(historically|already|reported|posted|clocked|achieved|spent|stood at|was at|were at)\b", context):
            continue
        if re.search(r"\b\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)", raw, re.I):
            continue

        candidate = {
            "raw": raw,
            "low": low,
            "high": high,
            "unit": unit or ("currency" if prefix else ""),
            "prefix": prefix or "",
            "comparator": (match.group("comparator") or "").lower(),
            "score": _target_candidate_score(text_lower, match, metrics),
            "start": match.start(),
            "end": match.end(),
        }
        candidates.append(candidate)

    if not candidates:
        return None
    candidates.sort(key=lambda item: item["score"], reverse=True)
    return candidates[0]


def choose_primary_metric(text: str, metrics: List[str], target: dict) -> str:
    """Choose the metric whose keywords appear closest to the selected target."""
    if not metrics:
        return ""
    text_lower = text.lower()
    target_pos = int(target.get("start", 0))
    best_metric = metrics[0]
    best_distance = 10**9

    for metric in metrics:
        for keyword in METRIC_KEYWORDS[metric]:
            for match in re.finditer(re.escape(keyword), text_lower):
                distance = abs(match.start() - target_pos)
                if distance < best_distance:
                    best_distance = distance
                    best_metric = metric
    return best_metric


def is_company_level_financial_target(text: str, primary_metric: str, target: dict) -> bool:
    """Reject project/property-level financial targets that consolidated CSVs cannot prove."""
    if primary_metric not in {"Revenue", "EBITDA Margin", "Net Profit"}:
        return True

    text_lower = text.lower()
    if target.get("unit") in {"%", "percent", "percentage", "bps", "basis points"} and "flow through" in text_lower:
        return False

    project_terms = re.search(
        r"\b(project|projects|property|properties|tower|towers|office|commercial|"
        r"specific hotel|new hotel|four hotels|these hotels)\b",
        text_lower,
    )
    company_terms = re.search(
        r"\b(company|consolidated|portfolio|full[- ]year|for the year|this financial year|"
        r"our revenue|our ebitda|we will do|guidance)\b",
        text_lower,
    )
    if project_terms and not company_terms:
        return False
    return True


def source_fy(source_period: str) -> Optional[int]:
    """Infer Indian fiscal year from a source period."""
    if not source_period:
        return None
    q_match = re.search(r"FY\s*'?(\d{2,4})", source_period, re.I)
    if q_match:
        fy = q_match.group(1)
        return int(f"20{fy}") if len(fy) == 2 else int(fy)

    parts = source_period.replace("_", " ").split()
    if len(parts) >= 2:
        month = MONTHS.get(parts[0][:3].lower())
        year_match = re.search(r"20\d{2}", source_period)
        if month and year_match:
            year = int(year_match.group(0))
            return year if month <= 3 else year + 1
    return None


def source_calendar_year(source_period: str) -> Optional[int]:
    key = source_period.replace("_", " ")
    year_match = re.search(r"20\d{2}", key)
    if year_match:
        return int(year_match.group(0))
    fy = source_fy(source_period)
    return fy


def period_key(label: str) -> Optional[Tuple[int, int]]:
    """Convert source/target labels to sortable calendar keys."""
    if not label or label == "Unknown":
        return None

    q_match = re.search(r"\b(Q[1-4])\s+FY\s*'?(\d{2,4})\b", label, re.I)
    if q_match:
        quarter = q_match.group(1).upper()
        fy_value = q_match.group(2)
        fy = int(f"20{fy_value}") if len(fy_value) == 2 else int(fy_value)
        month = QUARTER_TO_MONTH[quarter]
        year = fy if quarter == "Q4" else fy - 1
        return (year, month)

    fy_match = re.search(r"\bFY\s*'?(\d{2,4})\b", label, re.I)
    if fy_match:
        fy_value = fy_match.group(1)
        fy = int(f"20{fy_value}") if len(fy_value) == 2 else int(fy_value)
        return (fy, 3)

    parts = label.replace("_", " ").split()
    if len(parts) >= 2:
        month = MONTHS.get(parts[0][:3].lower())
        year_match = re.search(r"20\d{2}", label)
        if month and year_match:
            return (int(year_match.group(0)), month)
    return None


def target_is_after_source(target_period: str, source_period: str) -> bool:
    target_key = period_key(target_period)
    source_key = period_key(source_period)
    if target_key is None or source_key is None:
        return True
    return target_key > source_key


def _format_fy(value: str) -> str:
    year = int(value)
    if year < 100:
        year = 2000 + year
    return f"FY{str(year)[-2:]}"


def extract_target_period(text: str, source_period: str) -> Tuple[str, str]:
    """Extract explicit target period or infer common relative periods."""
    fy_range = FY_RANGE_PATTERN.search(text)
    if fy_range:
        return f"FY{fy_range.group('end')}", "explicit"

    match = FY_PATTERN.search(text)
    if match:
        fy_value = match.group("fy") or match.group("fy_long") or match.group("calendar")
        fy = _format_fy(fy_value)
        if match.group("q"):
            return f"Q{match.group('q')} {fy}", "explicit"
        return fy, "explicit"

    text_lower = text.lower()
    current_fy = source_fy(source_period)
    source_year = source_calendar_year(source_period)
    if not current_fy:
        return "Unknown", "unknown"

    if re.search(r"\b(current|this)\s+(financial|fiscal)\s+year\b", text_lower):
        return f"FY{str(current_fy)[-2:]}", "relative"
    if re.search(r"\b(current|this)\s+year\b", text_lower):
        return f"FY{str(current_fy)[-2:]}", "relative"
    if re.search(r"\bnext\s+(financial|fiscal)\s+year\b", text_lower):
        return f"FY{str(current_fy + 1)[-2:]}", "relative"

    year_horizon = re.search(
        r"\b(?P<first>\d+(?:\.\d+)?|one|two|three|four|five)"
        r"(?:\s+and\s+a\s+half)?(?:\s+to\s+(?P<second>\d+(?:\.\d+)?|one|two|three|four|five))?"
        r"\s+years?\s+(?:away|out|from now|from today|down the line)\b",
        text_lower,
    )
    if year_horizon and source_year:
        value = year_horizon.group("second") or year_horizon.group("first")
        years = NUMBER_WORDS.get(value, None)
        if years is None:
            years = int(float(value))
        target_year = source_year + years
        target_fy = target_year + 1
        return f"FY{str(target_fy)[-2:]}", "relative"

    if re.search(r"\bcoming quarters|next few quarters|near term|going forward\b", text_lower):
        return "Unknown", "near_term"
    return "Unknown", "unknown"


def infer_direction(text: str, metric: str) -> str:
    text_lower = text.lower()
    if metric == "Debt":
        return "down"
    if re.search(r"\bmaintain|sustain|stable|hold\b", text_lower):
        return "maintain"
    return "up"


def build_promise_id(company: str, source_file: str, speaker: str, text: str, target: str) -> str:
    digest = hashlib.sha1(
        f"{company}|{source_file}|{speaker}|{text[:500]}|{target}".encode("utf-8", errors="ignore")
    ).hexdigest()[:12]
    return f"promise_{digest}"


def write_json_atomic(path: str, payload) -> None:
    """Write JSON via replace so locked append permissions do not leave partial files."""
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    os.replace(tmp_path, path)


def iter_promises(chunks: Iterable[dict]) -> Iterable[dict]:
    target_docs = {"call_transcript", "quarterly_results", "announcement"}
    seen = set()

    for chunk in chunks:
        if chunk.get("doc_type") not in target_docs:
            continue
        if not is_management_chunk(chunk):
            continue

        sentences = split_into_sentences(chunk.get("text", ""))
        for sentence in sentences:
            if not is_forward_statement(sentence):
                continue
            if not is_company_scoped(sentence):
                continue

            metrics = map_to_metrics(sentence)
            metrics = [metric for metric in metrics if metric in VERIFIABLE_METRICS]
            if not metrics:
                continue

            target = extract_target(sentence, metrics)
            if target is None:
                continue
            if target["unit"] in NON_FINANCIAL_UNITS:
                continue
            if target["unit"] in {"lakh", "lakhs"} and not target["prefix"]:
                continue
            if (
                primary_metric := choose_primary_metric(sentence, metrics, target)
            ) == "Debt" and target["unit"] in {"%", "percent", "percentage", "bps", "basis points"}:
                debt_ratio_text = re.search(r"debt[- ]?to[- ]?equity|debt equity|leverage ratio", sentence, re.I)
                if not debt_ratio_text:
                    continue
            if target["unit"] in {"x", "times"}:
                debt_ratio_text = re.search(r"debt[- ]?to[- ]?equity|debt equity|leverage ratio", sentence, re.I)
                if primary_metric != "Debt" or not debt_ratio_text:
                    continue
            if not is_company_level_financial_target(sentence, primary_metric, target):
                continue

            target_period, period_basis = extract_target_period(sentence, chunk.get("period", ""))
            if target_period == "Unknown" and period_basis == "unknown":
                continue
            if not target_is_after_source(target_period, chunk.get("period", "")):
                continue
            direction = infer_direction(sentence, primary_metric)
            promise_id = build_promise_id(
                chunk.get("company", ""),
                chunk.get("source_file", ""),
                chunk.get("speaker", "Management"),
                sentence,
                target["raw"],
            )

            if promise_id in seen:
                continue
            seen.add(promise_id)

            yield {
                "id": promise_id,
                "company": chunk.get("company", ""),
                "source_period": chunk.get("period", ""),
                "target_period": target_period,
                "target_period_basis": period_basis,
                "doc_type": chunk.get("doc_type", ""),
                "speaker": chunk.get("speaker", "Management"),
                "source_file": chunk.get("source_file", ""),
                "text": sentence,
                "metrics": metrics,
                "primary_metric": primary_metric,
                "target": target["raw"],
                "target_value": {
                    "low": target["low"],
                    "high": target["high"],
                    "unit": target["unit"],
                    "comparator": target["comparator"],
                },
                "direction": direction,
            }


def extract_promises() -> List[dict]:
    print("=" * 60)
    print("  Promise Extractor (Said vs Done)")
    print("=" * 60)

    print("Loading data...")
    all_chunks = load_all_data()
    print("Scanning forward-looking statements...")

    promises = list(iter_promises(all_chunks))
    promises.sort(key=lambda item: (item["company"], item["source_file"], item["id"]))

    write_json_atomic(PROMISES_JSON_PATH, promises)

    print(f"Found {len(promises)} measurable promises.")
    print(f"Saved to {PROMISES_JSON_PATH}")
    return promises


if __name__ == "__main__":
    extract_promises()
