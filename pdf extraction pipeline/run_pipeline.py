"""
Pipeline Orchestrator — run_pipeline.py
Usage:
  python run_pipeline.py --file path/to/report.pdf --company IHCL --type annual_report --period FY24
  python run_pipeline.py --file path/to/transcript.pdf --company IHCL --type transcript --period Q2FY24
  python run_pipeline.py --file path/to/report.pdf --company IHCL --type annual_report --period FY24 --dry-run

Flags:
  --dry-run    Extract and print items but do NOT write to Supabase
  --skip-llm   Only embed chunks (skip Gemma extraction step)
  --skip-embed Only run Gemma extraction (skip embedding step)
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client
from pdf_extractor import process_annual_report
from transcript_parser import process_transcript
from gemma_extractor import process_annual_report_chunks, process_transcript_chunks
from embedder import embed_and_store_chunks


def get_supabase():
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))


def register_document(supabase, company_id: str, pdf_path: str,
                      doc_type: str, period: str) -> str:
    """Insert/upsert a row in the documents registry. Returns the document name."""
    p = Path(pdf_path)
    doc_name = p.name
    row = {
        "company_id":        company_id,
        "document_name":     doc_name,
        "document_type":     doc_type,
        "period":            period,
        "file_format":       "pdf",
        "file_path":         str(p.resolve()),
        "file_size_bytes":   p.stat().st_size if p.exists() else None,
        "extraction_status": "extracted",
    }
    try:
        supabase.table("documents").upsert(
            row, on_conflict="company_id,document_name"
        ).execute()
    except Exception as e:
        print(f"  [Registry] Could not register document: {e}")
    return doc_name


def update_document_status(supabase, company_id: str, doc_name: str,
                           status: str, counts: dict):
    """Mark document as processed and store final counts."""
    try:
        supabase.table("documents").update({
            "extraction_status": status,
            "chunks_count":      counts.get("chunks", 0),
            "guidance_count":    counts.get("guidance_claims", 0),
            "risk_count":        counts.get("risk_flags", 0),
            "extraction_logs":   json.dumps(counts),
            "updated_at":        "now()",
        }).eq("company_id", company_id).eq("document_name", doc_name).execute()
    except Exception as e:
        print(f"  [Registry] Could not update document status: {e}")


VALID_COMPANIES = ["IHCL", "CHALET", "LEMONTREE", "EIH", "ITCHOTELS"]
VALID_DOC_TYPES = ["annual_report", "transcript", "quarterly_results", "investor_presentation"]


def run_annual_report(pdf_path: str, company_id: str, period: str,
                      dry_run: bool, skip_llm: bool, skip_embed: bool):
    print(f"\n{'='*60}")
    print(f"ANNUAL REPORT PIPELINE")
    print(f"File   : {pdf_path}")
    print(f"Company: {company_id}  |  Period: {period}")
    print(f"Dry run: {dry_run}  |  Skip LLM: {skip_llm}  |  Skip embed: {skip_embed}")
    print(f"{'='*60}")

    t0 = time.time()
    supabase = get_supabase() if not dry_run else None

    # ── Register document ───────────────────────────────────────
    doc_name = Path(pdf_path).name
    if not dry_run:
        register_document(supabase, company_id, pdf_path, "annual_report", period)
        print(f"  [Registry] Document registered: {doc_name}")

    # ── Step 1: Extract text chunks and table rows ──────────────
    print("\n[Step 1] PDF Extraction")
    result = process_annual_report(pdf_path, company_id, period)
    text_chunks = result["text_chunks"]
    table_rows  = result["table_rows"]
    stats       = result["stats"]
    print(f"  Extracted: {len(text_chunks)} text chunks, {len(table_rows)} table rows")

    # ── Step 2: Gemma extraction → Supabase ────────────────────
    llm_counts = {}
    if not skip_llm:
        print("\n[Step 2] Gemma Extraction → Supabase")
        llm_counts = process_annual_report_chunks(text_chunks, table_rows, dry_run=dry_run)
        print(f"  Stored: {llm_counts}")
    else:
        print("\n[Step 2] Gemma Extraction — SKIPPED")

    # ── Step 3: Embeddings → document_chunks ───────────────────
    n_embedded = 0
    if not skip_embed:
        print("\n[Step 3] Embedding → document_chunks")
        n_embedded = embed_and_store_chunks(text_chunks, document_type="annual_report", dry_run=dry_run)
        print(f"  Embedded and stored: {n_embedded} chunks")
    else:
        print("\n[Step 3] Embedding — SKIPPED")

    # ── Update document registry ────────────────────────────────
    if not dry_run:
        final_counts = {**llm_counts, "chunks": n_embedded}
        update_document_status(supabase, company_id, doc_name, "processed", final_counts)

    elapsed = time.time() - t0
    print(f"\n{'='*60}")
    print(f"DONE in {elapsed:.1f}s")
    print(f"Pages processed : {stats['pages_processed']}/{stats['total_pages']}")
    print(f"Text chunks     : {len(text_chunks)}")
    print(f"Table rows      : {len(table_rows)}")
    print(f"{'='*60}\n")


def run_transcript(pdf_path: str, company_id: str, period: str,
                   dry_run: bool, skip_llm: bool, skip_embed: bool):
    print(f"\n{'='*60}")
    print(f"TRANSCRIPT PIPELINE")
    print(f"File   : {pdf_path}")
    print(f"Company: {company_id}  |  Period: {period or 'auto-detect'}")
    print(f"Dry run: {dry_run}  |  Skip LLM: {skip_llm}  |  Skip embed: {skip_embed}")
    print(f"{'='*60}")

    t0 = time.time()
    supabase = get_supabase() if not dry_run else None

    # ── Register document ───────────────────────────────────────
    doc_name = Path(pdf_path).name
    if not dry_run:
        register_document(supabase, company_id, pdf_path, "transcript", period or "")
        print(f"  [Registry] Document registered: {doc_name}")

    # ── Step 1: Parse transcript into speaker blocks ────────────
    print("\n[Step 1] Transcript Parsing")
    result = process_transcript(pdf_path, company_id, period or None)
    mgmt_chunks = result["mgmt_chunks"]
    all_chunks  = result["all_chunks"]
    stats       = result["stats"]
    detected_period = stats["period_detected"]
    print(f"  Period detected: {detected_period}")
    print(f"  Management chunks: {len(mgmt_chunks)} / Total: {len(all_chunks)}")

    # ── Step 2: Gemma guidance extraction → guidance_claims ────
    llm_counts = {}
    if not skip_llm:
        print("\n[Step 2] Gemma Guidance Extraction → guidance_claims")
        llm_counts = process_transcript_chunks(mgmt_chunks, dry_run=dry_run)
        print(f"  Stored: {llm_counts}")
    else:
        print("\n[Step 2] Gemma Extraction — SKIPPED")

    # ── Step 3: Embed all chunks (incl. analyst Q&A for RAG) ───
    n_embedded = 0
    if not skip_embed:
        print("\n[Step 3] Embedding → document_chunks")
        n_embedded = embed_and_store_chunks(all_chunks, document_type="transcript", dry_run=dry_run)
        print(f"  Embedded and stored: {n_embedded} chunks")
    else:
        print("\n[Step 3] Embedding — SKIPPED")

    # ── Update document registry ────────────────────────────────
    if not dry_run:
        final_counts = {**llm_counts, "chunks": n_embedded}
        update_document_status(supabase, company_id, doc_name, "processed", final_counts)

    elapsed = time.time() - t0
    print(f"\n{'='*60}")
    print(f"DONE in {elapsed:.1f}s")
    print(f"Speaker blocks  : {stats['total_speaker_blocks']}")
    print(f"Mgmt blocks     : {stats['management_blocks']}")
    print(f"Total chunks    : {len(all_chunks)}")
    print(f"{'='*60}\n")


# ─────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="EquityLens AI — PDF Ingestion Pipeline"
    )
    parser.add_argument("--file",    required=True, help="Path to PDF file")
    parser.add_argument("--company", required=True, choices=VALID_COMPANIES,
                        help="Company ID: IHCL | CHALET | LEMONTREE | EIH | ITCHOTELS")
    parser.add_argument("--type",    required=True, choices=VALID_DOC_TYPES,
                        help="Document type: annual_report | transcript | quarterly_results | investor_presentation")
    parser.add_argument("--period",  default=None,
                        help="Reporting period e.g. FY24 or Q2FY24 (auto-detected for transcripts)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Extract and print but do NOT write to Supabase")
    parser.add_argument("--skip-llm",   action="store_true",
                        help="Skip Gemma extraction, only run embeddings")
    parser.add_argument("--skip-embed", action="store_true",
                        help="Skip embeddings, only run Gemma extraction")

    args = parser.parse_args()

    # Validate file exists
    pdf_path = str(Path(args.file).resolve())
    if not Path(pdf_path).exists():
        print(f"[ERROR] File not found: {pdf_path}")
        sys.exit(1)

    # Validate period provided for annual reports
    if args.type == "annual_report" and not args.period:
        print("[ERROR] --period is required for annual_report (e.g. FY24)")
        sys.exit(1)

    if args.type in ("annual_report", "quarterly_results", "investor_presentation"):
        run_annual_report(
            pdf_path, args.company, args.period,
            dry_run=args.dry_run, skip_llm=args.skip_llm, skip_embed=args.skip_embed
        )
    elif args.type == "transcript":
        run_transcript(
            pdf_path, args.company, args.period,
            dry_run=args.dry_run, skip_llm=args.skip_llm, skip_embed=args.skip_embed
        )


if __name__ == "__main__":
    main()
