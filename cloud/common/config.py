"""Environment-driven configuration for EquityLens AI cloud pipelines."""

import json
import os
from pathlib import Path
from typing import Literal, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[2]


class CloudConfig(BaseModel):
    """Typed runtime configuration supporting both local and AWS execution."""

    storage_backend: Literal["local", "s3"] = "local"
    local_datalake_dir: Path = Field(default_factory=lambda: REPO_ROOT / "local_datalake")
    s3_bucket: str = "equity-lens-datalake-dev"
    aws_region: str = "ap-south-1"
    bedrock_region: str = "ap-south-1"

    llm_provider: Literal["featherless", "bedrock", "mock"] = "featherless"
    bedrock_model_id: str = "google.gemma-3-27b-it"
    featherless_api_key: Optional[str] = None
    featherless_base_url: str = "https://api.featherless.ai/v1"
    gemma_model: str = "google/gemma-3-27b-it"

    sink: Literal["s3", "supabase", "none"] = "s3"
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384
    chunk_chars: int = 3000
    chunk_overlap_chars: int = 400
    chunks_per_batch: int = 5

    supabase_url: Optional[str] = None
    supabase_service_key: Optional[str] = None

    def to_masked_dict(self) -> dict:
        """Return config dictionary with secrets masked for safe logging."""
        data = self.model_dump(mode="json")
        for secret_field in ("featherless_api_key", "supabase_service_key"):
            data[secret_field] = "***" if data.get(secret_field) else None
        return data


def _load_env_files() -> None:
    """Load root .env and cloud/.env without overriding already-set process env vars."""
    for candidate in (REPO_ROOT / ".env", REPO_ROOT / "cloud" / ".env"):
        if candidate.exists():
            load_dotenv(dotenv_path=candidate, override=False)


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return int(raw.strip())


def get_config() -> CloudConfig:
    """Construct a CloudConfig instance from environment variables."""
    _load_env_files()

    aws_region = os.getenv("AWS_REGION", "ap-south-1").strip() or "ap-south-1"
    bedrock_region = os.getenv("BEDROCK_REGION", aws_region).strip() or aws_region

    local_dir_raw = os.getenv("LOCAL_DATALAKE_DIR", "").strip()
    local_dir = Path(local_dir_raw) if local_dir_raw else (REPO_ROOT / "local_datalake")
    if not local_dir.is_absolute():
        local_dir = (REPO_ROOT / local_dir).resolve()

    return CloudConfig(
        storage_backend=os.getenv("STORAGE_BACKEND", "local").strip().lower(),  # type: ignore[arg-type]
        local_datalake_dir=local_dir,
        s3_bucket=os.getenv("S3_BUCKET", "equity-lens-datalake-dev").strip(),
        aws_region=aws_region,
        bedrock_region=bedrock_region,
        llm_provider=os.getenv("LLM_PROVIDER", "featherless").strip().lower(),  # type: ignore[arg-type]
        bedrock_model_id=os.getenv("BEDROCK_MODEL_ID", "google.gemma-3-27b-it").strip(),
        featherless_api_key=os.getenv("FEATHERLESS_API_KEY") or None,
        featherless_base_url=os.getenv(
            "FEATHERLESS_BASE_URL",
            os.getenv("LLM_BASE_URL", "https://api.featherless.ai/v1"),
        ).strip(),
        gemma_model=os.getenv(
            "GEMMA_MODEL",
            os.getenv("LLM_MODEL", "google/gemma-3-27b-it"),
        ).strip(),
        sink=os.getenv("SINK", "s3").strip().lower(),  # type: ignore[arg-type]
        embedding_model=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2").strip(),
        embedding_dim=_int_env("EMBEDDING_DIM", 384),
        chunk_chars=_int_env("CHUNK_CHARS", 3000),
        chunk_overlap_chars=_int_env("CHUNK_OVERLAP_CHARS", 400),
        chunks_per_batch=_int_env("CHUNKS_PER_BATCH", 5),
        supabase_url=os.getenv("SUPABASE_URL") or None,
        supabase_service_key=os.getenv("SUPABASE_SERVICE_KEY") or None,
    )


if __name__ == "__main__":
    print(json.dumps(get_config().to_masked_dict(), indent=2))
