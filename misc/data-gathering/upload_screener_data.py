"""
Upload Screener.in CSV data to Supabase financials table.
Reads profit_loss.csv, balance_sheet.csv, Quarter_Analysis_Table.csv
for each company and inserts into the financials table.

Usage: python upload_screener_data.py
"""

import os
import csv
from supabase import create_client

SUPABASE_URL = "https://nzofdwwcouzfpacapvmz.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im56b2Zkd3djb3V6ZnBhY2Fwdm16Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTg5NDE5OCwiZXhwIjoyMDkxNDcwMTk4fQ.YB0xsa4EOKjK0O3Vtgi23ffVdU3yAeEzPeW503Tqi4I"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

RAW_DATA_ROOT = os.path.join(os.path.dirname(__file__), "Raw Data Extraction")

COMPANY_MAP = {
    "IHCL": "Indian_Hotels",
    "CHALET": "Chalet_Hotels",
    "LEMONTREE": "Lemon_Tree_Hotels",
    "EIH": "EIH_Limited",
    "JUNIPER": "Juniper_Hotels",
}

# ─── Metric name mapping ───
PL_METRIC_MAP = {
    "Sales +": "revenue",
    "Expenses +": "expenses",
    "Operating Profit": "operating_profit",
    "OPM %": "opm",
    "Other Income +": "other_income",
    "Interest": "interest",
    "Depreciation": "depreciation",
    "Profit before tax": "pbt",
    "Tax %": "tax_rate",
    "Net Profit +": "net_profit",
    "EPS in Rs": "eps",
    "Dividend Payout %": "dividend_payout",
}

BS_METRIC_MAP = {
    "Equity Capital": "equity_capital",
    "Reserves": "reserves",
    "Borrowings +": "borrowings",
    "Other Liabilities +": "other_liabilities",
    "Total Liabilities": "total_liabilities",
    "Fixed Assets +": "fixed_assets",
    "CWIP": "cwip",
    "Investments": "investments",
    "Other Assets +": "other_assets",
    "Total Assets": "total_assets",
}

# ─── Period conversion ───
def mar_to_fy(col: str) -> str:
    """Convert 'Mar 2025' -> 'FY25', 'Mar 2014' -> 'FY14'"""
    parts = col.split()
    if len(parts) == 2 and parts[0] == "Mar":
        year = parts[1]
        return f"FY{year[-2:]}"
    return col

def quarter_to_period(col: str) -> str:
    """Convert 'Dec 2024' -> 'Q3 FY25', 'Sep 2024' -> 'Q2 FY25'"""
    parts = col.split()
    if len(parts) != 2:
        return col
    month, year = parts[0], int(parts[1])
    quarter_map = {
        "Jun": (f"Q1 FY{str(year + 1)[-2:]}", "quarterly"),
        "Sep": (f"Q2 FY{str(year + 1)[-2:]}", "quarterly"),
        "Dec": (f"Q3 FY{str(year + 1)[-2:]}", "quarterly"),
        "Mar": (f"Q4 FY{str(year)[-2:]}", "quarterly"),
    }
    result = quarter_map.get(month)
    return result[0] if result else col

def parse_value(val: str):
    """Parse a CSV value to float, handling %, commas, empty."""
    if not val or val.strip() == "":
        return None
    cleaned = val.replace("%", "").replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None

def get_unit(metric_key: str) -> str:
    """Get unit for a metric."""
    if metric_key in ("opm", "tax_rate", "dividend_payout"):
        return "%"
    if metric_key == "eps":
        return "INR"
    if metric_key in ("equity_capital", "reserves", "borrowings", "other_liabilities",
                       "total_liabilities", "fixed_assets", "cwip", "investments",
                       "other_assets", "total_assets", "revenue", "expenses",
                       "operating_profit", "other_income", "interest", "depreciation",
                       "pbt", "net_profit"):
        return "INR Cr"
    return ""

def normalise_text(s: str) -> str:
    """Replace non-breaking spaces and other unicode whitespace with regular space."""
    return s.replace("\xa0", " ").replace("\u200b", "").strip()

def read_csv_rows(filepath: str):
    """Read CSV and return rows (stop at Additional Metrics section)."""
    if not os.path.exists(filepath):
        return [], []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
    
    if not rows:
        return [], []
    
    headers = [normalise_text(h) for h in rows[0]]
    data_rows = []
    for row in rows[1:]:
        if not row or not normalise_text(row[0]):
            continue
        if normalise_text(row[0]) == "Additional Metrics":
            break
        data_rows.append([normalise_text(c) for c in row])
    
    return headers, data_rows

def upload_financials(company_id: str, folder: str):
    """Upload P&L, BS, and quarterly data for one company."""
    base = os.path.join(RAW_DATA_ROOT, folder)
    rows_to_insert = []
    
    # ─── P&L (annual) ───
    pl_path = os.path.join(base, "profit_loss.csv")
    headers, data = read_csv_rows(pl_path)
    
    for row in data:
        raw_metric = row[0] if row else ""
        metric_key = PL_METRIC_MAP.get(raw_metric)
        if not metric_key:
            continue
        
        for i, col in enumerate(headers[1:], 1):
            if col == "TTM":
                continue  # Skip TTM column
            if i >= len(row):
                continue
            val = parse_value(row[i])
            if val is None:
                continue
            
            period = mar_to_fy(col)
            rows_to_insert.append({
                "company_id": company_id,
                "period": period,
                "period_type": "annual",
                "metric": metric_key,
                "value": val,
                "unit": get_unit(metric_key),
                "source_document": f"Screener.in — {company_id} profit_loss.csv",
                "period_label": period,
            })
    
    # ─── Balance Sheet (annual) ───
    bs_path = os.path.join(base, "balance_sheet.csv")
    headers, data = read_csv_rows(bs_path)
    
    for row in data:
        raw_metric = row[0] if row else ""
        metric_key = BS_METRIC_MAP.get(raw_metric)
        if not metric_key:
            continue
        
        for i, col in enumerate(headers[1:], 1):
            if i >= len(row):
                continue
            # Skip non-March columns (interim like Sep 2025)
            if not col.startswith("Mar"):
                continue
            val = parse_value(row[i])
            if val is None:
                continue
            
            period = mar_to_fy(col)
            rows_to_insert.append({
                "company_id": company_id,
                "period": period,
                "period_type": "annual",
                "metric": metric_key,
                "value": val,
                "unit": get_unit(metric_key),
                "source_document": f"Screener.in — {company_id} balance_sheet.csv",
                "period_label": period,
            })
    
    # ─── Quarterly ───
    q_path = os.path.join(base, "Quarter_Analysis_Table.csv")
    headers, data = read_csv_rows(q_path)
    
    for row in data:
        raw_metric = row[0] if row else ""
        metric_key = PL_METRIC_MAP.get(raw_metric)
        if not metric_key:
            continue
        
        for i, col in enumerate(headers[1:], 1):
            if i >= len(row):
                continue
            val = parse_value(row[i])
            if val is None:
                continue
            
            period = quarter_to_period(col)
            rows_to_insert.append({
                "company_id": company_id,
                "period": period,
                "period_type": "quarterly",
                "metric": metric_key,
                "value": val,
                "unit": get_unit(metric_key),
                "source_document": f"Screener.in — {company_id} Quarter_Analysis_Table.csv",
                "period_label": period,
            })
    
    return rows_to_insert

def ensure_companies_exist():
    """Make sure all companies (including Juniper) exist in the companies table."""
    companies = [
        ("IHCL", "Indian Hotels Company Ltd", "INDHOTEL", "premium_luxury", "hybrid",
         ["Taj", "Vivanta", "SeleQtions", "Ginger"], ["Mumbai", "Delhi", "Bengaluru", "Goa"]),
        ("CHALET", "Chalet Hotels Ltd", "CHALET", "upper_midscale", "asset_heavy",
         ["Marriott", "Westin", "Four Points", "Novotel"], ["Mumbai", "Bengaluru", "Hyderabad", "Pune"]),
        ("LEMONTREE", "Lemon Tree Hotels Ltd", "LEMONTREE", "economy_midscale", "hybrid",
         ["Aurika", "Lemon Tree Premier", "Lemon Tree", "Red Fox", "Keys"], ["Delhi-NCR", "Hyderabad", "Mumbai", "Bengaluru"]),
        ("EIH", "EIH Ltd (Oberoi Group)", "EIHOTEL", "premium_luxury", "asset_heavy",
         ["Oberoi", "Trident"], ["Delhi", "Mumbai", "Udaipur", "Agra"]),
        ("JUNIPER", "Juniper Hotels Ltd", "JUNIPER", "luxury_upper_upscale", "asset_heavy",
         ["Grand Hyatt", "Andaz", "Hyatt Regency", "Hyatt Place"], ["Mumbai", "Delhi", "Ahmedabad", "Lucknow"]),
    ]
    
    for cid, name, ticker, segment, strategy, brands, markets in companies:
        supabase.table("companies").upsert({
            "id": cid,
            "name": name,
            "ticker_nse": ticker,
            "segment": segment,
            "strategy": strategy,
            "brands": brands,
            "key_markets": markets,
        }, on_conflict="id").execute()
    print(f"✓ Ensured {len(companies)} companies exist in DB")

def main():
    print("═" * 60)
    print("EquityLens AI — Uploading Screener.in data to Supabase")
    print("═" * 60)
    
    # Step 1: Ensure companies exist
    ensure_companies_exist()
    
    # Step 2: Clear old data (respect FK constraints)
    print("\n🗑  Clearing old data...")
    supabase.table("deviation_tracker").delete().neq("company_id", "___none___").execute()
    print("  ✓ Cleared deviation_tracker")
    supabase.table("financials").delete().neq("company_id", "___none___").execute()
    print("  ✓ Cleared financials")
    
    # Step 3: Upload each company
    total_rows = 0
    for company_id, folder in COMPANY_MAP.items():
        print(f"\n📊 Processing {company_id} ({folder})...")
        rows = upload_financials(company_id, folder)
        
        if not rows:
            print(f"  ⚠ No data found for {company_id}")
            continue
        
        # Insert in batches of 500
        batch_size = 500
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            supabase.table("financials").insert(batch).execute()
        
        total_rows += len(rows)
        print(f"  ✓ Uploaded {len(rows)} rows")
    
    print(f"\n{'═' * 60}")
    print(f"✓ Done! Total rows uploaded: {total_rows}")
    print(f"  Companies: {', '.join(COMPANY_MAP.keys())}")
    print(f"  Tables: financials")
    print(f"  Source: Screener.in CSVs from Raw Data Extraction/")
    print(f"{'═' * 60}")

if __name__ == "__main__":
    main()
