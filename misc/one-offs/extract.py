"""
Single-file PDF extractor. Reads FULL PDF → Groq calls → comprehensive extraction.
Covers: visions, insights, promises, hotel metrics, risks, credit ratings, strategy.
"""
import os, sys, json, time
os.chdir(os.path.join(os.path.dirname(__file__), "pdf extraction pipeline"))
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()

import pypdf
from openai import OpenAI

PDF_PATH = "data/IHCL/ihcl.pdf"
COMPANY = "IHCL"
PERIOD = "FY24"

SYSTEM_PROMPT = f"""You are an expert equity research analyst extracting intelligence from an Indian hotel company Annual Report.
Company: {COMPANY} | Period: {PERIOD}

Extract EVERY item that falls into these categories:

1. CEO/MD VISION & PROMISES: Chairman's message, MD letter, any vision statement, strategic direction, future commitments.
   Include the EXACT quote. These are the most important items.

2. MANAGEMENT GUIDANCE: Any forward-looking statement (will, expect, target, plan, aim, intend, guidance, outlook).
   Include exact quote, target period, and numeric targets if stated.

3. HOTEL OPERATIONAL METRICS: RevPAR, ADR, Occupancy %, F&B revenue/share, total room count/keys,
   new properties added, room nights, ARR, GOP/GOPPAR, brands, management contracts.

4. RISK FLAGS: Any risk, concern, auditor remark, governance issue, debt warning, litigation,
   regulatory risk, key person dependency, supply overhang.

5. CREDIT RATINGS: CRISIL, ICRA, CARE, Fitch, Moody's — rating, outlook, instrument, amount.

6. STRATEGIC INSIGHTS: Brand strategy, expansion plans, asset-light vs asset-heavy approach,
   new market entry, sustainability/ESG, digital initiatives, loyalty program, M&A.

For EACH item, return a JSON object with:
- "category": "vision" | "guidance" | "hotel_metric" | "risk" | "credit_rating" | "strategy"
- "page": page number (integer)
- "detail": clear description of the extracted fact
- "value": numeric value if applicable (float or null)
- "unit": "INR" | "%" | "rooms" | "INR Cr" | null
- "quote": EXACT words from the document (for vision, guidance, risk items)
- "target_period": future period if forward-looking (e.g. "FY25", "by 2030") or null
- "severity": for risks only — "critical" | "high" | "medium" | null

Return a JSON array. Be EXHAUSTIVE — extract every single relevant item. Miss nothing.
If a page has nothing relevant, skip it. Return ONLY the JSON array."""


MODEL = "llama-3.1-8b-instant"  # higher rate limits than 70B

SIGNAL_WORDS = [
    "revpar", "adr", "occupancy", "average daily rate", "room night",
    "f&b", "food and beverage", "fnb", "room count", "keys",
    "guidance", "target", "expect", "outlook", "plan to", "aim",
    "vision", "strategy", "expansion", "pipeline", "new hotel",
    "risk", "concern", "challenge", "debt", "borrowing", "leverage",
    "crisil", "icra", "care", "fitch", "moody", "rating",
    "chairman", "managing director", "ceo", "letter to shareholder",
    "brand", "sustainability", "esg", "growth", "margin", "capex",
    "highlight", "performance", "review", "management discussion",
    "promise", "commit", "intend", "will ", "asset light",
]


def call_groq(client, text_chunk, chunk_label, retries=3):
    """Make one Groq call with retry for rate limits."""
    for attempt in range(retries):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Extract from these pages:\n\n{text_chunk}"},
                ],
                temperature=0.1,
                max_tokens=4000,
            )
            raw = resp.choices[0].message.content
            start = raw.find("[")
            end = raw.rfind("]")
            if start != -1 and end != -1:
                items = json.loads(raw[start:end+1])
                print(f"  {chunk_label}: {len(items)} items")
                return items
            else:
                print(f"  {chunk_label}: no JSON in response")
                return []
        except Exception as e:
            err = str(e)
            if "429" in err and attempt < retries - 1:
                wait = 15 * (attempt + 1)
                print(f"  {chunk_label}: rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"  {chunk_label}: ERROR — {err[:100]}")
                return []
    return []


# ── Step 1: Read PDF, keep only important pages ──────────
print(f"Reading {PDF_PATH}...")
t0 = time.time()
reader = pypdf.PdfReader(PDF_PATH)
total = len(reader.pages)
print(f"  {total} pages loaded in {time.time()-t0:.1f}s")

page_texts = []
for i in range(total):
    txt = (reader.pages[i].extract_text() or "").strip()
    if len(txt) < 50:
        continue
    low = txt.lower()
    if any(kw in low for kw in SIGNAL_WORDS):
        page_texts.append((i + 1, txt))

print(f"  {len(page_texts)} important pages (out of {total})")

# ── Step 2: Split into chunks ────────────────────────────
CHARS_PER_CALL = 30000  # smaller chunks = faster responses + less rate limiting
chunks = []
current_chunk = ""
current_label_start = None

for page_num, txt in page_texts:
    page_block = f"\n\n--- PAGE {page_num} ---\n{txt}"
    if current_label_start is None:
        current_label_start = page_num
    if len(current_chunk) + len(page_block) > CHARS_PER_CALL:
        chunks.append((f"Pages {current_label_start}-{page_num-1}", current_chunk))
        current_chunk = page_block
        current_label_start = page_num
    else:
        current_chunk += page_block

if current_chunk:
    chunks.append((f"Pages {current_label_start}-{page_texts[-1][0]}", current_chunk))

print(f"  Split into {len(chunks)} Groq calls")

# ── Step 3: Call Groq for each chunk ─────────────────────
print(f"\nCalling Groq (Llama 3.3 70B) — {len(chunks)} calls...")
GROQ_KEY = os.getenv("GROQ_API_KEY") or "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"
client = OpenAI(
    api_key=GROQ_KEY,
    base_url="https://api.groq.com/openai/v1",
)

all_items = []
t1 = time.time()
for label, text in chunks:
    items = call_groq(client, text, label)
    all_items.extend(items)
    time.sleep(5)  # respect rate limits

elapsed = time.time() - t1
print(f"\nDone in {elapsed:.0f}s — {len(all_items)} total items extracted")

# ── Step 4: Display and save ─────────────────────────────
print(f"\n{'='*60}")
print(f"EXTRACTED {len(all_items)} ITEMS FROM {COMPANY} {PERIOD}")
print(f"{'='*60}\n")

# Group by category
from collections import Counter
cats = Counter(item.get("category") for item in all_items)
for cat, count in cats.most_common():
    print(f"  {cat}: {count} items")

print(f"\n{'-'*60}")
for item in all_items:
    cat = item.get("category", "?")
    pg = item.get("page", "?")
    detail = item.get("detail", "")
    val = item.get("value", "")
    unit = item.get("unit", "")
    quote = item.get("quote", "")
    print(f"\n[{cat.upper()}] p.{pg}: {detail}")
    if val:
        print(f"   Value: {val} {unit or ''}")
    if quote:
        print(f"   Quote: \"{quote[:200]}\"")

# Save full results
out_path = f"{COMPANY}_{PERIOD}_extracted.json"
with open(out_path, "w") as f:
    json.dump(all_items, f, indent=2, ensure_ascii=False)
print(f"\n{'='*60}")
print(f"Saved {len(all_items)} items to {out_path}")
print(f"{'='*60}")
