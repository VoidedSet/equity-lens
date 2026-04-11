"""
Unified Data Loader for Financial Data
=======================================
Loads all enriched (and raw) CSVs for all companies into a structured dict.
Provides fuzzy matching for company names and metric names.
"""

import os
import pandas as pd
import numpy as np

BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Raw Data Extraction")

COMPANIES = [
    "Chalet_Hotels",
    "EIH_Limited",
    "Indian_Hotels",
    "Juniper_Hotels",
    "Lemon_Tree_Hotels",
]

# Aliases for fuzzy matching
COMPANY_ALIASES = {
    "chalet": "Chalet_Hotels",
    "chalet hotels": "Chalet_Hotels",
    "chalet_hotels": "Chalet_Hotels",
    "eih": "EIH_Limited",
    "eih limited": "EIH_Limited",
    "eih_limited": "EIH_Limited",
    "oberoi": "EIH_Limited",
    "indian hotels": "Indian_Hotels",
    "indian_hotels": "Indian_Hotels",
    "ihcl": "Indian_Hotels",
    "taj": "Indian_Hotels",
    "taj hotels": "Indian_Hotels",
    "juniper": "Juniper_Hotels",
    "juniper hotels": "Juniper_Hotels",
    "juniper_hotels": "Juniper_Hotels",
    "lemon tree": "Lemon_Tree_Hotels",
    "lemon_tree": "Lemon_Tree_Hotels",
    "lemon tree hotels": "Lemon_Tree_Hotels",
    "lemon_tree_hotels": "Lemon_Tree_Hotels",
    "lemontree": "Lemon_Tree_Hotels",
}

CSV_FILES = {
    "balance_sheet": "balance_sheet.csv",
    "balance_sheet_enriched": "balance_sheet_enriched.csv",
    "profit_loss": "profit_loss.csv",
    "profit_loss_enriched": "profit_loss_enriched.csv",
    "quarter_analysis": "Quarter_Analysis_Table.csv",
    "quarter_analysis_enriched": "quarter_analysis_enriched.csv",
    "cross_metrics": "cross_metrics.csv",
}


def resolve_company(name: str) -> str:
    """Resolve a user-typed company name to the canonical folder name."""
    key = name.strip().lower().replace("-", "_")

    # Direct match
    if key in COMPANY_ALIASES:
        return COMPANY_ALIASES[key]

    # Partial match
    for alias, canonical in COMPANY_ALIASES.items():
        if key in alias or alias in key:
            return canonical

    # Return as-is (let caller handle error)
    return name


def load_csv(filepath: str) -> pd.DataFrame:
    """Load a financial CSV (metrics as rows, periods as columns)."""
    if not os.path.exists(filepath):
        return pd.DataFrame()

    raw = pd.read_csv(filepath, index_col=0)
    raw.index.name = "Metric"
    return raw


def load_company_data(company: str) -> dict:
    """Load all available CSV files for a company."""
    canonical = resolve_company(company)
    company_dir = os.path.join(BASE_DIR, canonical)

    if not os.path.exists(company_dir):
        return {"error": f"Company folder not found: {canonical}", "company": canonical}

    data = {"company": canonical}
    for key, filename in CSV_FILES.items():
        filepath = os.path.join(company_dir, filename)
        df = load_csv(filepath)
        if not df.empty:
            data[key] = df

    return data


def load_all_companies() -> dict:
    """Load data for all companies."""
    all_data = {}
    for company in COMPANIES:
        all_data[company] = load_company_data(company)
    return all_data


def get_metric_across_companies(
    metric: str,
    source: str = "profit_loss_enriched",
    companies: list = None,
    period: str = None,
) -> pd.DataFrame:
    """
    Extract a single metric across multiple companies.

    Returns a DataFrame with companies as rows and periods as columns
    (or a single column if period is specified).
    """
    if companies is None:
        companies = COMPANIES
    else:
        companies = [resolve_company(c) for c in companies]

    rows = {}
    for company in companies:
        data = load_company_data(company)
        df = data.get(source)
        if df is None:
            continue

        # Fuzzy match metric name
        matched_metric = fuzzy_match_metric(metric, df.index.tolist())
        if matched_metric is None:
            continue

        row = df.loc[matched_metric]
        if period:
            if period in row.index:
                rows[company] = {period: row[period]}
            else:
                continue
        else:
            rows[company] = row.to_dict()

    return pd.DataFrame(rows).T


def fuzzy_match_metric(query: str, available: list) -> str:
    """Find the closest matching metric name."""
    query_lower = query.strip().lower()

    # Exact match
    for m in available:
        if m.lower() == query_lower:
            return m

    # Contains match
    for m in available:
        if query_lower in m.lower() or m.lower() in query_lower:
            return m

    # Word-based match
    query_words = set(query_lower.replace("_", " ").replace("-", " ").split())
    best_match = None
    best_score = 0
    for m in available:
        m_words = set(m.lower().replace("_", " ").replace("-", " ").replace("+", "").replace("%", "").split())
        score = len(query_words & m_words)
        if score > best_score:
            best_score = score
            best_match = m

    return best_match if best_score > 0 else None


def get_available_metrics(source: str = "profit_loss_enriched", company: str = None) -> list:
    """List all available metric names from a given source."""
    if company is None:
        company = COMPANIES[0]
    else:
        company = resolve_company(company)

    data = load_company_data(company)
    df = data.get(source)
    if df is None:
        return []
    return df.index.tolist()


def get_company_summary(company: str) -> dict:
    """Get a quick summary of available data for a company."""
    data = load_company_data(company)
    summary = {"company": data.get("company", company)}

    for key in CSV_FILES:
        if key in data:
            df = data[key]
            summary[key] = {
                "metrics": df.index.tolist(),
                "periods": df.columns.tolist(),
                "shape": df.shape,
            }

    return summary
