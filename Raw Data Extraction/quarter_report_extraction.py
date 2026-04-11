import requests
from bs4 import BeautifulSoup
import os

BASE_URL = "https://www.screener.in"
PAGE_URL = "https://www.screener.in/company/INDHOTEL/consolidated/"

headers = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.screener.in/"
}

SAVE_FOLDER = "Indian_Hotels/Quarterly_Report"
os.makedirs(SAVE_FOLDER, exist_ok=True)

# Month mapping
month_map = {
    "1": "Jan", "2": "Feb", "3": "Mar", "4": "Apr",
    "5": "May", "6": "Jun", "7": "Jul", "8": "Aug",
    "9": "Sep", "10": "Oct", "11": "Nov", "12": "Dec"
}

# Step 1: Get page
response = requests.get(PAGE_URL, headers=headers)
soup = BeautifulSoup(response.text, "html.parser")

# Step 2: Extract links
pdf_links = []

for row in soup.find_all("tr"):
    first_col = row.find("td")
    if first_col and "Raw PDF" in first_col.text:
        for link in row.find_all("a"):
            href = link.get("href")
            if href:
                pdf_links.append(BASE_URL + href)

# Step 3: Download with proper naming
for link in pdf_links:
    print(f"Processing: {link}")

    try:
        # Extract month & year from URL
        parts = link.strip("/").split("/")
        month = parts[-2]
        year = parts[-1]

        month_name = month_map.get(month, month)

        filename = f"{month_name}_{year}.pdf"
        file_path = os.path.join(SAVE_FOLDER, filename)

        # Download (follow redirect)
        response = requests.get(link, headers=headers, allow_redirects=True)

        if ".pdf" in response.url:
            with open(file_path, "wb") as f:
                f.write(response.content)

            print(f"Downloaded: {file_path}")
        else:
            print("No PDF found")

    except Exception as e:
        print("Error:", e)

print("✅ All PDFs downloaded with proper names")