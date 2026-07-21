#!/usr/bin/env python3
"""Download Salted Shop (002847.SZ) official filings and Eastmoney datasets."""
from __future__ import annotations

import json
import re
from pathlib import Path

import fitz
import requests

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"
REPORTS = BASE / "年报"
TEXT = DATA / "pdf_text"
ANNOUNCEMENTS = REPORTS / "公告"
CODE = "002847"
SECUCODE = "002847.SZ"
CNINFO = "https://www.cninfo.com.cn/new/hisAnnouncement/query"
STATIC = "https://static.cninfo.com.cn/"
EASTMONEY = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.cninfo.com.cn/"}


def clean_title(value: str) -> str:
    return re.sub(r"<.*?>", "", value).replace("/", "_").strip()


def get_org_id() -> str:
    stocks = requests.get(
        "https://www.cninfo.com.cn/new/data/szse_stock.json", headers=HEADERS, timeout=30
    ).json()["stockList"]
    return next(item["orgId"] for item in stocks if item["code"] == CODE)


def query(org_id: str, start: str, end: str, category: str = "") -> list[dict]:
    payload = {
        "pageNum": 1,
        "pageSize": 100,
        "column": "szse",
        "tabName": "fulltext",
        "plate": "sz",
        "stock": f"{CODE},{org_id}",
        "searchkey": "",
        "secid": "",
        "category": category,
        "trade": "",
        "seDate": f"{start}~{end}",
        "sortName": "",
        "sortType": "",
        "isHLtitle": "true",
    }
    response = requests.post(CNINFO, headers=HEADERS, data=payload, timeout=60)
    response.raise_for_status()
    result = response.json()
    if result.get("totalAnnouncement", 0) > 100:
        raise RuntimeError(f"Query too broad: {start}~{end}: {result['totalAnnouncement']}")
    return result.get("announcements") or []


def download_pdf(item: dict, folder: Path, filename: str | None = None) -> dict:
    url = STATIC + item["adjunctUrl"].lstrip("/")
    title = clean_title(item["announcementTitle"])
    path = folder / (filename or f"{title}.pdf")
    response = requests.get(url, headers=HEADERS, timeout=120)
    response.raise_for_status()
    if not response.content.startswith(b"%PDF"):
        raise RuntimeError(f"Not PDF: {url}")
    path.write_bytes(response.content)
    doc = fitz.open(path)
    text = "\n\n".join(str(page.get_text()) for page in doc)
    (TEXT / f"{path.stem}.txt").write_text(text, encoding="utf-8")
    return {
        "date": item.get("announcementTime"),
        "title": title,
        "url": url,
        "file": str(path.relative_to(BASE)),
        "bytes": path.stat().st_size,
        "pages": doc.page_count,
    }


def fetch_eastmoney(report_name: str, page_size: int = 5000, sort_column: str = "REPORT_DATE") -> list[dict]:
    params = {
        "reportName": report_name,
        "columns": "ALL",
        "filter": f'(SECUCODE="{SECUCODE}")',
        "pageSize": page_size,
        "sortColumns": sort_column,
        "sortTypes": "-1",
        "source": "HSF10",
        "client": "PC",
    }
    response = requests.get(EASTMONEY, params=params, timeout=60)
    response.raise_for_status()
    payload = response.json()
    if not payload.get("success") or not payload.get("result"):
        raise RuntimeError(f"Eastmoney failed: {report_name}: {payload}")
    return payload["result"]["data"]


def main() -> None:
    for folder in (DATA, REPORTS, TEXT, ANNOUNCEMENTS):
        folder.mkdir(parents=True, exist_ok=True)
    org_id = get_org_id()

    annual_items = query(org_id, "2021-01-01", "2026-06-30", "category_ndbg_szsh")
    manifest: list[dict] = []
    for year in range(2020, 2026):
        matches = [
            item for item in annual_items
            if f"{year}年年度报告" in clean_title(item["announcementTitle"])
            and "摘要" not in clean_title(item["announcementTitle"])
            and "英文" not in clean_title(item["announcementTitle"])
            and "更正" not in clean_title(item["announcementTitle"])
        ]
        if not matches:
            raise RuntimeError(f"Missing annual report {year}")
        manifest.append(download_pdf(matches[0], REPORTS, f"{year}_盐津铺子_年度报告.pdf"))

    all_2026: list[dict] = []
    for month in range(1, 8):
        start = f"2026-{month:02d}-01"
        end = "2026-07-20" if month == 7 else f"2026-{month + 1:02d}-01"
        all_2026.extend(query(org_id, start, end))
    dedup = {item["adjunctUrl"]: item for item in all_2026}
    all_2026 = sorted(dedup.values(), key=lambda item: item.get("announcementTime", 0))
    (DATA / "announcements_2026.json").write_text(
        json.dumps(all_2026, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    q1 = [
        item for item in all_2026
        if "2026年一季度报告" in clean_title(item["announcementTitle"])
        or "2026年第一季度报告" in clean_title(item["announcementTitle"])
    ]
    if not q1:
        raise RuntimeError("Missing 2026 Q1 report")
    manifest.append(download_pdf(q1[-1], REPORTS, "2026Q1_盐津铺子_第一季度报告.pdf"))

    keywords = (
        "权益分派", "利润分配", "回购", "减持", "质押", "激励", "员工持股",
        "董事", "监事", "高级管理人员", "总经理", "投资", "收购", "关联交易",
        "股东大会决议", "监管", "问询", "业绩快报",
    )
    selected = [item for item in all_2026 if any(k in clean_title(item["announcementTitle"]) for k in keywords)]
    for item in selected:
        try:
            manifest.append(download_pdf(item, ANNOUNCEMENTS))
        except Exception as exc:
            print(f"WARN announcement download failed: {clean_title(item['announcementTitle'])}: {exc}")

    (REPORTS / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for report in ("RPT_DMSK_FN_INCOME", "RPT_DMSK_FN_BALANCE", "RPT_DMSK_FN_CASHFLOW"):
        rows = fetch_eastmoney(report, 500)
        (DATA / f"{report}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    valuation = fetch_eastmoney("RPT_VALUEANALYSIS_DET", 5000, "TRADE_DATE")
    (DATA / "valuation_history_raw.json").write_text(
        json.dumps(valuation, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"org_id": org_id, "reports": len(manifest), "announcements_2026": len(all_2026), "selected": len(selected), "valuation_rows": len(valuation)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
