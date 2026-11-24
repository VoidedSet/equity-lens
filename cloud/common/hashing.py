"""Deterministic SHA-256 identifiers for documents, chunks, and fact records."""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict


def sha256_bytes(data: bytes) -> str:
    """Compute hex SHA-256 digest of raw bytes."""
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Compute hex SHA-256 digest of a file via streaming reads."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(chunk_size)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def make_doc_id(data: bytes) -> str:
    """Return content-addressed document ID from raw file bytes."""
    return sha256_bytes(data)


def make_chunk_id(doc_id: str, chunk_index: int) -> str:
    """Return deterministic chunk ID from document ID and chunk ordinal."""
    payload = f"{doc_id}|{chunk_index}".encode("utf-8")
    return sha256_bytes(payload)


def _normalize_value(value: Any) -> Any:
    if isinstance(value, str):
        return " ".join(value.strip().lower().split())
    if isinstance(value, dict):
        return {str(k).strip().lower(): _normalize_value(v) for k, v in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_normalize_value(v) for v in value]
    return value


def make_record_id(company_id: str, table: str, key_fields: Dict[str, Any]) -> str:
    """Return deterministic record ID for idempotent Spark/Supabase deduplication."""
    normalized = {
        "company_id": company_id.strip().upper(),
        "table": table.strip().lower(),
        "keys": _normalize_value(key_fields),
    }
    canonical = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256_bytes(canonical.encode("utf-8"))
