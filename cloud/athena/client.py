"""Read-only Amazon Athena query client and local curated Parquet preset fallback."""

import os
import re
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

from cloud.common.companies import normalize_company_id
from cloud.common.config import REPO_ROOT, CloudConfig, get_config
from cloud.common.storage import StorageBackend, get_storage
from cloud.glue_jobs.lib.spark_utils import read_curated_parquet

QUERIES_DIR = REPO_ROOT / "cloud" / "athena" / "queries"

PRESET_QUERIES: Dict[str, Path] = {
    "cross_company_financials": QUERIES_DIR / "01_cross_company_financials.sql",
    "guidance_hit_rate": QUERIES_DIR / "02_guidance_hit_rate.sql",
    "risk_severity_summary": QUERIES_DIR / "03_risk_severity_summary.sql",
    "deviation_trends": QUERIES_DIR / "04_deviation_trends.sql",
}

_FORBIDDEN_SQL_RE = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE|MERGE|GRANT|REVOKE|MSCK)\b",
    re.IGNORECASE,
)


def validate_readonly_sql(sql: str) -> str:
    """Ensure SQL is a single read-only SELECT/WITH statement without DDL/DML keywords."""
    if not isinstance(sql, str):
        raise ValueError("SQL must be a string")
    cleaned = sql.strip()
    while cleaned.endswith(";"):
        cleaned = cleaned[:-1].strip()
    if not cleaned:
        raise ValueError("SQL query cannot be empty")
    if ";" in cleaned:
        raise ValueError("Multi-statement SQL queries are not allowed")
    if not re.match(r"^(SELECT|WITH)\b", cleaned, re.IGNORECASE):
        raise ValueError("Only read-only SELECT or WITH queries are permitted")
    if _FORBIDDEN_SQL_RE.search(cleaned):
        raise ValueError("Forbidden DDL/DML keyword detected in SQL query")
    return cleaned


class AthenaClient:
    """Lazy boto3 Amazon Athena client executing validated read-only SQL queries."""

    def __init__(
        self,
        database: str = "equity_lens",
        workgroup: str = "equity-lens-analytics-dev",
        output_location: Optional[str] = None,
        region: str = "ap-south-1",
        client: Any = None,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self.database = database
        self.workgroup = workgroup
        self.output_location = output_location
        self.region = region
        self._client = client
        self.sleep_fn = sleep_fn

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        import boto3

        self._client = boto3.client("athena", region_name=self.region)
        return self._client

    def execute_query(
        self,
        sql: str,
        max_rows: int = 100,
        poll_interval: float = 0.5,
        timeout_seconds: float = 60.0,
    ) -> Dict[str, Any]:
        validated_sql = validate_readonly_sql(sql)
        client = self._get_client()

        start_kwargs: Dict[str, Any] = {
            "QueryString": validated_sql,
            "QueryExecutionContext": {"Database": self.database},
            "WorkGroup": self.workgroup,
        }
        if self.output_location:
            start_kwargs["ResultConfiguration"] = {"OutputLocation": self.output_location}

        start_resp = client.start_query_execution(**start_kwargs)
        query_id = start_resp["QueryExecutionId"]

        deadline = time.monotonic() + timeout_seconds
        state = "QUEUED"
        reason = ""
        while True:
            exec_resp = client.get_query_execution(QueryExecutionId=query_id)
            status = exec_resp["QueryExecution"]["Status"]
            state = status["State"]
            if state == "SUCCEEDED":
                break
            if state in ("FAILED", "CANCELLED"):
                reason = status.get("StateChangeReason", state)
                raise RuntimeError(f"Athena query {query_id} {state}: {reason}")
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Athena query {query_id} timed out after {timeout_seconds}s")
            self.sleep_fn(poll_interval)

        res_resp = client.get_query_results(QueryExecutionId=query_id, MaxResults=max(2, max_rows + 1))
        raw_rows = res_resp.get("ResultSet", {}).get("Rows", [])
        if not raw_rows:
            return {
                "engine": "athena",
                "query_execution_id": query_id,
                "columns": [],
                "rows": [],
                "row_count": 0,
            }

        columns = [cell.get("VarCharValue", "") for cell in raw_rows[0].get("Data", [])]
        parsed_rows: List[Dict[str, Any]] = []
        for raw_row in raw_rows[1 : max_rows + 1]:
            cells = raw_row.get("Data", [])
            row_dict = {
                col: (cells[idx].get("VarCharValue") if idx < len(cells) else None)
                for idx, col in enumerate(columns)
            }
            parsed_rows.append(row_dict)

        return {
            "engine": "athena",
            "query_execution_id": query_id,
            "columns": columns,
            "rows": parsed_rows,
            "row_count": len(parsed_rows),
        }


def query_local_curated_preset(
    preset: str,
    storage: StorageBackend,
    company: Optional[str] = None,
) -> Dict[str, Any]:
    """Offline fallback computing the 4 Athena preset queries from local curated/ Parquet."""
    if preset not in PRESET_QUERIES:
        raise ValueError(f"Unknown Athena preset {preset!r}. Choose one of: {', '.join(PRESET_QUERIES)}")

    company_filter = normalize_company_id(company) if company and company.upper() != "ALL" else None

    if preset == "cross_company_financials":
        fin_rows = read_curated_parquet("financials", storage)
        annual_fy = [
            r
            for r in fin_rows
            if r.get("period_type") == "annual"
            and str(r.get("period") or "").startswith("FY")
            and (not company_filter or r.get("company_id") == company_filter)
        ]
        latest_by_cm: Dict[tuple, Dict[str, Any]] = {}
        for r in sorted(annual_fy, key=lambda x: str(x.get("period") or "")):
            latest_by_cm[(r["company_id"], r["metric"])] = r

        per_company: Dict[str, Dict[str, Any]] = defaultdict(dict)
        for (cid, metric), r in latest_by_cm.items():
            per_company[cid]["company_id"] = cid
            if metric == "revenue":
                per_company[cid]["latest_period"] = r.get("period")
                per_company[cid]["revenue_cr"] = r.get("value")
                per_company[cid]["revenue_yoy_pct"] = r.get("yoy_change")
            elif metric == "operating_profit":
                per_company[cid]["operating_profit_cr"] = r.get("value")
            elif metric == "opm":
                per_company[cid]["opm_pct"] = r.get("value")
            elif metric == "net_profit":
                per_company[cid]["net_profit_cr"] = r.get("value")
            elif metric == "interest":
                per_company[cid]["interest_cr"] = r.get("value")
            elif metric == "borrowings":
                per_company[cid]["borrowings_cr"] = r.get("value")
            elif metric == "revpar":
                per_company[cid]["revpar_inr"] = r.get("value")

        columns = [
            "company_id", "latest_period", "revenue_cr", "revenue_yoy_pct",
            "operating_profit_cr", "opm_pct", "net_profit_cr",
            "borrowings_cr", "revpar_inr", "interest_coverage",
        ]
        rows: List[Dict[str, Any]] = []
        for cid, data in per_company.items():
            op = data.get("operating_profit_cr")
            intr = data.get("interest_cr")
            icr = round(float(op) / float(intr), 2) if (op is not None and intr not in (None, 0)) else None
            data["interest_coverage"] = icr
            rows.append({col: data.get(col) for col in columns})
        rows.sort(key=lambda r: float(r["revenue_cr"]) if r.get("revenue_cr") is not None else -1.0, reverse=True)
        return {"engine": "local_curated", "columns": columns, "rows": rows, "row_count": len(rows)}

    if preset == "guidance_hit_rate":
        cred_rows = read_curated_parquet("credibility_scores", storage)
        dev_rows = read_curated_parquet("deviation_tracker", storage)
        if company_filter:
            cred_rows = [r for r in cred_rows if r.get("company_id") == company_filter]
            dev_rows = [r for r in dev_rows if r.get("company_id") == company_filter]

        dev_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: {"BEAT": 0, "IN-LINE": 0, "MISS": 0})
        for d in dev_rows:
            flag = d.get("flag")
            if flag in ("BEAT", "IN-LINE", "MISS"):
                dev_counts[d["company_id"]][flag] += 1

        columns = [
            "company_id", "overall_score", "hit_rate", "avg_deviation",
            "consecutive_misses", "trend", "total_matched_count",
            "beats", "in_lines", "misses",
        ]
        rows = []
        for c in cred_rows:
            cid = c["company_id"]
            counts = dev_counts[cid]
            rows.append(
                {
                    "company_id": cid,
                    "overall_score": c.get("overall_score"),
                    "hit_rate": c.get("hit_rate"),
                    "avg_deviation": c.get("avg_deviation"),
                    "consecutive_misses": c.get("consecutive_misses"),
                    "trend": c.get("trend"),
                    "total_matched_count": c.get("total_matched_count"),
                    "beats": counts["BEAT"],
                    "in_lines": counts["IN-LINE"],
                    "misses": counts["MISS"],
                }
            )
        rows.sort(key=lambda r: float(r["overall_score"]) if r.get("overall_score") is not None else -1.0, reverse=True)
        return {"engine": "local_curated", "columns": columns, "rows": rows, "row_count": len(rows)}

    if preset == "risk_severity_summary":
        risk_rows = read_curated_parquet("risk_flags", storage)
        if company_filter:
            risk_rows = [r for r in risk_rows if r.get("company_id") == company_filter]

        grouped: Dict[tuple, List[str]] = defaultdict(list)
        for r in risk_rows:
            grouped[(r["company_id"], r.get("category"), r.get("severity"))].append(str(r.get("period") or ""))

        sev_order = {"critical": 1, "high": 2, "medium": 3}
        columns = ["company_id", "category", "severity", "flag_count", "earliest_period", "latest_period"]
        rows = []
        for (cid, cat, sev), periods in grouped.items():
            non_empty = [p for p in periods if p]
            rows.append(
                {
                    "company_id": cid,
                    "category": cat,
                    "severity": sev,
                    "flag_count": len(periods),
                    "earliest_period": min(non_empty) if non_empty else None,
                    "latest_period": max(non_empty) if non_empty else None,
                }
            )
        rows.sort(key=lambda r: (str(r["company_id"]), sev_order.get(str(r["severity"]), 9), -int(r["flag_count"])))
        return {"engine": "local_curated", "columns": columns, "rows": rows, "row_count": len(rows)}

    # deviation_trends
    dev_rows = read_curated_parquet("deviation_tracker", storage)
    if company_filter:
        dev_rows = [r for r in dev_rows if r.get("company_id") == company_filter]
    columns = [
        "company_id", "period", "metric_type", "check_type", "guided_value",
        "actual_value", "delta", "delta_pct", "flag", "severity", "pattern",
        "source_guidance", "source_actual",
    ]
    rows = [{col: r.get(col) for col in columns} for r in dev_rows]
    rows.sort(key=lambda r: (str(r["company_id"]), str(r["period"])), reverse=False)
    return {"engine": "local_curated", "columns": columns, "rows": rows, "row_count": len(rows)}


def query_lakehouse(
    sql: Optional[str] = None,
    preset: Optional[str] = None,
    company: Optional[str] = None,
    config: Optional[CloudConfig] = None,
    athena_client: Optional[AthenaClient] = None,
    storage: Optional[StorageBackend] = None,
    max_rows: int = 100,
) -> Dict[str, Any]:
    """Query curated tables via Amazon Athena when in S3 mode or via local Parquet presets offline."""
    cfg = config or get_config()
    athena_mode = os.getenv("ATHENA_MODE", "auto").strip().lower()
    use_athena = athena_client is not None or (cfg.storage_backend == "s3" and athena_mode != "local")

    if use_athena:
        client = athena_client or AthenaClient(
            database=os.getenv("ATHENA_DATABASE", "equity_lens"),
            workgroup=os.getenv("ATHENA_WORKGROUP", "equity-lens-analytics-dev"),
            output_location=f"s3://{cfg.s3_bucket}/athena-results/",
            region=cfg.aws_region,
        )
        if preset:
            if preset not in PRESET_QUERIES:
                raise ValueError(f"Unknown preset: {preset!r}")
            target_sql = PRESET_QUERIES[preset].read_text(encoding="utf-8")
        elif sql:
            target_sql = sql
        else:
            raise ValueError("Either 'preset' or 'sql' must be provided")
        return client.execute_query(target_sql, max_rows=max_rows)

    store = storage or get_storage(cfg)
    if preset:
        return query_local_curated_preset(preset=preset, storage=store, company=company)
    if sql:
        validate_readonly_sql(sql)
        raise RuntimeError(
            "Custom SQL requires STORAGE_BACKEND=s3 (Amazon Athena). In local mode, pass a 'preset' name."
        )
    raise ValueError("Either 'preset' or 'sql' must be provided")


def format_rows_as_markdown(
    columns: Sequence[str],
    rows: Sequence[Dict[str, Any]],
    max_display: int = 25,
) -> str:
    """Format query output rows as a clean Markdown table for agent synthesis."""
    if not columns or not rows:
        return "_No rows returned._"
    header = "| " + " | ".join(str(c) for c in columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    lines = [header, sep]
    for row in list(rows)[:max_display]:
        vals = [str(row.get(c) if row.get(c) is not None else "") for c in columns]
        lines.append("| " + " | ".join(vals) + " |")
    if len(rows) > max_display:
        lines.append(f"\n_Showing {max_display} of {len(rows)} rows._")
    return "\n".join(lines)
