import requests
from bs4 import BeautifulSoup
import os
import warnings

warnings.filterwarnings("ignore")

URL = "https://www.screener.in/company/INDHOTEL/consolidated/"

headers = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.screener.in/"
}

SAVE_FOLDER = "Indian_Hotels/Call_Transcripts"
os.makedirs(SAVE_FOLDER, exist_ok=True)

response = requests.get(URL, headers=headers)
soup = BeautifulSoup(response.text, "html.parser")

rows = soup.select(".concalls li")

seen_files = set()  # prevent duplicates

for row in rows:
    try:
        # Get date
        date_div = row.find("div", class_="nowrap")
        if not date_div:
            continue

        date_text = date_div.text.strip()
        month, year = date_text.split()
        year = int(year)

        # ✅ filter till 2022 only
        if year < 2022:
            continue

        filename = f"{year}_{month}.pdf"

        # skip duplicate months
        if filename in seen_files:
            continue
        seen_files.add(filename)

        file_path = os.path.join(SAVE_FOLDER, filename)

        # Find valid transcript link
        transcript_link = row.find("a", string="Transcript")
        if not transcript_link:
            continue

        pdf_url = transcript_link.get("href")

        print(f"Downloading: {filename}")

        # Download with SSL fix
        res = requests.get(pdf_url, headers=headers, verify=False, timeout=20)

        # ✅ Check if it's actually a PDF
        content_type = res.headers.get("Content-Type", "")
        if "pdf" not in content_type.lower():
            print("❌ Skipped (not a real PDF)")
            continue

        # ✅ Check file size (avoid 1KB junk)
        if len(res.content) < 5000:
            print("❌ Skipped (too small / junk)")
            continue

        with open(file_path, "wb") as f:
            f.write(res.content)

        print(f"Saved: {file_path}")

    except Exception as e:
        print("Error:", e)

print("✅ Clean transcripts downloaded")