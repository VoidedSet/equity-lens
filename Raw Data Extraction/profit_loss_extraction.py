import requests
from bs4 import BeautifulSoup
import csv
import os

URL = "https://www.screener.in/company/INDHOTEL/consolidated/"

headers = {
    "User-Agent": "Mozilla/5.0"
}

SAVE_PATH = "Indian_Hotels/profit_loss.csv"
os.makedirs("Indian_Hotels", exist_ok=True)

response = requests.get(URL, headers=headers)
soup = BeautifulSoup(response.text, "html.parser")

# =========================
# 1. PROFIT & LOSS TABLE
# =========================

section = soup.find("section", id="profit-loss")
table = section.find("table", class_="data-table")

# Headers (years)
header_row = table.find("thead").find_all("th")
headers_row = ["Metric"]

for th in header_row[1:]:
    headers_row.append(th.text.strip())

data_rows = []

for row in table.find("tbody").find_all("tr"):
    cols = row.find_all("td")

    if not cols:
        continue

    metric = cols[0].text.strip()
    values = [col.text.strip().replace(",", "") for col in cols[1:]]

    data_rows.append([metric] + values)

# =========================
# 2. CAGR / ROE / METRICS
# =========================

extra_data = []

range_tables = section.find_all("table", class_="ranges-table")

for rtable in range_tables:
    title = rtable.find("th").text.strip()

    for row in rtable.find_all("tr")[1:]:
        cols = row.find_all("td")
        if len(cols) == 2:
            period = cols[0].text.strip()
            value = cols[1].text.strip()

            metric_name = f"{title} ({period})"
            extra_data.append([metric_name, value])

# =========================
# 3. SAVE CSV
# =========================

with open(SAVE_PATH, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)

    # Main table
    writer.writerow(headers_row)
    writer.writerows(data_rows)

    # Empty row separator
    writer.writerow([])

    # Extra metrics
    writer.writerow(["Additional Metrics", "Value"])
    writer.writerows(extra_data)

print("✅ Saved to", SAVE_PATH)