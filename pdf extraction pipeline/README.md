# PDF Extraction Pipeline

Ingestion pipeline that extracts cited facts from PDFs and writes to Supabase.
Install dependencies and run a single PDF:

```bash
pip install -r requirements.txt
python run_pipeline.py --file <path> --company <CODE> --type <annual_report|transcript> --period <FYxx|QxFYxx>
```
