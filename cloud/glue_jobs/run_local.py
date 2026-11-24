"""Local runner executing all Phase 4 curation jobs sequentially."""

import json
from typing import Any, Dict, List, Optional

from cloud.common.storage import StorageBackend
from cloud.glue_jobs import compute_deviations, curate_chunks, curate_facts, curate_financials
from cloud.glue_jobs.lib.spark_utils import parse_job_args, resolve_storage_from_args


def run_all(storage: StorageBackend, engine: str = "auto") -> Dict[str, Any]:
    """Run all curation stages in dependency order."""
    fin_res = curate_financials.run(storage, engine=engine)
    facts_res = curate_facts.run(storage, engine=engine)
    chunks_res = curate_chunks.run(storage, engine=engine)
    dev_res = compute_deviations.run(storage, engine=engine)
    return {
        "financials": fin_res,
        "facts": facts_res,
        "document_chunks": chunks_res,
        "deviations_and_credibility": dev_res,
    }


def main(argv: Optional[List[str]] = None) -> int:
    job_args = parse_job_args(argv)
    _, storage = resolve_storage_from_args(job_args)
    summary = run_all(storage, engine=job_args["engine"])
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
