"""
Earnings Call Transcript Parser
- Splits transcript PDF into speaker blocks (CEO, CFO, MD, Analyst, etc.)
- Tags each block with speaker name, title, approximate timestamp, page number
- Management blocks → Gemma guidance extraction
- All blocks → document_chunks embeddings for Q&A RAG
"""

import re
import pdfplumber
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from config import SKIP_SPEAKERS, CHUNK_CHARS, CHUNK_OVERLAP_CHARS


# ─────────────────────────────────────────────────────────────────
# SPEAKER DETECTION PATTERNS
# Handles formats seen in Indian hotel company transcripts:
#   "Puneet Chhatwal:"
#   "Puneet Chhatwal (MD & CEO):"
#   "Giridhar Sanjeevi – CFO:"
#   "Management:" / "Analyst:"
#   "Moderator:" (skip)
# ─────────────────────────────────────────────────────────────────

SPEAKER_RE = re.compile(
    r"^([A-Z][A-Za-z\s\.\-\']{2,50}?"          # Name (starts with capital)
    r"(?:\s*[\(\[–\-]\s*"                        # optional ( or [ or –
    r"(?:MD|CEO|CFO|COO|CRO|President|Director|Chairman|"
    r"Managing Director|Chief Executive|Chief Financial|"
    r"Chief Operating|Head|VP|Vice President|Analyst|"
    r"Moderator|Operator|Coordinator)"
    r"[^\)\]]*[\)\]])?"                          # closing ) or ]
    r")\s*[:\-–]\s*",                            # colon or dash separator
    re.MULTILINE
)

# Patterns that identify the speaker as a management member
MGMT_TITLE_RE = re.compile(
    r"\b(MD|CEO|CFO|COO|CRO|President|Chairman|"
    r"Managing Director|Chief Executive|Chief Financial|"
    r"Chief Operating|Director|Head of|VP|Vice President)\b",
    re.IGNORECASE
)

# Patterns for extracting timestamps like [00:12:45] or 12:41 from text
TIMESTAMP_RE = re.compile(r"\[?(\d{1,2}:\d{2}(?::\d{2})?)\]?")

# Quarter/period header patterns: "Q2 FY2024 Earnings Call" etc.
PERIOD_RE = re.compile(
    r"(Q[1-4]\s*FY\s*\d{2,4}|FY\s*\d{2,4}|"
    r"(?:first|second|third|fourth)\s+quarter\s+FY\s*\d{2,4})",
    re.IGNORECASE
)


def extract_period_from_header(pdf_path: str) -> Optional[str]:
    """Try to extract the quarter/period from the first 3 pages of transcript."""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages[:3]:
            text = page.extract_text() or ""
            m = PERIOD_RE.search(text)
            if m:
                raw = m.group(1)
                # Normalise: "Q2 FY2024" → "Q2 FY24"
                raw = re.sub(r"FY\s*20(\d{2})", r"FY\1", raw, flags=re.IGNORECASE)
                raw = re.sub(r"\s+", " ", raw).strip().upper()
                return raw
    return None


def is_management_speaker(speaker_name: str) -> bool:
    """Return True if speaker is a company management member (not analyst/operator)."""
    name_lower = speaker_name.lower()
    for skip in SKIP_SPEAKERS:
        if skip in name_lower:
            return False
    # Explicitly mark analysts as non-management
    if re.search(r"\banalyst\b|\bresearch\b|\binvestor\b", name_lower):
        return False
    # Has a management title = management
    if MGMT_TITLE_RE.search(speaker_name):
        return True
    # Heuristic: short name without title, treat as unknown (keep for RAG, not guidance)
    return False


def extract_speaker_blocks(full_text: str) -> List[Dict]:
    """
    Split the full transcript text into speaker blocks.
    Returns list of {speaker, is_management, text, char_start}.
    """
    blocks = []
    matches = list(SPEAKER_RE.finditer(full_text))

    for i, match in enumerate(matches):
        speaker_raw = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        block_text = full_text[start:end].strip()

        if not block_text:
            continue

        # Extract title from name if present
        title_match = re.search(
            r"[\(\[–\-]\s*([^)\]]+?)[\)\]]", speaker_raw
        )
        title = title_match.group(1).strip() if title_match else None
        # Clean name: remove title part
        name = re.sub(r"\s*[\(\[–\-][^\)\]]*[\)\]]", "", speaker_raw).strip()

        # Extract timestamps from block text
        timestamps = TIMESTAMP_RE.findall(block_text)
        first_ts = timestamps[0] if timestamps else None

        blocks.append({
            "speaker_raw": speaker_raw,
            "speaker_name": name,
            "speaker_title": title,
            "is_management": is_management_speaker(speaker_raw),
            "text": block_text,
            "first_timestamp": first_ts,
            "char_start": match.start(),
        })

    return blocks


# ─────────────────────────────────────────────────────────────────
# CHUNK MANAGEMENT BLOCKS (for Gemma guidance extraction)
# ─────────────────────────────────────────────────────────────────

def chunk_speaker_block(block: Dict, source_document: str,
                        company_id: str, period: str,
                        chunk_size: int = CHUNK_CHARS,
                        overlap: int = CHUNK_OVERLAP_CHARS) -> List[Dict]:
    """
    Split a long speaker block into overlapping chunks.
    Each chunk retains speaker metadata.
    """
    text = block["text"]
    chunks = []
    start = 0
    idx = 0
    while start < len(text):
        end = start + chunk_size
        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append({
                "type": "transcript_chunk",
                "chunk_text": chunk_text,
                "chunk_index": idx,
                "speaker": block["speaker_name"],
                "speaker_title": block["speaker_title"],
                "is_management": block["is_management"],
                "source_timestamp": block["first_timestamp"],
                "source_document": source_document,
                "section_name": "earnings_call",
                "company_id": company_id,
                "period": period,
            })
            idx += 1
        start += chunk_size - overlap

    return chunks


# ─────────────────────────────────────────────────────────────────
# PAGE-NUMBER MAPPING
# pdfplumber gives us page text; we need to map speaker blocks
# back to page numbers for citations.
# ─────────────────────────────────────────────────────────────────

def build_page_char_index(pdf_path: str) -> List[Tuple[int, int, int]]:
    """
    Returns list of (page_num, char_start, char_end) across the full text.
    Used to reverse-map a character offset → page number.
    """
    index = []
    offset = 0
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            index.append((page_num, offset, offset + len(text)))
            offset += len(text) + 1  # +1 for newline separator
    return index


def char_offset_to_page(char_offset: int,
                         page_index: List[Tuple[int, int, int]]) -> int:
    """Binary-search the page index to find the page number for a char offset."""
    for page_num, start, end in page_index:
        if start <= char_offset < end:
            return page_num
    return page_index[-1][0] if page_index else 1


# ─────────────────────────────────────────────────────────────────
# MAIN: PROCESS TRANSCRIPT
# ─────────────────────────────────────────────────────────────────

def process_transcript(pdf_path: str, company_id: str,
                        period: Optional[str] = None) -> Dict:
    """
    Main entry point for Earnings Call Transcript PDFs.

    Args:
        pdf_path: absolute path to the PDF
        company_id: e.g. "IHCL"
        period: e.g. "Q2FY24" — auto-detected from header if None

    Returns:
        {
          "mgmt_chunks": [...],   # management-only chunks → guidance extraction
          "all_chunks": [...],    # all chunks → embeddings for Q&A
          "stats": {...}
        }
    """
    source_document = Path(pdf_path).name

    # Auto-detect period from transcript header
    if not period:
        period = extract_period_from_header(pdf_path) or "UNKNOWN"

    print(f"\n[Transcript Parser] Processing: {source_document}")
    print(f"  Company: {company_id} | Period: {period}")

    # Build full text with page index for citation
    full_text_parts = []
    page_index = build_page_char_index(pdf_path)

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            full_text_parts.append(page.extract_text() or "")

    full_text = "\n".join(full_text_parts)

    # Split into speaker blocks
    blocks = extract_speaker_blocks(full_text)
    print(f"  Speaker blocks found: {len(blocks)}")
    mgmt_blocks = [b for b in blocks if b["is_management"]]
    print(f"  Management blocks: {len(mgmt_blocks)}")

    # Attach page numbers to blocks
    for block in blocks:
        block["source_page"] = char_offset_to_page(
            block["char_start"], page_index
        )

    # Chunk all blocks
    all_chunks: List[Dict] = []
    mgmt_chunks: List[Dict] = []

    for block in blocks:
        block_chunks = chunk_speaker_block(
            block, source_document, company_id, period
        )
        # Add page number to each chunk
        for c in block_chunks:
            c["source_page"] = block["source_page"]
        all_chunks.extend(block_chunks)
        if block["is_management"]:
            mgmt_chunks.extend(block_chunks)

    stats = {
        "total_speaker_blocks": len(blocks),
        "management_blocks": len(mgmt_blocks),
        "total_chunks": len(all_chunks),
        "management_chunks": len(mgmt_chunks),
        "period_detected": period,
    }
    print(f"  Chunks: {len(all_chunks)} total | {len(mgmt_chunks)} management")

    return {"mgmt_chunks": mgmt_chunks, "all_chunks": all_chunks, "stats": stats}
