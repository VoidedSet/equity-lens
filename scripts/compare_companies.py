"""
Compare Companies — Cross-company metric comparison
=====================================================
Usage: python scripts/compare_companies.py <metric> <companies> [--source <source>] [--periods <periods>]

Examples:
    python scripts/compare_companies.py "Sales +" all
    python scripts/compare_companies.py "ROE %" "Chalet_Hotels,Indian_Hotels" --source cross_metrics
    python scripts/compare_companies.py "Net Profit Margin %" all --periods "Mar 2023,Mar 2024,Mar 2025"
"""

import sys
import os
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.data_loader import (
    load_company_data, resolve_company, COMPANIES,
    get_metric_across_companies, fuzzy_match_metric,
)
from agent.chart_engine import grouped_bar_chart, single_bar_chart
import pandas as pd
import numpy as np


# Auto-detect source based on metric name
METRIC_SOURCE_MAP = {
    "profit_loss_enriched": [
        "Sales +", "Expenses +", "Operating Profit", "OPM %", "Other Income +",
        "Interest", "Depreciation", "Profit before tax", "Tax %", "Net Profit +",
        "EPS in Rs", "Dividend Payout %", "EBITDA", "EBITDA Margin %",
        "Net Profit Margin %", "Interest Coverage Ratio", "Effective Tax Rate %",
        "EBIT", "Core Net Profit", "Cost-to-Income Ratio", "Depreciation to Sales %",
        "Interest to Sales %", "YoY Sales Growth %", "YoY Net Profit Growth %",
        "YoY Operating Profit Growth %",
    ],
    "balance_sheet_enriched": [
        "Equity Capital", "Reserves", "Borrowings +", "Other Liabilities +",
        "Total Liabilities", "Fixed Assets +", "CWIP", "Investments", "Other Assets +",
        "Total Assets", "Net Worth", "Debt-to-Equity Ratio", "Total Debt Ratio",
        "Equity Multiplier", "Fixed Assets to Total Assets %", "CWIP to Fixed Assets %",
        "Working Capital Proxy", "Net Fixed Assets", "Investments to Total Assets %",
        "Book Value per Share (Rs)", "YoY Asset Growth %", "YoY Debt Growth %",
        "YoY Net Worth Growth %",
    ],
    "cross_metrics": [
        "ROE %", "ROA %", "ROCE %", "Asset Turnover Ratio", "Fixed Asset Turnover",
        "DuPont - Net Margin %", "DuPont - Asset Turnover", "DuPont - Equity Multiplier",
        "Financial Leverage Ratio",
    ],
    "quarter_analysis_enriched": [
        "QoQ Sales Growth %", "QoQ Net Profit Growth %", "QoQ Operating Profit Growth %",
        "YoY Sales Growth %", "YoY Net Profit Growth %", "Trailing 4Q Sales",
        "Trailing 4Q Net Profit",
    ],
}


def detect_source(metric: str) -> str:
    """Auto-detect which CSV file contains the metric."""
    metric_lower = metric.lower()
    for source, metrics in METRIC_SOURCE_MAP.items():
        for m in metrics:
            if m.lower() == metric_lower or metric_lower in m.lower():
                return source
    return "profit_loss_enriched"  # default


def main():
    parser = argparse.ArgumentParser(description="Compare a metric across companies")
    parser.add_argument("metric", help="Metric to compare")
    parser.add_argument("companies", help="Comma-separated company names or 'all'")
    parser.add_argument("--source", default="auto", help="CSV source file key")
    parser.add_argument("--periods", default="", help="Comma-separated periods to show")
    args = parser.parse_args()

    # Resolve companies
    if args.companies.lower() == "all":
        companies = COMPANIES
    else:
        companies = [resolve_company(c.strip()) for c in args.companies.split(",")]

    # Detect source
    source = args.source if args.source != "auto" else detect_source(args.metric)

    # Load data
    comparison_data = {}
    matched_metric = None

    for company in companies:
        data = load_company_data(company)
        df = data.get(source)
        if df is None:
            continue

        if matched_metric is None:
            matched_metric = fuzzy_match_metric(args.metric, df.index.tolist())
        if matched_metric is None:
            continue

        row = df.loc[matched_metric]
        comparison_data[company] = row

    if not comparison_data:
        print(json.dumps({
            "output": f"No data found for metric '{args.metric}' in source '{source}'",
            "error": True,
        }))
        return

    # Build comparison DataFrame
    comp_df = pd.DataFrame(comparison_data).T
    comp_df = comp_df.apply(pd.to_numeric, errors="coerce")

    # Filter periods if specified
    if args.periods:
        selected = [p.strip() for p in args.periods.split(",")]
        available = [p for p in selected if p in comp_df.columns]
        if available:
            comp_df = comp_df[available]

    # Use last 5 periods by default (or fewer if not available)
    if comp_df.shape[1] > 5 and not args.periods:
        comp_df = comp_df.iloc[:, -5:]

    # Drop columns that are all NaN
    comp_df = comp_df.dropna(axis=1, how="all")

    # Determine if percentage metric
    is_pct = "%" in matched_metric or "ratio" in matched_metric.lower()

    # Generate chart
    chart_name = f"compare_{matched_metric.replace(' ', '_').replace('%', 'pct').replace('+', '')[:30]}"
    chart_path = grouped_bar_chart(
        comp_df,
        title=f"{matched_metric} — Company Comparison",
        ylabel=matched_metric,
        chart_name=chart_name,
        is_percentage=is_pct,
    )

    # Also generate a single-period bar chart if comparing for latest period
    latest_col = comp_df.columns[-1]
    latest_data = comp_df[latest_col].dropna().to_dict()

    if latest_data:
        chart_path_latest = single_bar_chart(
            latest_data,
            title=f"{matched_metric} — {latest_col}",
            ylabel=matched_metric,
            chart_name=f"{chart_name}_latest",
            is_percentage=is_pct,
            horizontal=True,
        )
    else:
        chart_path_latest = None

    # Output result
    result = {
        "output": comp_df.to_string(),
        "metric": matched_metric,
        "source": source,
        "companies": list(comp_df.index),
        "periods": list(comp_df.columns),
        "chart_path": chart_path,
        "chart_path_latest": chart_path_latest,
        "summary": {},
    }

    # Add summary stats
    for company in comp_df.index:
        vals = comp_df.loc[company].dropna()
        if len(vals) > 0:
            result["summary"][company] = {
                "latest": float(vals.iloc[-1]),
                "min": float(vals.min()),
                "max": float(vals.max()),
                "avg": float(vals.mean()),
            }

    print(json.dumps(result, default=str))


if __name__ == "__main__":
    main()
