import requests
from bs4 import BeautifulSoup
import csv

URL = "https://www.screener.in/company/INDHOTEL/consolidated/"

headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(URL, headers=headers)
soup = BeautifulSoup(response.text, "html.parser")

# Find the quarterly table
table = soup.find("table", class_="data-table")

# Extract headers (dates)
header_row = table.find("thead").find_all("th")
headers = ["Metric"]

for th in header_row[1:]:
    headers.append(th.text.strip())

# Extract data rows
data = []

for row in table.find("tbody").find_all("tr"):
    cols = row.find_all("td")

    # Skip rows like "Raw PDF"
    if not cols or "Raw PDF" in cols[0].text:
        continue

    metric = cols[0].text.strip()
    values = [col.text.strip().replace(",", "") for col in cols[1:]]

    data.append([metric] + values)

# Save to CSV
with open("Indian_Hotels/Quarter_Analysis_Table.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(headers)
    writer.writerows(data)

print("✅ Data saved to Quarter_Analysis_Table.csv")