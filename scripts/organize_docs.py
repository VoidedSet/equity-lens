#!/usr/bin/env python3
"""
organize_docs.py
----------------
Flattens all company documents from 'Raw Data Extraction' into a single
unified 'data/files/' folder with filenames prefixed by company code.

Output format:  COMPANYCODE_SubfolderType_OriginalFilename.ext
Examples:
  IHCL_Annual_Reports_2025.pdf
  CHALET_Quarterly_Report_Dec_2024.pdf
  EIH_Credit_Ratings_2025_Dec_29.pdf

Run from project root:
  python3 scripts/organize_docs.py
  python3 scripts/organize_docs.py --dry-run
"""

import argparse
import shutil
from pathlib import Path

# Mapping: folder name → company code used in the system
COMPANY_MAP = {
    "Chalet_Hotels":      "CHALET",
    "EIH_Limited":        "EIH",
    "Indian_Hotels":      "IHCL",
    "Juniper_Hotels":     "JUNIPER",
    "Lemon_Tree_Hotels":  "LEMONTREE",
}

ROOT = Path(__file__).parent.parent
SOURCE_DIR = ROOT / "Raw Data Extraction"
DEST_DIR   = ROOT / "data" / "files"


def slugify(text: str) -> str:
    """Replace spaces and path separators with underscores for safe filenames."""
    return text.replace(" ", "_").replace("/", "_").replace("\\", "_")


def build_dest_name(company_code: str, relative_parts: tuple[str, ...]) -> str:
    """
    Build the flat destination filename.
    relative_parts: path components relative to the company folder, e.g.
        ("Annual_Reports", "2025.pdf")
    Returns: "IHCL_Annual_Reports_2025.pdf"
    """
    parts = [company_code] + [slugify(p) for p in relative_parts]
    return "_".join(parts)


def collect_files(source_dir: Path) -> list[tuple[str, Path, str]]:
    """
    Returns list of (company_code, source_path, dest_filename) tuples.
    """
    entries = []
    for company_folder, code in COMPANY_MAP.items():
        company_path = source_dir / company_folder
        if not company_path.is_dir():
            print(f"  [warn] Missing company folder: {company_path}")
            continue
        for file_path in sorted(company_path.rglob("*")):
            if not file_path.is_file():
                continue
            # Relative path components (subfolder + filename)
            rel = file_path.relative_to(company_path)
            dest_name = build_dest_name(code, rel.parts)
            entries.append((code, file_path, dest_name))
    return entries


def run(dry_run: bool = False) -> None:
    if not SOURCE_DIR.exists():
        print(f"[error] Source directory not found: {SOURCE_DIR}")
        return

    entries = collect_files(SOURCE_DIR)
    if not entries:
        print("[warn] No files found.")
        return

    print(f"Found {len(entries)} files across {len(COMPANY_MAP)} companies.\n")

    if not dry_run:
        DEST_DIR.mkdir(parents=True, exist_ok=True)

    counts = {code: 0 for code in COMPANY_MAP.values()}
    skipped = 0

    for code, src, dest_name in entries:
        dest_path = DEST_DIR / dest_name
        if dest_path.exists():
            skipped += 1
            continue
        print(f"  {'[dry] ' if dry_run else ''}Copy  {src.relative_to(ROOT)}  →  data/files/{dest_name}")
        if not dry_run:
            shutil.copy2(src, dest_path)
        counts[code] += 1

    print(f"\n{'[dry-run] ' if dry_run else ''}Done.")
    for code, n in counts.items():
        print(f"  {code}: {n} files {'would be ' if dry_run else ''}copied")
    if skipped:
        print(f"  Skipped (already exist): {skipped}")

    if not dry_run:
        print(f"\nAll files now in: {DEST_DIR}")
        print("Update your db.ts resolveSource() to look in data/files/ using the new naming convention.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Organise company docs into data/files/")
    parser.add_argument("--dry-run", action="store_true", help="Preview without copying files")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
