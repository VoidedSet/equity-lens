"""Raw data lake uploader with period classification and content-hash deduplication."""

import argparse
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from cloud.common.companies import normalize_company_id
from cloud.common.config import get_config
from cloud.common.hashing import make_doc_id
from cloud.common.manifest import DocumentManifest, ManifestStore
from cloud.common.storage import StorageBackend, get_storage

# Mirrors MONTH_TO_QUARTER in pdf extraction pipeline/ingest_all.py for earnings transcripts
TRANSCRIPT_MONTH_TO_QUARTER = {
    "jan": ("Q3", 0), "feb": ("Q3", 0), "mar": ("Q3", 0), "apr": ("Q3", 0),
    "may": ("Q4", 0), "jun": ("Q4", 0), "jul": ("Q4", 0),
    "aug": ("Q1", 1), "sep": ("Q1", 1),
    "oct": ("Q2", 1), "nov": ("Q2", 1), "dec": ("Q2", 1),
}

# Mirrors quarterly result report filenames in Data Ingestion/extract_pdfs_to_json.py
QUARTERLY_PDF_MONTH_MAP = {
    "jun": ("Q1", 1),
    "sep": ("Q2", 1),
    "dec": ("Q3", 1),
    "mar": ("Q4", 0),
}

FOLDER_TO_PDF_DOC_TYPE = {
    "annual_reports": "annual_report",
    "annual_report": "annual_report",
    "quarterly_report": "quarterly_results",
    "quarterly_reports": "quarterly_results",
    "announcements": "announcement",
    "credit_ratings": "credit_rating",
    "transcripts": "transcript",
    "call_transcripts": "transcript",
    "investor_presentations": "investor_presentation",
}

SCREENER_CSV_TYPES = {
    "profit_loss.csv": "profit_loss",
    "profit_loss_enriched.csv": "profit_loss_enriched",
    "balance_sheet.csv": "balance_sheet",
    "balance_sheet_enriched.csv": "balance_sheet_enriched",
    "quarter_analysis_table.csv": "quarter_analysis",
    "quarter_analysis_enriched.csv": "quarter_analysis_enriched",
    "cross_metrics.csv": "cross_metrics",
}

EXTRACTED_JSON_TYPES = {
    "announcement.json": "announcement",
    "annual_report.json": "annual_report",
    "credit_rating.json": "credit_rating",
    "quarterly_results.json": "quarterly_results",
}


def extract_period_from_filename(filename: str, doc_type: str) -> str:
    """Derive normalized fiscal period label from raw file names."""
    if doc_type in ("screener_csv", "extracted_json") or doc_type in SCREENER_CSV_TYPES.values():
        return "ALL"

    stem = Path(filename).stem
    low_stem = stem.lower()

    if doc_type == "annual_report":
        match = re.search(r"(\d{4})", stem)
        if match:
            return f"FY{int(match.group(1)) % 100:02d}"
        fy_match = re.search(r"fy\s*(\d{2,4})", low_stem)
        if fy_match:
            return f"FY{int(fy_match.group(1)) % 100:02d}"
        return "UNKNOWN"

    if doc_type == "quarterly_results":
        match = re.match(r"([a-z]{3})[_\-\s](\d{4})", low_stem)
        if match and match.group(1) in QUARTERLY_PDF_MONTH_MAP:
            qtr, offset = QUARTERLY_PDF_MONTH_MAP[match.group(1)]
            fy = (int(match.group(2)) + offset) % 100
            return f"{qtr}FY{fy:02d}"

    if doc_type == "transcript":
        match = re.match(r"(\d{4})[_\-\s]([a-z]{3})", low_stem)
        if match and match.group(2) in TRANSCRIPT_MONTH_TO_QUARTER:
            qtr, offset = TRANSCRIPT_MONTH_TO_QUARTER[match.group(2)]
            fy = (int(match.group(1)) + offset) % 100
            return f"{qtr}FY{fy:02d}"
        q_match = re.search(r"(q[1-4])[_\-\s]*fy\s*(\d{2,4})", low_stem)
        if q_match:
            return f"{q_match.group(1).upper()}FY{int(q_match.group(2)) % 100:02d}"

    if doc_type in ("credit_rating", "announcement"):
        match = re.match(r"(\d{4})[_\-\s]([a-z]{3})(?:[_\-\s]\d{1,2})?", low_stem)
        if match:
            return f"{match.group(1)}_{match.group(2).capitalize()}"

    q_match = re.search(r"(q[1-4])[_\-\s]*fy\s*(\d{2,4})", low_stem)
    if q_match:
        return f"{q_match.group(1).upper()}FY{int(q_match.group(2)) % 100:02d}"

    yr_match = re.search(r"(\d{4})", stem)
    if yr_match:
        return f"FY{int(yr_match.group(1)) % 100:02d}"
    return "UNKNOWN"


def _detect_company_from_path(path: Path, root: Path) -> Optional[str]:
    """Search path ancestors (inclusive of root name if needed) for a known company identifier."""
    try:
        rel_parts = list(path.relative_to(root).parts[:-1])
    except ValueError:
        rel_parts = []

    candidates = rel_parts + list(reversed(root.parts))
    for part in candidates:
        resolved = normalize_company_id(part, default=None)
        if resolved is not None:
            return resolved
    return None


def classify_raw_file(path: Path, root: Path) -> Optional[Dict[str, str]]:
    """Classify a local file into source_type, canonical company_id, doc_type, and period."""
    if not path.is_file():
        return None

    company_id = _detect_company_from_path(path, root)
    if company_id is None:
        return None

    name_lower = path.name.lower()
    suffix = path.suffix.lower()
    parent_lower = path.parent.name.lower()

    if suffix == ".json":
        if name_lower in EXTRACTED_JSON_TYPES:
            return {
                "source_type": "extracted_json",
                "company_id": company_id,
                "doc_type": EXTRACTED_JSON_TYPES[name_lower],
                "period": "ALL",
            }
        if "transcript" in parent_lower or "transcript" in name_lower:
            return {
                "source_type": "transcript_json",
                "company_id": company_id,
                "doc_type": "transcript",
                "period": extract_period_from_filename(path.name, "transcript"),
            }
        return None

    if suffix == ".csv":
        if name_lower in SCREENER_CSV_TYPES:
            return {
                "source_type": "screener_csv",
                "company_id": company_id,
                "doc_type": SCREENER_CSV_TYPES[name_lower],
                "period": "ALL",
            }
        return None

    if suffix == ".pdf":
        doc_type = FOLDER_TO_PDF_DOC_TYPE.get(parent_lower)
        if doc_type is None:
            if "transcript" in name_lower:
                doc_type = "transcript"
            elif "rating" in name_lower:
                doc_type = "credit_rating"
            elif "annual" in name_lower or re.fullmatch(r"\d{4}\.pdf", name_lower):
                doc_type = "annual_report"
            else:
                doc_type = "annual_report"
        return {
            "source_type": "pdf",
            "company_id": company_id,
            "doc_type": doc_type,
            "period": extract_period_from_filename(path.name, doc_type),
        }

    return None


def build_raw_key(
    source_type: str,
    company_id: str,
    doc_type: str,
    period: str,
    doc_id: str,
    filename: str,
) -> str:
    """Build deterministic S3 key inside the raw/ zone."""
    safe_period = re.sub(r"[^A-Za-z0-9_-]", "_", period or "UNKNOWN")
    safe_name = filename.replace(" ", "_")
    return (
        f"raw/source={source_type}/company={company_id}/"
        f"doc_type={doc_type}/period={safe_period}/{doc_id[:12]}__{safe_name}"
    )


def upload_raw_directory(
    source_dir: Path,
    storage: StorageBackend,
    manifests: ManifestStore,
    company_filter: Optional[str] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Walk source_dir, deduplicate via SHA-256 manifest lookup, and upload raw files."""
    if not source_dir.exists():
        raise FileNotFoundError(f"Source directory does not exist: {source_dir}")

    normalized_filter = normalize_company_id(company_filter) if company_filter else None

    summary: Dict[str, Any] = {
        "scanned": 0,
        "uploaded": 0,
        "skipped_duplicate": 0,
        "skipped_unclassified": 0,
        "errors": 0,
        "uploaded_doc_ids": [],
        "doc_ids": [],
    }

    for path in sorted(p for p in source_dir.rglob("*") if p.is_file()):
        summary["scanned"] += 1
        meta = classify_raw_file(path, source_dir)
        if meta is None:
            summary["skipped_unclassified"] += 1
            continue

        if normalized_filter and meta["company_id"] != normalized_filter:
            continue

        try:
            raw_bytes = path.read_bytes()
            doc_id = make_doc_id(raw_bytes)
            summary["doc_ids"].append(doc_id)

            raw_key = build_raw_key(
                source_type=meta["source_type"],
                company_id=meta["company_id"],
                doc_type=meta["doc_type"],
                period=meta["period"],
                doc_id=doc_id,
                filename=path.name,
            )

            if manifests.exists(doc_id) and storage.exists(raw_key):
                summary["skipped_duplicate"] += 1
                continue

            if dry_run:
                summary["uploaded"] += 1
                summary["uploaded_doc_ids"].append(doc_id)
                continue

            content_type = {
                ".pdf": "application/pdf",
                ".json": "application/json",
                ".csv": "text/csv",
            }.get(path.suffix.lower(), "application/octet-stream")

            raw_uri = storage.write_bytes(raw_key, raw_bytes, content_type=content_type)
            manifest = DocumentManifest(
                doc_id=doc_id,
                company_id=meta["company_id"],
                source_type=meta["source_type"],  # type: ignore[arg-type]
                doc_type=meta["doc_type"],
                period=meta["period"],
                raw_key=raw_key,
                raw_uri=raw_uri,
                filename=path.name,
                content_sha256=doc_id,
                size_bytes=len(raw_bytes),
                status="raw",
            )
            manifests.save(manifest)
            summary["uploaded"] += 1
            summary["uploaded_doc_ids"].append(doc_id)
        except Exception as exc:
            print(f"[upload_raw] Failed for {path}: {exc}")
            summary["errors"] += 1

    return summary


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Upload raw EquityLens documents with manifest deduplication.")
    parser.add_argument("--source-dir", required=True, help="Local directory containing raw PDFs, CSVs, or JSONs.")
    parser.add_argument("--company", default=None, help="Optional canonical company ID or alias filter.")
    parser.add_argument("--dry-run", action="store_true", help="Classify and hash without writing files.")
    args = parser.parse_args(argv)

    cfg = get_config()
    storage = get_storage(cfg)
    manifests = ManifestStore(storage)
    result = upload_raw_directory(
        source_dir=Path(args.source_dir),
        storage=storage,
        manifests=manifests,
        company_filter=args.company,
        dry_run=args.dry_run,
    )
    print(result)
    return 0 if result["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
