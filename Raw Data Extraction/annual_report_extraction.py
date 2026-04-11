import requests
from bs4 import BeautifulSoup
import os
import re

URL = "https://www.screener.in/company/INDHOTEL/consolidated/"

headers = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.screener.in/"
}

SAVE_FOLDER = "Indian_Hotels/Annual_Reports"
os.makedirs(SAVE_FOLDER, exist_ok=True)

response = requests.get(URL, headers=headers)
soup = BeautifulSoup(response.text, "html.parser")

section = soup.find("div", class_="annual-reports")
items = section.find_all("li")

for item in items:
    try:
        a_tag = item.find("a")
        text = a_tag.text.strip()
        pdf_url = a_tag.get("href")

        # ✅ Extract year using regex
        match = re.search(r"\b(20\d{2})\b", text)

        if match:
            year = int(match.group(1))

            if 2022 <= year <= 2025:
                filename = f"{year}.pdf"
                file_path = os.path.join(SAVE_FOLDER, filename)

                print(f"Downloading: {filename}")

                pdf_data = requests.get(pdf_url, headers=headers).content

                with open(file_path, "wb") as f:
                    f.write(pdf_data)

                print(f"Saved: {file_path}")

    except Exception as e:
        print("Error:", e)

print("✅ Annual reports downloaded correctly")