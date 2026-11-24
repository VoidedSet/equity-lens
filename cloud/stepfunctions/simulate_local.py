"""Local parallel Step Functions simulator executing Map workers, barrier, curation, and sync."""

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional, Sequence

from cloud.common.config import CloudConfig, get_config
from cloud.common.llm import LLMProvider
from cloud.common.manifest import ManifestStore
from cloud.common.storage import StorageBackend, get_storage
from cloud.glue_jobs import run_local
from cloud.stepfunctions import list_pending, mark_quarantined
from cloud.sync.supabase_sync import sync_curated_to_supabase
from cloud.worker.process_document import process_document


def run_pipeline_local(
    storage: StorageBackend,
    config: Optional[CloudConfig] = None,
    max_concurrency: int = 4,
    company_id: Optional[str] = None,
    max_docs: Optional[int] = None,
    llm_provider: Optional[LLMProvider] = None,
    embed_fn: Optional[Callable[[Sequence[str]], List[List[float]]]] = None,
    skip_llm: bool = False,
    skip_embed: bool = False,
    sync_supabase: bool = False,
    supabase_client: Any = None,
    engine: str = "auto",
    force_curate: bool = False,
) -> Dict[str, Any]:
    """Mirror document_pipeline.asl.json locally using a bounded ThreadPoolExecutor."""
    cfg = config or get_config()
    pending = list_pending.handler(
        {
            "company_id": company_id,
            "max_docs": max_docs or 0,
            "force_curate": force_curate,
        },
        None,
        storage=storage,
    )

    doc_ids: List[str] = pending["doc_ids"]
    if not doc_ids and not force_curate:
        return {
            "status": "no_work",
            "pending": pending,
            "map_results": [],
            "curation": None,
            "sync": None,
        }

    def _run_one(doc_id: str) -> Dict[str, Any]:
        try:
            return process_document(
                doc_id=doc_id,
                storage=storage,
                manifests=ManifestStore(storage),
                config=cfg,
                llm_provider=llm_provider,
                embed_fn=embed_fn,
                skip_llm=skip_llm,
                skip_embed=skip_embed,
            )
        except Exception as exc:
            mark_quarantined.handler(
                {
                    "doc_id": doc_id,
                    "worker_error": {"Error": type(exc).__name__, "Cause": str(exc)},
                },
                None,
                storage=storage,
            )
            return {"doc_id": doc_id, "status": "quarantined", "error": str(exc)}

    map_results: List[Dict[str, Any]] = []
    if doc_ids:
        with ThreadPoolExecutor(max_workers=max(1, max_concurrency)) as pool:
            futures = {pool.submit(_run_one, did): did for did in doc_ids}
            for fut in as_completed(futures):
                map_results.append(fut.result())

    curation_summary = run_local.run_all(storage, engine=engine)

    sync_summary = None
    if sync_supabase:
        sync_summary = sync_curated_to_supabase(
            storage=storage,
            supabase_client=supabase_client,
            config=cfg,
        )

    return {
        "status": "succeeded",
        "pending": pending,
        "map_results": sorted(map_results, key=lambda r: r.get("doc_id", "")),
        "curation": curation_summary,
        "sync": sync_summary,
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Simulate Step Functions document pipeline locally.")
    parser.add_argument("--max-concurrency", type=int, default=4)
    parser.add_argument("--company", default=None)
    parser.add_argument("--max-docs", type=int, default=0)
    parser.add_argument("--skip-llm", action="store_true")
    parser.add_argument("--skip-embed", action="store_true")
    parser.add_argument("--sync-supabase", action="store_true")
    parser.add_argument("--force-curate", action="store_true")
    parser.add_argument("--engine", choices=["auto", "spark", "pyarrow"], default="auto")
    args = parser.parse_args(argv)

    cfg = get_config()
    storage = get_storage(cfg)
    result = run_pipeline_local(
        storage=storage,
        config=cfg,
        max_concurrency=args.max_concurrency,
        company_id=args.company,
        max_docs=args.max_docs or None,
        skip_llm=args.skip_llm,
        skip_embed=args.skip_embed,
        sync_supabase=args.sync_supabase,
        engine=args.engine,
        force_curate=args.force_curate,
    )
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
