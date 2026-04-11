"""
Trend Analysis — Multi-year trend for any metric
==================================================
Usage: python scripts/trend_analysis.py <company> <metric> [--source <source>]

Examples:
    python scripts/trend_analysis.py Indian_Hotels "Sales +"
    python scripts/trend_analysis.py EIH_Limited "ROE %" --source cross_metrics
"""

import sys
import os
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.data_loader import load_company_data, resolve_company, fuzzy_match_metric
from agent.chart_engine import line_chart
import pandas as pd
import numpy as np


def detect_source(metric: str, data: dict) -> str:
    """Auto-detect source based on metric availability."""
    for source_key in ["profit_loss_enriched", "balance_sheet_enriched",
                       "cross_metrics", "quarter_analysis_enriched"]:
        df = data.get(source_key)
        if df is not None:
            match = fuzzy_match_metric(metric, df.index.tolist())
            if match:
                return source_key
    return "profit_loss_enriched"


def main():
    parser = argparse.ArgumentParser(description="Multi-year trend analysis")
    parser.add_argument("company", help="Company name")
    parser.add_argument("metric", help="Metric to track")
    parser.add_argument("--source", default="auto", help="CSV source")
    args = parser.parse_args()

    company = resolve_company(args.company)
    data = load_company_data(company)

    # Auto-detect or use specified source
    source = args.source if args.source != "auto" else detect_source(args.metric, data)

    df = data.get(source)
    if df is None:
        print(json.dumps({"output": f"Source '{source}' not found for {company}", "error": True}))
        return

    matched_metric = fuzzy_match_metric(args.metric, df.index.tolist())
    if matched_metric is None:
        print(json.dumps({
            "output": f"Metric '{args.metric}' not found in {source}. Available: {df.index.tolist()[:15]}",
            "error": True,
        }))
        return

    series = df.loc[matched_metric].apply(pd.to_numeric, errors="coerce")

    # Filter out TTM for cleaner trend
    if "TTM" in series.index:
        series = series.drop("TTM")

    # Remove NaN values
    series = series.dropna()

    if len(series) == 0:
        print(json.dumps({"output": f"No data available for {matched_metric}", "error": True}))
        return

    is_pct = "%" in matched_metric or "ratio" in matched_metric.lower()

    # Generate trend line chart
    chart_df = pd.DataFrame({company: series}).T
    chart_name = f"trend_{company}_{matched_metric.replace(' ', '_')[:20]}"

    chart_path = line_chart(
        chart_df,
        title=f"{company.replace('_', ' ')} — {matched_metric} Trend",
        ylabel=matched_metric,
        chart_name=chart_name,
        is_percentage=is_pct,
    )

    # Calculate trend statistics
    values = series.values.astype(float)
    cagr = None
    if len(values) > 1 and values[0] > 0 and values[-1] > 0:
        n_years = len(values) - 1
        cagr = round(((values[-1] / values[0]) ** (1 / n_years) - 1) * 100, 2)

    result = {
        "output": f"Trend: {matched_metric} for {company.replace('_', ' ')}\n{series.to_string()}",
        "metric": matched_metric,
        "company": company,
        "source": source,
        "periods": list(series.index),
        "values": [float(v) for v in values],
        "chart_path": chart_path,
        "statistics": {
            "start_value": float(values[0]),
            "end_value": float(values[-1]),
            "min": float(values.min()),
            "max": float(values.max()),
            "avg": float(values.mean()),
            "cagr_pct": cagr,
            "total_change_pct": round((values[-1] - values[0]) / abs(values[0]) * 100, 2) if values[0] != 0 else None,
        },
    }

    print(json.dumps(result, default=str))


if __name__ == "__main__":
    main()
