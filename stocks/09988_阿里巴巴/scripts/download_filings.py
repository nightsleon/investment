#!/usr/bin/env python3
"""Download Alibaba official earnings reports and annual reports."""
import os
import re
import urllib.parse
from pathlib import Path
import requests
import fitz
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
REPORT_DIR = BASE / "年报"
TEXT_DIR = BASE / "data" / "pdf_text"
DATA_DIR = BASE / "data"
for d in (REPORT_DIR, TEXT_DIR, DATA_DIR):
    d.mkdir(parents=True, exist_ok=True)

REPORTS = [
    {
        "报告期": "FY2027 Q1 (June Quarter 2026)",
        "披露日": "2026-08-20",
        "标题": "June Quarter 2026 Results (Q1 FY2027)",
        "url": "https://data.alibabagroup.com/ecms-files/1567773279/a9d0a2f3-beca-402c-b3c1-526c2064d10f/June%20Quarter%202026%20Results.pdf",
        "filename": "2026-08-20_June_Quarter_2026_Results.pdf"
    },
    {
        "报告期": "FY2027 Q1 演示文稿",
        "披露日": "2026-08-20",
        "标题": "CN Jun 2026 Q - Alibaba Earnings Call",
        "url": "https://data.alibabagroup.com/ecms-files/1567773279/6a298f57-826a-460c-a85b-fd9b11f2339d/CN%20Jun%202026%20Q%20-%20Alibaba%20Earnings%20Call.pdf",
        "filename": "2026-08-20_CN_Jun_2026_Q_Earnings_Call.pdf"
    },
    {
        "报告期": "FY2026 全年 (2026財務年度報告)",
        "披露日": "2026-07-08",
        "标题": "阿里巴巴集團控股有限公司2026財務年度報告",
        "url": "https://data.alibabagroup.com/ecms-files/1514443390/c62cb431-2d83-4196-9c85-e242ed1df244/%E9%98%BF%E9%87%8C%E5%B7%B4%E5%B7%B4%E9%9B%86%E5%9C%98%E6%8E%A7%E8%82%A1%E6%9C%89%E9%99%90%E5%85%AC%E5%8F%B82026%E8%B2%A1%E5%8B%99%E5%B9%B4%E5%BA%A6%E5%A0%B1%E5%91%8A.pdf",
        "filename": "2026-07-08_FY2026_2026財務年度報告.pdf"
    },
    {
        "报告期": "FY2025 全年 (2025財務年度報告)",
        "披露日": "2025-06-18",
        "标题": "阿里巴巴集團控股有限公司2025財務年度報告",
        "url": "https://data.alibabagroup.com/ecms-files/1514443390/49a076a3-a1a2-48b1-b21f-dcaee54f1852/%E9%98%BF%E9%87%8C%E5%B7%B4%E5%B7%B4%E9%9B%86%E5%9C%98%E6%8E%A7%E8%82%A1%E6%9C%89%E9%99%90%E5%85%AC%E5%8F%B82025%E8%B2%A1%E5%8B%99%E5%B9%B4%E5%BA%A6%E5%A0%B1%E5%91%8A.pdf",
        "filename": "2025-06-18_FY2025_2025財務年度報告.pdf"
    },
    {
        "报告期": "FY2024 全年 (2024財務年度報告)",
        "披露日": "2024-06-25",
        "标题": "阿里巴巴集團控股有限公司2024財務年度報告",
        "url": "https://data.alibabagroup.com/ecms-files/1514443390/1fe55b48-c185-4a95-94c3-422d3bce7276/%E9%98%BF%E9%87%8C%E5%B7%B4%E5%B7%B4%E9%9B%86%E5%9C%98%E6%8E%A7%E8%82%A1%E6%9C%89%E9%99%90%E5%85%AC%E5%8F%B82024%E8%B2%A1%E5%8B%99%E5%B9%B4%E5%BA%A6%E5%A0%B1%E5%91%8A.pdf",
        "filename": "2024-06-25_FY2024_2024財務年度報告.pdf"
    }
]

headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
records = []
for item in REPORTS:
    pdf_path = REPORT_DIR / item["filename"]
    print(f"Checking {item['filename']}...")
    if not pdf_path.exists():
        print(f"Downloading from {item['url']}...")
        r = requests.get(item["url"], headers=headers, timeout=120)
        r.raise_for_status()
        if not r.content.startswith(b"%PDF"):
            print(f"Warning: {item['filename']} is not valid PDF!")
            continue
        pdf_path.write_bytes(r.content)
        print(f"Saved {pdf_path.name} ({len(r.content)/1024/1024:.2f} MB)")
    else:
        print(f"Already exists: {pdf_path.name}")
    
    text_path = TEXT_DIR / (pdf_path.stem + ".txt")
    if not text_path.exists():
        print(f"Extracting text to {text_path.name}...")
        doc = fitz.open(pdf_path)
        pages = [str(page.get_text("text")) for page in doc]
        text_path.write_text("\n\n".join(pages), encoding="utf-8")
        print(f"Extracted {len(pages)} pages.")
    
    records.append({
        "报告期": item["报告期"],
        "披露日": item["披露日"],
        "标题": item["标题"],
        "官方URL": item["url"],
        "本地PDF": str(pdf_path.relative_to(BASE)),
        "文本底稿": str(text_path.relative_to(BASE)),
    })

df = pd.DataFrame(records)
df.to_csv(DATA_DIR / "official_filings.csv", index=False, encoding="utf-8-sig")
print("Official filings indexed successfully:")
print(df[["报告期", "披露日", "本地PDF"]].to_string(index=False))
