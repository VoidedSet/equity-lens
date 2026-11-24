"""Phase 5 tests: verify Athena DDL aligns 100% with CURATED_SCHEMAS, queries, and CDK syntax."""

import py_compile
import re
import unittest

from cloud.common.config import REPO_ROOT
from cloud.glue_jobs.lib.schemas import PARTITION_COLUMNS, TABLE_FIELD_SPECS


class TestPhase5AthenaAndGlue(unittest.TestCase):
    def test_ddl_covers_all_curated_tables_and_columns(self) -> None:
        db_sql = (REPO_ROOT / "cloud" / "athena" / "ddl" / "00_database.sql").read_text(encoding="utf-8")
        self.assertIn("CREATE DATABASE IF NOT EXISTS equity_lens", db_sql)

        ddl_sql = (REPO_ROOT / "cloud" / "athena" / "ddl" / "01_curated_tables.sql").read_text(encoding="utf-8")
        table_blocks = re.findall(
            r"CREATE EXTERNAL TABLE IF NOT EXISTS equity_lens\.(\w+)\s*\((.*?)\)\s*PARTITIONED BY\s*\((.*?)\).*?TBLPROPERTIES\s*\((.*?)\);",
            ddl_sql,
            flags=re.DOTALL | re.IGNORECASE,
        )
        found = {name: (cols, parts, props) for name, cols, parts, props in table_blocks}
        self.assertEqual(set(found.keys()), set(TABLE_FIELD_SPECS.keys()))

        for table_name, field_specs in TABLE_FIELD_SPECS.items():
            cols_block, parts_block, props_block = found[table_name]
            expected_part_cols = set(PARTITION_COLUMNS[table_name])
            expected_data_cols = {name for name, _ in field_specs if name not in expected_part_cols}

            ddl_data_cols = {
                line.strip().rstrip(",").split()[0]
                for line in cols_block.strip().splitlines()
                if line.strip()
            }
            ddl_part_cols = {
                line.strip().rstrip(",").split()[0]
                for line in parts_block.strip().splitlines()
                if line.strip()
            }
            self.assertEqual(ddl_data_cols, expected_data_cols, f"Data columns mismatch for {table_name}")
            self.assertEqual(ddl_part_cols, expected_part_cols, f"Partition columns mismatch for {table_name}")
            self.assertIn("'projection.enabled' = 'true'", props_block)
            self.assertIn("'parquet.compression' = 'SNAPPY'", props_block)

    def test_reference_athena_queries_exist(self) -> None:
        queries_dir = REPO_ROOT / "cloud" / "athena" / "queries"
        expected = [
            "01_cross_company_financials.sql",
            "02_guidance_hit_rate.sql",
            "03_risk_severity_summary.sql",
            "04_deviation_trends.sql",
        ]
        for qfile in expected:
            path = queries_dir / qfile
            self.assertTrue(path.exists(), f"Missing Athena query file: {path}")
            content = path.read_text(encoding="utf-8")
            self.assertIn("equity_lens.", content)

    def test_cdk_infra_files_compile(self) -> None:
        infra_dir = REPO_ROOT / "cloud" / "infra"
        self.assertTrue((infra_dir / "cdk.json").exists())
        self.assertTrue((infra_dir / "requirements.txt").exists())
        py_compile.compile(str(infra_dir / "lakehouse_stack.py"), doraise=True)
        py_compile.compile(str(infra_dir / "app.py"), doraise=True)


if __name__ == "__main__":
    unittest.main()
