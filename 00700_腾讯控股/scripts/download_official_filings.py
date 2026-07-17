#!/usr/bin/env python3
"""Download Tencent official earnings releases and build a source ledger."""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urljoin

import fitz
import pandas as pd
import requests
from bs4 import BeautifulSoup

BASE = Path(__file__).resolve().parents[1]
REPORT_DIR = BASE / "年报"
TEXT_DIR = BASE / "data" / "pdf_text"
DATA_DIR = BASE / "data"
for directory in (REPORT_DIR, TEXT_DIR, DATA_DIR):
    directory.mkdir(parents=True, exist_ok=True)

INDEX_URL = "https://www.tencent.com/en-us/investors/financial-news.html"
html = requests.get(INDEX_URL, timeout=90).text
soup = BeautifulSoup(html, "html.parser")
records: list[dict[str, str]] = []
seen: set[str] = set()
for anchor in soup.select('a[href$=".pdf"]'):
    title = " ".join(anchor.get_text(" ", strip=True).split())
    raw_href = anchor.get("href")
    if not isinstance(raw_href, str):
        continue
    href = urljoin(INDEX_URL, raw_href)
    if href in seen or "Tencent Announces" not in title or "Results" not in title:
        continue
    match = re.search(r"(20\d{2})[.-](\d{2})[.-](\d{2})", title)
    if not match or not (2016 <= int(match.group(1)) <= 2026):
        continue
    seen.add(href)
    disclosure_date = "-".join(match.groups())
    clean_title = re.sub(r"^20\d{2}[.-]\d{2}[.-]\d{2}\s*", "", title)
    clean_title = re.sub(r"\s*PDF$", "", clean_title)
    period_match = re.search(r"(20\d{2}) (.+?) Results", clean_title)
    period = f"{period_match.group(1)} {period_match.group(2)}" if period_match else clean_title
    filename = f"{disclosure_date}_{period.replace('/', '-')}.pdf"
    path = REPORT_DIR / filename
    if not path.exists():
        response = requests.get(href, timeout=120)
        response.raise_for_status()
        if not response.content.startswith(b"%PDF"):
            raise RuntimeError(f"not a PDF: {href}")
        path.write_bytes(response.content)
    text_path = TEXT_DIR / (path.stem + ".txt")
    if not text_path.exists():
        doc = fitz.open(path)
        pages = [str(page.get_text("text")) for page in doc]
        text_path.write_text("\n\n".join(pages), encoding="utf-8")
    records.append({
        "报告期": period,
        "披露日": disclosure_date,
        "标题": clean_title,
        "官方URL": href,
        "本地PDF": str(path.relative_to(BASE)),
        "文本底稿": str(text_path.relative_to(BASE)),
    })

ledger = pd.DataFrame(records).sort_values(["披露日", "标题"], ascending=[False, True])
ledger.to_csv(DATA_DIR / "official_filings.csv", index=False, encoding="utf-8-sig")
print(f"downloaded/indexed {len(ledger)} official earnings releases")
print(ledger.head(10).to_string(index=False))
