"""Step Functions Lambda handler: mark failed documents and record quarantine diagnostics."""

import json
from typing import Any, Dict, Optional

from cloud.common.config import get_config
from cloud.common.manifest import ManifestStore
from cloud.common.quarantine import QuarantineWriter
from cloud.common.storage import StorageBackend, get_storage


def handler(
    event: Optional[Dict[str, Any]],
    context: Any,
    storage: Optional[StorageBackend] = None,
) -> Dict[str, Any]:
    """Transition manifest to 'failed' (if present) and persist Step Functions error payload."""
    payload = event or {}
    doc_id = str(payload.get("doc_id") or "").strip() or "unknown"
    worker_error = payload.get("worker_error")
    if isinstance(worker_error, dict):
        err_name = str(worker_error.get("Error") or "StepFunctionsTaskError")
        cause = str(worker_error.get("Cause") or "")
        message = f"{err_name}: {cause}" if cause else err_name
    else:
        message = json.dumps(worker_error, default=str) if worker_error else "Unknown Step Functions error"

    store = storage or get_storage(get_config())
    manifests = ManifestStore(store)
    if manifests.exists(doc_id):
        manifests.mark_failed(doc_id, message)

    QuarantineWriter(store).write(
        stage="stepfunctions",
        doc_id=doc_id,
        input_ref={"doc_id": doc_id, "event": payload},
        error={"message": message, "worker_error": worker_error},
    )

    return {"doc_id": doc_id, "status": "quarantined"}
