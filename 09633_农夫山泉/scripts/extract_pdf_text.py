#!/usr/bin/env python3
"""将官方 PDF 提取为带 PDF 页码标记的文本，便于财务校验。"""
from pathlib import Path
import pdfplumber

BASE = Path(__file__).resolve().parents[1]
PDF_DIR = BASE / "年报"
OUT_DIR = BASE / "data" / "pdf_text"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for pdf_path in sorted(PDF_DIR.glob("*.pdf")):
        out_path = OUT_DIR / f"{pdf_path.stem}.txt"
        if out_path.exists() and out_path.stat().st_mtime >= pdf_path.stat().st_mtime:
            print(f"skip {pdf_path.name}")
            continue
        chunks = []
        with pdfplumber.open(pdf_path) as pdf:
            for page_no, page in enumerate(pdf.pages, 1):
                text = page.extract_text(x_tolerance=2, y_tolerance=3) or ""
                chunks.append(f"\n===== PDF_PAGE {page_no} =====\n{text}\n")
            print(f"{pdf_path.name}: {len(pdf.pages)} pages")
        out_path.write_text("".join(chunks), encoding="utf-8")


if __name__ == "__main__":
    main()
