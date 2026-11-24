"""Document manifest models and lifecycle store backed by StorageBackend."""

from datetime import datetime, timezone
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from cloud.common.storage import StorageBackend


def utc_now_iso() -> str:
    """Return ISO-8601 UTC timestamp string."""
    return datetime.now(timezone.utc).isoformat()


class DocumentManifest(BaseModel):
    """State record tracking a single raw source document through the lakehouse."""

    doc_id: str
    company_id: str
    source_type: Literal["pdf", "transcript_json", "extracted_json", "screener_csv"]
    doc_type: str
    period: str
    raw_key: str
    raw_uri: str
    filename: str
    content_sha256: str
    size_bytes: int
    status: Literal["raw", "processing", "processed", "failed"] = "raw"
    attempts: int = 0
    error_message: Optional[str] = None
    outputs: Dict[str, str] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)


class ManifestStore:
    """Reads and writes per-document JSON manifests under manifests/documents/."""

    PREFIX = "manifests/documents/"

    def __init__(self, storage: StorageBackend) -> None:
        self.storage = storage

    def key_for(self, doc_id: str) -> str:
        return f"{self.PREFIX}{doc_id}.json"

    def exists(self, doc_id: str) -> bool:
        return self.storage.exists(self.key_for(doc_id))

    def get(self, doc_id: str) -> Optional[DocumentManifest]:
        key = self.key_for(doc_id)
        if not self.storage.exists(key):
            return None
        return DocumentManifest.model_validate(self.storage.read_json(key))

    def save(self, manifest: DocumentManifest) -> DocumentManifest:
        manifest.updated_at = utc_now_iso()
        self.storage.write_json(self.key_for(manifest.doc_id), manifest.model_dump(mode="json"))
        return manifest

    def mark_processing(self, doc_id: str) -> DocumentManifest:
        manifest = self.get(doc_id)
        if manifest is None:
            raise FileNotFoundError(f"Manifest not found for doc_id={doc_id}")
        manifest.status = "processing"
        manifest.attempts += 1
        manifest.error_message = None
        return self.save(manifest)

    def mark_processed(self, doc_id: str, outputs: Dict[str, str]) -> DocumentManifest:
        manifest = self.get(doc_id)
        if manifest is None:
            raise FileNotFoundError(f"Manifest not found for doc_id={doc_id}")
        manifest.status = "processed"
        manifest.error_message = None
        manifest.outputs = {**manifest.outputs, **outputs}
        return self.save(manifest)

    def mark_failed(self, doc_id: str, error_message: str) -> DocumentManifest:
        manifest = self.get(doc_id)
        if manifest is None:
            raise FileNotFoundError(f"Manifest not found for doc_id={doc_id}")
        manifest.status = "failed"
        manifest.error_message = error_message[:2000]
        return self.save(manifest)

    def list_manifests(
        self,
        status: Optional[str] = None,
        company_id: Optional[str] = None,
    ) -> List[DocumentManifest]:
        items: List[DocumentManifest] = []
        for key in self.storage.list_keys(self.PREFIX):
            if not key.endswith(".json"):
                continue
            manifest = DocumentManifest.model_validate(self.storage.read_json(key))
            if status and manifest.status != status:
                continue
            if company_id and manifest.company_id != company_id:
                continue
            items.append(manifest)
        return items
