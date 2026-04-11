"""
EquityLens AI — PDF Text Extraction (Tables Eliminated)
========================================================
Extracts ONLY textual paragraphs from PDFs, skipping all tables.
Outputs JSON with page-level citations for Supabase ingestion.

Uses:
  - pdfplumber: detect table bounding boxes
  - PyMuPDF (fitz): extract text blocks with coordinates
  - Compares block positions against table regions to filter out tables

Output format per PDF:
{
    "source_file": "2025.pdf",
    "company_id": "IHCL",
    "document_type": "annual_report",
    "period": "FY25",
    "total_pages": 180,
    "pages": [
        {
            "page_number": 1,
            "paragraphs": [
                "Chairman's message to shareholders...",
                "Another paragraph of text..."
            ]
        },
        ...
    ]
}
"""

import fitz  # PyMuPDF
import pdfplumber
import json
import os
import re
import sys
from pathlib import Path


# ═══════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════

# Base path to raw data (adjust if needed)
RAW_DATA_BASE = Path(r"c:\Users\91845\Desktop\DataHack4.0\the-big-leagues\Raw Data Extraction")

# Output directory
OUTPUT_DIR = Path(r"c:\Users\91845\Desktop\DataHack4.0\the-big-leagues\Data Ingestion\extracted_json")

# Company folder → company_id mapping
COMPANY_MAP = {
    "Indian_Hotels": "IHCL",
    "Chalet_Hotels": "CHALET",
    "Lemon_Tree_Hotels": "LEMONTREE",
    "EIH_Limited": "EIH",
    "Juniper_Hotels": "ITCHOTELS",  # adjust if different
}

# Folder → document_type mapping
FOLDER_DOC_TYPE = {
    "Annual_Reports": "annual_report",
    "Quarterly_Report": "quarterly_results",
    "Announcements": "announcement",
    "Credit_Ratings": "credit_rating",
}


# ═══════════════════════════════════════════════════════════
# PERIOD EXTRACTION FROM FILENAMES
# ═══════════════════════════════════════════════════════════

def extract_period_from_filename(filename: str, doc_type: str) -> str:
    """
    Extract fiscal period from PDF filename.
    
    Annual Reports:
        2025.pdf → FY25
        2024.pdf → FY24
    
    Quarterly Reports:
        Dec_2022.pdf → Q3 FY23
        Mar_2023.pdf → Q4 FY23
        Jun_2023.pdf → Q1 FY24
        Sep_2023.pdf → Q2 FY24
    
    Credit Ratings:
        2023_Nov_06.pdf → Nov 2023
        2024_Sep_25.pdf → Sep 2024
    
    Announcements:
        2026_Apr_01.pdf → Apr 2026
    """
    stem = Path(filename).stem  # remove .pdf
    
    if doc_type == "annual_report":
        # Format: 2025.pdf → FY25
        match = re.match(r"(\d{4})", stem)
        if match:
            year = int(match.group(1))
            return f"FY{year % 100}"
        return stem
    
    elif doc_type == "quarterly_results":
        # Format: Dec_2022.pdf, Mar_2023.pdf, Jun_2023.pdf, Sep_2023.pdf
        match = re.match(r"([A-Za-z]+)_(\d{4})", stem)
        if match:
            month_str = match.group(1)
            year = int(match.group(2))
            
            month_to_quarter = {
                "Jun": ("Q1", year + 1),   # Jun 2023 = Q1 FY24
                "Sep": ("Q2", year + 1),   # Sep 2023 = Q2 FY24
                "Dec": ("Q3", year + 1),   # Dec 2022 = Q3 FY23
                "Mar": ("Q4", year),       # Mar 2023 = Q4 FY23
            }
            
            if month_str in month_to_quarter:
                q, fy = month_to_quarter[month_str]
                return f"{q} FY{fy % 100}"
        return stem
    
    elif doc_type in ("credit_rating", "announcement"):
        # Format: 2023_Nov_06.pdf → Nov 2023
        match = re.match(r"(\d{4})_([A-Za-z]+)_(\d+)", stem)
        if match:
            year = match.group(1)
            month = match.group(2)
            return f"{month} {year}"
        # Fallback: 2026_Feb_19.pdf
        return stem
    
    return stem


# ═══════════════════════════════════════════════════════════
# TABLE DETECTION (using pdfplumber)
# ═══════════════════════════════════════════════════════════

def get_table_bboxes(pdf_path: str) -> dict:
    """
    Use pdfplumber to find table bounding boxes on each page.
    Returns: {page_index: [(x0, y0, x1, y1), ...]}
    """
    table_data = {}
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                tables = page.find_tables()
                bboxes = [table.bbox for table in tables]
                table_data[i] = bboxes
    except Exception as e:
        print(f"  [WARN] pdfplumber table detection failed: {e}")
        # Return empty — will extract all text without filtering
        return {}
    
    return table_data


def is_inside_table(block_bbox: tuple, table_bboxes: list) -> bool:
    """Check if a text block overlaps with any table region."""
    x0, y0, x1, y1 = block_bbox
    
    for tb in table_bboxes:
        tx0, ty0, tx1, ty1 = tb
        # Check overlap (not completely outside)
        if not (x1 < tx0 or x0 > tx1 or y1 < ty0 or y0 > ty1):
            return True
    return False


# ═══════════════════════════════════════════════════════════
# ADDITIONAL TABLE HEURISTICS
# ═══════════════════════════════════════════════════════════

def looks_like_table_text(text: str) -> bool:
    """
    Extra heuristic to catch table-like text that pdfplumber misses.
    Catches rows of numbers, aligned columns, etc.
    """
    lines = text.strip().split("\n")
    if not lines:
        return False
    
    # If most lines are very short and contain mostly numbers → likely a table
    short_numeric_lines = 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Count how much of the line is digits, dots, commas, spaces, %, ₹
        numeric_chars = sum(1 for c in stripped if c in "0123456789.,%-₹() ")
        if len(stripped) > 0 and numeric_chars / len(stripped) > 0.7 and len(stripped) < 100:
            short_numeric_lines += 1
    
    # If >60% of non-empty lines look like table rows
    non_empty = sum(1 for l in lines if l.strip())
    if non_empty > 2 and short_numeric_lines / max(non_empty, 1) > 0.6:
        return True
    
    return False


# ═══════════════════════════════════════════════════════════
# PARAGRAPH CLEANING
# ═══════════════════════════════════════════════════════════

def clean_paragraph(text: str) -> str:
    """Clean extracted text: fix spacing, remove artifacts."""
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    # Remove page number artifacts like "Page 1 of 18"
    text = re.sub(r'Page\s+\d+\s+of\s+\d+', '', text).strip()
    return text


def is_meaningful_paragraph(text: str, min_words: int = 8) -> bool:
    """Filter out headers, footers, and tiny fragments."""
    words = text.split()
    if len(words) < min_words:
        return False
    # Skip if it's just a page header/footer
    if re.match(r'^(confidential|disclaimer|page \d+|©)', text.lower()):
        return False
    return True


# ═══════════════════════════════════════════════════════════
# MAIN EXTRACTION
# ═══════════════════════════════════════════════════════════

def extract_pdf_to_json(pdf_path: str, company_id: str, doc_type: str, period: str) -> dict:
    """
    Extract text from a PDF, eliminating tables, returning JSON with citations.
    """
    pdf_path = str(pdf_path)
    filename = os.path.basename(pdf_path)
    
    print(f"  [PDF] Processing: {filename} ({doc_type}, {period})")
    
    # Step 1: Detect table regions with pdfplumber
    print(f"       Detecting tables...")
    table_bboxes = get_table_bboxes(pdf_path)
    
    # Step 2: Extract text blocks with PyMuPDF, skipping table regions
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    
    pages_data = []
    total_paragraphs = 0
    skipped_table_blocks = 0
    skipped_heuristic_blocks = 0
    
    for page_num in range(total_pages):
        page = doc[page_num]
        blocks = page.get_text("blocks")  # Returns (x0, y0, x1, y1, text, block_no, block_type)
        page_tables = table_bboxes.get(page_num, [])
        
        paragraphs = []
        
        for block in blocks:
            x0, y0, x1, y1, text = block[0], block[1], block[2], block[3], block[4]
            block_type = block[6] if len(block) > 6 else 0
            
            # Skip image blocks
            if block_type != 0:
                continue
            
            block_bbox = (x0, y0, x1, y1)
            
            # Skip if inside a detected table region
            if is_inside_table(block_bbox, page_tables):
                skipped_table_blocks += 1
                continue
            
            # Skip if text looks like a table (heuristic)
            if looks_like_table_text(text):
                skipped_heuristic_blocks += 1
                continue
            
            # Clean and validate
            cleaned = clean_paragraph(text)
            if is_meaningful_paragraph(cleaned):
                paragraphs.append(cleaned)
        
        if paragraphs:
            pages_data.append({
                "page_number": page_num + 1,
                "paragraphs": paragraphs
            })
            total_paragraphs += len(paragraphs)
    
    doc.close()
    
    print(f"       [OK] {total_pages} pages -> {total_paragraphs} paragraphs extracted")
    print(f"       [SKIP] {skipped_table_blocks} table blocks, {skipped_heuristic_blocks} heuristic blocks")
    
    return {
        "source_file": filename,
        "company_id": company_id,
        "document_type": doc_type,
        "period": period,
        "total_pages": total_pages,
        "total_paragraphs": total_paragraphs,
        "pages": pages_data
    }


# ═══════════════════════════════════════════════════════════
# BATCH PROCESSING
# ═══════════════════════════════════════════════════════════

def process_company(company_folder: str, company_id: str):
    """Process all PDFs for a single company."""
    
    company_path = RAW_DATA_BASE / company_folder
    if not company_path.exists():
        print(f"[ERROR] Company folder not found: {company_path}")
        return
    
    print(f"\n{'='*60}")
    print(f"[HOTEL] Processing: {company_folder} ({company_id})")
    print(f"{'='*60}")
    
    # Create output directory for this company
    company_output = OUTPUT_DIR / company_id
    company_output.mkdir(parents=True, exist_ok=True)
    
    # Process each PDF folder
    for folder_name, doc_type in FOLDER_DOC_TYPE.items():
        folder_path = company_path / folder_name
        
        if not folder_path.exists():
            print(f"\n  [WARN] Folder not found: {folder_name} -- skipping")
            continue
        
        print(f"\n  [DIR] {folder_name} -> {doc_type}")
        
        # Find all PDFs
        pdf_files = sorted(folder_path.glob("*.pdf"))
        
        if not pdf_files:
            print(f"     No PDFs found in {folder_name}")
            continue
        
        print(f"     Found {len(pdf_files)} PDF(s)")
        
        # Process each PDF
        results = []
        for pdf_file in pdf_files:
            period = extract_period_from_filename(pdf_file.name, doc_type)
            
            try:
                result = extract_pdf_to_json(
                    pdf_path=pdf_file,
                    company_id=company_id,
                    doc_type=doc_type,
                    period=period
                )
                results.append(result)
            except Exception as e:
                print(f"       [FAIL] {pdf_file.name} -- {e}")
                continue
        
        # Save all results for this document type as one JSON file
        if results:
            output_file = company_output / f"{doc_type}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            total_paras = sum(r["total_paragraphs"] for r in results)
            print(f"\n  [SAVED] {output_file.name} ({len(results)} docs, {total_paras} total paragraphs)")


def main():
    """Main entry point — process specified company or all."""
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Parse command line args
    if len(sys.argv) > 1:
        # Process specific company: python extract_pdfs_to_json.py Indian_Hotels
        company_folder = sys.argv[1]
        if company_folder in COMPANY_MAP:
            process_company(company_folder, COMPANY_MAP[company_folder])
        else:
            print(f"[ERROR] Unknown company: {company_folder}")
            print(f"   Available: {', '.join(COMPANY_MAP.keys())}")
    else:
        # Default: process Indian_Hotels only
        print("[START] EquityLens AI -- PDF Text Extraction")
        print("   Extracting text paragraphs, eliminating tables")
        print("   Output: JSON with page-level citations\n")
        
        process_company("Indian_Hotels", "IHCL")
    
    print(f"\n{'='*60}")
    print(f"[DONE] Extracted JSON files are in: {OUTPUT_DIR}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
