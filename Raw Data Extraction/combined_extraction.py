import requests
from bs4 import BeautifulSoup
import csv
import os
import re
import warnings
from datetime import datetime
from urllib.parse import urljoin, urlparse, parse_qs


# ============================================================
# CONFIG — Update these as needed
# ============================================================
URL = "https://www.screener.in/company/JUNIPER/consolidated/"
BASE_URL = "https://www.screener.in"
DEST_FOLDER = "Juniper_Hotels"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.screener.in/"
}


# ============================================================
# 1. ANNOUNCEMENTS EXTRACTION
# ============================================================
def extract_announcements():
    print("\n" + "="*60)
    print("📢 EXTRACTING ANNOUNCEMENTS")
    print("="*60)

    save_folder = os.path.join(DEST_FOLDER, "Announcements")
    os.makedirs(save_folder, exist_ok=True)

    current_year = datetime.now().year

    month_map = {
        "Jan": "Jan", "Feb": "Feb", "Mar": "Mar", "Apr": "Apr",
        "May": "May", "Jun": "Jun", "Jul": "Jul", "Aug": "Aug",
        "Sep": "Sep", "Oct": "Oct", "Nov": "Nov", "Dec": "Dec"
    }

    response = requests.get(URL, headers=HEADERS)
    soup = BeautifulSoup(response.text, "html.parser")

    ann_section = soup.find("div", id="company-announcements-tab")
    items = ann_section.find_all("li")

    for item in items:
        try:
            a_tag = item.find("a")
            pdf_url = a_tag.get("href")

            desc = item.find("div", class_="ink-600 smaller").text.strip()

            date_part = desc.split("-")[0].strip()
            day, month = date_part.split()

            day = day.zfill(2)
            month_name = month_map.get(month, month)

            filename = f"{current_year}_{month_name}_{day}.pdf"
            file_path = os.path.join(save_folder, filename)

            print(f"Downloading: {filename}")

            pdf_data = requests.get(pdf_url, headers=HEADERS).content

            with open(file_path, "wb") as f:
                f.write(pdf_data)

            print(f"Saved: {file_path}")

        except Exception as e:
            print("Error:", e)

    print("✅ All announcements downloaded with year")


# ============================================================
# 2. ANNUAL REPORT EXTRACTION
# ============================================================
def extract_annual_reports():
    print("\n" + "="*60)
    print("📄 EXTRACTING ANNUAL REPORTS")
    print("="*60)

    save_folder = os.path.join(DEST_FOLDER, "Annual_Reports")
    os.makedirs(save_folder, exist_ok=True)

    response = requests.get(URL, headers=HEADERS)
    soup = BeautifulSoup(response.text, "html.parser")

    section = soup.find("div", class_="annual-reports")
    items = section.find_all("li")

    for item in items:
        try:
            a_tag = item.find("a")
            text = a_tag.text.strip()
            pdf_url = a_tag.get("href")

            match = re.search(r"\b(20\d{2})\b", text)

            if match:
                year = int(match.group(1))

                if 2022 <= year <= 2025:
                    filename = f"{year}.pdf"
                    file_path = os.path.join(save_folder, filename)

                    print(f"Downloading: {filename}")

                    pdf_data = requests.get(pdf_url, headers=HEADERS).content

                    with open(file_path, "wb") as f:
                        f.write(pdf_data)

                    print(f"Saved: {file_path}")

        except Exception as e:
            print("Error:", e)

    print("✅ Annual reports downloaded correctly")


# ============================================================
# 3. BALANCE SHEET EXTRACTION
# ============================================================
def extract_balance_sheet():
    print("\n" + "="*60)
    print("📊 EXTRACTING BALANCE SHEET")
    print("="*60)

    save_path = os.path.join(DEST_FOLDER, "balance_sheet.csv")
    os.makedirs(DEST_FOLDER, exist_ok=True)

    response = requests.get(URL, headers=HEADERS)
    soup = BeautifulSoup(response.text, "html.parser")

    section = soup.find("section", id="balance-sheet")
    table = section.find("table", class_="data-table")

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

    with open(save_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers_row)
        writer.writerows(data_rows)

    print("✅ Saved to", save_path)


# ============================================================
# 4. CALL TRANSCRIPTS EXTRACTION
# ============================================================
def extract_call_transcripts():
    print("\n" + "="*60)
    print("📞 EXTRACTING CALL TRANSCRIPTS")
    print("="*60)

    warnings.filterwarnings("ignore")

    save_folder = os.path.join(DEST_FOLDER, "Call_Transcripts")
    os.makedirs(save_folder, exist_ok=True)

    response = requests.get(URL, headers=HEADERS)
    soup = BeautifulSoup(response.text, "html.parser")

    rows = soup.select(".concalls li")

    seen_files = set()

    for row in rows:
        try:
            date_div = row.find("div", class_="nowrap")
            if not date_div:
                continue

            date_text = date_div.text.strip()
            month, year = date_text.split()
            year = int(year)

            if year < 2022:
                continue

            filename = f"{year}_{month}.pdf"

            if filename in seen_files:
                continue
            seen_files.add(filename)

            file_path = os.path.join(save_folder, filename)

            transcript_link = row.find("a", string="Transcript")
            if not transcript_link:
                continue

            pdf_url = transcript_link.get("href")

            print(f"Downloading: {filename}")

            res = requests.get(pdf_url, headers=HEADERS, verify=False, timeout=20)

            content_type = res.headers.get("Content-Type", "")
            if "pdf" not in content_type.lower():
                print("❌ Skipped (not a real PDF)")
                continue

            if len(res.content) < 5000:
                print("❌ Skipped (too small / junk)")
                continue

            with open(file_path, "wb") as f:
                f.write(res.content)

            print(f"Saved: {file_path}")

        except Exception as e:
            print("Error:", e)

    print("✅ Clean transcripts downloaded")


# ============================================================
# 5. CREDIT RATINGS EXTRACTION
# ============================================================
def extract_credit_ratings():
    print("\n" + "="*60)
    print("⭐ EXTRACTING CREDIT RATINGS")
    print("="*60)

    save_folder = os.path.join(DEST_FOLDER, "Credit_Ratings")
    os.makedirs(save_folder, exist_ok=True)

    month_map = {
        "Jan": "Jan", "Feb": "Feb", "Mar": "Mar", "Apr": "Apr",
        "May": "May", "Jun": "Jun", "Jul": "Jul", "Aug": "Aug",
        "Sep": "Sep", "Oct": "Oct", "Nov": "Nov", "Dec": "Dec",
    }

    DEFAULT_YEAR = datetime.now().year
    MIN_YEAR = 2022

    session = requests.Session()
    session.headers.update(HEADERS)

    def safe_filename(year, month, day):
        return f"{year}_{month}_{day:02d}.pdf"

    def extract_date(desc: str):
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
        r = session.get(url, allow_redirects=True, timeout=30)
        r.raise_for_status()

        with open(out_path, "wb") as f:
            f.write(r.content)

    def get_icra_pdf_url(page_url):
        r = session.get(page_url, timeout=30)
        r.raise_for_status()

        s = BeautifulSoup(r.text, "html.parser")
        iframe = s.find("iframe", id="iframeRationaleReport")

        if iframe and iframe.get("src"):
            iframe_src = urljoin(page_url, iframe["src"])
            parsed = urlparse(iframe_src)
            q = parse_qs(parsed.query)

            if "file" in q and q["file"]:
                file_path = q["file"][0]
                return urljoin("https://www.icra.in", file_path)

        pdf_tag = s.find("a", href=lambda x: x and ".pdf" in x.lower())
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

            if year < MIN_YEAR:
                continue

            filename = safe_filename(year, month, day)
            file_path = os.path.join(save_folder, filename)

            print(f"Processing: {filename}")

            if "careratings.com" in link or ".pdf" in link.lower():
                download_pdf(link, file_path)
                print(f"Saved: {file_path}")
                continue

            if "icra.in" in link:
                pdf_url = get_icra_pdf_url(link)
                if not pdf_url:
                    print(f"No PDF found for ICRA page: {link}")
                    continue

                download_pdf(pdf_url, file_path)
                print(f"Saved: {file_path}")
                continue

            download_pdf(link, file_path)
            print(f"Saved: {file_path}")

        except Exception as e:
            print("Error:", e)

    print("✅ Credit ratings downloaded")


# ============================================================
# 6. PROFIT & LOSS EXTRACTION
# ============================================================
def extract_profit_loss():
    print("\n" + "="*60)
    print("💰 EXTRACTING PROFIT & LOSS")
    print("="*60)

    save_path = os.path.join(DEST_FOLDER, "profit_loss.csv")
    os.makedirs(DEST_FOLDER, exist_ok=True)

    response = requests.get(URL, headers=HEADERS)
    soup = BeautifulSoup(response.text, "html.parser")

    section = soup.find("section", id="profit-loss")
    table = section.find("table", class_="data-table")

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

    # CAGR / ROE / METRICS
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

    with open(save_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        writer.writerow(headers_row)
        writer.writerows(data_rows)

        writer.writerow([])

        writer.writerow(["Additional Metrics", "Value"])
        writer.writerows(extra_data)

    print("✅ Saved to", save_path)


# ============================================================
# 7. QUARTERLY REPORT EXTRACTION (PDFs)
# ============================================================
def extract_quarter_reports():
    print("\n" + "="*60)
    print("📑 EXTRACTING QUARTERLY REPORTS (PDFs)")
    print("="*60)

    save_folder = os.path.join(DEST_FOLDER, "Quarterly_Report")
    os.makedirs(save_folder, exist_ok=True)

    month_map = {
        "1": "Jan", "2": "Feb", "3": "Mar", "4": "Apr",
        "5": "May", "6": "Jun", "7": "Jul", "8": "Aug",
        "9": "Sep", "10": "Oct", "11": "Nov", "12": "Dec"
    }

    response = requests.get(URL, headers=HEADERS)
    soup = BeautifulSoup(response.text, "html.parser")

    pdf_links = []

    for row in soup.find_all("tr"):
        first_col = row.find("td")
        if first_col and "Raw PDF" in first_col.text:
            for link in row.find_all("a"):
                href = link.get("href")
                if href:
                    pdf_links.append(BASE_URL + href)

    for link in pdf_links:
        print(f"Processing: {link}")

        try:
            parts = link.strip("/").split("/")
            month = parts[-2]
            year = parts[-1]

            month_name = month_map.get(month, month)

            filename = f"{month_name}_{year}.pdf"
            file_path = os.path.join(save_folder, filename)

            response = requests.get(link, headers=HEADERS, allow_redirects=True)

            if ".pdf" in response.url:
                with open(file_path, "wb") as f:
                    f.write(response.content)

                print(f"Downloaded: {file_path}")
            else:
                print("No PDF found")

        except Exception as e:
            print("Error:", e)

    print("✅ All PDFs downloaded with proper names")


# ============================================================
# 8. QUARTERLY TABLE EXTRACTION (CSV)
# ============================================================
def extract_quarter_table():
    print("\n" + "="*60)
    print("📋 EXTRACTING QUARTERLY TABLE (CSV)")
    print("="*60)

    save_path = os.path.join(DEST_FOLDER, "Quarter_Analysis_Table.csv")
    os.makedirs(DEST_FOLDER, exist_ok=True)

    response = requests.get(URL, headers=HEADERS)
    soup = BeautifulSoup(response.text, "html.parser")

    table = soup.find("table", class_="data-table")

    header_row = table.find("thead").find_all("th")
    headers_row = ["Metric"]

    for th in header_row[1:]:
        headers_row.append(th.text.strip())

    data = []

    for row in table.find("tbody").find_all("tr"):
        cols = row.find_all("td")

        if not cols or "Raw PDF" in cols[0].text:
            continue

        metric = cols[0].text.strip()
        values = [col.text.strip().replace(",", "") for col in cols[1:]]

        data.append([metric] + values)

    with open(save_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers_row)
        writer.writerows(data)

    print("✅ Saved to", save_path)


# ============================================================
# RUN ALL EXTRACTIONS
# ============================================================
if __name__ == "__main__":
    print("🚀 Starting all extractions...")
    print(f"📂 Destination folder: {DEST_FOLDER}")
    print(f"🔗 Source URL: {URL}\n")

    extract_announcements()
    extract_annual_reports()
    extract_balance_sheet()
    extract_call_transcripts()
    extract_credit_ratings()
    extract_profit_loss()
    extract_quarter_reports()
    extract_quarter_table()

    print("\n" + "="*60)
    print("🎉 ALL 8 EXTRACTIONS COMPLETED!")
    print("="*60)
