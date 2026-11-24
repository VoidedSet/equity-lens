"""Phase 7 tests: Bedrock presets/fallback, worker entrypoint, Dockerfile, and ECS CDK syntax."""

import argparse
import json
import py_compile
import tempfile
import unittest
from pathlib import Path
from typing import List

from cloud.common.config import REPO_ROOT, CloudConfig
from cloud.common.llm import BedrockProvider, MockLLMProvider, resolve_bedrock_model_id
from cloud.common.manifest import DocumentManifest, ManifestStore
from cloud.common.storage import LocalStorage
from cloud.glue_jobs import run_local
from cloud.ingest.upload_raw import upload_raw_directory
from cloud.worker.entrypoint import build_parser, run_mode


class _FakeValidationException(Exception):
    def __init__(self, msg: str = "This model does not support system messages") -> None:
        super().__init__(msg)
        self.response = {
            "Error": {"Code": "ValidationException"},
            "ResponseMetadata": {"HTTPStatusCode": 400},
        }


class _FakeSystemFallbackBedrockClient:
    def __init__(self) -> None:
        self.calls: List[dict] = []

    def converse(self, **kwargs):
        self.calls.append(kwargs)
        if "system" in kwargs:
            raise _FakeValidationException()
        return {"output": {"message": {"content": [{"text": '[{"table": "RAW_DATA", "value_text": "ok"}]'}]}}}


class TestBedrockPresetsAndSystemFallback(unittest.TestCase):
    def test_resolve_presets_and_raw_ids(self) -> None:
        self.assertEqual(resolve_bedrock_model_id("gemma3-27b"), "google.gemma-3-27b-it")
        self.assertEqual(resolve_bedrock_model_id("mistral-large-3"), "mistral.mistral-large-3-675b-instruct")
        self.assertEqual(resolve_bedrock_model_id("us.mistral.mistral-large-3-675b-instruct"), "us.mistral.mistral-large-3-675b-instruct")

    def test_system_prompt_folds_into_user_message_on_validation_error(self) -> None:
        fake_client = _FakeSystemFallbackBedrockClient()
        provider = BedrockProvider(model_id="mistral-large-3", region="ap-south-1", client=fake_client)
        self.assertEqual(provider.model_id, "mistral.mistral-large-3-675b-instruct")

        out1 = provider.generate("SYS RULES", "USER DATA")
        self.assertIn("RAW_DATA", out1)
        self.assertEqual(len(fake_client.calls), 2)
        self.assertIn("system", fake_client.calls[0])
        self.assertNotIn("system", fake_client.calls[1])
        folded_text = fake_client.calls[1]["messages"][0]["content"][0]["text"]
        self.assertIn("SYS RULES", folded_text)
        self.assertIn("USER DATA", folded_text)

        # Subsequent call remembers _supports_system=False and skips the failing attempt
        out2 = provider.generate("SYS RULES", "MORE DATA")
        self.assertIn("RAW_DATA", out2)
        self.assertEqual(len(fake_client.calls), 3)
        self.assertNotIn("system", fake_client.calls[2])


class _FakeTableQuery:
    def __init__(self, store: dict, conflict_cols: List[str]) -> None:
        self._store = store
        self._conflict_cols = conflict_cols
        self._rows: List[dict] = []

    def upsert(self, rows: List[dict], on_conflict: str = "id") -> "_FakeTableQuery":
        self._rows = rows
        self._conflict_cols = [c.strip() for c in on_conflict.split(",") if c.strip()]
        return self

    def execute(self):
        for r in self._rows:
            self._store[tuple(r.get(c) for c in self._conflict_cols)] = dict(r)
        return self._rows


class _FakeSupabase:
    def __init__(self) -> None:
        self.tables: dict[str, dict] = {}

    def table(self, name: str) -> _FakeTableQuery:
        return _FakeTableQuery(self.tables.setdefault(name, {}), ["id"])


class TestWorkerEntrypointAndDocker(unittest.TestCase):
    def test_entrypoint_modes_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as src_tmp, tempfile.TemporaryDirectory() as lake_tmp:
            tr_dir = Path(src_tmp) / "Indian_Hotels" / "Call_Transcripts_JSON"
            tr_dir.mkdir(parents=True)
            (tr_dir / "2024_Aug.json").write_text(
                json.dumps([{"speaker": "Puneet Chhatwal, MD", "text": "We expect 12% RevPAR growth in FY25."}]),
                encoding="utf-8",
            )

            storage = LocalStorage(Path(lake_tmp))
            manifests = ManifestStore(storage)
            cfg = CloudConfig(storage_backend="local", local_datalake_dir=Path(lake_tmp))

            up = upload_raw_directory(Path(src_tmp), storage, manifests)
            self.assertEqual(up["uploaded"], 1)
            doc_id = up["uploaded_doc_ids"][0]

            # 1. list_pending
            parser = build_parser()
            args_list = parser.parse_args(["--mode", "list_pending", "--company", "IHCL"])
            pending = run_mode("list_pending", args_list, storage=storage, config=cfg)
            self.assertEqual(pending["doc_ids"], [doc_id])

            # 2. process_document
            mock_llm = MockLLMProvider(
                responses=[
                    json.dumps(
                        [
                            {
                                "table": "guidance_claims",
                                "metric_type": "revpar",
                                "target_period": "FY25",
                                "guidance_value_point": 12.0,
                                "unit": "%",
                                "verbatim_quote": "We expect 12% RevPAR growth in FY25.",
                            }
                        ]
                    )
                ]
            )
            args_proc = parser.parse_args(["--mode", "process_document", "--doc-id", doc_id])
            proc_res = run_mode(
                "process_document",
                args_proc,
                storage=storage,
                config=cfg,
                llm_provider=mock_llm,
                embed_fn=lambda texts: [[0.01] * 384 for _ in texts],
            )
            self.assertEqual(proc_res["status"], "processed")

            # After processing, list_pending is empty
            pending_after = run_mode("list_pending", args_list, storage=storage, config=cfg)
            self.assertEqual(pending_after["count"], 0)

            # 3. curate + supabase_sync via entrypoint
            run_local.run_all(storage, engine="pyarrow")
            fake_sb = _FakeSupabase()
            args_sync = parser.parse_args(["--mode", "supabase_sync", "--batch-size", "50"])
            sync_res = run_mode(
                "supabase_sync",
                args_sync,
                storage=storage,
                config=cfg,
                supabase_client=fake_sb,
            )
            self.assertEqual(sync_res["total_errors"], 0)
            self.assertEqual(len(fake_sb.tables["guidance_claims"]), 1)
            self.assertEqual(len(fake_sb.tables["document_chunks"]), 1)

    def test_docker_files_and_compute_cdk_compile(self) -> None:
        dockerfile = (REPO_ROOT / "cloud" / "worker" / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("FROM python:3.11-slim", dockerfile)
        self.assertIn("all-MiniLM-L6-v2", dockerfile)
        self.assertIn("cloud.worker.entrypoint", dockerfile)

        dockerignore = (REPO_ROOT / ".dockerignore").read_text(encoding="utf-8")
        self.assertIn("Raw Data Extraction/", dockerignore)
        self.assertIn("local_datalake/", dockerignore)

        reqs = (REPO_ROOT / "cloud" / "worker" / "requirements.txt").read_text(encoding="utf-8")
        self.assertIn("boto3", reqs)
        self.assertIn("sentence-transformers", reqs)
        self.assertNotIn("pyspark", reqs)

        py_compile.compile(str(REPO_ROOT / "cloud" / "infra" / "lakehouse_stack.py"), doraise=True)
        py_compile.compile(str(REPO_ROOT / "cloud" / "infra" / "compute_stack.py"), doraise=True)


if __name__ == "__main__":
    unittest.main()
