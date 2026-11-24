"""Unified ECS/Fargate container CLI entrypoint for document extraction, sync, and scorecards."""

import argparse
import json
import sys
from typing import Any, Callable, Dict, List, Optional, Sequence

from cloud.common.companies import normalize_company_id
from cloud.common.config import CloudConfig, get_config
from cloud.common.llm import LLMProvider
from cloud.common.manifest import ManifestStore
from cloud.common.storage import StorageBackend, get_storage
from cloud.sync.supabase_sync import sync_curated_to_supabase
from cloud.worker.process_document import _load_pipeline_module, process_document


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="EquityLens ECS/Fargate Worker Entrypoint")
    parser.add_argument(
        "--mode",
        required=True,
        choices=["process_document", "supabase_sync", "scorecard", "list_pending"],
        help="Execution mode for the worker container.",
    )
    parser.add_argument("--doc-id", default="", help="Document SHA-256 ID (process_document mode).")
    parser.add_argument("--force", action="store_true", help="Re-process even if already processed.")
    parser.add_argument("--skip-llm", action="store_true", help="Skip LLM extraction.")
    parser.add_argument("--skip-embed", action="store_true", help="Skip embedding generation.")
    parser.add_argument("--tables", default="", help="Comma-separated tables for supabase_sync mode.")
    parser.add_argument("--batch-size", type=int, default=200, help="Upsert batch size for supabase_sync.")
    parser.add_argument("--dry-run", action="store_true", help="Dry-run without DB writes.")
    parser.add_argument("--company", default="ALL", help="Company ID/alias or ALL.")
    parser.add_argument("--max-docs", type=int, default=0, help="Optional max documents for list_pending.")
    return parser


def run_mode(
    mode: str,
    args: argparse.Namespace,
    storage: Optional[StorageBackend] = None,
    config: Optional[CloudConfig] = None,
    llm_provider: Optional[LLMProvider] = None,
    embed_fn: Optional[Callable[[Sequence[str]], List[List[float]]]] = None,
    supabase_client: Any = None,
) -> Dict[str, Any]:
    """Execute one worker mode cleanly with optional dependency overrides for testing."""
    cfg = config or get_config()
    store = storage or get_storage(cfg)

    if mode == "process_document":
        if not args.doc_id:
            raise ValueError("--doc-id is required when --mode=process_document")
        manifests = ManifestStore(store)
        return process_document(
            doc_id=args.doc_id,
            storage=store,
            manifests=manifests,
            config=cfg,
            llm_provider=llm_provider,
            embed_fn=embed_fn,
            force=args.force,
            skip_llm=args.skip_llm,
            skip_embed=args.skip_embed,
        )

    if mode == "supabase_sync":
        tables_list = [t.strip() for t in (args.tables or "").split(",") if t.strip()] or None
        return sync_curated_to_supabase(
            storage=store,
            supabase_client=supabase_client,
            config=cfg,
            tables=tables_list,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
        )

    if mode == "scorecard":
        scorecard_computer = _load_pipeline_module("scorecard_computer")
        sb = supabase_client or scorecard_computer.get_supabase()
        company_arg = (args.company or "ALL").strip()
        if company_arg.upper() == "ALL":
            targets = list(scorecard_computer.COMPANIES)
        else:
            targets = [normalize_company_id(company_arg)]

        peer_cache: Dict[str, Dict[str, float]] = {}
        for cid in targets:
            scorecard_computer.compute_scorecard(cid, sb, peer_cache=peer_cache)
        return {"mode": "scorecard", "companies": targets, "status": "completed"}

    if mode == "list_pending":
        manifests = ManifestStore(store)
        company_arg = (args.company or "").strip()
        company_filter = (
            None if not company_arg or company_arg.upper() == "ALL" else normalize_company_id(company_arg)
        )
        pending = [
            m.doc_id
            for m in manifests.list_manifests(company_id=company_filter)
            if m.status in ("raw", "failed")
        ]
        if args.max_docs and args.max_docs > 0:
            pending = pending[: args.max_docs]
        return {"doc_ids": pending, "count": len(pending)}

    raise ValueError(f"Unsupported worker mode: {mode!r}")


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = run_mode(args.mode, args)
        print(json.dumps(result, indent=2, default=str))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "error", "mode": args.mode, "error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
