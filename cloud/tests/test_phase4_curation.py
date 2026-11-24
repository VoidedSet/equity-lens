"""Phase 4 tests: PyArrow/PySpark curation jobs, DQ validation, deduplication, and deviations."""

import tempfile
import unittest
from pathlib import Path

from cloud.common.hashing import make_chunk_id, make_record_id
from cloud.common.storage import LocalStorage
from cloud.glue_jobs import compute_deviations, curate_chunks, curate_facts, curate_financials, run_local
from cloud.glue_jobs.lib.spark_utils import read_curated_parquet


class TestPhase4Curation(unittest.TestCase):
    def test_curate_financials_yoy_dedup_and_quarantine(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            storage = LocalStorage(Path(tmp))

            # Screener profit_loss JSONL (including Additional Metrics cutoff & TTM skip)
            storage.write_jsonl(
                "processed/screener/company=IHCL/profit_loss.jsonl",
                [
                    {
                        "doc_id": "d_pl",
                        "company_id": "IHCL",
                        "doc_type": "profit_loss",
                        "filename": "profit_loss.csv",
                        "row_index": 1,
                        "metric_name": "Sales +",
                        "values": {"Mar 2024": "6,769", "Mar 2025": "8,334", "TTM": "8,500"},
                        "ingested_at": "2026-11-24T01:00:00+00:00",
                    },
                    {
                        "doc_id": "d_pl",
                        "company_id": "IHCL",
                        "doc_type": "profit_loss",
                        "filename": "profit_loss.csv",
                        "row_index": 2,
                        "metric_name": "Additional Metrics",
                        "values": {"Mar 2024": "10"},
                        "ingested_at": "2026-11-24T01:00:00+00:00",
                    },
                    {
                        "doc_id": "d_pl",
                        "company_id": "IHCL",
                        "doc_type": "profit_loss",
                        "filename": "profit_loss.csv",
                        "row_index": 3,
                        "metric_name": "Operating Profit",  # after Additional Metrics -> ignored
                        "values": {"Mar 2024": "999"},
                        "ingested_at": "2026-11-24T01:00:00+00:00",
                    },
                ],
            )

            # Facts financials JSONL with duplicate record_id (latest ingested_at must win) + 1 invalid row
            revpar_rid = make_record_id(
                "IHCL",
                "financials",
                {
                    "period": "FY25",
                    "period_type": "annual",
                    "metric": "revpar",
                    "source_document": "2025.pdf",
                    "source_page": 10,
                },
            )
            storage.write_jsonl(
                "processed/facts/table=financials/company=IHCL/d_ar.jsonl",
                [
                    {
                        "record_id": revpar_rid,
                        "doc_id": "d_ar",
                        "company_id": "IHCL",
                        "period": "FY25",
                        "period_type": "annual",
                        "metric": "revpar",
                        "value": 8100.0,
                        "unit": "INR",
                        "source_document": "2025.pdf",
                        "source_page": 10,
                        "ingested_at": "2026-11-24T01:00:00+00:00",
                    },
                    {
                        "record_id": revpar_rid,
                        "doc_id": "d_ar",
                        "company_id": "IHCL",
                        "period": "FY25",
                        "period_type": "annual",
                        "metric": "revpar",
                        "value": 8450.0,  # newer wins
                        "unit": "INR",
                        "source_document": "2025.pdf",
                        "source_page": 10,
                        "ingested_at": "2026-11-24T02:00:00+00:00",
                    },
                    {
                        "record_id": "bad_row_id",
                        "doc_id": "d_ar",
                        "company_id": "IHCL",
                        "period": "FY25",
                        "period_type": "annual",
                        "metric": "revpar",
                        "value": float("nan"),  # invalid -> quarantined
                        "source_document": "2025.pdf",
                        "ingested_at": "2026-11-24T02:00:00+00:00",
                    },
                ],
            )

            res = curate_financials.run(storage, engine="pyarrow")
            self.assertEqual(res["quarantined"], 1)
            self.assertEqual(res["deduplicated"], 3)  # FY24 revenue, FY25 revenue, FY25 revpar
            self.assertTrue(storage.exists("quarantine/curation/financials/batch/error.json"))

            curated = read_curated_parquet("financials", storage)
            self.assertEqual(len(curated), 3)
            by_metric_period = {(r["metric"], r["period"]): r for r in curated}
            self.assertEqual(by_metric_period[("revpar", "FY25")]["value"], 8450.0)
            self.assertNotIn(("operating_profit", "FY24"), by_metric_period)
            self.assertNotIn(("revenue", "TTM"), by_metric_period)
            expected_yoy = round(((8334.0 - 6769.0) / 6769.0) * 100.0, 2)
            self.assertEqual(by_metric_period[("revenue", "FY25")]["yoy_change"], expected_yoy)

    def test_end_to_end_curation_and_deviations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            storage = LocalStorage(Path(tmp))

            # Financials for IHCL FY24 and FY25 OPM
            storage.write_jsonl(
                "processed/facts/table=financials/company=IHCL/f1.jsonl",
                [
                    {
                        "record_id": make_record_id("IHCL", "financials", {"period": "FY24", "metric": "opm"}),
                        "doc_id": "f1",
                        "company_id": "IHCL",
                        "period": "FY24",
                        "period_type": "annual",
                        "metric": "opm",
                        "value": 33.0,
                        "unit": "%",
                        "source_document": "2024.pdf",
                        "source_page": 40,
                        "ingested_at": "2026-11-24T01:00:00+00:00",
                    },
                    {
                        "record_id": make_record_id("IHCL", "financials", {"period": "FY25", "metric": "opm"}),
                        "doc_id": "f1",
                        "company_id": "IHCL",
                        "period": "FY25",
                        "period_type": "annual",
                        "metric": "opm",
                        "value": 24.0,
                        "unit": "%",
                        "source_document": "2025.pdf",
                        "source_page": 42,
                        "ingested_at": "2026-11-24T01:00:00+00:00",
                    },
                ],
            )

            # Guidance claims (FY24 BEAT, FY25 MISS) + Risk Flag + Chunk
            storage.write_jsonl(
                "processed/facts/table=guidance_claims/company=IHCL/g1.jsonl",
                [
                    {
                        "record_id": make_record_id("IHCL", "guidance_claims", {"p": "FY24"}),
                        "doc_id": "g1",
                        "company_id": "IHCL",
                        "statement_quarter": "Q1FY24",
                        "target_period": "FY 2024",
                        "metric_type": "EBITDA Margin",
                        "guidance_value_point": 30.0,
                        "unit": "%",
                        "verbatim_quote": "We target 30% EBITDA margin in FY24.",
                        "check_type": "check_3_driver",
                        "source_document": "2023_Aug.json",
                        "source_page": 2,
                        "ingested_at": "2026-11-24T01:00:00+00:00",
                    },
                    {
                        "record_id": make_record_id("IHCL", "guidance_claims", {"p": "FY25"}),
                        "doc_id": "g1",
                        "company_id": "IHCL",
                        "statement_quarter": "Q1FY25",
                        "target_period": "FY25",
                        "metric_type": "EBITDA Margin",
                        "guidance_value_point": 32.0,
                        "unit": "%",
                        "verbatim_quote": "We expect 32% EBITDA margin in FY25.",
                        "check_type": "check_3_driver",
                        "source_document": "2024_Aug.json",
                        "source_page": 3,
                        "ingested_at": "2026-11-24T01:00:00+00:00",
                    },
                ],
            )
            storage.write_jsonl(
                "processed/facts/table=risk_flags/company=JUNIPER/r1.jsonl",
                [
                    {
                        "record_id": make_record_id("JUNIPER", "risk_flags", {"d": "debt"}),
                        "doc_id": "r1",
                        "company_id": "ITCHOTELS",  # alias normalized to JUNIPER
                        "period": "FY24",
                        "category": "debt",
                        "description": "High leverage from airport hotel capex.",
                        "severity": "high",
                        "source_document": "2024.pdf",
                        "source_page": 55,
                        "ingested_at": "2026-11-24T01:00:00+00:00",
                    }
                ],
            )
            cid0 = make_chunk_id("doc_c", 0)
            storage.write_jsonl(
                "processed/chunks/company=IHCL/doc_type=annual_report/doc_c.jsonl",
                [
                    {
                        "chunk_id": cid0,
                        "doc_id": "doc_c",
                        "company_id": "IHCL",
                        "document_type": "annual_report",
                        "period": "FY25",
                        "chunk_index": 0,
                        "section_name": "md&a",
                        "source_document": "2025.pdf",
                        "source_page": 10,
                        "chunk_text": "Older version",
                        "ingested_at": "2026-11-24T01:00:00+00:00",
                    },
                    {
                        "chunk_id": cid0,
                        "doc_id": "doc_c",
                        "company_id": "IHCL",
                        "document_type": "annual_report",
                        "period": "FY25",
                        "chunk_index": 0,
                        "section_name": "md&a",
                        "source_document": "2025.pdf",
                        "source_page": 10,
                        "chunk_text": "Updated chunk text",
                        "ingested_at": "2026-11-24T02:00:00+00:00",
                    },
                ],
            )

            summary = run_local.run_all(storage, engine="pyarrow")
            self.assertEqual(summary["facts"]["risk_flags"]["deduplicated"], 1)
            self.assertEqual(summary["document_chunks"]["deduplicated"], 1)
            self.assertEqual(summary["deviations_and_credibility"]["deviations_count"], 2)
            self.assertEqual(summary["deviations_and_credibility"]["credibility_count"], 1)

            devs = read_curated_parquet("deviation_tracker", storage)
            flags_by_period = {d["period"]: d["flag"] for d in devs}
            self.assertEqual(flags_by_period["FY24"], "BEAT")
            self.assertEqual(flags_by_period["FY25"], "MISS")

            cred = read_curated_parquet("credibility_scores", storage)
            self.assertEqual(len(cred), 1)
            self.assertEqual(cred[0]["hit_rate"], 50.0)
            self.assertEqual(cred[0]["consecutive_misses"], 1)

            chunks = read_curated_parquet("document_chunks", storage)
            self.assertEqual(chunks[0]["chunk_text"], "Updated chunk text")
            self.assertEqual(chunks[0]["document_type"], "annual_report")

            risks = read_curated_parquet("risk_flags", storage)
            self.assertEqual(risks[0]["company_id"], "JUNIPER")


if __name__ == "__main__":
    unittest.main()
