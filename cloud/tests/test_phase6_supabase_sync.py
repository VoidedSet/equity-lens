"""Phase 6 tests: idempotent Supabase sync, retry/quarantine, and scorecard peer cache."""

import py_compile
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

from cloud.common.config import REPO_ROOT
from cloud.common.hashing import make_chunk_id, make_record_id
from cloud.common.storage import LocalStorage
from cloud.glue_jobs import run_local
from cloud.sync.supabase_sync import sync_curated_to_supabase


class _TransientSupabaseError(Exception):
    status_code = 503


class _FakeResult:
    def __init__(self, data: List[Dict[str, Any]]) -> None:
        self.data = data


class _FakeTableQuery:
    def __init__(self, client: "_FakeSupabaseClient", table_name: str) -> None:
        self._client = client
        self._table_name = table_name
        self._rows: List[Dict[str, Any]] = []
        self._conflict_cols: List[str] = []

    def upsert(self, rows: List[Dict[str, Any]], on_conflict: str = "id") -> "_FakeTableQuery":
        self._rows = rows
        self._conflict_cols = [c.strip() for c in on_conflict.split(",") if c.strip()]
        return self

    def execute(self) -> _FakeResult:
        self._client.calls[self._table_name] = self._client.calls.get(self._table_name, 0) + 1
        fail_plan = self._client.fail_plan.get(self._table_name)
        if fail_plan and fail_plan["remaining"] > 0:
            fail_plan["remaining"] -= 1
            raise fail_plan["exc"]

        store = self._client.tables.setdefault(self._table_name, {})
        for row in self._rows:
            key = tuple(row.get(col) for col in self._conflict_cols)
            store[key] = dict(row)
        return _FakeResult(self._rows)


class _FakeSupabaseClient:
    def __init__(self) -> None:
        self.tables: Dict[str, Dict[tuple, Dict[str, Any]]] = {}
        self.calls: Dict[str, int] = {}
        self.fail_plan: Dict[str, Dict[str, Any]] = {}

    def table(self, name: str) -> _FakeTableQuery:
        return _FakeTableQuery(self, name)


def _seed_curated_lake(storage: LocalStorage) -> None:
    ts = "2026-11-24T01:00:00+00:00"
    storage.write_jsonl(
        "processed/facts/table=financials/company=IHCL/d1.jsonl",
        [
            {
                "record_id": make_record_id("IHCL", "financials", {"period": "FY25", "metric": "opm"}),
                "doc_id": "d1",
                "company_id": "IHCL",
                "period": "FY25",
                "period_type": "annual",
                "metric": "opm",
                "value": 33.2,
                "unit": "%",
                "source_document": "2025.pdf",
                "source_page": 20,
                "ingested_at": ts,
            }
        ],
    )
    storage.write_jsonl(
        "processed/facts/table=guidance_claims/company=IHCL/d2.jsonl",
        [
            {
                "record_id": make_record_id("IHCL", "guidance_claims", {"period": "FY25"}),
                "doc_id": "d2",
                "company_id": "IHCL",
                "statement_quarter": "Q1FY25",
                "target_period": "FY25",
                "metric_type": "EBITDA Margin",
                "guidance_value_point": 32.0,
                "unit": "%",
                "verbatim_quote": "We expect 32% EBITDA margin in FY25.",
                "check_type": "check_3_driver",
                "source_document": "2024_Aug.json",
                "source_page": 1,
                "ingested_at": ts,
            }
        ],
    )
    storage.write_jsonl(
        "processed/facts/table=risk_flags/company=CHALET/d3.jsonl",
        [
            {
                "record_id": make_record_id("CHALET", "risk_flags", {"d": "debt"}),
                "doc_id": "d3",
                "company_id": "CHALET",
                "period": "FY25",
                "category": "debt",
                "description": "High capex debt burden.",
                "severity": "high",
                "source_document": "2025.pdf",
                "source_page": 50,
                "ingested_at": ts,
            }
        ],
    )
    storage.write_jsonl(
        "processed/facts/table=credit_ratings/company=EIH/d4.jsonl",
        [
            {
                "record_id": make_record_id("EIH", "credit_ratings", {"a": "ICRA"}),
                "doc_id": "d4",
                "company_id": "EIH",
                "period": "Sep 2024",
                "rating_agency": "ICRA",
                "rating_scale": "AA+",
                "rating_outlook": "Stable",
                "source_document": "2024_Sep.pdf",
                "source_page": 1,
                "ingested_at": ts,
            }
        ],
    )
    storage.write_jsonl(
        "processed/facts/table=raw_data/company=LEMONTREE/d5.jsonl",
        [
            {
                "record_id": make_record_id("LEMONTREE", "raw_data", {"k": "vision"}),
                "doc_id": "d5",
                "company_id": "LEMONTREE",
                "period": "FY25",
                "category": "strategy",
                "key_name": "asset_light",
                "value_text": "Focus on asset-light management contracts.",
                "source_document": "2025.pdf",
                "source_page": 6,
                "ingested_at": ts,
            }
        ],
    )
    cid = make_chunk_id("d1", 0)
    storage.write_jsonl(
        "processed/chunks/company=IHCL/doc_type=annual_report/d1.jsonl",
        [
            {
                "chunk_id": cid,
                "doc_id": "d1",
                "company_id": "IHCL",
                "document_type": "annual_report",
                "period": "FY25",
                "chunk_index": 0,
                "section_name": "md&a",
                "source_document": "2025.pdf",
                "source_page": 20,
                "chunk_text": "IHCL achieved 33.2% operating margin in FY25.",
                "ingested_at": ts,
            }
        ],
    )
    storage.write_jsonl(
        "processed/embeddings/company=IHCL/d1.jsonl",
        [
            {
                "chunk_id": cid,
                "doc_id": "d1",
                "company_id": "IHCL",
                "document_type": "annual_report",
                "period": "FY25",
                "chunk_index": 0,
                "section_name": "md&a",
                "source_document": "2025.pdf",
                "source_page": 20,
                "chunk_text": "IHCL achieved 33.2% operating margin in FY25.",
                "embedding": [0.02] * 384,
                "embedding_model": "all-MiniLM-L6-v2",
                "ingested_at": ts,
            }
        ],
    )
    run_local.run_all(storage, engine="pyarrow")


class TestPhase6SupabaseSync(unittest.TestCase):
    def test_idempotent_double_sync_across_all_tables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            storage = LocalStorage(Path(tmp))
            _seed_curated_lake(storage)

            fake_sb = _FakeSupabaseClient()
            res1 = sync_curated_to_supabase(storage, supabase_client=fake_sb, sleep_fn=lambda _: None)
            self.assertEqual(res1["total_errors"], 0)
            self.assertEqual(res1["total_upserted"], 8)  # 1 row in each of the 8 tables

            counts_after_run1 = {tbl: len(rows) for tbl, rows in fake_sb.tables.items()}
            self.assertEqual(counts_after_run1["companies"], 5)
            for tbl in (
                "financials",
                "guidance_claims",
                "risk_flags",
                "credit_ratings",
                "raw_data",
                "deviation_tracker",
                "credibility_scores",
                "document_chunks",
            ):
                self.assertEqual(counts_after_run1[tbl], 1)

            # Verify lakehouse-only columns were stripped
            dev_row = next(iter(fake_sb.tables["deviation_tracker"].values()))
            self.assertNotIn("guidance_record_id", dev_row)
            self.assertNotIn("ingested_at", dev_row)
            chunk_row = next(iter(fake_sb.tables["document_chunks"].values()))
            self.assertEqual(len(chunk_row["embedding"]), 384)
            self.assertNotIn("embedding_model", chunk_row)

            # Second sync must produce identical row counts
            res2 = sync_curated_to_supabase(storage, supabase_client=fake_sb, sleep_fn=lambda _: None)
            self.assertEqual(res2["total_errors"], 0)
            counts_after_run2 = {tbl: len(rows) for tbl, rows in fake_sb.tables.items()}
            self.assertEqual(counts_after_run1, counts_after_run2)

    def test_sync_retry_and_quarantine_isolation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            storage = LocalStorage(Path(tmp))
            _seed_curated_lake(storage)

            fake_sb = _FakeSupabaseClient()
            # risk_flags fails twice transiently (recovers on 3rd attempt); financials fails permanently
            fake_sb.fail_plan["risk_flags"] = {"remaining": 2, "exc": _TransientSupabaseError("503")}
            fake_sb.fail_plan["financials"] = {"remaining": 10, "exc": ValueError("permanent bad row")}

            res = sync_curated_to_supabase(storage, supabase_client=fake_sb, sleep_fn=lambda _: None)
            self.assertEqual(res["tables"]["financials"]["errors"], 1)
            self.assertEqual(res["tables"]["risk_flags"]["errors"], 0)
            self.assertEqual(res["tables"]["risk_flags"]["upserted"], 1)
            self.assertTrue(storage.exists("quarantine/sync/financials_batch_0/error.json"))


class TestScorecardPeerCache(unittest.TestCase):
    def test_peer_cache_avoids_quadratic_queries(self) -> None:
        pipeline_dir = str(REPO_ROOT / "pdf extraction pipeline")
        if pipeline_dir not in sys.path:
            sys.path.insert(0, pipeline_dir)
        py_compile.compile(str(REPO_ROOT / "pdf extraction pipeline" / "scorecard_computer.py"), doraise=True)
        import scorecard_computer  # type: ignore[import-not-found]

        snapshot_calls: List[str] = []

        def _fake_snapshot(cid: str, _sb: Any) -> Dict[str, float]:
            snapshot_calls.append(cid)
            base = 60.0 + len(cid)
            return {
                "industry_position": base,
                "financial_quality": base,
                "management_credibility": base,
                "risk_identification": base,
                "stress_test_resilience": base,
                "composite": base,
            }

        peer_cache: Dict[str, Dict[str, float]] = {}
        with patch.object(scorecard_computer, "_dimension_snapshot", side_effect=_fake_snapshot):
            for cid in scorecard_computer.COMPANIES:
                cur = {
                    "industry_position": 70.0,
                    "financial_quality": 70.0,
                    "management_credibility": 70.0,
                    "risk_identification": 70.0,
                    "stress_test_resilience": 70.0,
                    "composite": 70.0,
                }
                norm = scorecard_computer.compute_peer_normalization(cid, cur, None, peer_cache=peer_cache)
                self.assertIn("dimensions", norm)

        # First company triggers _dimension_snapshot for the 4 remaining peers; subsequent 4 reuse peer_cache
        self.assertEqual(len(snapshot_calls), len(scorecard_computer.COMPANIES) - 1)


if __name__ == "__main__":
    unittest.main()
