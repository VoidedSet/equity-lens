"""Quick runner - avoids space-in-path issues."""
import sys, os
os.chdir(os.path.join(os.path.dirname(__file__), "pdf extraction pipeline"))
sys.path.insert(0, ".")

from dotenv import load_dotenv
load_dotenv()

from pdf_extractor import process_annual_report
from gemma_extractor import process_annual_report_chunks

# Step 1: Fast PDF extraction
print("=" * 60)
result = process_annual_report("data/IHCL/ihcl.pdf", "IHCL", "FY24")
chunks = result["text_chunks"]
print(f"\nStep 1 done: {len(chunks)} chunks")

# Step 2: Gemma extraction (parallel + batched)
print("=" * 60)
counts = process_annual_report_chunks(chunks, [], dry_run="--dry-run" in sys.argv)
print(f"\nStep 2 done: {counts}")
print("=" * 60)
