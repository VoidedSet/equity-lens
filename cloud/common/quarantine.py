"""Dead-letter / quarantine writer for failed documents and invalid LLM payloads."""

from typing import Any, Dict, Optional

from cloud.common.manifest import utc_now_iso
from cloud.common.storage import StorageBackend


class QuarantineWriter:
    """Persists error diagnostics and raw outputs under quarantine/<stage>/<doc_id>/."""

    def __init__(self, storage: StorageBackend) -> None:
        self.storage = storage

    def write(
        self,
        stage: str,
        doc_id: str,
        input_ref: Dict[str, Any],
        error: Dict[str, Any],
        raw_llm_output: Optional[str] = None,
    ) -> str:
        prefix = f"quarantine/{stage}/{doc_id}/"
        self.storage.write_json(f"{prefix}input_ref.json", input_ref)
        error_payload = {"recorded_at": utc_now_iso(), **error}
        self.storage.write_json(f"{prefix}error.json", error_payload)
        if raw_llm_output is not None:
            self.storage.write_text(f"{prefix}raw_llm_output.txt", raw_llm_output)
        return prefix
