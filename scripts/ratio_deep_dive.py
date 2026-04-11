"""
Ratio Deep Dive — DuPont decomposition & leverage analysis
============================================================
Usage: python scripts/ratio_deep_dive.py <company> [--year <year>]

Examples:
    python scripts/ratio_deep_dive.py Indian_Hotels
    python scripts/ratio_deep_dive.py Chalet_Hotels --year "Mar 2024"
"""

import sys
import os
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.data_loader import load_company_data, resolve_company
from agent.chart_engine import single_bar_chart, grouped_bar_chart, line_chart
import pandas as pd
import numpy as np


def main():
    parser = argparse.ArgumentParser(description="DuPont & ratio deep dive")
    parser.add_argument("company", help="Company name")
    parser.add_argument("--year", default="", help="Year to analyze")
    args = parser.parse_args()

    company = resolve_company(args.company)
    data = load_company_data(company)

    cm = data.get("cross_metrics")
    pl = data.get("profit_loss_enriched")
    bs = data.get("balance_sheet_enriched")

    if cm is None:
        print(json.dumps({"output": f"Cross metrics not found for {company}. Run feature_engineering.py first.", "error": True}))
        return

    # Determine year
    if args.year:
        year = args.year
    else:
        year = cm.columns[-1]

    if year not in cm.columns:
        print(json.dumps({
            "output": f"Year '{year}' not found. Available: {cm.columns.tolist()}",
            "error": True,
        }))
        return

    # Extract DuPont components
    def get_val(df, metric, col):
        if df is None or metric not in df.index or col not in df.columns:
            return None
        v = df.loc[metric, col]
        return float(v) if not pd.isna(v) else None

    roe = get_val(cm, "ROE %", year)
    roa = get_val(cm, "ROA %", year)
    roce = get_val(cm, "ROCE %", year)
    net_margin = get_val(cm, "DuPont - Net Margin %", year)
    asset_turnover = get_val(cm, "DuPont - Asset Turnover", year)
    equity_mult = get_val(cm, "DuPont - Equity Multiplier", year)
    fixed_asset_turnover = get_val(cm, "Fixed Asset Turnover", year)
    leverage = get_val(cm, "Financial Leverage Ratio", year)

    # DuPont bar chart
    dupont_data = {}
    if net_margin is not None:
        dupont_data["Net Margin %"] = net_margin
    if asset_turnover is not None:
        dupont_data["Asset Turnover"] = asset_turnover
    if equity_mult is not None:
        dupont_data["Equity Multiplier"] = equity_mult

    chart_path_dupont = None
    if dupont_data:
        chart_path_dupont = single_bar_chart(
            dupont_data,
            title=f"{company.replace('_', ' ')} — DuPont Decomposition ({year})",
            ylabel="Value",
            chart_name=f"dupont_{company}_{year.replace(' ', '_')}",
        )

    # Historical trend of ROE components
    chart_path_trend = None
    if len(cm.columns) > 1:
        trend_metrics = ["ROE %", "ROA %", "ROCE %"]
        available_trends = [m for m in trend_metrics if m in cm.index]
        if available_trends:
            trend_df = cm.loc[available_trends].apply(pd.to_numeric, errors="coerce")
            chart_path_trend = line_chart(
                trend_df,
                title=f"{company.replace('_', ' ')} — Return Ratios Over Time",
                ylabel="Percentage (%)",
                chart_name=f"returns_trend_{company}",
                is_percentage=True,
            )

    # Leverage analysis (from balance sheet)
    leverage_data = {}
    chart_path_leverage = None
    if bs is not None:
        for metric in ["Debt-to-Equity Ratio", "Total Debt Ratio", "Equity Multiplier"]:
            if metric in bs.index:
                series = bs.loc[metric].apply(pd.to_numeric, errors="coerce").dropna()
                if len(series) > 0:
                    leverage_data[metric] = series

    if leverage_data:
        lev_df = pd.DataFrame(leverage_data).T
        chart_path_leverage = line_chart(
            lev_df,
            title=f"{company.replace('_', ' ')} — Leverage Ratios Over Time",
            ylabel="Ratio",
            chart_name=f"leverage_{company}",
        )

    result = {
        "output": (
            f"Ratio Deep Dive for {company.replace('_', ' ')} ({year})\n\n"
            f"=== DuPont Decomposition ===\n"
            f"  ROE = Net Margin × Asset Turnover × Equity Multiplier\n"
            f"  ROE = {net_margin}% × {asset_turnover} × {equity_mult} = {roe}%\n\n"
            f"=== Key Ratios ===\n"
            f"  ROE: {roe}%\n"
            f"  ROA: {roa}%\n"
            f"  ROCE: {roce}%\n"
            f"  Fixed Asset Turnover: {fixed_asset_turnover}\n"
            f"  Financial Leverage: {leverage}x\n"
        ),
        "company": company,
        "year": year,
        "dupont": {
            "roe_pct": roe,
            "net_margin_pct": net_margin,
            "asset_turnover": asset_turnover,
            "equity_multiplier": equity_mult,
            "verification": round(net_margin * asset_turnover * equity_mult / 100, 2) if all(v is not None for v in [net_margin, asset_turnover, equity_mult]) else None,
        },
        "ratios": {
            "roe_pct": roe,
            "roa_pct": roa,
            "roce_pct": roce,
            "fixed_asset_turnover": fixed_asset_turnover,
            "financial_leverage": leverage,
        },
        "chart_path": chart_path_dupont,
        "chart_path_trend": chart_path_trend,
        "chart_path_leverage": chart_path_leverage,
    }

    print(json.dumps(result, default=str))


if __name__ == "__main__":
    main()
