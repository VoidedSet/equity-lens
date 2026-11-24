"""Phase 8 tests: ASL state machine validation, Lambdas, orchestration CDK, and fault-isolated simulator."""

import json
import py_compile
import re
import tempfile
import unittest
from pathlib import Path
from typing import Dict, List

from cloud.common.config import REPO_ROOT, CloudConfig
from cloud.common.llm import MockLLMProvider
from cloud.common.manifest import DocumentManifest, ManifestStore
from cloud.common.storage import LocalStorage
from cloud.ingest.upload_raw import upload_raw_directory
from cloud.stepfunctions import list_pending, mark_quarantined
from cloud.stepfunctions.simulate_local import run_pipeline_local


def _validate_state_scope(scope: dict, testcase: unittest.TestCase) -> None:
    states = scope["States"]
    testcase.assertIn(scope["StartAt"], states)
    for name, state in states.items():
        if "Next" in state:
            testcase.assertIn(state["Next"], states, f"Invalid Next target in state {name}")
        if "Default" in state:
            testcase.assertIn(state["Default"], states, f"Invalid Default target in choice {name}")
        for choice in state.get("Choices", []):
            testcase.assertIn(choice["Next"], states, f"Invalid Choice Next target in {name}")
        for catch in state.get("Catch", []):
            testcase.assertIn(catch["Next"], states, f"Invalid Catch target in {name}")
        if state.get("Type") == "Parallel":
            for branch in state.get("Branches", []):
                _validate_state_scope(branch, testcase)
        if state.get("Type") == "Map":
            _validate_state_scope(state["ItemProcessor"], testcase)


class _FakeTableQuery:
    def __init__(self, store: dict) -> None:
        self._store = store
        self._rows: List[dict] = []
        self._conflict_cols: List[str] = ["id"]

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
        self.tables: Dict[str, dict] = {}

    def table(self, name: str) -> _FakeTableQuery:
        return _FakeTableQuery(self.tables.setdefault(name, {}),)


class TestPhase8StepFunctions(unittest.TestCase):
    def test_asl_validity_and_cdk_substitutions(self) -> None:
        asl_path = REPO_ROOT / "cloud" / "stepfunctions" / "document_pipeline.asl.json"
        asl_text = asl_path.read_text(encoding="utf-8")
        asl = json.loads(asl_text)

        _validate_state_scope(asl, self)
        map_state = asl["States"]["ProcessDocumentsMap"]
        self.assertLessEqual(map_state["MaxConcurrency"], 10)
        self.assertGreaterEqual(map_state["MaxConcurrency"], 1)

        placeholders = set(re.findall(r"\$\{(\w+)\}", asl_text))
        self.assertTrue(placeholders)

        orch_path = REPO_ROOT / "cloud" / "infra" / "orchestration_stack.py"
        orch_src = orch_path.read_text(encoding="utf-8")
        for key in placeholders:
            self.assertIn(f'"{key}"', orch_src, f"ASL placeholder {key} missing from orchestration_stack.py")

        py_compile.compile(str(orch_path), doraise=True)
        py_compile.compile(str(REPO_ROOT / "cloud" / "infra" / "app.py"), doraise=True)

    def test_list_pending_and_mark_quarantined_lambdas(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            storage = LocalStorage(Path(tmp))
            manifests = ManifestStore(storage)
            base = dict(
                source_type="pdf",
                doc_type="annual_report",
                period="FY25",
                raw_key="raw/doc.pdf",
                raw_uri="file:///raw/doc.pdf",
                filename="2025.pdf",
                size_bytes=10,
            )
            manifests.save(DocumentManifest(doc_id="d_raw", company_id="IHCL", content_sha256="d_raw", status="raw", **base))
            manifests.save(DocumentManifest(doc_id="d_fail", company_id="EIH", content_sha256="d_fail", status="failed", **base))
            manifests.save(DocumentManifest(doc_id="d_done", company_id="IHCL", content_sha256="d_done", status="processed", **base))

            res_all = list_pending.handler({}, None, storage=storage)
            self.assertEqual(set(res_all["doc_ids"]), {"d_raw", "d_fail"})

            res_ihcl = list_pending.handler({"company_id": "Taj Hotels"}, None, storage=storage)
            self.assertEqual(res_ihcl["doc_ids"], ["d_raw"])

            q_res = mark_quarantined.handler(
                {"doc_id": "d_raw", "worker_error": {"Error": "ECS.TaskFailed", "Cause": "OOM"}},
                None,
                storage=storage,
            )
            self.assertEqual(q_res["status"], "quarantined")
            self.assertEqual(manifests.get("d_raw").status, "failed")  # type: ignore[union-attr]
            self.assertTrue(storage.exists("quarantine/stepfunctions/d_raw/error.json"))

    def test_local_simulator_isolates_failing_document(self) -> None:
        with tempfile.TemporaryDirectory() as src_tmp, tempfile.TemporaryDirectory() as lake_tmp:
            src_root = Path(src_tmp)
            ihcl_tr = src_root / "Indian_Hotels" / "Call_Transcripts_JSON"
            ihcl_tr.mkdir(parents=True)
            (ihcl_tr / "2024_Aug.json").write_text(
                json.dumps([{"speaker": "Puneet Chhatwal, MD", "text": "We target 12% RevPAR growth in FY25."}]),
                encoding="utf-8",
            )
            (src_root / "Indian_Hotels" / "profit_loss.csv").write_text(
                "Metric,Mar 2024,Mar 2025\nSales +,6769,8334\n",
                encoding="utf-8",
            )
            bad_tr = src_root / "Juniper_Hotels" / "Call_Transcripts_JSON"
            bad_tr.mkdir(parents=True)
            (bad_tr / "2024_Nov.json").write_text("{corrupt json", encoding="utf-8")

            storage = LocalStorage(Path(lake_tmp))
            manifests = ManifestStore(storage)
            cfg = CloudConfig(storage_backend="local", local_datalake_dir=Path(lake_tmp))

            upload_raw_directory(src_root, storage, manifests)
            bad_doc_id = manifests.list_manifests(company_id="JUNIPER")[0].doc_id
            good_doc_ids = {m.doc_id for m in manifests.list_manifests(company_id="IHCL")}

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
                                "verbatim_quote": "We target 12% RevPAR growth in FY25.",
                            }
                        ]
                    )
                ]
            )
            fake_sb = _FakeSupabase()

            result = run_pipeline_local(
                storage=storage,
                config=cfg,
                max_concurrency=2,
                llm_provider=mock_llm,
                embed_fn=lambda texts: [[0.01] * 384 for _ in texts],
                sync_supabase=True,
                supabase_client=fake_sb,
                engine="pyarrow",
            )
            self.assertEqual(result["status"], "succeeded")

            statuses = {r["doc_id"]: r["status"] for r in result["map_results"]}
            self.assertEqual(statuses[bad_doc_id], "quarantined")
            for gid in good_doc_ids:
                self.assertEqual(statuses[gid], "processed")

            self.assertEqual(manifests.get(bad_doc_id).status, "failed")  # type: ignore[union-attr]
            self.assertTrue(storage.exists(f"quarantine/stepfunctions/{bad_doc_id}/error.json"))
            self.assertEqual(len(fake_sb.tables["financials"]), 2)
            self.assertEqual(len(fake_sb.tables["guidance_claims"]), 1)
            self.assertEqual(len(fake_sb.tables["document_chunks"]), 1)

            # Re-running IHCL only finds no pending work
            rerun_ihcl = run_pipeline_local(storage=storage, config=cfg, company_id="IHCL", engine="pyarrow")
            self.assertEqual(rerun_ihcl["status"], "no_work")


if __name__ == "__main__":
    unittest.main()
