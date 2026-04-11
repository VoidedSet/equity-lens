import os
from dotenv import load_dotenv

load_dotenv()

# ── LLM Provider (Groq — fast + free) ──────────────────────────
FEATHERLESS_API_KEY = os.getenv("GROQ_API_KEY") or os.getenv("FEATHERLESS_API_KEY")
FEATHERLESS_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
GEMMA_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")

# ── Supabase ────────────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

# ── Companies ───────────────────────────────────────────────────
COMPANIES = ["IHCL", "CHALET", "LEMONTREE", "EIH", "ITCHOTELS"]

COMPANY_NAMES = {
    "IHCL":      "Indian Hotels Company Ltd",
    "CHALET":    "Chalet Hotels Ltd",
    "LEMONTREE": "Lemon Tree Hotels Ltd",
    "EIH":       "EIH Ltd (Oberoi Group)",
    "ITCHOTELS": "ITC Hotels Ltd",
}

# ── Chunking ────────────────────────────────────────────────────
CHUNK_CHARS = 3000       # ~800 tokens at ~3.7 chars/token
CHUNK_OVERLAP_CHARS = 400

# ── Embeddings ──────────────────────────────────────────────────
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

# ── Annual Report: sections worth extracting ────────────────────
HIGH_VALUE_SECTIONS = [
    "management discussion",
    "md&a",
    "management's discussion",
    "operations review",
    "operational review",
    "operational performance",
    "business overview",
    "financial review",
    "performance review",
    "risk factors",
    "risks and concerns",
    "key risks",
    "notes to financial",
    "notes to the financial",
    "notes to accounts",
    "chairman",
    "managing director",
    "director's report",
    "directors report",
    "hotel operations",
    "revenue breakdown",
    "key performance indicators",
    "kpi",
    "segmental",
    "segment",
    "capital expenditure",
    "debt",
    "borrowings",
]

# ── Transcript: management speaker patterns ──────────────────────
MGMT_SPEAKER_PATTERNS = [
    r"(MD|CEO|CFO|COO|CRO|Chairman|Managing Director|Chief Executive|Chief Financial)",
]

SKIP_SPEAKERS = ["operator", "moderator", "coordinator", "thank you"]
