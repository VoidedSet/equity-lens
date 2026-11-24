"""Phases 2 & 3 tests: Bedrock Converse provider, schema validation, worker & quarantine."""

import json
import tempfile
import unittest
from pathlib import Path
from typing import List

from cloud.common.config import REPO_ROOT, CloudConfig
from cloud.common.llm import BedrockProvider, MockLLMProvider
from cloud.common.manifest import ManifestStore
from cloud.common.schemas import validate_fact
from cloud.common.storage import LocalStorage
from cloud.ingest.upload_raw import upload_raw_directory
from cloud.worker.process_document import process_document


class _FakeThrottlingError(Exception):
    def __init__(self, code: str = "ThrottlingException", status: int = 429) -> None:
        super().__init__(code)
        self.response = {
            "Error": {"Code": code},
            "ResponseMetadata": {"HTTPStatusCode": status},
        }


class _FakeBedrockClient:
    def __init__(self, fail_times: int = 0) -> None:
        self.fail_times = fail_times
        self.calls: List[dict] = []

    def converse(self, **kwargs):
        self.calls.append(kwargs)
        if len(self.calls) <= self.fail_times:
            raise _FakeThrottlingError()
        return {
            "output": {
                "message": {
                    "content": [
                        {"text": '[{"table": "RAW_DATA", '},
                        {"text": '"value_text": "Part 2"}]'},
                    ]
                }
            }
        }


def _mock_embedder(texts) -> List[List[float]]:
    return [[0.01] * 384 for _ in texts]


class TestBedrockProvider(unittest.TestCase):
    def test_converse_request_and_exponential_retry(self) -> None:
        fake_client = _FakeBedrockClient(fail_times=2)
        sleeps: List[float] = []
        provider = BedrockProvider(
            model_id="google.gemma-3-27b-it",
            region="ap-south-1",
            client=fake_client,
            max_attempts=4,
            base_delay=1.0,
            max_delay=10.0,
            sleep_fn=sleeps.append,
        )
        out = provider.generate("sys prompt", "user text", temperature=0.1, max_tokens=512)
        self.assertIn("RAW_DATA", out)
        self.assertIn("Part 2", out)
        self.assertEqual(len(fake_client.calls), 3)
        self.assertEqual(len(sleeps), 2)
        self.assertGreater(sleeps[0], 0.0)
        self.assertLessEqual(sleeps[0], 1.0)
        self.assertLessEqual(sleeps[1], 2.0)

        first_call = fake_client.calls[0]
        self.assertEqual(first_call["modelId"], "google.gemma-3-27b-it")
        self.assertEqual(first_call["system"], [{"text": "sys prompt"}])
        self.assertEqual(first_call["messages"], [{"role": "user", "content": [{"text": "user text"}]}])
        self.assertEqual(first_call["inferenceConfig"], {"temperature": 0.1, "maxTokens": 512})


class TestFactSchemaValidation(unittest.TestCase):
    def test_all_five_tables_valid_and_invalid_cases(self) -> None:
        ts = "2026-11-24T00:00:00+00:00"
        valid_items = [
            {
                "table": "HOTEL_OPS_METRIC",
                "company_id": "ITCHOTELS",
                "source_document": "2025.pdf",
                "source_page": 12,
                "period": "FY25",
                "metric": "revpar",
                "value": 8500,
                "unit": "INR",
                "period_type": "annual",
            },
            {
                "table": "guidance_claims",
                "company_id": "IHCL",
                "source_document": "2024_Aug.json",
                "source_page": 2,
                "period": "Q1FY25",
                "metric_type": "revpar",
                "target_period": "FY25",
                "guidance_value_low": 10,
                "guidance_value_high": 12,
                "unit": "%",
                "verbatim_quote": "We expect RevPAR to grow 10-12% in FY25.",
            },
            {
                "table": "RISK_FLAG",
                "company_id": "CHALET",
                "source_document": "2024.pdf",
                "source_page": 50,
                "period": "FY24",
                "category": "debt",
                "severity": "high",
                "description": "Elevated debt load due to ongoing capex.",
            },
            {
                "table": "CREDIT_RATING",
                "company_id": "EIH",
                "source_document": "2024_Sep_25.pdf",
                "source_page": 1,
                "period": "Sep 2024",
                "rating_agency": "ICRA",
                "rating_scale": "AA+",
                "rating_outlook": "Stable",
                "rating_amount_crores": 500.0,
            },
            {
                "table": "RAW_DATA",
                "company_id": "LEMONTREE",
                "source_document": "2025.pdf",
                "source_page": 8,
                "period": "FY25",
                "category": "strategy",
                "key_name": "asset_light",
                "value_text": "Focus on managed room additions in Tier 2 cities.",
            },
        ]

        seen_ids = set()
        for item in valid_items:
            table, row, err = validate_fact(item, doc_id="doc123", ingested_at=ts)
            self.assertIsNone(err)
            self.assertIsNotNone(row)
            self.assertNotIn(row["record_id"], seen_ids)
            seen_ids.add(row["record_id"])
            if item["company_id"] == "ITCHOTELS":
                self.assertEqual(row["company_id"], "JUNIPER")

        # Invalid cases
        _, bad_quote, err1 = validate_fact(
            {
                "table": "guidance_claims",
                "company_id": "IHCL",
                "source_document": "2024.pdf",
                "verbatim_quote": "   ",
            },
            doc_id="doc123",
            ingested_at=ts,
        )
        self.assertIsNone(bad_quote)
        self.assertIn("verbatim_quote", err1 or "")

        _, bad_cat, err2 = validate_fact(
            {
                "table": "risk_flags",
                "company_id": "IHCL",
                "source_document": "2024.pdf",
                "category": "not_a_valid_category",
                "description": "Something bad.",
            },
            doc_id="doc123",
            ingested_at=ts,
        )
        self.assertIsNone(bad_cat)
        self.assertIsNotNone(err2)

        _, bad_val, err3 = validate_fact(
            {
                "table": "financials",
                "company_id": "IHCL",
                "source_document": "2024.pdf",
                "period": "FY24",
                "metric": "revpar",
                "value": "not-a-number",
            },
            doc_id="doc123",
            ingested_at=ts,
        )
        self.assertIsNone(bad_val)
        self.assertIsNotNone(err3)


class TestProcessDocumentEndToEnd(unittest.TestCase):
    def test_real_ihcl_announcement_and_quarantine(self) -> None:
        announcement_path = REPO_ROOT / "Data Ingestion" / "extracted_json" / "IHCL" / "announcement.json"
        self.assertTrue(announcement_path.exists())

        with tempfile.TemporaryDirectory() as src_tmp, tempfile.TemporaryDirectory() as lake_tmp:
            # Stage real IHCL announcement.json into a temp folder so we test a single doc cleanly
            ihcl_dir = Path(src_tmp) / "IHCL"
            ihcl_dir.mkdir(parents=True)
            (ihcl_dir / "announcement.json").write_bytes(announcement_path.read_bytes())

            storage = LocalStorage(Path(lake_tmp))
            manifests = ManifestStore(storage)
            cfg = CloudConfig(storage_backend="local", local_datalake_dir=Path(lake_tmp), chunks_per_batch=5)

            up = upload_raw_directory(Path(src_tmp), storage, manifests)
            self.assertEqual(up["uploaded"], 1)
            doc_id = up["uploaded_doc_ids"][0]

            # Batch 1 returns 1 valid fact + 1 invalid fact; batch 2+ returns malformed text
            mock_llm = MockLLMProvider(
                responses=[
                    json.dumps(
                        [
                            {
                                "table": "RAW_DATA",
                                "category": "governance",
                                "key_name": "share_transfer_window",
                                "value_text": "Company opened a special window for re-lodgement of physical share transfers.",
                            },
                            {
                                "table": "RISK_FLAG",
                                "category": "invalid_enum",
                                "description": "Should go to quarantine.",
                            },
                        ]
                    ),
                    "NOT VALID JSON AT ALL {{{",
                ]
            )

            res = process_document(
                doc_id=doc_id,
                storage=storage,
                manifests=manifests,
                config=cfg,
                llm_provider=mock_llm,
                embed_fn=_mock_embedder,
            )
            self.assertEqual(res["status"], "processed")
            self.assertGreater(res["chunks_count"], 0)
            self.assertEqual(res["facts_count"], 1)
            self.assertGreaterEqual(res["quarantined_count"], 1)

            # Verify processed outputs exist
            self.assertTrue(storage.exists(res["outputs"]["chunks"]))
            self.assertTrue(storage.exists(res["outputs"]["embeddings"]))
            self.assertTrue(storage.exists(res["outputs"]["facts_raw_data"]))
            self.assertTrue(storage.exists(f"quarantine/extraction/{doc_id}/error.json"))
            self.assertTrue(storage.exists(f"quarantine/extraction/{doc_id}/raw_llm_output.txt"))

            emb_rows = storage.read_jsonl(res["outputs"]["embeddings"])
            self.assertEqual(len(emb_rows), res["chunks_count"])
            self.assertEqual(len(emb_rows[0]["embedding"]), 384)

            # Re-running without force skips idempotently
            res2 = process_document(
                doc_id=doc_id,
                storage=storage,
                manifests=manifests,
                config=cfg,
                llm_provider=mock_llm,
                embed_fn=_mock_embedder,
            )
            self.assertEqual(res2["status"], "skipped_already_processed")

    def test_transcript_json_and_screener_csv(self) -> None:
        with tempfile.TemporaryDirectory() as src_tmp, tempfile.TemporaryDirectory() as lake_tmp:
            src_root = Path(src_tmp)
            tr_dir = src_root / "Juniper_Hotels" / "Call_Transcripts_JSON"
            tr_dir.mkdir(parents=True)
            (tr_dir / "2024_Aug.json").write_text(
                json.dumps(
                    [
                        {"speaker": "Moderator", "text": "Welcome everyone to the Q1 FY25 earnings call."},
                        {
                            "speaker": "Varun Chandra, MD",
                            "text": "We expect RevPAR to grow 14% in FY25 with healthy occupancy across Mumbai and Delhi.",
                        },
                    ]
                ),
                encoding="utf-8",
            )

            csv_dir = src_root / "Indian_Hotels"
            csv_dir.mkdir(parents=True)
            (csv_dir / "profit_loss.csv").write_text(
                "Metric,Mar 2024,Mar 2025\nSales +,6769,8334\nOperating Profit,2157,2769\n",
                encoding="utf-8",
            )

            storage = LocalStorage(Path(lake_tmp))
            manifests = ManifestStore(storage)
            cfg = CloudConfig(storage_backend="local", local_datalake_dir=Path(lake_tmp))

            up = upload_raw_directory(src_root, storage, manifests)
            self.assertEqual(up["uploaded"], 2)

            by_src = {m.source_type: m for m in manifests.list_manifests()}
            tr_manifest = by_src["transcript_json"]
            csv_manifest = by_src["screener_csv"]

            mock_llm = MockLLMProvider(
                responses=[
                    json.dumps(
                        [
                            {
                                "table": "guidance_claims",
                                "metric_type": "revpar",
                                "target_period": "FY25",
                                "guidance_value_point": 14.0,
                                "unit": "%",
                                "verbatim_quote": "We expect RevPAR to grow 14% in FY25",
                                "check_type": "check_1_revpar",
                            }
                        ]
                    )
                ]
            )

            tr_res = process_document(
                doc_id=tr_manifest.doc_id,
                storage=storage,
                manifests=manifests,
                config=cfg,
                llm_provider=mock_llm,
                embed_fn=_mock_embedder,
            )
            self.assertEqual(tr_res["status"], "processed")
            self.assertEqual(tr_res["chunks_count"], 1)  # Moderator filtered out
            self.assertEqual(tr_res["facts_count"], 1)
            self.assertTrue(storage.exists(tr_res["outputs"]["facts_guidance_claims"]))

            csv_res = process_document(
                doc_id=csv_manifest.doc_id,
                storage=storage,
                manifests=manifests,
                config=cfg,
            )
            self.assertEqual(csv_res["status"], "processed")
            self.assertEqual(csv_res["facts_count"], 2)
            scr_rows = storage.read_jsonl(csv_res["outputs"]["screener"])
            self.assertEqual(scr_rows[0]["metric_name"], "Sales +")
            self.assertEqual(scr_rows[0]["values"]["Mar 2025"], "8334")


if __name__ == "__main__":
    unittest.main()
