import fitz  # PyMuPDF
import pdfplumber

def get_table_bboxes(pdf_path):
    table_data = {}

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            tables = page.find_tables()
            bboxes = []

            for table in tables:
                # bbox = (x0, top, x1, bottom)
                bboxes.append(table.bbox)

            table_data[i] = bboxes

    return table_data


def is_inside_table(block_bbox, table_bboxes):
    x0, y0, x1, y1 = block_bbox

    for tb in table_bboxes:
        tx0, ty0, tx1, ty1 = tb

        # check overlap
        if not (x1 < tx0 or x0 > tx1 or y1 < ty0 or y0 > ty1):
            return True
    return False


def extract_text_without_tables(pdf_path, output_txt):
    doc = fitz.open(pdf_path)
    table_bboxes = get_table_bboxes(pdf_path)

    full_text = ""

    for page_num in range(len(doc)):
        page = doc[page_num]

        blocks = page.get_text("blocks")  # gives text blocks with bbox
        page_tables = table_bboxes.get(page_num, [])

        page_text = f"\n--- Page {page_num + 1} ---\n"

        for block in blocks:
            x0, y0, x1, y1, text, *_ = block
            block_bbox = (x0, y0, x1, y1)

            if not is_inside_table(block_bbox, page_tables):
                page_text += text.strip() + "\n"

        full_text += page_text

    with open(output_txt, "w", encoding="utf-8") as f:
        f.write(full_text)

    print(f"Clean text saved to: {output_txt}")


# Usage
pdf_path = "C:/Users/91845/Desktop/DataHack/Raw Data Extraction/Indian_Hotels/Annual_Reports/2025.pdf"
output_txt = "C:/Users/91845/Desktop/DataHack/Raw Data Extraction/Indian_Hotels/Annual_Reports/2025.txt"

extract_text_without_tables(pdf_path, output_txt)