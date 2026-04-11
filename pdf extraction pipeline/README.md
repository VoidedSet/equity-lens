# EquityLens AI — PDF Extraction Pipeline

Extracts CEO statements, management guidance, operational metrics, and risk flags from Indian hotel company Annual Reports and Earnings Call Transcripts. Every fact stored with `[Document | Page | Period]` citations in Supabase.

---

## Setup (do this first)

### 1. Install dependencies

> Requires Python 3.10+. Install Ghostscript first (needed by camelot):
> - Windows: https://www.ghostscript.com/releases/gsdnld.html → download & install, add to PATH

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
copy .env.example .env
```

Edit `.env` and fill in:
- `FEATHERLESS_API_KEY` — from https://featherless.ai
- `SUPABASE_URL` — from your Supabase project settings
- `SUPABASE_SERVICE_KEY` — **Service Role** key (not anon key) from Supabase settings

### 3. Deploy Supabase schema

Go to your Supabase project → **SQL Editor** → paste and run the entire contents of `schema.sql`.

This creates all 8 tables + pgvector function + inserts 5 companies.

---

## Folder structure for PDFs

Place your PDFs in the `data/` folder:

```
data/
├── IHCL/
│   ├── IHCL_FY24_AR.pdf
│   ├── IHCL_Q1FY24_transcript.pdf
│   ├── IHCL_Q2FY24_transcript.pdf
│   ├── IHCL_Q3FY24_transcript.pdf
│   └── IHCL_Q4FY24_transcript.pdf
├── CHALET/
├── LEMONTREE/
├── EIH/
├── ITCHOTELS/
└── industry/
    └── TO-Oct2025.pdf
```

---

## Usage

### Process an Annual Report
```bash
python run_pipeline.py --file data/IHCL/IHCL_FY24_AR.pdf --company IHCL --type annual_report --period FY24
```

### Process an Earnings Call Transcript
```bash
python run_pipeline.py --file data/IHCL/IHCL_Q2FY24_transcript.pdf --company IHCL --type transcript --period Q2FY24
```

### Test without writing to Supabase (dry run)
```bash
python run_pipeline.py --file data/IHCL/IHCL_FY24_AR.pdf --company IHCL --type annual_report --period FY24 --dry-run
```

### Skip Gemma, only embed chunks (useful if LLM extraction already done)
```bash
python run_pipeline.py --file data/IHCL/IHCL_FY24_AR.pdf --company IHCL --type annual_report --period FY24 --skip-llm
```

---

## What gets extracted

| Source | Extracted → Table |
|---|---|
| Annual Report — ops tables | RevPAR, ADR, Occupancy, F&B share, room count → `financials` |
| Annual Report — MD&A text | CEO statements, forward guidance → `guidance_claims` |
| Annual Report — Risk Factors | Debt concerns, governance flags → `risk_flags` |
| Annual Report — Notes to FS | Debt breakdown, interest costs → `financials` + `risk_flags` |
| Annual Report — all sections | Qualitative insights → `raw_data` |
| Transcript — management blocks | Every guidance promise with verbatim quote + timestamp → `guidance_claims` |
| All text chunks | Embeddings for Q&A RAG → `document_chunks` |

---

## Pipeline files

| File | Role |
|---|---|
| `schema.sql` | Full Supabase schema — run once in SQL Editor |
| `config.py` | API keys, company IDs, chunking config |
| `pdf_extractor.py` | pdfplumber + TOC section detection + table extraction |
| `transcript_parser.py` | Speaker-aware chunker for earnings call transcripts |
| `gemma_extractor.py` | Gemma 3 27B-IT extraction + routing to Supabase tables |
| `embedder.py` | all-MiniLM-L6-v2 → 384-dim vectors → document_chunks |
| `run_pipeline.py` | CLI orchestrator — run this for each PDF |

---

## Recommended processing order (per company)

1. Annual Reports FY22 → FY24 (historical financials baseline)
2. Quarterly Transcripts Q1FY24 → Q4FY24 (guidance claims by quarter)
3. Run `06_deviation_computer.py` (separate script — computes BEAT/MISS/IN-LINE)

Priority companies for demo: **IHCL first**, then **Lemon Tree** (strongest contrast).
