"""Step Functions Lambda handler: list pending ('raw' or 'failed') document manifests."""

from typing import Any, Dict, List, Optional

from cloud.common.companies import normalize_company_id
from cloud.common.config import get_config
from cloud.common.manifest import ManifestStore
from cloud.common.storage import StorageBackend, get_storage


def handler(
    event: Optional[Dict[str, Any]],
    context: Any,
    storage: Optional[StorageBackend] = None,
) -> Dict[str, Any]:
    """Return pending doc_ids matching statuses/company filter for Step Functions Map state."""
    payload = event or {}
    statuses = tuple(payload.get("statuses") or ("raw", "failed"))
    raw_company = payload.get("company_id")
    company_filter = normalize_company_id(str(raw_company)) if raw_company else None
    max_docs = int(payload.get("max_docs") or 0)
    force_curate = bool(payload.get("force_curate", False))

    store = storage or get_storage(get_config())
    manifests = ManifestStore(store)

    doc_ids: List[str] = [
        m.doc_id
        for m in manifests.list_manifests(company_id=company_filter)
        if m.status in statuses
    ]
    if max_docs > 0:
        doc_ids = doc_ids[:max_docs]

    return {
        "doc_ids": doc_ids,
        "count": len(doc_ids),
        "force_curate": force_curate,
    }
