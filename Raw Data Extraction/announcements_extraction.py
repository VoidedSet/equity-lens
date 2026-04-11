import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime

URL = "https://www.screener.in/company/INDHOTEL/consolidated/"

headers = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.screener.in/"
}

SAVE_FOLDER = "Indian_Hotels/Announcements"
os.makedirs(SAVE_FOLDER, exist_ok=True)

# Current year
current_year = datetime.now().year

# Month mapping
month_map = {
    "Jan": "Jan", "Feb": "Feb", "Mar": "Mar", "Apr": "Apr",
    "May": "May", "Jun": "Jun", "Jul": "Jul", "Aug": "Aug",
    "Sep": "Sep", "Oct": "Oct", "Nov": "Nov", "Dec": "Dec"
}

response = requests.get(URL, headers=headers)
soup = BeautifulSoup(response.text, "html.parser")

ann_section = soup.find("div", id="company-announcements-tab")
items = ann_section.find_all("li")

for item in items:
    try:
        a_tag = item.find("a")
        pdf_url = a_tag.get("href")

        desc = item.find("div", class_="ink-600 smaller").text.strip()

        # Extract date
        date_part = desc.split("-")[0].strip()
        day, month = date_part.split()

        day = day.zfill(2)
        month_name = month_map.get(month, month)

        # Final filename
        filename = f"{current_year}_{month_name}_{day}.pdf"
        file_path = os.path.join(SAVE_FOLDER, filename)

        print(f"Downloading: {filename}")

        pdf_data = requests.get(pdf_url, headers=headers).content

        with open(file_path, "wb") as f:
            f.write(pdf_data)

        print(f"Saved: {file_path}")

    except Exception as e:
        print("Error:", e)

print("✅ All announcements downloaded with year")