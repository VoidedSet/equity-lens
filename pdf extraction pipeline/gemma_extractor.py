"""
Gemma 3 27B-IT Extractor (via Featherless AI — OpenAI-compatible API)
- Takes text chunks from pdf_extractor or transcript_parser
- Calls Gemma with targeted prompts to extract cited facts
- Routes extracted items to correct Supabase table:
    financials | guidance_claims | risk_flags | raw_data
- Never stores unverifiable claims (hallucination guard)
"""

import json
import time
import re
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI
from supabase import create_client, Client
from config import (
    FEATHERLESS_API_KEY, FEATHERLESS_BASE_URL, GEMMA_MODEL,
    SUPABASE_URL, SUPABASE_SERVICE_KEY
)

MAX_WORKERS = 1  # sequential to avoid Featherless rate limits
CHUNKS_PER_BATCH = 5  # chunks per single LLM call

# ─────────────────────────────────────────────────────────────────
# CLIENTS
# ─────────────────────────────────────────────────────────────────

def get_llm_client() -> OpenAI:
    return OpenAI(api_key=FEATHERLESS_API_KEY, base_url=FEATHERLESS_BASE_URL)

def get_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


# ─────────────────────────────────────────────────────────────────
# PROMPTS
# ─────────────────────────────────────────────────────────────────

ANNUAL_REPORT_SYSTEM = """You are an equity research analyst extracting qualitative intelligence from Indian hotel company Annual Reports and investor documents.

Your job: extract ONLY facts EXPLICITLY STATED in the provided text chunk.
NEVER invent, infer, or extrapolate. If not clearly stated, do NOT include it.

IMPORTANT SCOPE RULES:
- DO extract: CEO/MD vision statements, strategic commitments, management promises, forward-looking guidance, risk disclosures, governance concerns, hotel-specific operational metrics
- DO NOT extract: Standard P&L items (Revenue, EBITDA, PAT, Net Profit), Balance Sheet items (Total Debt, Equity, Assets), or financial ratios (ROCE, ROE) — these come from a separate structured data source
- Hotel-specific ops metrics ARE in scope: RevPAR, ADR, Occupancy %, F&B revenue share, room count/keys, new property additions

Classify each extracted item into EXACTLY ONE category:
1. HOTEL_OPS_METRIC - hotel-specific operational metrics NOT available on financial databases: RevPAR, ADR, Occupancy %, F&B share, room count, keys added, new properties
2. GUIDANCE_CLAIM - any forward-looking statement or commitment about future performance (will, expect, target, plan, aim, intend, guidance, outlook)
3. RISK_FLAG - any risk, concern, auditor remark, governance issue, negative flag, or warning explicitly mentioned
4. CREDIT_RATING - any mention of a credit rating by CRISIL, ICRA, CARE, Fitch, Moody's, or S&P (rating scale, outlook, instrument, amount, rationale)
5. RAW_DATA - qualitative insights: CEO vision, strategy statements, market commentary, brand positioning, management tone, sustainability commitments

Return a JSON array. Each item must include:
- "table": "financials" (for HOTEL_OPS_METRIC) | "guidance_claims" | "risk_flags" | "credit_ratings" | "raw_data"
- "source_document": filename as provided
- "source_page": page number as provided (integer)
- "period": reporting period (e.g. "FY24", "Q2 FY24")
- "company_id": company ID as provided

For HOTEL_OPS_METRIC → table: "financials", also include:
- "metric": revpar|adr|occupancy|fnb_share|room_count|fnb_revenue|room_revenue|arr
- "value": numeric value (float)
- "unit": INR | % | rooms
- "period_type": "quarterly" | "annual"

For GUIDANCE_CLAIM → table: "guidance_claims", also include:
- "metric_type": revpar|adr|occupancy|rooms_keys|revenue|ebitda_margin|capex|fnb_revenue|properties|debt|other
- "target_period": future period guided (e.g. "FY25", "next 2 years")
- "guidance_value_point": single numeric value if stated (float or null)
- "guidance_value_low": range lower bound (float or null)
- "guidance_value_high": range upper bound (float or null)
- "unit": % | INR Cr | rooms | INR | null
- "verbatim_quote": EXACT words — copy-paste, do not paraphrase
- "confidence_language": "will"|"expect"|"target"|"plan"|"aim"|"hope"|"intend"
- "speaker": who said it (if named, else null)
- "check_type": check_1_revpar|check_2_keys|check_3_driver|check_4_fnb|check_5_debt|check_6_supply|other

For RISK_FLAG → table: "risk_flags", also include:
- "category": debt|governance|operational|regulatory|auditor|supply_overhang|margin_compression|management_mismatch|key_person
- "subcategory": more specific label (e.g. "interest_rate_risk", "covenant_breach", "promoter_pledge", "auditor_qualification")
- "description": one-sentence summary of the risk
- "severity": "critical"|"high"|"medium"
- "verbatim_quote": exact triggering text (or null)

For CREDIT_RATING → table: "credit_ratings", also include:
- "rating_agency": CRISIL|ICRA|CARE|Fitch|Moody's|S&P
- "rating_scale": e.g. AAA|AA+|AA|A+|A|BBB+|BBB (as stated)
- "rating_outlook": Stable|Positive|Negative|Under Review|Watch
- "instrument": e.g. Long Term Bank Facilities|NCD|Commercial Paper|Senior Secured
- "rating_amount_crores": numeric amount in INR Crores (float or null)
- "previous_rating": prior rating if mentioned (or null)
- "watch_status": CreditWatch/RatingWatch status if any (or null)
- "rationale": brief rationale quoted from document (1-2 sentences or null)

For RAW_DATA → table: "raw_data", also include:
- "data_type": "qualitative"|"strategic"|"other"
- "category": vision|strategy|brand|expansion|management|market|sustainability|governance|other
- "key_name": short snake_case label (e.g. "ceo_vision_fy25", "brand_strategy", "tier2_expansion_plan")
- "value_text": extracted content verbatim or closely paraphrased (2-4 sentences max)

If nothing worth extracting, return [].
Return ONLY the JSON array. No explanation text."""


TRANSCRIPT_SYSTEM = """You are an expert equity research analyst extracting management guidance from earnings call transcripts of Indian hotel companies.
Your ONLY job is to extract FORWARD-LOOKING guidance statements made by company management.

A guidance statement is: any quantitative or semi-quantitative commitment, expectation, or forecast made by the CEO/CFO/MD about future performance.

Examples of guidance statements:
- "We expect RevPAR to grow 12-15% in FY25" → EXTRACT
- "We plan to add 1,500 new rooms by FY26" → EXTRACT  
- "Our target EBITDA margin is 32% for next year" → EXTRACT
- "We are comfortable with our leverage" → EXTRACT (qualitative guidance on debt)
- "The industry is doing well" → SKIP (generic comment, not company-specific guidance)

For each guidance statement found, return a JSON object with:
- "table": always "guidance_claims"
- "company_id": as provided
- "statement_quarter": the quarter this was said in (as provided)
- "target_period": the future period being guided (e.g. "FY25", "Q3 FY24", "next 2 years")
- "metric_type": revpar|adr|occupancy|rooms_keys|revenue|ebitda_margin|capex|fnb_revenue|properties|debt|interest_coverage|other
- "guidance_value_point": single numeric value if stated (float or null)
- "guidance_value_low": lower bound of range (float or null)
- "guidance_value_high": upper bound of range (float or null)
- "unit": % | INR Cr | rooms | INR | bps | x | null
- "verbatim_quote": EXACT words from transcript — copy-paste, do not paraphrase
- "confidence_language": "will"|"expect"|"target"|"plan"|"aim"|"hope"|"intend"|"comfortable"|"guidance"
- "speaker": speaker name as provided
- "check_type": check_1_revpar|check_2_keys|check_3_driver|check_4_fnb|check_5_debt|check_6_supply|other
- "source_document": as provided
- "source_page": as provided (integer)
- "source_timestamp": timestamp if available (e.g. "12:41"), else null
- "period": statement_quarter as provided

Return a JSON array of guidance objects. If no guidance found, return [].
Return ONLY the JSON array. No explanation text."""


TABLE_ROW_SYSTEM = """You are extracting hotel-specific operational metrics from a table row in an Indian hotel company's Annual Report.
The table row is provided as a key-value dictionary.

IMPORTANT: ONLY extract hotel operational metrics. DO NOT extract P&L or Balance Sheet numbers.
In scope: RevPAR, ADR (Average Daily Rate), Occupancy %, F&B revenue share, room count, keys added, new properties
Out of scope: Revenue (INR Cr), EBITDA, PAT, Total Debt, ROCE, ROE — skip these

For each in-scope hotel ops metric found, return a JSON object with:
- "table": "financials"
- "metric": revpar|adr|occupancy|fnb_share|room_count|fnb_revenue|room_revenue|arr
- "value": numeric value (float)
- "unit": INR | % | rooms
- "period": the period this row represents (infer from row data or use provided period)
- "period_type": "quarterly" | "annual"
- "source_document": as provided
- "source_page": as provided (integer)
- "company_id": as provided
- "period_label": human-readable period label

If row has no hotel ops metrics, return [].
Return ONLY a JSON array."""


# ─────────────────────────────────────────────────────────────────
# LLM CALL WITH RETRY
# ─────────────────────────────────────────────────────────────────

def call_gemma(client: OpenAI, system_prompt: str, user_content: str,
               retries: int = 3, delay: float = 2.0) -> Optional[str]:
    """Call Gemma with retry on failure. Returns raw response text."""
    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=GEMMA_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.1,
                max_tokens=2048,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"  [Gemma] Attempt {attempt+1} failed: {e}")
            if attempt < retries - 1:
                time.sleep(delay * (attempt + 1))
    return None


def parse_json_response(raw: str) -> List[Dict]:
    """Robustly parse JSON from Gemma response (handles markdown code blocks)."""
    if not raw:
        return []
    # Strip markdown code fences
    raw = re.sub(r"```(?:json)?\s*", "", raw)
    raw = re.sub(r"```\s*", "", raw)
    raw = raw.strip()
    # Find the JSON array
    start = raw.find("[")
    end = raw.rfind("]")
    if start == -1 or end == -1:
        return []
    try:
        return json.loads(raw[start:end+1])
    except json.JSONDecodeError as e:
        print(f"  [Parser] JSON decode error: {e}")
        return []


# ─────────────────────────────────────────────────────────────────
# SUPABASE ROUTERS
# ─────────────────────────────────────────────────────────────────

TABLE_NAME_MAP = {
    "HOTEL_OPS_METRIC": "financials",
    "hotel_ops_metric": "financials",
    "FINANCIAL_METRIC": "financials",
    "financial_metric": "financials",
    "GUIDANCE_CLAIM": "guidance_claims",
    "guidance_claim": "guidance_claims",
    "RISK_FLAG": "risk_flags",
    "risk_flag": "risk_flags",
    "CREDIT_RATING": "credit_ratings",
    "credit_rating": "credit_ratings",
    "RAW_DATA": "raw_data",
}


def route_to_supabase(supabase: Client, items: List[Dict]) -> Dict[str, int]:
    """Route extracted items to the correct Supabase table."""
    counts = {"financials": 0, "guidance_claims": 0, "risk_flags": 0,
              "raw_data": 0, "credit_ratings": 0, "errors": 0}

    for item in items:
        table = TABLE_NAME_MAP.get(item.get("table"), item.get("table"))
        item["table"] = table
        if table not in counts:
            counts["errors"] += 1
            continue

        # Build the row for each table
        try:
            row = build_row(item, table)
            if row:
                supabase.table(table).insert(row).execute()
                counts[table] += 1
        except Exception as e:
            print(f"  [Supabase] Insert error ({table}): {e}")
            counts["errors"] += 1

    return counts


def build_row(item: Dict, table: str) -> Optional[Dict]:
    """Build a clean row dict for the given Supabase table."""
    base = {
        "company_id": item.get("company_id"),
        "source_document": item.get("source_document"),
        "source_page": item.get("source_page"),
    }
    if not base["company_id"] or not base["source_document"]:
        return None

    if table == "financials":
        val = item.get("value")
        if val is None:
            return None
        try:
            val = float(val)
        except (TypeError, ValueError):
            return None
        return {
            **base,
            "period": item.get("period"),
            "metric": item.get("metric", "unknown"),
            "value": val,
            "unit": item.get("unit"),
            "yoy_change": item.get("yoy_change"),
            "period_type": item.get("period_type", "annual"),
            "period_label": item.get("period_label") or item.get("period"),
        }

    if table == "guidance_claims":
        quote = item.get("verbatim_quote", "").strip()
        if not quote:
            return None
        return {
            **base,
            "statement_quarter": item.get("statement_quarter") or item.get("period"),
            "target_period": item.get("target_period"),
            "metric_type": item.get("metric_type", "other"),
            "guidance_value_low": _safe_float(item.get("guidance_value_low")),
            "guidance_value_high": _safe_float(item.get("guidance_value_high")),
            "guidance_value_point": _safe_float(item.get("guidance_value_point")),
            "unit": item.get("unit"),
            "verbatim_quote": quote,
            "confidence_language": item.get("confidence_language"),
            "speaker": item.get("speaker"),
            "check_type": item.get("check_type"),
            "source_timestamp": item.get("source_timestamp"),
        }

    if table == "risk_flags":
        desc = item.get("description", "").strip()
        if not desc:
            return None
        return {
            **base,
            "period": item.get("period"),
            "category": item.get("category", "operational"),
            "subcategory": item.get("subcategory"),
            "description": desc,
            "severity": item.get("severity", "medium"),
            "verbatim_quote": item.get("verbatim_quote"),
            "check_type": item.get("check_type"),
        }

    if table == "credit_ratings":
        agency = item.get("rating_agency", "").strip()
        if not agency:
            return None
        return {
            **base,
            "period": item.get("period"),
            "rating_agency":         agency,
            "rating_scale":          item.get("rating_scale"),
            "rating_outlook":        item.get("rating_outlook"),
            "instrument":            item.get("instrument"),
            "rating_date":           item.get("rating_date"),
            "rating_amount_crores":  _safe_float(item.get("rating_amount_crores")),
            "previous_rating":       item.get("previous_rating"),
            "watch_status":          item.get("watch_status"),
            "rationale":             item.get("rationale"),
        }

    if table == "raw_data":
        content = item.get("value_text", "").strip()
        if not content:
            return None
        return {
            **base,
            "period": item.get("period"),
            "data_type": item.get("data_type", "qualitative"),
            "category": item.get("category", "other"),
            "key_name": item.get("key_name"),
            "value_text": content,
            "value_numeric": _safe_float(item.get("value_numeric")),
            "context": item.get("context"),
        }

    return None


def _safe_float(val) -> Optional[float]:
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


# ─────────────────────────────────────────────────────────────────
# PRE-FILTER: Skip boilerplate chunks BEFORE calling LLM
# ─────────────────────────────────────────────────────────────────

SKIP_KEYWORDS = [
    "registered office", "cin:", "company secretary", "statutory auditor",
    "notice is hereby given", "proxy form", "attendance slip",
    "board of directors" , "corporate information",
    "din:", "icai membership", "chartered accountant",
    "independent auditor", "balance sheet abstract",
    "form aoc", "form mgt", "secretarial audit",
    "related party transaction", "managerial remuneration",
    "composition of committees", "number of meetings",
    "details of remuneration", "place: mumbai", "place: new delhi",
    "(rupees in", "schedule forming", "cash flow statement",
    "significant accounting", "deferred tax",
]

SIGNAL_KEYWORDS = [
    "revpar", "adr", "occupancy", "average daily rate",
    "room night", "f&b", "fnb", "food and beverage",
    "guidance", "target", "expect", "outlook", "will ", "plan to",
    "aim to", "intend", "vision", "strategy", "expansion",
    "new hotel", "new propert", "pipeline", "key addition",
    "rooms under", "management contract", "asset light",
    "crisil", "icra", "care", "fitch", "moody",
    "credit rating", "rating", "upgrade", "downgrade",
    "risk", "concern", "challenge", "threat", "headwind",
    "debt", "borrowing", "leverage", "interest coverage",
    "chairman", "managing director", "ceo", "letter to",
    "brand", "sustainability", "esg", "market share",
    "revenue per", "margin", "growth", "capex",
]


def is_high_signal_chunk(chunk_text: str) -> bool:
    """Return True if this chunk is worth sending to LLM."""
    text = chunk_text.lower()
    # Skip if matches boilerplate
    skip_score = sum(1 for kw in SKIP_KEYWORDS if kw in text)
    if skip_score >= 3:
        return False
    # Keep if matches signal keywords
    signal_score = sum(1 for kw in SIGNAL_KEYWORDS if kw in text)
    return signal_score >= 1


# ─────────────────────────────────────────────────────────────────
# BATCH: Combine multiple chunks into one LLM call
# ─────────────────────────────────────────────────────────────────

def build_batched_user_msg(chunks: List[Dict], prompt_type: str = "annual") -> str:
    """Combine up to CHUNKS_PER_BATCH chunks into one user message."""
    parts = []
    for i, chunk in enumerate(chunks):
        if prompt_type == "annual":
            parts.append(
                f"--- CHUNK {i+1} ---\n"
                f"Company: {chunk['company_id']}\n"
                f"Document: {chunk['source_document']}\n"
                f"Page: {chunk['source_page']}\n"
                f"Section: {chunk.get('section_name', 'unknown')}\n"
                f"Period: {chunk['period']}\n\n"
                f"{chunk['chunk_text']}\n"
            )
        else:  # transcript
            parts.append(
                f"--- CHUNK {i+1} ---\n"
                f"Company: {chunk['company_id']}\n"
                f"Quarter: {chunk['period']}\n"
                f"Speaker: {chunk.get('speaker', 'Unknown')} ({chunk.get('speaker_title') or 'Management'})\n"
                f"Document: {chunk['source_document']}\n"
                f"Page: {chunk['source_page']}\n\n"
                f"{chunk['chunk_text']}\n"
            )
    return "\n".join(parts)


def process_one_batch(client: OpenAI, system_prompt: str, chunks: List[Dict],
                      prompt_type: str = "annual") -> List[Dict]:
    """Process a batch of chunks in one LLM call. Returns extracted items with metadata."""
    user_msg = build_batched_user_msg(chunks, prompt_type)
    raw = call_gemma(client, system_prompt, user_msg)
    items = parse_json_response(raw)

    # Inject metadata — match items to their source chunk via source_page
    page_to_chunk = {c["source_page"]: c for c in chunks}
    for item in items:
        pg = item.get("source_page")
        src_chunk = page_to_chunk.get(pg, chunks[0])  # fallback to first chunk
        item.setdefault("company_id", src_chunk["company_id"])
        item.setdefault("source_document", src_chunk["source_document"])
        item.setdefault("source_page", src_chunk["source_page"])
        item.setdefault("period", src_chunk["period"])
        if prompt_type == "transcript":
            item.setdefault("speaker", src_chunk.get("speaker"))
            item.setdefault("source_timestamp", src_chunk.get("source_timestamp"))
            item.setdefault("statement_quarter", src_chunk["period"])
            item["table"] = "guidance_claims"

    return items


# ─────────────────────────────────────────────────────────────────
# PARALLEL BATCH PROCESSORS
# ─────────────────────────────────────────────────────────────────

def process_annual_report_chunks(
    text_chunks: List[Dict],
    table_rows: List[Dict],
    dry_run: bool = False,
) -> Dict[str, int]:
    """
    Process Annual Report chunks: pre-filter → batch → parallel LLM → Supabase.
    """
    client = get_llm_client()
    supabase = get_supabase_client() if not dry_run else None
    total_counts = {"financials": 0, "guidance_claims": 0, "risk_flags": 0,
                    "raw_data": 0, "credit_ratings": 0, "errors": 0, "skipped": 0}

    # ── Pre-filter ────────────────────────────────────────────────
    filtered = [c for c in text_chunks if is_high_signal_chunk(c["chunk_text"])]
    skipped = len(text_chunks) - len(filtered)
    total_counts["skipped"] = skipped
    print(f"\n[Gemma Extractor] Annual Report")
    print(f"  Total chunks: {len(text_chunks)} → After filter: {len(filtered)} (skipped {skipped} boilerplate)")

    # ── Build batches of CHUNKS_PER_BATCH ─────────────────────────
    batches = [filtered[i:i+CHUNKS_PER_BATCH] for i in range(0, len(filtered), CHUNKS_PER_BATCH)]
    print(f"  API calls needed: {len(batches)} (batched {CHUNKS_PER_BATCH}/call, {MAX_WORKERS} parallel)")

    # ── Process in parallel ───────────────────────────────────────
    all_items = []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(process_one_batch, client, ANNUAL_REPORT_SYSTEM, batch, "annual"): idx
            for idx, batch in enumerate(batches)
        }
        done = 0
        for future in as_completed(futures):
            try:
                items = future.result()
                all_items.extend(items)
                done += 1
                if done % 5 == 0 or done == len(batches):
                    elapsed = time.time() - t0
                    print(f"  Progress: {done}/{len(batches)} batches ({elapsed:.0f}s)")
            except Exception as e:
                print(f"  [Error] Batch failed: {e}")
                total_counts["errors"] += 1

    # ── Also process table rows (few, sequential is fine) ─────────
    for row in table_rows:
        user_msg = (
            f"Company: {row['company_id']}\n"
            f"Document: {row['source_document']}\n"
            f"Page: {row['source_page']}\n"
            f"Period: {row['period']}\n\n"
            f"TABLE ROW:\n{json.dumps(row['data'], indent=2)}"
        )
        raw = call_gemma(client, TABLE_ROW_SYSTEM, user_msg)
        items = parse_json_response(raw)
        for item in items:
            item.setdefault("company_id", row["company_id"])
            item.setdefault("source_document", row["source_document"])
            item.setdefault("source_page", row["source_page"])
            item.setdefault("period", row["period"])
        all_items.extend(items)

    # ── Route to Supabase ─────────────────────────────────────────
    if dry_run:
        for item in all_items:
            tbl = TABLE_NAME_MAP.get(item.get("table"), item.get("table"))
            snippet = item.get("verbatim_quote") or item.get("value_text") or item.get("description") or str(item.get("value", ""))
            print(f"  [DRY RUN] {tbl}: {snippet[:120]}")
    else:
        counts = route_to_supabase(supabase, all_items)
        for k, v in counts.items():
            total_counts[k] = total_counts.get(k, 0) + v

    elapsed = time.time() - t0
    print(f"\n[Gemma Extractor] Done in {elapsed:.0f}s. Items: {len(all_items)} | Stored: {total_counts}")
    return total_counts


def process_transcript_chunks(
    mgmt_chunks: List[Dict],
    dry_run: bool = False,
) -> Dict[str, int]:
    """
    Process transcript management chunks: batch → parallel LLM → guidance_claims.
    """
    client = get_llm_client()
    supabase = get_supabase_client() if not dry_run else None
    total_counts = {"guidance_claims": 0, "errors": 0}

    batches = [mgmt_chunks[i:i+CHUNKS_PER_BATCH] for i in range(0, len(mgmt_chunks), CHUNKS_PER_BATCH)]
    print(f"\n[Gemma Extractor] Transcript — {len(mgmt_chunks)} chunks → {len(batches)} batched calls ({MAX_WORKERS} parallel)")

    all_items = []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(process_one_batch, client, TRANSCRIPT_SYSTEM, batch, "transcript"): idx
            for idx, batch in enumerate(batches)
        }
        done = 0
        for future in as_completed(futures):
            try:
                items = future.result()
                all_items.extend(items)
                done += 1
                if done % 5 == 0 or done == len(batches):
                    print(f"  Progress: {done}/{len(batches)} batches")
            except Exception as e:
                print(f"  [Error] Batch failed: {e}")
                total_counts["errors"] += 1

    if dry_run:
        for item in all_items:
            print(f"  [DRY RUN] guidance: {item.get('verbatim_quote', '')[:120]}")
    else:
        counts = route_to_supabase(supabase, all_items)
        total_counts["guidance_claims"] += counts.get("guidance_claims", 0)
        total_counts["errors"] += counts.get("errors", 0)

    elapsed = time.time() - t0
    print(f"\n[Gemma Extractor] Done in {elapsed:.0f}s. Guidance claims: {total_counts['guidance_claims']}")
    return total_counts
