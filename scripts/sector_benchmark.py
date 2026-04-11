"""
Sector Benchmark — Rank all companies across key KPIs
=======================================================
Usage: python scripts/sector_benchmark.py [--year <year>] [--metrics <metrics>]

Examples:
    python scripts/sector_benchmark.py
    python scripts/sector_benchmark.py --year "Mar 2025"
    python scripts/sector_benchmark.py --metrics "Sales +,Net Profit Margin %,ROE %"
"""

import sys
import os
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.data_loader import load_company_data, COMPANIES, fuzzy_match_metric
from agent.chart_engine import heatmap_chart, single_bar_chart
import pandas as pd
import numpy as np


# Default KPIs for sector ranking
DEFAULT_METRICS = [
    ("Sales +", "profit_loss_enriched", "Revenue (₹Cr)"),
    ("EBITDA Margin %", "profit_loss_enriched", "EBITDA Margin"),
    ("Net Profit Margin %", "profit_loss_enriched", "Net Margin"),
    ("Interest Coverage Ratio", "profit_loss_enriched", "Interest Coverage"),
    ("Debt-to-Equity Ratio", "balance_sheet_enriched", "D/E Ratio"),
    ("ROE %", "cross_metrics", "ROE"),
    ("ROCE %", "cross_metrics", "ROCE"),
]


def main():
    parser = argparse.ArgumentParser(description="Sector benchmark ranking")
    parser.add_argument("--year", default="", help="Year for comparison")
    parser.add_argument("--metrics", default="", help="Comma-separated metrics")
    args = parser.parse_args()

    # Load all company data
    all_data = {}
    for company in COMPANIES:
        all_data[company] = load_company_data(company)

    # Determine which year to use
    if args.year:
        year = args.year
    else:
        # Use the latest common year
        year = "Mar 2025"  # Most likely latest for all

    # Determine metrics
    if args.metrics:
        custom_metrics = [m.strip() for m in args.metrics.split(",")]
        metrics_list = []
        for m in custom_metrics:
            # Auto-detect source
            for source in ["profit_loss_enriched", "balance_sheet_enriched", "cross_metrics"]:
                for company in COMPANIES:
                    df = all_data[company].get(source)
                    if df is not None:
                        match = fuzzy_match_metric(m, df.index.tolist())
                        if match:
                            metrics_list.append((match, source, match))
                            break
                else:
                    continue
                break
    else:
        metrics_list = DEFAULT_METRICS

    # Build the ranking matrix
    ranking_data = {}

    for company in COMPANIES:
        company_data = all_data[company]
        row = {}

        for metric_name, source, display_name in metrics_list:
            df = company_data.get(source)
            if df is None:
                row[display_name] = np.nan
                continue

            matched = fuzzy_match_metric(metric_name, df.index.tolist())
            if matched is None:
                row[display_name] = np.nan
                continue

            # Try the specified year
            if year in df.columns:
                val = df.loc[matched, year]
            else:
                # Use the latest available
                val = df.loc[matched].iloc[-1]

            try:
                row[display_name] = float(val) if not pd.isna(val) else np.nan
            except (ValueError, TypeError):
                row[display_name] = np.nan

        ranking_data[company] = row

    ranking_df = pd.DataFrame(ranking_data).T

    # Generate heatmap
    chart_path = heatmap_chart(
        ranking_df,
        title=f"Hotel Sector Benchmark — {year}",
        chart_name=f"sector_benchmark_{year.replace(' ', '_')}",
        fmt=".1f",
    )

    # Rank each metric (1=best)
    rankings = pd.DataFrame(index=ranking_df.index, columns=ranking_df.columns)
    lower_is_better = {"D/E Ratio"}  # metrics where lower value = better rank

    for col in ranking_df.columns:
        vals = ranking_df[col].dropna()
        if col in lower_is_better:
            ranks = vals.rank(ascending=True)
        else:
            ranks = vals.rank(ascending=False)
        rankings[col] = ranks

    # Calculate overall rank (avg of all ranks)
    rankings["Overall Rank"] = rankings.mean(axis=1).round(1)
    rankings = rankings.sort_values("Overall Rank")

    # Generate overall ranking bar chart
    overall_scores = rankings["Overall Rank"].to_dict()
    # Invert so lower rank = higher bar (better)
    max_rank = max(overall_scores.values())
    inverted = {k: max_rank - v + 1 for k, v in overall_scores.items()}

    chart_path_overall = single_bar_chart(
        inverted,
        title=f"Overall Company Ranking — {year}",
        ylabel="Score (higher = better)",
        chart_name=f"overall_ranking_{year.replace(' ', '_')}",
        horizontal=True,
    )

    result = {
        "output": (
            f"Sector Benchmark — {year}\n\n"
            f"=== Raw Values ===\n{ranking_df.to_string()}\n\n"
            f"=== Rankings (1=Best) ===\n{rankings.to_string()}"
        ),
        "year": year,
        "raw_values": ranking_df.to_dict(),
        "rankings": rankings.to_dict(),
        "overall_rank": rankings["Overall Rank"].to_dict(),
        "chart_path": chart_path,
        "chart_path_overall": chart_path_overall,
        "best_company": rankings.index[0],
        "worst_company": rankings.index[-1],
    }

    print(json.dumps(result, default=str))


if __name__ == "__main__":
    main()
