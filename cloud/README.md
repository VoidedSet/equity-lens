# EquityLens AI — Cloud Lakehouse Package (`cloud/`)

This package implements the AWS Medallion lakehouse pipeline for EquityLens AI while keeping local development and offline testing first-class (`STORAGE_BACKEND=local`).

## Environment Setup

- **Runtime Note:** AWS Glue 5.0 uses Spark 3.5 on **Python 3.11** (PySpark 3.5 does not support Python 3.13). For PySpark / Glue work in Phase 4+, create a dedicated Python 3.11 virtual environment (`.venv-cloud/`) with Java 11 or 17.
- Core Phases 0–3 utilities and `unittest` checks run cleanly on Python 3.11–3.13.

```bash
# Copy configuration template (never commit cloud/.env)
cp cloud/.env.example cloud/.env

# Inspect resolved configuration (secrets masked)
python -m cloud.common.config

# Ingest local files to raw/ (or S3 when STORAGE_BACKEND=s3)
python -m cloud.ingest.upload_raw --source-dir "Data Ingestion/extracted_json"

# Process a single manifest document to processed/
python -m cloud.worker.process_document --doc-id <doc_id>

# Run offline unit tests
python -m unittest discover -s cloud/tests -v
```
