#!/usr/bin/env python3
"""Download China Shenhua official filings and Eastmoney datasets."""
from __future__ import annotations

import calendar
import json
import re
from datetime import date, datetime
from pathlib import Path

import fitz
import requests

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"
REPORTS = BASE / "年报"
TEXT = DATA / "pdf_text"
ANNOUNCEMENTS = REPORTS / "公告"
CODE = "601088"
SECUCODE = "601088.SH"
ORG_ID = "9900003701"
CNINFO = "https://www.cninfo.com.cn/new/hisAnnouncement/query"
STATIC = "https://static.cninfo.com.cn/"
EASTMONEY = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.cninfo.com.cn/"}
CUTOFF = date(2026, 7, 21)


def clean_title(value: str) -> str:
    return re.sub(r"<.*?>", "", value).replace("/", "_").strip()


def query(start: str, end: str, searchkey: str = "", category: str = "") -> list[dict]:
    payload = {
        "pageNum": 1, "pageSize": 100, "column": "sse", "tabName": "fulltext",
        "plate": "sh", "stock": f"{CODE},{ORG_ID}", "searchkey": searchkey,
        "secid": "", "category": category, "trade": "", "seDate": f"{start}~{end}",
        "sortName": "", "sortType": "", "isHLtitle": "true",
    }
    response = requests.post(CNINFO, headers=HEADERS, data=payload, timeout=60)
    response.raise_for_status()
    result = response.json()
    if result.get("totalAnnouncement", 0) > 100:
        raise RuntimeError(f"Query too broad: {start}~{end}: {result['totalAnnouncement']}")
    return result.get("announcements") or []


def month_ranges(start_year: int, start_month: int, end: date):
    year, month = start_year, start_month
    while (year, month) <= (end.year, end.month):
        first = date(year, month, 1)
        last = date(year, month, calendar.monthrange(year, month)[1])
        yield first.isoformat(), min(last, end).isoformat()
        month = month + 1
        if month == 13:
            year, month = year + 1, 1


def download_pdf(item: dict, folder: Path, filename: str | None = None) -> dict:
    url = STATIC + item["adjunctUrl"].lstrip("/")
    title = clean_title(item["announcementTitle"])
    path = folder / (filename or f"{title}.pdf")
    if not path.exists():
        response = requests.get(url, headers=HEADERS, timeout=180)
        response.raise_for_status()
        if not response.content.startswith(b"%PDF"):
            raise RuntimeError(f"Not PDF: {url}")
        path.write_bytes(response.content)
    doc = fitz.open(path)
    text_path = TEXT / f"{path.stem}.txt"
    if not text_path.exists():
        text_path.write_text("\n\n".join(str(page.get_text()) for page in doc), encoding="utf-8")
    return {
        "date": datetime.fromtimestamp(item.get("announcementTime", 0) / 1000).date().isoformat(),
        "title": title, "url": url, "file": str(path.relative_to(BASE)),
        "bytes": path.stat().st_size, "pages": doc.page_count,
    }


def fetch_eastmoney(report_name: str, page_size: int = 5000, sort_column: str = "REPORT_DATE") -> list[dict]:
    params = {
        "reportName": report_name, "columns": "ALL", "filter": f'(SECUCODE="{SECUCODE}")',
        "pageSize": page_size, "sortColumns": sort_column, "sortTypes": "-1",
        "source": "HSF10", "client": "PC",
    }
    response = requests.get(EASTMONEY, params=params, timeout=90)
    response.raise_for_status()
    payload = response.json()
    if not payload.get("success") or not payload.get("result"):
        raise RuntimeError(f"Eastmoney failed: {report_name}: {payload}")
    return payload["result"]["data"]


def main() -> None:
    for folder in (DATA, REPORTS, TEXT, ANNOUNCEMENTS, BASE / "charts", BASE / "reports", BASE / "scripts"):
        folder.mkdir(parents=True, exist_ok=True)

    annual_items = query("2021-01-01", CUTOFF.isoformat(), searchkey="年度报告")
    manifest: list[dict] = []
    for year in range(2020, 2026):
        matches = [item for item in annual_items
                   if f"{year}年度报告" in clean_title(item["announcementTitle"])
                   and all(word not in clean_title(item["announcementTitle"]) for word in ("摘要", "英文", "半年度"))]
        if not matches:
            raise RuntimeError(f"Missing annual report {year}")
        manifest.append(download_pdf(matches[0], REPORTS, f"{year}_中国神华_年度报告.pdf"))

    all_items: list[dict] = []
    for start, end in month_ranges(2025, 7, CUTOFF):
        all_items.extend(query(start, end))
    for keyword in ("第一季度报告", "权益分派", "利润分配", "收购", "资产购买", "关联交易", "增资", "董事", "总经理", "减持", "质押", "回购", "监管", "问询", "运营数据"):
        all_items.extend(query("2025-07-01", CUTOFF.isoformat(), searchkey=keyword))
    dedup = {item["adjunctUrl"]: item for item in all_items}
    all_items = sorted(dedup.values(), key=lambda item: item.get("announcementTime", 0))
    (DATA / "announcements_2025H2_2026.json").write_text(json.dumps(all_items, ensure_ascii=False, indent=2), encoding="utf-8")

    q1 = [item for item in all_items if "2026年第一季度报告" in clean_title(item["announcementTitle"])]
    if not q1:
        raise RuntimeError("Missing 2026 Q1 report")
    manifest.append(download_pdf(q1[-1], REPORTS, "2026Q1_中国神华_第一季度报告.pdf"))

    keep_titles = {
        "中国神华2025年半年度权益分派实施公告",
        "中国神华2025年度权益分派实施公告",
        "中国神华2026年6月份主要运营数据公告",
        "中国神华能源股份有限公司发行股份及支付现金购买资产并募集配套资金暨关联交易报告书",
        "中国神华能源股份有限公司发行股份及支付现金购买资产并募集配套资金暨关联交易实施情况暨新增股份上市公告书",
        "中国神华能源股份有限公司发行股份及支付现金购买资产并募集配套资金暨关联交易之募集配套资金向特定对象发行股份发行情况报告书",
        "中国神华关于发行股份及支付现金购买资产并募集配套资金暨关联交易之标的资产过户完成的公告",
        "中国神华关于向财务公司增资暨关联交易进展的公告",
    }
    selected = [item for item in all_items if clean_title(item["announcementTitle"]) in keep_titles]
    for item in selected:
        try:
            manifest.append(download_pdf(item, ANNOUNCEMENTS))
        except Exception as exc:
            print(f"WARN {clean_title(item['announcementTitle'])}: {exc}")

    (REPORTS / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    for report in ("RPT_DMSK_FN_INCOME", "RPT_DMSK_FN_BALANCE", "RPT_DMSK_FN_CASHFLOW"):
        rows = fetch_eastmoney(report, 500)
        (DATA / f"{report}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    valuation = fetch_eastmoney("RPT_VALUEANALYSIS_DET", 5000, "TRADE_DATE")
    (DATA / "valuation_history_raw.json").write_text(json.dumps(valuation, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"annual_and_q1": 7, "announcements": len(all_items), "selected_downloads": len(selected), "valuation_rows": len(valuation)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
