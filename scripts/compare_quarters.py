"""
Compare Quarters — Quarterly trend analysis for a single company
=================================================================
Usage: python scripts/compare_quarters.py <company> <metric> [--last N]

Examples:
    python scripts/compare_quarters.py Indian_Hotels "Sales +" --last 8
    python scripts/compare_quarters.py Chalet_Hotels "Net Profit Margin %"
"""

import sys
import os
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.data_loader import load_company_data, resolve_company, fuzzy_match_metric
from agent.chart_engine import line_chart, grouped_bar_chart
import pandas as pd
import numpy as np


def main():
    parser = argparse.ArgumentParser(description="Quarterly trend for a company")
    parser.add_argument("company", help="Company name")
    parser.add_argument("metric", help="Metric to track")
    parser.add_argument("--last", type=int, default=8, help="Number of recent quarters")
    args = parser.parse_args()

    company = resolve_company(args.company)
    data = load_company_data(company)

    # Try enriched first, then raw
    qa = data.get("quarter_analysis_enriched")
    if qa is None or (hasattr(qa, 'empty') and qa.empty):
        qa = data.get("quarter_analysis")
    if qa is None:
        print(json.dumps({"output": f"No quarterly data found for {company}", "error": True}))
        return

    matched_metric = fuzzy_match_metric(args.metric, qa.index.tolist())
    if matched_metric is None:
        print(json.dumps({
            "output": f"Metric '{args.metric}' not found. Available: {qa.index.tolist()[:15]}",
            "error": True,
        }))
        return

    # Get the series
    series = qa.loc[matched_metric].apply(pd.to_numeric, errors="coerce")

    # Take last N quarters
    series = series.tail(args.last)

    # Calculate QoQ and YoY changes
    qoq_changes = series.pct_change() * 100
    yoy_changes = series.pct_change(periods=4) * 100

    is_pct = "%" in matched_metric

    # Generate line chart
    chart_df = pd.DataFrame({company: series}).T
    chart_name = f"quarterly_{company}_{matched_metric.replace(' ', '_')[:20]}"

    chart_path = line_chart(
        chart_df,
        title=f"{company.replace('_', ' ')} — {matched_metric} (Quarterly)",
        ylabel=matched_metric,
        chart_name=chart_name,
        is_percentage=is_pct,
    )

    # Also create a bar chart
    bar_data = pd.DataFrame({company: series}).T
    chart_path_bar = grouped_bar_chart(
        bar_data,
        title=f"{company.replace('_', ' ')} — {matched_metric} (Quarterly)",
        ylabel=matched_metric,
        chart_name=f"{chart_name}_bar",
        is_percentage=is_pct,
    )

    result = {
        "output": f"Quarterly {matched_metric} for {company.replace('_', ' ')}:\n{series.to_string()}",
        "metric": matched_metric,
        "company": company,
        "quarters": list(series.index),
        "values": [float(v) if not np.isnan(v) else None for v in series.values],
        "chart_path": chart_path,
        "chart_path_bar": chart_path_bar,
        "analysis": {
            "latest": float(series.iloc[-1]) if not np.isnan(series.iloc[-1]) else None,
            "previous": float(series.iloc[-2]) if len(series) > 1 and not np.isnan(series.iloc[-2]) else None,
            "qoq_change_pct": float(qoq_changes.iloc[-1]) if not np.isnan(qoq_changes.iloc[-1]) else None,
            "yoy_change_pct": float(yoy_changes.iloc[-1]) if len(yoy_changes) > 0 and not np.isnan(yoy_changes.iloc[-1]) else None,
            "min": float(series.min()),
            "max": float(series.max()),
            "avg": float(series.mean()),
            "trend": "improving" if series.iloc[-1] > series.iloc[-3] else "declining" if len(series) > 2 else "stable",
        },
    }

    print(json.dumps(result, default=str))


if __name__ == "__main__":
    main()
