"""Phase 9 tests: Athena client & local presets, agent athena_sql tool, S3 presigning, and news upload."""

import importlib.util
import os
import py_compile
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

from agent.tool_registry import execute_tool
from cloud.athena.client import AthenaClient, query_lakehouse, validate_readonly_sql
from cloud.common.config import REPO_ROOT, CloudConfig
from cloud.common.hashing import make_record_id
from cloud.common.storage import LocalStorage, S3Storage
from cloud.glue_jobs import run_local


class _FakeAthenaBotoClient:
    def __init__(self, fail_state: str = "") -> None:
        self.fail_state = fail_state
        self.polls = 0
        self.started_sql = ""

    def start_query_execution(self, **kwargs):
        self.started_sql = kwargs["QueryString"]
        return {"QueryExecutionId": "qid-123"}

    def get_query_execution(self, QueryExecutionId: str):
        self.polls += 1
        if self.fail_state:
            return {"QueryExecution": {"Status": {"State": self.fail_state, "StateChangeReason": "syntax error"}}}
        state = "RUNNING" if self.polls == 1 else "SUCCEEDED"
        return {"QueryExecution": {"Status": {"State": state}}}

    def get_query_results(self, QueryExecutionId: str, MaxResults: int = 101):
        return {
            "ResultSet": {
                "Rows": [
                    {"Data": [{"VarCharValue": "company_id"}, {"VarCharValue": "revenue_cr"}]},
                    {"Data": [{"VarCharValue": "IHCL"}, {"VarCharValue": "8334.0"}]},
                    {"Data": [{"VarCharValue": "EIH"}, {"VarCharValue": "2900.0"}]},
                ]
            }
        }


class _FakeS3BotoClient:
    def __init__(self) -> None:
        self.calls: List[dict] = []

    def generate_presigned_url(self, ClientMethod: str, Params: Dict[str, Any], ExpiresIn: int) -> str:
        self.calls.append({"method": ClientMethod, "params": Params, "expires_in": ExpiresIn})
        return f"https://{Params['Bucket']}.s3.ap-south-1.amazonaws.com/{Params['Key']}?X-Amz-Expires={ExpiresIn}"


class TestAthenaClientAndAgentTool(unittest.TestCase):
    def test_validate_readonly_sql(self) -> None:
        self.assertEqual(validate_readonly_sql("  SELECT * FROM equity_lens.financials; "), "SELECT * FROM equity_lens.financials")
        self.assertEqual(
            validate_readonly_sql("WITH cte AS (SELECT 1) SELECT * FROM cte"),
            "WITH cte AS (SELECT 1) SELECT * FROM cte",
        )
        for bad_sql in (
            "",
            "DROP TABLE equity_lens.financials",
            "DELETE FROM equity_lens.financials",
            "INSERT INTO equity_lens.financials VALUES ('a')",
            "SELECT 1; DROP TABLE equity_lens.financials",
            "MSCK REPAIR TABLE equity_lens.financials",
        ):
            with self.assertRaises(ValueError, msg=f"Expected ValueError for {bad_sql!r}"):
                validate_readonly_sql(bad_sql)

    def test_athena_client_poll_and_parse(self) -> None:
        fake = _FakeAthenaBotoClient()
        client = AthenaClient(client=fake, sleep_fn=lambda _: None)
        res = client.execute_query("SELECT company_id, revenue_cr FROM equity_lens.financials;")
        self.assertEqual(res["engine"], "athena")
        self.assertEqual(res["columns"], ["company_id", "revenue_cr"])
        self.assertEqual(res["row_count"], 2)
        self.assertEqual(res["rows"][0], {"company_id": "IHCL", "revenue_cr": "8334.0"})

        bad_client = AthenaClient(client=_FakeAthenaBotoClient(fail_state="FAILED"), sleep_fn=lambda _: None)
        with self.assertRaises(RuntimeError):
            bad_client.execute_query("SELECT 1")

    def test_local_curated_presets_and_agent_tool(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            storage = LocalStorage(Path(tmp))
            ts = "2026-11-25T00:00:00+00:00"
            storage.write_jsonl(
                "processed/facts/table=financials/company=IHCL/f1.jsonl",
                [
                    {
                        "record_id": make_record_id("IHCL", "financials", {"p": "FY25", "m": "revenue"}),
                        "doc_id": "f1",
                        "company_id": "IHCL",
                        "period": "FY25",
                        "period_type": "annual",
                        "metric": "revenue",
                        "value": 8334.0,
                        "unit": "INR Cr",
                        "source_document": "2025.pdf",
                        "ingested_at": ts,
                    },
                    {
                        "record_id": make_record_id("IHCL", "financials", {"p": "FY25", "m": "opm"}),
                        "doc_id": "f1",
                        "company_id": "IHCL",
                        "period": "FY25",
                        "period_type": "annual",
                        "metric": "opm",
                        "value": 33.2,
                        "unit": "%",
                        "source_document": "2025.pdf",
                        "ingested_at": ts,
                    },
                    {
                        "record_id": make_record_id("IHCL", "financials", {"p": "FY25", "m": "operating_profit"}),
                        "doc_id": "f1",
                        "company_id": "IHCL",
                        "period": "FY25",
                        "period_type": "annual",
                        "metric": "operating_profit",
                        "value": 2769.0,
                        "unit": "INR Cr",
                        "source_document": "2025.pdf",
                        "ingested_at": ts,
                    },
                    {
                        "record_id": make_record_id("IHCL", "financials", {"p": "FY25", "m": "interest"}),
                        "doc_id": "f1",
                        "company_id": "IHCL",
                        "period": "FY25",
                        "period_type": "annual",
                        "metric": "interest",
                        "value": 200.0,
                        "unit": "INR Cr",
                        "source_document": "2025.pdf",
                        "ingested_at": ts,
                    },
                ],
            )
            storage.write_jsonl(
                "processed/facts/table=guidance_claims/company=IHCL/g1.jsonl",
                [
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
                        "source_document": "2024_Aug.json",
                        "ingested_at": ts,
                    }
                ],
            )
            storage.write_jsonl(
                "processed/facts/table=risk_flags/company=IHCL/r1.jsonl",
                [
                    {
                        "record_id": make_record_id("IHCL", "risk_flags", {"c": "debt"}),
                        "doc_id": "r1",
                        "company_id": "IHCL",
                        "period": "FY25",
                        "category": "debt",
                        "description": "Debt covenant monitoring.",
                        "severity": "medium",
                        "source_document": "2025.pdf",
                        "ingested_at": ts,
                    }
                ],
            )
            run_local.run_all(storage, engine="pyarrow")
            cfg = CloudConfig(storage_backend="local", local_datalake_dir=Path(tmp))

            for preset_name in (
                "cross_company_financials",
                "guidance_hit_rate",
                "risk_severity_summary",
                "deviation_trends",
            ):
                res = query_lakehouse(preset=preset_name, company="IHCL", config=cfg, storage=storage)
                self.assertEqual(res["engine"], "local_curated")
                self.assertEqual(res["row_count"], 1, f"Expected 1 row for {preset_name}")

            fin_res = query_lakehouse(preset="cross_company_financials", config=cfg, storage=storage)
            self.assertEqual(fin_res["rows"][0]["interest_coverage"], 13.85)

            with patch.dict(os.environ, {"LOCAL_DATALAKE_DIR": tmp, "STORAGE_BACKEND": "local"}):
                tool_res = execute_tool("athena_sql", {"preset": "guidance_hit_rate", "company": "Taj"})
                self.assertFalse(tool_res.get("error"))
                self.assertEqual(tool_res["row_count"], 1)
                self.assertIn("IHCL", tool_res["output"])


class TestS3PresignAndNewsHelpers(unittest.TestCase):
    def test_storage_presign_url(self) -> None:
        fake_s3 = _FakeS3BotoClient()
        s3 = S3Storage(bucket="equity-lens-datalake-dev", region="ap-south-1", client=fake_s3)
        url = s3.presign_url("raw/source=pdf/company=IHCL/2025.pdf", expires_in=600)
        self.assertIn("equity-lens-datalake-dev.s3.ap-south-1.amazonaws.com", url)
        self.assertIn("X-Amz-Expires=600", url)

        with tempfile.TemporaryDirectory() as tmp:
            local = LocalStorage(Path(tmp))
            local.write_bytes("raw/doc.pdf", b"%PDF")
            self.assertTrue(local.presign_url("raw/doc.pdf").startswith("file://"))

    def test_news_extract_digest_items_and_normalization(self) -> None:
        mod_path = REPO_ROOT / "worflow_news" / "upload_news_to_supabase.py"
        spec = importlib.util.spec_from_file_location("upload_news_to_supabase", mod_path)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        sample_digest = {
            "companies": {
                "IHCL": [
                    {"title": "IHCL opens Taj resort", "url": "https://ex.com/1", "company_tags": ["IHCL"]},
                ],
                "JUNIPER": [
                    {
                        "title": "Juniper expansion",
                        "url": "https://ex.com/2",
                        "company_tags": ["JUNIPERHOTELS", "ITCHOTELS"],
                    },
                    # Duplicate across sections should collapse
                    {"title": "IHCL opens Taj resort", "url": "https://ex.com/1", "company_tags": ["IHCL"]},
                ],
            },
            "sector_news": [
                {"title": "India tourism rises", "url": "https://ex.com/3", "company_tags": []},
            ],
            "global_hospitality_news": [
                {"title": "Global RevPAR outlook", "url": "https://ex.com/4", "company_tags": []},
            ],
        }
        items = mod.extract_digest_items(sample_digest)
        self.assertEqual(len(items), 4)
        self.assertEqual(mod.normalize_company_tags(items[1]["company_tags"]), ["JUNIPER", "JUNIPER"])

    def test_python_files_compile(self) -> None:
        for rel in (
            "cloud/common/storage.py",
            "cloud/athena/client.py",
            "agent/prompts.py",
            "agent/tool_registry.py",
            "worflow_news/upload_news_to_supabase.py",
            "worflow_news/news_pipeline.py",
        ):
            py_compile.compile(str(REPO_ROOT / rel), doraise=True)


if __name__ == "__main__":
    unittest.main()
