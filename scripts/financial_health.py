"""
Financial Health Scorecard — Radar chart based assessment
==========================================================
Usage: python scripts/financial_health.py <company> [--year <year>]

Examples:
    python scripts/financial_health.py Chalet_Hotels
    python scripts/financial_health.py Indian_Hotels --year "Mar 2025"
"""

import sys
import os
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.data_loader import load_company_data, resolve_company
from agent.chart_engine import radar_chart, single_bar_chart
import pandas as pd
import numpy as np


def score_metric(value, low, high, higher_is_better=True):
    """
    Score a metric value on a 0-100 scale.
    low/high define the range for 20-80 score mapping.
    """
    if pd.isna(value) or value is None:
        return 50  # neutral

    if higher_is_better:
        if value <= low:
            return 10
        elif value >= high:
            return 95
        else:
            return 10 + (value - low) / (high - low) * 85
    else:
        # Lower is better (e.g., debt ratio)
        if value >= high:
            return 10
        elif value <= low:
            return 95
        else:
            return 95 - (value - low) / (high - low) * 85


def main():
    parser = argparse.ArgumentParser(description="Financial health scorecard")
    parser.add_argument("company", help="Company name")
    parser.add_argument("--year", default="", help="Year to evaluate")
    args = parser.parse_args()

    company = resolve_company(args.company)
    data = load_company_data(company)

    pl = data.get("profit_loss_enriched")
    bs = data.get("balance_sheet_enriched")
    cm = data.get("cross_metrics")

    if pl is None or bs is None:
        print(json.dumps({"output": f"Insufficient data for {company}", "error": True}))
        return

    # Determine year to evaluate
    if args.year:
        year = args.year
    else:
        # Use latest common year (exclude TTM)
        pl_cols = [c for c in pl.columns if c != "TTM"]
        bs_cols = list(bs.columns)
        common = [c for c in pl_cols if c in bs_cols]
        year = common[-1] if common else pl_cols[-1]

    # Extract key values
    def get_val(df, metric, col):
        if df is None or metric not in df.index or col not in df.columns:
            return None
        v = df.loc[metric, col]
        return float(v) if not pd.isna(v) else None

    opm = get_val(pl, "EBITDA Margin %", year)
    npm = get_val(pl, "Net Profit Margin %", year)
    icr = get_val(pl, "Interest Coverage Ratio", year)
    de = get_val(bs, "Debt-to-Equity Ratio", year)
    sales_growth = get_val(pl, "YoY Sales Growth %", year)
    np_growth = get_val(pl, "YoY Net Profit Growth %", year)
    roe = get_val(cm, "ROE %", year) if cm is not None and year in cm.columns else None
    roce = get_val(cm, "ROCE %", year) if cm is not None and year in cm.columns else None
    asset_turnover = get_val(cm, "Asset Turnover Ratio", year) if cm is not None and year in cm.columns else None
    cost_ratio = get_val(pl, "Cost-to-Income Ratio", year)

    # Score each dimension (0-100)
    scores = {
        "Profitability": np.mean([
            score_metric(opm, 15, 45, True),
            score_metric(npm, 5, 25, True),
            score_metric(roe, 5, 20, True) if roe else 50,
        ]),
        "Leverage": np.mean([
            score_metric(de, 0.2, 2.0, False),
            score_metric(icr, 1.5, 6.0, True),
        ]),
        "Efficiency": np.mean([
            score_metric(cost_ratio, 0.45, 0.85, False) if cost_ratio else 50,
            score_metric(asset_turnover, 0.1, 0.6, True) if asset_turnover else 50,
        ]),
        "Growth": np.mean([
            score_metric(sales_growth, 0, 40, True) if sales_growth else 50,
            score_metric(np_growth, 0, 60, True) if np_growth else 50,
        ]),
        "Returns": np.mean([
            score_metric(roe, 5, 20, True) if roe else 50,
            score_metric(roce, 8, 25, True) if roce else 50,
        ]),
        "Coverage": score_metric(icr, 1.5, 8.0, True),
    }

    # Round scores
    scores = {k: round(v, 1) for k, v in scores.items()}
    overall = round(np.mean(list(scores.values())), 1)

    # Generate radar chart
    chart_name = f"health_{company}_{year.replace(' ', '_')}"
    chart_path = radar_chart(
        scores,
        title=f"{company.replace('_', ' ')} — Financial Health ({year})",
        chart_name=chart_name,
    )

    # Generate bar chart of raw metrics
    raw_metrics = {
        "OPM %": opm,
        "NPM %": npm,
        "ROE %": roe,
        "ROCE %": roce,
        "D/E": de,
        "ICR": icr,
    }
    raw_metrics = {k: v for k, v in raw_metrics.items() if v is not None}

    result = {
        "output": f"Financial Health Scorecard for {company.replace('_', ' ')} ({year})\n"
                  f"Overall Score: {overall}/100\n\n"
                  f"Dimension Scores:\n" + "\n".join([f"  {k}: {v}/100" for k, v in scores.items()]),
        "company": company,
        "year": year,
        "overall_score": overall,
        "dimension_scores": scores,
        "raw_metrics": {k: v for k, v in raw_metrics.items()},
        "chart_path": chart_path,
        "health_grade": (
            "Excellent" if overall >= 80 else
            "Good" if overall >= 65 else
            "Average" if overall >= 50 else
            "Below Average" if overall >= 35 else
            "Poor"
        ),
    }

    print(json.dumps(result, default=str))


if __name__ == "__main__":
    main()
