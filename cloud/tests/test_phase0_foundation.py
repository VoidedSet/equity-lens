"""Phase 0 tests: company canonicalization, config masking, and secret/path hygiene."""

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from cloud.common.companies import CANONICAL_COMPANIES, normalize_company_id
from cloud.common.config import REPO_ROOT, get_config


class TestCompanies(unittest.TestCase):
    def test_canonical_companies_and_aliases(self) -> None:
        self.assertEqual(CANONICAL_COMPANIES, ("IHCL", "CHALET", "LEMONTREE", "EIH", "JUNIPER"))
        self.assertEqual(normalize_company_id("ihcl"), "IHCL")
        self.assertEqual(normalize_company_id("Indian_Hotels"), "IHCL")
        self.assertEqual(normalize_company_id("Taj Hotels"), "IHCL")
        self.assertEqual(normalize_company_id("Chalet_Hotels"), "CHALET")
        self.assertEqual(normalize_company_id("Lemon Tree Hotels Ltd"), "LEMONTREE")
        self.assertEqual(normalize_company_id("Oberoi"), "EIH")
        self.assertEqual(normalize_company_id("Juniper_Hotels"), "JUNIPER")
        self.assertEqual(normalize_company_id("ITCHOTELS"), "JUNIPER")
        self.assertEqual(normalize_company_id("ITC Hotels"), "JUNIPER")

    def test_invalid_company_raises_or_defaults(self) -> None:
        with self.assertRaises(ValueError):
            normalize_company_id("UNKNOWN_CO")
        with self.assertRaises(ValueError):
            normalize_company_id("   ")
        self.assertIsNone(normalize_company_id("UNKNOWN_CO", default=None))


class TestConfig(unittest.TestCase):
    def test_defaults_and_env_overrides_and_masking(self) -> None:
        with patch.dict(
            os.environ,
            {
                "STORAGE_BACKEND": "s3",
                "S3_BUCKET": "my-test-bucket",
                "AWS_REGION": "us-east-1",
                "LLM_PROVIDER": "bedrock",
                "BEDROCK_MODEL_ID": "meta.llama3-3-70b-instruct-v1:0",
                "FEATHERLESS_API_KEY": "secret-featherless",
                "SUPABASE_SERVICE_KEY": "secret-supa",
            },
            clear=False,
        ):
            cfg = get_config()
            self.assertEqual(cfg.storage_backend, "s3")
            self.assertEqual(cfg.s3_bucket, "my-test-bucket")
            self.assertEqual(cfg.aws_region, "us-east-1")
            self.assertEqual(cfg.llm_provider, "bedrock")
            self.assertEqual(cfg.bedrock_model_id, "meta.llama3-3-70b-instruct-v1:0")

            masked = cfg.to_masked_dict()
            self.assertEqual(masked["featherless_api_key"], "***")
            self.assertEqual(masked["supabase_service_key"], "***")
            self.assertNotIn("secret-featherless", str(masked))
            self.assertNotIn("secret-supa", str(masked))


class TestSecretAndPathHygiene(unittest.TestCase):
    def test_no_hardcoded_secrets_or_personal_paths(self) -> None:
        files_to_check = [
            REPO_ROOT / "misc" / "data-gathering" / "upload_screener_data.py",
            REPO_ROOT / "misc" / "data_formatter" / "app.py",
            REPO_ROOT / "misc" / "data_formatter" / "data_formatter_local.py",
            REPO_ROOT / "misc" / "data_formatter" / "ingest_engine.py",
            REPO_ROOT / "misc" / "one-offs" / "extract.py",
            REPO_ROOT / "Data Ingestion" / "extract_pdfs_to_json.py",
        ]
        forbidden_tokens = ("eyJhbGciOi", "rc_6bfc", "gsk_", "Users\\91845", "datahack-the big leagues")
        for file_path in files_to_check:
            self.assertTrue(file_path.exists(), f"Missing expected file: {file_path}")
            content = file_path.read_text(encoding="utf-8")
            for token in forbidden_tokens:
                self.assertNotIn(token, content, f"Found forbidden token {token!r} in {file_path}")

        extract_src = (REPO_ROOT / "Data Ingestion" / "extract_pdfs_to_json.py").read_text(encoding="utf-8")
        self.assertIn('"Juniper_Hotels": "JUNIPER"', extract_src)


if __name__ == "__main__":
    unittest.main()
