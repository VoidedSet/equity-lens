# AWS Console & Local Toolchain Setup Guide

Use this checklist to configure your AWS account, IAM credentials, S3 lakehouse, Amazon Bedrock model access, Glue/Athena, and Supabase migrations so the code on `feat/aws-cloud-pipeline` can run against real AWS services.

---

## 1. Billing Guardrail (Do This First)

1. Sign in to the AWS Console as your root or billing-admin user and open **Billing and Cost Management** → **Budgets**.
2. Click **Create budget** → **Use a template (simplified)** → **Monthly cost budget**.
3. Set a budget amount (e.g., `$10` or `$25`), add your email address for alerts at `50%`, `80%`, and `100%` actual/forecasted spend, and save.
4. Keep Glue jobs on **Glue `5.0` / `G.1X` / `2` workers** (configured in [lakehouse_stack.py](../../cloud/infra/lakehouse_stack.py)) to minimize DPU-minute cost.

---

## 2. IAM User, Access Keys & AWS CLI v2

Never generate access keys on the AWS root user. Create a dedicated IAM developer user instead:

1. Open **IAM** → **Users** → **Create user** → name it `equity-lens-dev`.
2. Choose **Attach policies directly** and grant permissions needed across Phases 1–8 (for a personal dev account, you can scope custom policies or temporarily attach managed policies for **S3**, **AmazonBedrockFullAccess**, **AWSGlueConsoleFullAccess**, **AmazonAthenaFullAccess**, **AWSCloudFormationFullAccess**, **AmazonECS_FullAccess**, **AWSStepFunctionsFullAccess**, **SecretsManagerReadWrite**, and **IAMFullAccess** for CDK role creation, then tighten before production).
3. Open the newly created `equity-lens-dev` user → **Security credentials** → **Access keys** → **Create access key**.
4. Select **Application running outside AWS** (or **Command Line Interface (CLI)**), confirm, and **download the `.csv`** or copy the **Access key ID** and **Secret access key**.
5. Install AWS CLI v2 on Windows PowerShell and configure a named profile:

```powershell
winget install Amazon.AWSCLI
aws --version

aws configure --profile equity-lens
# AWS Access Key ID: <paste access key>
# AWS Secret Access Key: <paste secret key>
# Default region name: ap-south-1
# Default output format: json

# Tell current shell (or add AWS_PROFILE=equity-lens to cloud/.env / PowerShell)
$env:AWS_PROFILE = "equity-lens"
aws sts get-caller-identity
```

---

## 3. S3 Data Lake Bucket

You can either let AWS CDK create the bucket in Step 5 or create it manually first:

1. Open **S3** → **Create bucket** in **Asia Pacific (Mumbai) `ap-south-1`**.
2. Bucket name: `equity-lens-datalake-<your-12-digit-account-id>-dev` (globally unique lowercase).
3. Keep **Block all public access** enabled and **Server-side encryption with Amazon S3 managed keys (SSE-S3)** enabled.
4. *(Optional)* Under **Management** → **Lifecycle rules**, add a rule expiring objects under prefix `athena-results/` after `30` days.
5. Once configured, test raw upload from your local machine:

```powershell
# Set STORAGE_BACKEND=s3 and S3_BUCKET=equity-lens-datalake-<account-id>-dev in cloud/.env
python -m cloud.ingest.upload_raw --source-dir "Data Ingestion/extracted_json" --dry-run
python -m cloud.ingest.upload_raw --source-dir "Data Ingestion/extracted_json"
```

---

## 4. Amazon Bedrock Model Access

1. Open **Amazon Bedrock** in the AWS Console.
2. Check **Model access** (or **Model catalog** → **Modify model access**) in `ap-south-1`.
   - Note that Bedrock model availability varies by region—if **Gemma** (`google.gemma-3-27b-it`) is unavailable in `ap-south-1`, switch the Console region to `us-east-1` or `us-west-2` and enable either Gemma or a fallback such as **Meta Llama 3.3 70B Instruct** (`meta.llama3-3-70b-instruct-v1:0`) or **Amazon Nova**.
3. Copy the exact **Model ID** and the region where you enabled it into `cloud/.env`:

```dotenv
LLM_PROVIDER=bedrock
BEDROCK_REGION=ap-south-1   # or us-east-1 if enabled there
BEDROCK_MODEL_ID=google.gemma-3-27b-it
```

4. Test a single document against Bedrock after uploading raw manifests:

```powershell
python -m cloud.worker.process_document --doc-id <64-char-doc-id>
```

---

## 5. AWS Glue, CDK Deployment & Amazon Athena

### Option A — Deploy via AWS CDK (Recommended)

```powershell
npm install -g aws-cdk
python -m pip install -r cloud/infra/requirements.txt

cd cloud/infra
cdk bootstrap aws://<account-id>/ap-south-1
cdk deploy
cd ../..
```

Then package `cloud/` and upload Glue scripts to S3:

```powershell
Compress-Archive -Path cloud -DestinationPath cloud_pkg.zip -Force
aws s3 cp cloud_pkg.zip s3://<bucket>/scripts/cloud_pkg.zip
aws s3 cp cloud/glue_jobs/ s3://<bucket>/scripts/glue_jobs/ --recursive
```

### Option B — Manual Console Setup for Athena

1. Open **Amazon Athena** → **Query editor** → **Settings** → **Manage**.
2. Set **Location of query result** to `s3://<bucket>/athena-results/` (or select workgroup `equity-lens-analytics-dev` if deployed via CDK).
3. Run [cloud/athena/ddl/00_database.sql](../../cloud/athena/ddl/00_database.sql) to create database `equity_lens`.
4. Open [cloud/athena/ddl/01_curated_tables.sql](../../cloud/athena/ddl/01_curated_tables.sql), replace every `${S3_BUCKET}` with your bucket name, and run it in Athena Query Editor. Because all 8 tables use **Partition Projection**, queries work immediately without waiting for Glue Crawlers.
5. Run [cloud/athena/queries/01_cross_company_financials.sql](../../cloud/athena/queries/01_cross_company_financials.sql) to verify curated Parquet reads.

---

## 6. Supabase Idempotency Migration & Secret Rotation

1. **Rotate previously committed credentials:** In your Supabase Dashboard, Featherless AI Dashboard, and Groq Console, rotate the old keys that were previously committed in `misc/` prior to Phase 0 cleanup.
2. **Apply the Phase 6 SQL migration:** Open **Supabase Dashboard** → **SQL Editor**, paste [cloud/sql/001_idempotency.sql](../../cloud/sql/001_idempotency.sql), and execute it. This seeds `JUNIPER` in `companies` and creates unique `record_id` / `chunk_id` indexes.
3. **Configure `cloud/.env`:** Copy [cloud/.env.example](../../cloud/.env.example) to `cloud/.env` (gitignored) and fill in `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `S3_BUCKET`, `BEDROCK_REGION`, and `BEDROCK_MODEL_ID`.
4. *(For Phase 7 ECS)* Store `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` in **AWS Secrets Manager** under a secret such as `equity-lens/supabase`.
5. Run idempotent sync:

```powershell
python -m cloud.sync.supabase_sync --dry-run
python -m cloud.sync.supabase_sync
```

---

## 7. Local Python 3.11 + Docker Toolchain (For Local Spark & Phase 7)

AWS Glue `5.0` runs Spark `3.5` on **Python 3.11** (PySpark `3.5` does not support Python `3.13`). Before running local Spark (`--engine spark`) or container builds:

```powershell
# 1. Install Python 3.11 alongside Python 3.13
winget install Python.Python.3.11

# 2. Create dedicated cloud virtual environment
py -3.11 -m venv .venv-cloud
.\.venv-cloud\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r cloud/requirements.txt

# 3. Install Docker Desktop (required for Phase 7 ECS container image builds)
winget install Docker.DockerDesktop
```
