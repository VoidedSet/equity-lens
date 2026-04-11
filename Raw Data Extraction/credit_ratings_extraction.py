import os
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse, parse_qs

import requests
from bs4 import BeautifulSoup

URL = "https://www.screener.in/company/INDHOTEL/consolidated/"
SAVE_FOLDER = "Indian_Hotels/Credit_Ratings"
os.makedirs(SAVE_FOLDER, exist_ok=True)

headers = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.screener.in/",
}

month_map = {
    "Jan": "Jan", "Feb": "Feb", "Mar": "Mar", "Apr": "Apr",
    "May": "May", "Jun": "Jun", "Jul": "Jul", "Aug": "Aug",
    "Sep": "Sep", "Oct": "Oct", "Nov": "Nov", "Dec": "Dec",
}

DEFAULT_YEAR = datetime.now().year
MIN_YEAR = 2022  # keep 2022 and newer

session = requests.Session()
session.headers.update(headers)

def safe_filename(year, month, day):
    return f"{year}_{month}_{day:02d}.pdf"

def extract_date(desc: str):
    """
    Handles:
      '20 Feb from icra'
      '1 Dec 2025 from care'
    """
    left = desc.split("from")[0].strip()
    tokens = left.split()

    if len(tokens) == 2:
        day_str, month = tokens
        year = DEFAULT_YEAR
    else:
        day_str, month, year_str = tokens[:3]
        year = int(year_str)

    day = int(day_str)
    month = month_map.get(month, month)
    return year, month, day

def download_pdf(url, out_path):
    """
    Downloads a PDF or a URL that redirects to a PDF.
    """
    r = session.get(url, allow_redirects=True, timeout=30)
    r.raise_for_status()

    with open(out_path, "wb") as f:
        f.write(r.content)

def get_icra_pdf_url(page_url):
    """
    ICRA page contains:
    <iframe id="iframeRationaleReport" src="/web/viewer.html?file=/Rating/ShowRationalReportFilePdf/141054">
    """
    r = session.get(page_url, timeout=30)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    iframe = soup.find("iframe", id="iframeRationaleReport")

    if iframe and iframe.get("src"):
        iframe_src = urljoin(page_url, iframe["src"])
        parsed = urlparse(iframe_src)
        q = parse_qs(parsed.query)

        if "file" in q and q["file"]:
            file_path = q["file"][0]
            # This is the actual PDF endpoint on ICRA
            return urljoin("https://www.icra.in", file_path)

    # fallback: try to find any PDF link on the page
    pdf_tag = soup.find("a", href=lambda x: x and ".pdf" in x.lower())
    if pdf_tag and pdf_tag.get("href"):
        return urljoin(page_url, pdf_tag["href"])

    return None

# Load Screener page
res = session.get(URL, timeout=30)
res.raise_for_status()
soup = BeautifulSoup(res.text, "html.parser")

section = soup.find("div", class_="credit-ratings")
items = section.find_all("li") if section else []

for item in items:
    try:
        a_tag = item.find("a")
        if not a_tag or not a_tag.get("href"):
            continue

        link = a_tag["href"]
        desc_tag = item.find("div", class_="ink-600 smaller")
        if not desc_tag:
            continue

        desc = desc_tag.text.strip()
        year, month, day = extract_date(desc)

        # keep only 2022 and newer
        if year < MIN_YEAR:
            continue

        filename = safe_filename(year, month, day)
        file_path = os.path.join(SAVE_FOLDER, filename)

        print(f"Processing: {filename}")

        # CARE links are already PDFs or redirect to PDFs
        if "careratings.com" in link or ".pdf" in link.lower():
            download_pdf(link, file_path)
            print(f"Saved: {file_path}")
            continue

        # ICRA links are pages; extract PDF from iframe/file param
        if "icra.in" in link:
            pdf_url = get_icra_pdf_url(link)
            if not pdf_url:
                print(f"No PDF found for ICRA page: {link}")
                continue

            download_pdf(pdf_url, file_path)
            print(f"Saved: {file_path}")
            continue

        # Fallback for anything else
        download_pdf(link, file_path)
        print(f"Saved: {file_path}")

    except Exception as e:
        print("Error:", e)

print("Done.")