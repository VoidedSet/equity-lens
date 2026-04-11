"""
Tool Registry — Maps LLM tool calls to script execution
=========================================================
Routes tool calls to pre-built scripts and handles dynamic code generation.
"""

import os
import sys
import json
import subprocess
import traceback
import tempfile

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.data_loader import resolve_company, COMPANIES

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def execute_tool(tool_name: str, args: dict) -> dict:
    """
    Execute a tool by name with the given arguments.
    Returns a dict with 'output' (text data) and optionally 'chart_path'.
    """
    tool_map = {
        "compare_companies": run_compare_companies,
        "compare_quarters": run_compare_quarters,
        "financial_health": run_financial_health,
        "trend_analysis": run_trend_analysis,
        "ratio_deep_dive": run_ratio_deep_dive,
        "sector_benchmark": run_sector_benchmark,
        "custom_analysis": run_custom_analysis,
    }

    handler = tool_map.get(tool_name)
    if handler is None:
        return {"output": f"Unknown tool: {tool_name}", "error": True}

    try:
        return handler(args)
    except Exception as e:
        return {
            "output": f"Tool execution error: {str(e)}\n{traceback.format_exc()}",
            "error": True,
        }


def _run_script(script_name: str, cli_args: list) -> dict:
    """Run a script from the scripts/ directory and capture its output."""
    script_path = os.path.join(SCRIPTS_DIR, script_name)

    if not os.path.exists(script_path):
        return {"output": f"Script not found: {script_path}", "error": True}

    cmd = [sys.executable, script_path] + cli_args

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=PROJECT_ROOT,
        )

        output = result.stdout.strip()
        if result.stderr:
            output += f"\n[STDERR]: {result.stderr.strip()}"

        # Try to parse as JSON
        try:
            parsed = json.loads(output.split("\n")[-1] if "\n" in output else output)
            return parsed
        except json.JSONDecodeError:
            # Not JSON, return as text
            return {"output": output, "chart_path": _find_latest_chart()}

    except subprocess.TimeoutExpired:
        return {"output": "Script timed out after 60 seconds", "error": True}
    except Exception as e:
        return {"output": f"Failed to run script: {e}", "error": True}


def _find_latest_chart() -> str:
    """Find the most recently created chart in the output directory."""
    charts = []
    for f in os.listdir(OUTPUT_DIR):
        if f.endswith(".png"):
            path = os.path.join(OUTPUT_DIR, f)
            charts.append((os.path.getmtime(path), path))

    if charts:
        charts.sort(reverse=True)
        return charts[0][1]
    return None


# ─── Tool Handlers ───────────────────────────────────────────────────────────

def run_compare_companies(args: dict) -> dict:
    """Execute the compare_companies script."""
    metric = args.get("metric", "Sales +")
    companies = args.get("companies", "all")
    source = args.get("source", "auto")
    periods = args.get("periods", "")

    cli_args = [metric, companies]
    if source and source != "auto":
        cli_args += ["--source", source]
    if periods:
        cli_args += ["--periods", periods]

    return _run_script("compare_companies.py", cli_args)


def run_compare_quarters(args: dict) -> dict:
    """Execute the compare_quarters script."""
    company = resolve_company(args.get("company", "Indian_Hotels"))
    metric = args.get("metric", "Sales +")
    last_n = str(args.get("last_n", 8))

    return _run_script("compare_quarters.py", [company, metric, "--last", last_n])


def run_financial_health(args: dict) -> dict:
    """Execute the financial_health script."""
    company = resolve_company(args.get("company", "Indian_Hotels"))
    year = args.get("year", "")

    cli_args = [company]
    if year:
        cli_args += ["--year", year]

    return _run_script("financial_health.py", cli_args)


def run_trend_analysis(args: dict) -> dict:
    """Execute the trend_analysis script."""
    company = resolve_company(args.get("company", "Indian_Hotels"))
    metric = args.get("metric", "Sales +")
    source = args.get("source", "auto")

    cli_args = [company, metric]
    if source and source != "auto":
        cli_args += ["--source", source]

    return _run_script("trend_analysis.py", cli_args)


def run_ratio_deep_dive(args: dict) -> dict:
    """Execute the ratio_deep_dive script."""
    company = resolve_company(args.get("company", "Indian_Hotels"))
    year = args.get("year", "")

    cli_args = [company]
    if year:
        cli_args += ["--year", year]

    return _run_script("ratio_deep_dive.py", cli_args)


def run_sector_benchmark(args: dict) -> dict:
    """Execute the sector_benchmark script."""
    year = args.get("year", "")
    metrics = args.get("metrics", "")

    cli_args = []
    if year:
        cli_args += ["--year", year]
    if metrics:
        cli_args += ["--metrics", metrics]

    return _run_script("sector_benchmark.py", cli_args)


def run_custom_analysis(args: dict) -> dict:
    """
    Generate and execute a custom Python script for novel queries.
    The LLM provides an analysis plan that we convert to executable code.
    """
    query = args.get("query", "")
    plan = args.get("analysis_plan", "")

    # Build a safe custom script
    script_code = f'''
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import json

from agent.data_loader import load_company_data, load_all_companies, get_metric_across_companies, COMPANIES, resolve_company
from agent.chart_engine import (
    grouped_bar_chart, line_chart, single_bar_chart, heatmap_chart, radar_chart,
    COMPANY_COLORS, OUTPUT_DIR
)

# Analysis plan: {plan}
# Query: {query}

try:
    all_data = load_all_companies()
    results = {{}}

    # Execute the analysis plan
    {_indent_plan(plan)}

    print(json.dumps({{"output": str(results), "chart_path": None}}, default=str))

except Exception as e:
    print(json.dumps({{"output": f"Custom analysis error: {{e}}", "error": True}}))
'''

    # Write to a temp file and execute
    temp_path = os.path.join(OUTPUT_DIR, "_custom_analysis.py")
    with open(temp_path, "w") as f:
        f.write(script_code)

    try:
        result = subprocess.run(
            [sys.executable, temp_path],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=PROJECT_ROOT,
        )

        output = result.stdout.strip()
        if result.stderr:
            output += f"\n[STDERR]: {result.stderr.strip()}"

        try:
            return json.loads(output.split("\n")[-1])
        except json.JSONDecodeError:
            return {"output": output, "chart_path": _find_latest_chart()}

    except Exception as e:
        return {"output": f"Custom script error: {e}", "error": True}
    finally:
        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)


def _indent_plan(plan: str) -> str:
    """Convert analysis plan text into a basic data-loading snippet."""
    # Since the LLM plan is descriptive, we provide a general-purpose template
    return """
    # Load data for all companies
    for company in COMPANIES:
        data = all_data[company]
        pl = data.get("profit_loss_enriched")
        bs = data.get("balance_sheet_enriched")
        qa = data.get("quarter_analysis_enriched")
        cm = data.get("cross_metrics")

        latest_cols = []
        if pl is not None and len(pl.columns) > 0:
            latest_cols = pl.columns[-3:].tolist()

        results[company] = {
            "available_data": list(data.keys()),
            "latest_periods": latest_cols,
        }

        if pl is not None:
            results[company]["latest_sales"] = str(pl.loc["Sales +"].iloc[-1]) if "Sales +" in pl.index else "N/A"
            results[company]["latest_net_profit"] = str(pl.loc["Net Profit +"].iloc[-1]) if "Net Profit +" in pl.index else "N/A"

        if cm is not None:
            results[company]["latest_roe"] = str(cm.loc["ROE %"].iloc[-1]) if "ROE %" in cm.index else "N/A"
    """
