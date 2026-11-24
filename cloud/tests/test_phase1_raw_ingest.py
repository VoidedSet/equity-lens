"""Phase 1 tests: LocalStorage, deterministic hashing, ManifestStore, and upload_raw."""

import tempfile
import unittest
from pathlib import Path

from cloud.common.config import REPO_ROOT
from cloud.common.hashing import make_chunk_id, make_doc_id, make_record_id
from cloud.common.manifest import DocumentManifest, ManifestStore
from cloud.common.storage import LocalStorage
from cloud.ingest.upload_raw import extract_period_from_filename, upload_raw_directory


class TestHashingAndStorage(unittest.TestCase):
    def test_deterministic_hashing(self) -> None:
        doc_a = make_doc_id(b"hello world")
        doc_b = make_doc_id(b"hello world")
        self.assertEqual(doc_a, doc_b)
        self.assertEqual(len(doc_a), 64)

        self.assertEqual(make_chunk_id(doc_a, 0), make_chunk_id(doc_a, 0))
        self.assertNotEqual(make_chunk_id(doc_a, 0), make_chunk_id(doc_a, 1))

        rec1 = make_record_id("ihcl", "Financials", {"period": " FY24 ", "metric": "RevPAR"})
        rec2 = make_record_id("IHCL", "financials", {"metric": "revpar", "period": "fy24"})
        self.assertEqual(rec1, rec2)

    def test_local_storage_roundtrip_and_traversal_guard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            storage = LocalStorage(Path(tmp))
            storage.write_bytes("raw/a/file.bin", b"\x00\x01\x02")
            self.assertTrue(storage.exists("raw/a/file.bin"))
            self.assertEqual(storage.read_bytes("raw/a/file.bin"), b"\x00\x01\x02")

            storage.write_text("processed/note.txt", "hello")
            self.assertEqual(storage.read_text("processed/note.txt"), "hello")

            storage.write_json("manifests/doc.json", {"ok": True})
            self.assertEqual(storage.read_json("manifests/doc.json"), {"ok": True})

            storage.write_jsonl("processed/rows.jsonl", [{"id": 1}, {"id": 2}])
            self.assertEqual(storage.read_jsonl("processed/rows.jsonl"), [{"id": 1}, {"id": 2}])

            self.assertEqual(
                storage.list_keys("processed/"),
                ["processed/note.txt", "processed/rows.jsonl"],
            )

            with self.assertRaises(ValueError):
                storage.read_bytes("../outside.txt")
            with self.assertRaises(ValueError):
                storage.write_text("raw/../../escape.txt", "nope")


class TestManifestStore(unittest.TestCase):
    def test_manifest_lifecycle_and_filtering(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            storage = LocalStorage(Path(tmp))
            store = ManifestStore(storage)

            m1 = DocumentManifest(
                doc_id="doc1",
                company_id="IHCL",
                source_type="pdf",
                doc_type="annual_report",
                period="FY24",
                raw_key="raw/doc1.pdf",
                raw_uri="file:///raw/doc1.pdf",
                filename="2024.pdf",
                content_sha256="doc1",
                size_bytes=100,
            )
            store.save(m1)
            self.assertTrue(store.exists("doc1"))

            m_proc = store.mark_processing("doc1")
            self.assertEqual(m_proc.status, "processing")
            self.assertEqual(m_proc.attempts, 1)

            m_done = store.mark_processed("doc1", {"chunks": "processed/chunks/doc1.jsonl"})
            self.assertEqual(m_done.status, "processed")
            self.assertEqual(m_done.outputs["chunks"], "processed/chunks/doc1.jsonl")

            m2 = m1.model_copy(update={"doc_id": "doc2", "company_id": "JUNIPER"})
            store.save(m2)
            store.mark_failed("doc2", "simulated error")

            self.assertEqual(len(store.list_manifests()), 2)
            self.assertEqual([m.doc_id for m in store.list_manifests(status="processed")], ["doc1"])
            self.assertEqual([m.doc_id for m in store.list_manifests(company_id="JUNIPER")], ["doc2"])


class TestRawUploader(unittest.TestCase):
    def test_period_extraction(self) -> None:
        self.assertEqual(extract_period_from_filename("2025.pdf", "annual_report"), "FY25")
        self.assertEqual(extract_period_from_filename("Dec_2022.pdf", "quarterly_results"), "Q3FY23")
        self.assertEqual(extract_period_from_filename("Mar_2023.pdf", "quarterly_results"), "Q4FY23")
        self.assertEqual(extract_period_from_filename("2023_Aug.json", "transcript"), "Q1FY24")
        self.assertEqual(extract_period_from_filename("2023_Nov_06.pdf", "credit_rating"), "2023_Nov")

    def test_synthetic_raw_data_tree_and_dedup(self) -> None:
        with tempfile.TemporaryDirectory() as src_tmp, tempfile.TemporaryDirectory() as lake_tmp:
            src_root = Path(src_tmp)
            (src_root / "Indian_Hotels" / "Annual_Reports").mkdir(parents=True)
            (src_root / "Indian_Hotels" / "Annual_Reports" / "2025.pdf").write_bytes(b"%PDF-1.4 IHCL FY25")
            (src_root / "Juniper_Hotels" / "Call_Transcripts_JSON").mkdir(parents=True)
            (src_root / "Juniper_Hotels" / "Call_Transcripts_JSON" / "2024_Aug.json").write_text(
                '[{"speaker": "Varun Chandra", "text": "We expect 12% RevPAR growth."}]',
                encoding="utf-8",
            )
            (src_root / "EIH_Limited").mkdir(parents=True)
            (src_root / "EIH_Limited" / "profit_loss.csv").write_text(
                "Metric,Mar 2024,Mar 2025\nSales +,2500,2900\n",
                encoding="utf-8",
            )

            storage = LocalStorage(Path(lake_tmp))
            manifests = ManifestStore(storage)

            first = upload_raw_directory(src_root, storage, manifests)
            self.assertEqual(first["uploaded"], 3)
            self.assertEqual(first["skipped_duplicate"], 0)
            self.assertEqual(first["errors"], 0)

            second = upload_raw_directory(src_root, storage, manifests)
            self.assertEqual(second["uploaded"], 0)
            self.assertEqual(second["skipped_duplicate"], 3)

            all_manifests = manifests.list_manifests()
            by_company = {m.company_id: m for m in all_manifests}
            self.assertEqual(set(by_company.keys()), {"IHCL", "JUNIPER", "EIH"})
            self.assertEqual(by_company["IHCL"].period, "FY25")
            self.assertEqual(by_company["JUNIPER"].period, "Q1FY25")
            self.assertEqual(by_company["EIH"].source_type, "screener_csv")

    def test_real_extracted_json_ihcl_and_itchotels_canonicalized(self) -> None:
        extracted_root = REPO_ROOT / "Data Ingestion" / "extracted_json"
        self.assertTrue((extracted_root / "IHCL").exists())
        self.assertTrue((extracted_root / "ITCHOTELS").exists())

        with tempfile.TemporaryDirectory() as lake_tmp:
            storage = LocalStorage(Path(lake_tmp))
            manifests = ManifestStore(storage)

            ihcl_res = upload_raw_directory(extracted_root / "IHCL", storage, manifests)
            juniper_res = upload_raw_directory(extracted_root / "ITCHOTELS", storage, manifests)
            self.assertGreaterEqual(ihcl_res["uploaded"], 4)
            self.assertGreaterEqual(juniper_res["uploaded"], 4)

            juniper_manifests = manifests.list_manifests(company_id="JUNIPER")
            self.assertEqual(len(juniper_manifests), juniper_res["uploaded"])
            self.assertEqual(manifests.list_manifests(company_id="ITCHOTELS"), [])

            # Re-upload must skip all as duplicates
            rerun = upload_raw_directory(extracted_root / "ITCHOTELS", storage, manifests)
            self.assertEqual(rerun["uploaded"], 0)
            self.assertEqual(rerun["skipped_duplicate"], juniper_res["uploaded"])


if __name__ == "__main__":
    unittest.main()
