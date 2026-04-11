"""
Text Preprocessor
=================
Loads all JSON files from Data Ingestion/extracted_json/,
flattens pages -> paragraphs -> clean sentences.
Returns structured list of text chunks with metadata.
"""

import os
import re
import json

BASE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "Data Ingestion", "extracted_json"
)

COMPANIES = {
    "CHALET": "Chalet_Hotels",
    "EIH": "EIH_Limited",
    "IHCL": "Indian_Hotels",
    "JUNIPER": "Juniper_Hotels",
    "LEMONTREE": "Lemon_Tree_Hotels",
}

DOC_TYPES = ["announcement", "annual_report", "credit_rating", "quarterly_results"]


def clean_text(text: str) -> str:
    """Clean junk characters, normalize whitespace."""
    if not text or not isinstance(text, str):
        return ""
    # Remove control characters (keep newlines temporarily)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
    # Replace non-breaking spaces
    text = text.replace('\xa0', ' ')
    # Replace multiple spaces
    text = re.sub(r' {2,}', ' ', text)
    # Strip
    text = text.strip()
    return text


def is_useful_text(text: str, min_words: int = 5) -> bool:
    """Filter out junk/boilerplate text."""
    if len(text) < 20:
        return False
    words = text.split()
    if len(words) < min_words:
        return False
    # Filter out pure URL/email lines
    if text.startswith("http") or text.startswith("www."):
        return False
    # Filter out lines that are mostly numbers/special chars
    alpha_ratio = sum(c.isalpha() for c in text) / max(len(text), 1)
    if alpha_ratio < 0.3:
        return False
    # Filter out known boilerplate
    boilerplate = [
        "digitally signed by", "page 1 of", "page 2 of",
        "scrip code", "bse limited", "national stock exchange",
        "yours sincerely", "you are requested to kindly",
    ]
    text_lower = text.lower()
    for bp in boilerplate:
        if bp in text_lower and len(text) < 200:
            return False
    return True


def split_sentences(text: str) -> list:
    """Split text into sentences (basic)."""
    # Split on period followed by space+uppercase, or question/exclamation marks
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
    return [s.strip() for s in sentences if len(s.strip()) > 15]


def load_document_json(filepath: str) -> list:
    """Load a document JSON file, return list of paragraphs."""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if not isinstance(data, list):
        data = [data]

    paragraphs = []
    for doc in data:
        period = doc.get("period", "unknown")
        source = doc.get("source_file", "")
        doc_type = doc.get("document_type", "")

        pages = doc.get("pages", [])
        if isinstance(pages, str):
            # Some files have pages as string representation
            try:
                pages = json.loads(pages.replace("'", '"'))
            except Exception:
                pages = []

        for page in pages:
            if not isinstance(page, dict):
                continue
            page_num = page.get("page_number", 0)
            for para in page.get("paragraphs", []):
                cleaned = clean_text(para)
                if is_useful_text(cleaned):
                    paragraphs.append({
                        "text": cleaned,
                        "period": period,
                        "source_file": source,
                        "doc_type": doc_type,
                        "page": page_num,
                    })
    return paragraphs


def load_transcript_json(filepath: str) -> list:
    """Load a call transcript JSON file, return list of speaker-text pairs."""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if not isinstance(data, list):
        return []

    # Extract period from filename (e.g., 2025_Feb.json -> Feb 2025)
    fname = os.path.basename(filepath).replace('.json', '')
    parts = fname.split('_')
    period = f"{parts[1]} {parts[0]}" if len(parts) >= 2 else fname

    entries = []
    for item in data:
        speaker = item.get("speaker", "Unknown")
        text = clean_text(item.get("text", ""))
        if is_useful_text(text, min_words=8):
            entries.append({
                "text": text,
                "speaker": speaker,
                "period": period,
                "source_file": os.path.basename(filepath),
                "doc_type": "call_transcript",
                "page": 0,
            })
    return entries


def load_all_company_data(company_code: str) -> list:
    """Load all textual data for a company."""
    company_dir = os.path.join(BASE_DIR, company_code)
    if not os.path.exists(company_dir):
        return []

    all_chunks = []

    # Load document JSONs
    for doc_type in DOC_TYPES:
        fpath = os.path.join(company_dir, f"{doc_type}.json")
        if os.path.exists(fpath):
            chunks = load_document_json(fpath)
            for c in chunks:
                c["company"] = company_code
            all_chunks.extend(chunks)

    # Load call transcripts
    transcript_dir = os.path.join(company_dir, "Call_Transcripts_JSON")
    if os.path.exists(transcript_dir):
        for fname in sorted(os.listdir(transcript_dir)):
            if fname.endswith('.json'):
                fpath = os.path.join(transcript_dir, fname)
                chunks = load_transcript_json(fpath)
                for c in chunks:
                    c["company"] = company_code
                all_chunks.extend(chunks)

    return all_chunks


def load_all_data() -> list:
    """Load ALL textual data across ALL companies."""
    all_data = []
    for code in COMPANIES:
        chunks = load_all_company_data(code)
        all_data.extend(chunks)
        print(f"  {code}: {len(chunks)} text chunks loaded")
    return all_data


if __name__ == "__main__":
    print("Loading all textual data...")
    data = load_all_data()
    print(f"\nTotal: {len(data)} text chunks across {len(COMPANIES)} companies")

    # Show breakdown by doc type
    from collections import Counter
    type_counts = Counter(d["doc_type"] for d in data)
    for dtype, count in type_counts.most_common():
        print(f"  {dtype}: {count}")
