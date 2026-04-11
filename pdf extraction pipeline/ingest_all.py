"""
Master Ingestion Script — ingest_all.py
Processes ALL 5 companies' transcripts (JSON) and Annual Reports (PDF).

Usage:
  python ingest_all.py                    # Full run (all companies, all docs)
  python ingest_all.py --company IHCL     # Single company
  python ingest_all.py --skip-llm         # Only embeddings (skip Gemma)
  python ingest_all.py --skip-embed       # Only Gemma extraction (skip embeddings)
  python ingest_all.py --transcripts-only # Only process transcripts
  python ingest_all.py --ar-only          # Only process annual reports
  python ingest_all.py --dry-run          # Print what would be done
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv
load_dotenv()

from config import COMPANIES, COMPANY_NAMES, MGMT_SPEAKER_PATTERNS, SKIP_SPEAKERS
from config import CHUNK_CHARS, CHUNK_OVERLAP_CHARS

# ── Company → folder mapping ──────────────────────────────────
COMPANY_DIRS = {
    "IHCL":      "Indian_Hotels",
    "CHALET":    "Chalet_Hotels",
    "LEMONTREE": "Lemon_Tree_Hotels",
    "EIH":       "EIH_Limited",
    "JUNIPER":   "Juniper_Hotels",
}

RAW_DATA_ROOT = Path(__file__).parent.parent / "Raw Data Extraction"

# ── Period detection from transcript JSON filename ─────────────
# Filenames like "2023_Aug.json" → "Q1FY24" (Aug 2023 = Q1 FY24 results)
MONTH_TO_QUARTER = {
    "Jan": ("Q3", 0), "Feb": ("Q3", 0), "Mar": ("Q3", 0), "Apr": ("Q3", 0),
    "May": ("Q4", 0), "Jun": ("Q4", 0), "Jul": ("Q4", 0),
    "Aug": ("Q1", 1), "Sep": ("Q1", 1),
    "Oct": ("Q2", 1), "Nov": ("Q2", 1), "Dec": ("Q2", 1),
}

def filename_to_period(filename: str) -> str:
    """Convert '2023_Aug.json' → 'Q1FY24'."""
    m = re.match(r"(\d{4})_(\w+)\.json", filename)
    if not m:
        return "UNKNOWN"
    year = int(m.group(1))
    month = m.group(2)
    if month not in MONTH_TO_QUARTER:
        return f"FY{year % 100}"
    quarter, fy_offset = MONTH_TO_QUARTER[month]
    fy = (year + fy_offset) % 100
    return f"{quarter}FY{fy:02d}"


def ar_year_to_period(year_str: str) -> str:
    """Convert '2024' → 'FY24'."""
    try:
        return f"FY{int(year_str) % 100:02d}"
    except ValueError:
        return f"FY{year_str}"


# ── Transcript JSON → chunks ──────────────────────────────────
MGMT_RE = re.compile(
    r"\b(MD|CEO|CFO|COO|CRO|President|Chairman|"
    r"Managing Director|Chief Executive|Chief Financial|"
    r"Chief Operating|Director|Head of|VP|Vice President)\b",
    re.IGNORECASE
)

# Known management speakers across all 5 companies (plain names from JSON transcripts)
KNOWN_MGMT_NAMES = {
    # IHCL
    "puneet chhatwal", "giridhar sanjeevi",
    # Chalet Hotels
    "sanjay sethi", "milind wagh", "rajeev newar",
    # Lemon Tree
    "patanjali keswani", "rattan keswani", "kapil sharma",
    # EIH
    "vikram oberoi", "vikramjit oberoi", "vikramjit singh oberoi",
    "kallol kundu",
    # Juniper Hotels
    "varun chandra", "anurag bhatia",
}

# Non-management patterns
NON_MGMT_RE = re.compile(
    r"\b(analyst|research|investor|participant|moderator|operator|"
    r"coordinator|securities|capital|financial services|broking|"
    r"fund|asset management|advisors|equities)\b",
    re.IGNORECASE
)

def is_management(speaker: str) -> bool:
    low = speaker.lower().strip()
    # Skip known non-management
    for skip in SKIP_SPEAKERS:
        if skip in low:
            return False
    if NON_MGMT_RE.search(low):
        return False
    # Check known management names
    for name in KNOWN_MGMT_NAMES:
        if name in low:
            return True
    # Check title-based detection
    if MGMT_RE.search(speaker):
        return True
    # Heuristic: if speaker has no title/affiliation markers and isn't
    # clearly an analyst, they might be management (common in Indian transcripts
    # where MD/CEO speaks with just their name)
    if not re.search(r"\b(of|at|with|from|in|on)\b", low) and len(low.split()) < 4:
        return True
    return False


def json_transcript_to_chunks(
    json_path: str, company_id: str, period: str
) -> Dict[str, List[Dict]]:
    """
    Read a Call Transcript JSON and produce chunks for:
    - mgmt_chunks: management speaker blocks → Gemma guidance extraction
    - all_chunks: all speaker blocks → embeddings for RAG
    """
    with open(json_path, "r", encoding="utf-8") as f:
        entries = json.load(f)

    source_document = Path(json_path).name
    all_chunks = []
    mgmt_chunks = []
    chunk_idx = 0

    for entry in entries:
        speaker = entry.get("speaker", "Unknown")
        text = entry.get("text", "").strip()
        if not text:
            continue

        is_mgmt = is_management(speaker)

        # Split long blocks into overlapping chunks
        start = 0
        while start < len(text):
            end = min(start + CHUNK_CHARS, len(text))
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunk = {
                    "type": "transcript_chunk",
                    "chunk_text": chunk_text,
                    "chunk_index": chunk_idx,
                    "speaker": speaker,
                    "is_management": is_mgmt,
                    "source_document": source_document,
                    "section_name": "earnings_call",
                    "company_id": company_id,
                    "period": period,
                    "source_page": None,
                    "source_timestamp": None,
                }
                all_chunks.append(chunk)
                if is_mgmt:
                    mgmt_chunks.append(chunk)
                chunk_idx += 1
            start += CHUNK_CHARS - CHUNK_OVERLAP_CHARS

    return {"mgmt_chunks": mgmt_chunks, "all_chunks": all_chunks}


# ── Main orchestration ────────────────────────────────────────

def process_company_transcripts(
    company_id: str, dry_run: bool, skip_llm: bool, skip_embed: bool
) -> Dict[str, int]:
    """Process all JSON transcripts for a company."""
    from gemma_extractor import process_transcript_chunks
    from embedder import embed_and_store_chunks

    company_dir = COMPANY_DIRS.get(company_id)
    if not company_dir:
        print(f"  [SKIP] No directory mapping for {company_id}")
        return {}

    # Check per-company transcripts first, then top-level
    transcript_dir = RAW_DATA_ROOT / company_dir / "Call_Transcripts_JSON"
    if not transcript_dir.exists():
        # Try top-level Call_Transcripts_JSON (shared across companies)
        transcript_dir = RAW_DATA_ROOT / "Call_Transcripts_JSON"

    if not transcript_dir.exists():
        print(f"  [SKIP] No transcript JSON directory for {company_id}")
        return {}

    json_files = sorted(transcript_dir.glob("*.json"))
    if not json_files:
        print(f"  [SKIP] No JSON transcripts found for {company_id}")
        return {}

    total_counts = {"guidance_claims": 0, "chunks_embedded": 0, "transcripts": 0}

    for jf in json_files:
        period = filename_to_period(jf.name)
        print(f"\n  📄 {jf.name} → {period}")

        result = json_transcript_to_chunks(str(jf), company_id, period)
        mgmt_chunks = result["mgmt_chunks"]
        all_chunks = result["all_chunks"]
        print(f"    Chunks: {len(all_chunks)} total | {len(mgmt_chunks)} management")

        # Gemma guidance extraction from management chunks
        if not skip_llm and mgmt_chunks:
            print(f"    [Gemma] Extracting guidance from {len(mgmt_chunks)} management chunks...")
            try:
                llm_counts = process_transcript_chunks(mgmt_chunks, dry_run=dry_run)
                total_counts["guidance_claims"] += llm_counts.get("guidance_claims", 0)
                print(f"    [Gemma] → {llm_counts}")
            except Exception as e:
                print(f"    [Gemma] Error: {e}")

        # Embed all chunks for RAG
        if not skip_embed and all_chunks:
            print(f"    [Embed] Embedding {len(all_chunks)} chunks...")
            try:
                n = embed_and_store_chunks(all_chunks, document_type="transcript", dry_run=dry_run)
                total_counts["chunks_embedded"] += n
                print(f"    [Embed] → {n} chunks stored")
            except Exception as e:
                print(f"    [Embed] Error: {e}")

        total_counts["transcripts"] += 1

    return total_counts


def process_company_annual_reports(
    company_id: str, dry_run: bool, skip_llm: bool, skip_embed: bool
) -> Dict[str, int]:
    """Process all Annual Report PDFs for a company."""
    from pdf_extractor import process_annual_report
    from gemma_extractor import process_annual_report_chunks
    from embedder import embed_and_store_chunks

    company_dir = COMPANY_DIRS.get(company_id)
    if not company_dir:
        return {}

    ar_dir = RAW_DATA_ROOT / company_dir / "Annual_Reports"
    if not ar_dir.exists():
        # Try top-level Annual_Reports
        ar_dir = RAW_DATA_ROOT / "Annual_Reports"

    if not ar_dir.exists():
        print(f"  [SKIP] No Annual Reports directory for {company_id}")
        return {}

    pdf_files = sorted(ar_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"  [SKIP] No Annual Report PDFs found for {company_id}")
        return {}

    total_counts = {"risk_flags": 0, "raw_data": 0, "chunks_embedded": 0, "reports": 0}

    for pdf in pdf_files:
        period = ar_year_to_period(pdf.stem)
        print(f"\n  📕 {pdf.name} → {period}")

        try:
            result = process_annual_report(str(pdf), company_id, period)
            text_chunks = result["text_chunks"]
            table_rows = result["table_rows"]
            print(f"    Extracted: {len(text_chunks)} text chunks, {len(table_rows)} table rows")
        except Exception as e:
            print(f"    [ERROR] PDF extraction failed: {e}")
            continue

        # Gemma extraction
        if not skip_llm and (text_chunks or table_rows):
            print(f"    [Gemma] Extracting from {len(text_chunks)} chunks + {len(table_rows)} tables...")
            try:
                llm_counts = process_annual_report_chunks(text_chunks, table_rows, dry_run=dry_run)
                total_counts["risk_flags"] += llm_counts.get("risk_flags", 0)
                total_counts["raw_data"] += llm_counts.get("raw_data", 0)
                print(f"    [Gemma] → {llm_counts}")
            except Exception as e:
                print(f"    [Gemma] Error: {e}")

        # Embed chunks
        if not skip_embed and text_chunks:
            print(f"    [Embed] Embedding {len(text_chunks)} chunks...")
            try:
                n = embed_and_store_chunks(text_chunks, document_type="annual_report", dry_run=dry_run)
                total_counts["chunks_embedded"] += n
                print(f"    [Embed] → {n} chunks stored")
            except Exception as e:
                print(f"    [Embed] Error: {e}")

        total_counts["reports"] += 1

    return total_counts


def main():
    parser = argparse.ArgumentParser(description="EquityLens AI — Master Ingestion Pipeline")
    parser.add_argument("--company", choices=COMPANIES + ["ALL"], default="ALL")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-llm", action="store_true")
    parser.add_argument("--skip-embed", action="store_true")
    parser.add_argument("--transcripts-only", action="store_true")
    parser.add_argument("--ar-only", action="store_true")
    args = parser.parse_args()

    targets = COMPANIES if args.company == "ALL" else [args.company]

    print(f"\n{'='*60}")
    print(f"EQUITYLENS AI — MASTER INGESTION PIPELINE")
    print(f"Companies : {', '.join(targets)}")
    print(f"Dry run   : {args.dry_run}")
    print(f"Skip LLM  : {args.skip_llm}")
    print(f"Skip Embed: {args.skip_embed}")
    print(f"{'='*60}")

    t0 = time.time()
    grand_totals = {}

    for company_id in targets:
        print(f"\n{'─'*60}")
        print(f"🏨 {company_id} — {COMPANY_NAMES.get(company_id, company_id)}")
        print(f"{'─'*60}")

        # Transcripts
        if not args.ar_only:
            print(f"\n[Transcripts] Processing...")
            tc = process_company_transcripts(
                company_id, args.dry_run, args.skip_llm, args.skip_embed
            )
            grand_totals[f"{company_id}_transcripts"] = tc
            print(f"[Transcripts] Done: {tc}")

        # Annual Reports
        if not args.transcripts_only:
            print(f"\n[Annual Reports] Processing...")
            ac = process_company_annual_reports(
                company_id, args.dry_run, args.skip_llm, args.skip_embed
            )
            grand_totals[f"{company_id}_annual_reports"] = ac
            print(f"[Annual Reports] Done: {ac}")

    elapsed = time.time() - t0
    print(f"\n{'='*60}")
    print(f"INGESTION COMPLETE in {elapsed:.1f}s")
    for k, v in grand_totals.items():
        print(f"  {k}: {v}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
