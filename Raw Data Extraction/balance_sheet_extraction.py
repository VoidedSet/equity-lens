import requests
from bs4 import BeautifulSoup
import csv
import os

URL = "https://www.screener.in/company/INDHOTEL/consolidated/"

headers = {
    "User-Agent": "Mozilla/5.0"
}

SAVE_PATH = "Indian_Hotels/balance_sheet.csv"
os.makedirs("Indian_Hotels", exist_ok=True)

response = requests.get(URL, headers=headers)
soup = BeautifulSoup(response.text, "html.parser")

# =========================
# BALANCE SHEET SECTION
# =========================

section = soup.find("section", id="balance-sheet")
table = section.find("table", class_="data-table")

# Extract headers (years)
header_row = table.find("thead").find_all("th")
headers_row = ["Metric"]

for th in header_row[1:]:
    headers_row.append(th.text.strip())

# Extract data
data_rows = []

for row in table.find("tbody").find_all("tr"):
    cols = row.find_all("td")

    if not cols:
        continue

    metric = cols[0].text.strip()
    values = [col.text.strip().replace(",", "") for col in cols[1:]]

    data_rows.append([metric] + values)

# =========================
# SAVE CSV
# =========================

with open(SAVE_PATH, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(headers_row)
    writer.writerows(data_rows)

print("✅ Saved to", SAVE_PATH)