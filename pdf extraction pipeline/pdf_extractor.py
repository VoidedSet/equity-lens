"""
PDF Extractor for Annual Reports
- Extracts text page-by-page with exact page numbers (critical for citations)
- Detects Table of Contents → maps section names to page ranges
- Filters to HIGH_VALUE_SECTIONS only (skips ~60% of boilerplate)
- Extracts tables from operational metric pages using pdfplumber
- Chunks filtered text into ~800-token blocks tagged with page + section
"""

import re
import pdfplumber
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from config import HIGH_VALUE_SECTIONS, CHUNK_CHARS, CHUNK_OVERLAP_CHARS


# ─────────────────────────────────────────────────────────────────
# TOC PARSING
# ─────────────────────────────────────────────────────────────────

def extract_toc(pdf_path: str) -> Dict[str, int]:
    """
    Parse the Table of Contents to get {section_name: start_page}.
    Looks for lines that match: 'Section Name ........ 45' or 'Section Name 45'
    Returns best-effort mapping; empty dict if no TOC found.
    """
    toc_map: Dict[str, int] = {}
    toc_page_limit = 12  # TOC is almost always in the first 12 pages

    # Pattern: text followed by dots (optional) then a page number
    toc_line_re = re.compile(
        r"^(.{5,80}?)\s*\.{2,}\s*(\d{1,4})\s*$|"   # "Section ........ 45"
        r"^(.{5,80}?)\s{3,}(\d{1,4})\s*$",           # "Section         45"
        re.MULTILINE
    )

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages[:toc_page_limit], start=1):
            text = page.extract_text() or ""
            # Quick check: a TOC page has many lines ending in numbers
            lines = text.strip().splitlines()
            number_ending = sum(1 for l in lines if re.search(r"\d{1,4}\s*$", l.strip()))
            if number_ending < 5:
                continue
            for match in toc_line_re.finditer(text):
                name = (match.group(1) or match.group(3) or "").strip().lower()
                pg   = int(match.group(2) or match.group(4) or 0)
                if name and pg > 0:
                    toc_map[name] = pg

    return toc_map


def classify_page_section(page_text: str, toc_map: Dict[str, int], page_num: int) -> Optional[str]:
    """
    Given page text and TOC, return the section name this page likely belongs to.
    Falls back to keyword scanning if TOC mapping is unavailable.
    """
    text_lower = page_text.lower()

    # 1. Check if this page starts a known high-value section (heading detection)
    for section in HIGH_VALUE_SECTIONS:
        # Look for section heading at start of page or after a line break
        if re.search(rf"(^|\n)\s*{re.escape(section)}", text_lower):
            return section

    # 2. Fallback: if toc_map exists, find which section this page number falls under
    if toc_map:
        sorted_sections = sorted(toc_map.items(), key=lambda x: x[1])
        current_section = None
        for sec_name, start_pg in sorted_sections:
            if start_pg <= page_num:
                current_section = sec_name
            else:
                break
        if current_section:
            for kw in HIGH_VALUE_SECTIONS:
                if kw in current_section:
                    return current_section

    return None  # Not a high-value page


def is_high_value_page(page_text: str, page_num: int, toc_map: Dict[str, int]) -> Tuple[bool, str]:
    """Returns (is_high_value, section_name)."""
    text_lower = page_text.lower()

    # Always include pages with hotel KPIs even outside named sections
    kpi_keywords = [
        "revpar", "rev par", "revenue per available room",
        "average daily rate", "adr", "occupancy rate", "occupancy %",
        "fnb revenue", "f&b revenue", "room revenue", "ebitda margin",
        "interest coverage", "new keys", "room additions", "pipeline",
        "management discussion", "md&a", "risk factor",
        "chairman", "managing director message",
        "notes to financial", "notes to accounts",
        "borrowings", "long-term debt",
    ]
    for kw in kpi_keywords:
        if kw in text_lower:
            return True, kw

    section = classify_page_section(page_text, toc_map, page_num)
    if section:
        return True, section

    return False, ""


# ─────────────────────────────────────────────────────────────────
# TABLE EXTRACTION
# ─────────────────────────────────────────────────────────────────

HOTEL_TABLE_KEYWORDS = [
    "revpar", "occupancy", "average daily rate", "adr",
    "f&b", "fnb", "room revenue", "rooms sold",
    "available room", "room nights",
]


def extract_tables_from_page(page, page_num: int, source_document: str,
                              company_id: str, period: str) -> List[Dict]:
    """
    Extract tables from a pdfplumber page.
    Returns list of row-dicts ready to be processed by gemma_extractor.
    Only runs on pages that have hotel KPI keywords.
    """
    extracted = []
    tables = page.extract_tables()
    if not tables:
        return extracted

    for table in tables:
        if not table or len(table) < 2:
            continue
        # Check if any header cell contains hotel KPI keywords
        header_row = [str(c).lower() for c in (table[0] or []) if c]
        header_text = " ".join(header_row)
        if not any(kw in header_text for kw in HOTEL_TABLE_KEYWORDS):
            continue

        headers = [str(c).strip() if c else f"col_{i}" for i, c in enumerate(table[0])]
        for row in table[1:]:
            if not row or all(c is None for c in row):
                continue
            row_dict = {headers[i]: str(row[i]).strip() if row[i] else "" for i in range(len(headers))}
            extracted.append({
                "type": "table_row",
                "data": row_dict,
                "source_document": source_document,
                "source_page": page_num,
                "company_id": company_id,
                "period": period,
            })

    return extracted


# ─────────────────────────────────────────────────────────────────
# TEXT CHUNKING
# ─────────────────────────────────────────────────────────────────

def chunk_text(text: str, page_num: int, section: str,
               source_document: str, company_id: str, period: str,
               chunk_size: int = CHUNK_CHARS,
               overlap: int = CHUNK_OVERLAP_CHARS) -> List[Dict]:
    """
    Split text into overlapping chunks.
    Each chunk tagged with citation metadata.
    """
    text = text.strip()
    if not text:
        return []

    chunks = []
    start = 0
    idx = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append({
                "type": "text_chunk",
                "chunk_text": chunk,
                "chunk_index": idx,
                "section_name": section,
                "source_document": source_document,
                "source_page": page_num,
                "company_id": company_id,
                "period": period,
            })
            idx += 1
        start += chunk_size - overlap

    return chunks


# ─────────────────────────────────────────────────────────────────
# MAIN: PROCESS ANNUAL REPORT
# ─────────────────────────────────────────────────────────────────

def process_annual_report(pdf_path: str, company_id: str, period: str) -> Dict:
    """
    Main entry point for Annual Report PDFs.
    Uses pypdf for FAST text extraction (10x faster than pdfplumber).
    """
    import pypdf
    import time as _time

    source_document = Path(pdf_path).name
    text_chunks: List[Dict] = []

    print(f"\n[PDF Extractor] Processing: {source_document}")
    print(f"  Company: {company_id} | Period: {period}")

    t0 = _time.time()

    # FAST text extraction with pypdf
    reader = pypdf.PdfReader(pdf_path)
    total_pages = len(reader.pages)
    print(f"  Total pages: {total_pages}")

    pages_processed = 0
    pages_skipped = 0

    for page_num in range(1, total_pages + 1):
        page_text = reader.pages[page_num - 1].extract_text() or ""
        if not page_text.strip() or len(page_text.strip()) < 50:
            pages_skipped += 1
            continue

        is_hv, section = is_high_value_page(page_text, page_num, {})
        if not is_hv:
            pages_skipped += 1
            continue

        pages_processed += 1
        page_chunks = chunk_text(
            page_text, page_num, section,
            source_document, company_id, period
        )
        text_chunks.extend(page_chunks)

    elapsed = _time.time() - t0
    stats = {
        "total_pages": total_pages,
        "pages_processed": pages_processed,
        "pages_skipped": pages_skipped,
        "text_chunks": len(text_chunks),
        "table_rows": 0,
    }
    print(f"  Done in {elapsed:.1f}s — Pages: {pages_processed}/{total_pages} | Chunks: {len(text_chunks)}")

    return {"text_chunks": text_chunks, "table_rows": [], "stats": stats}
