#!/usr/bin/env python3
"""采集512890官方净值并复算相对中证红利低波动全收益指数的跟踪差。"""

from __future__ import annotations

import csv
import json
import math
import statistics
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = Path(__file__).resolve().parents[1]
PRICE_DIR = BASE / "sources" / "etf-hisotry-price"
INDEX_FILE = BASE / "sources" / "performance-data" / "H30269_中证红利低波动_全收益_2016-06-30_2026-07-31.csv"
DAILY_OUTPUT = PRICE_DIR / "512890_vs_中证红利低波动全收益_2019-01-18_2026-07-31.csv"
SUMMARY_OUTPUT = PRICE_DIR / "512890_vs_中证红利低波动全收益_跟踪差汇总.csv"
SOURCE_OUTPUT = PRICE_DIR / "512890_历史净值_东方财富_2018-12-19_2026-08-04.json"

API_URL = "https://api.fund.eastmoney.com/f10/lsjz"
FUND_CODE = "512890"
START_DATE = date(2019, 1, 18)
END_DATE = date(2026, 7, 31)


def fetch_page(page_index: int, page_size: int = 200) -> dict:
    params = urlencode(
        {
            "fundCode": FUND_CODE,
            "pageIndex": page_index,
            "pageSize": page_size,
            "startDate": "",
            "endDate": "",
        }
    )
    request = Request(
        f"{API_URL}?{params}",
        headers={
            "Referer": "https://fundf10.eastmoney.com/",
            "User-Agent": "Mozilla/5.0",
        },
    )
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def fetch_all_nav() -> list[dict]:
    first = fetch_page(1)
    total = int(first["TotalCount"])
    page_size = int(first["PageSize"])
    rows = list(first["Data"]["LSJZList"])
    pages = math.ceil(total / page_size)
    for page in range(2, pages + 1):
        payload = fetch_page(page)
        rows.extend(payload["Data"]["LSJZList"])
    rows.sort(key=lambda row: row["FSRQ"])
    if len(rows) != total:
        raise RuntimeError(f"净值记录数不一致：expected={total}, actual={len(rows)}")
    return rows


def read_index() -> dict[date, float]:
    with INDEX_FILE.open(encoding="utf-8-sig") as handle:
        return {
            datetime.strptime(row["交易日期"], "%Y%m%d").date(): float(row["收盘点位"])
            for row in csv.DictReader(handle)
        }


def annualized_return(start_value: float, end_value: float, start: date, end: date) -> float:
    years = (end - start).days / 365.2425
    return (end_value / start_value) ** (1 / years) - 1


def tracking_error(rows: list[dict], start: date, end: date) -> float:
    selected = [row for row in rows if start <= row["date"] <= end]
    differences = []
    for previous, current in zip(selected, selected[1:]):
        fund_return = current["fund_nav"] / previous["fund_nav"] - 1
        index_return = current["index"] / previous["index"] - 1
        differences.append(fund_return - index_return)
    return statistics.stdev(differences) * math.sqrt(250)


def summarize(rows: list[dict], label: str, start: date, end: date) -> dict[str, str]:
    lookup = {row["date"]: row for row in rows}
    start_row, end_row = lookup[start], lookup[end]
    fund_total = end_row["fund_nav"] / start_row["fund_nav"] - 1
    index_total = end_row["index"] / start_row["index"] - 1
    fund_annual = annualized_return(start_row["fund_nav"], end_row["fund_nav"], start, end)
    index_annual = annualized_return(start_row["index"], end_row["index"], start, end)
    return {
        "区间": label,
        "起始日期": start.isoformat(),
        "结束日期": end.isoformat(),
        "交易日数": str(sum(start <= row["date"] <= end for row in rows)),
        "ETF累计收益(%)": f"{fund_total * 100:.4f}",
        "全收益指数累计收益(%)": f"{index_total * 100:.4f}",
        "累计收益差(百分点)": f"{(fund_total - index_total) * 100:.4f}",
        "ETF年化收益(%)": f"{fund_annual * 100:.4f}",
        "全收益指数年化收益(%)": f"{index_annual * 100:.4f}",
        "年化跟踪差(百分点)": f"{(fund_annual - index_annual) * 100:.4f}",
        "年化跟踪误差(%)": f"{tracking_error(rows, start, end) * 100:.4f}",
    }


def main() -> None:
    nav_rows = fetch_all_nav()
    cash_events = [row for row in nav_rows if "派现金" in (row.get("FHSP") or "")]
    if cash_events:
        raise RuntimeError("检测到现金分红，不能直接用累计净值替代分红再投资收益")

    SOURCE_OUTPUT.write_text(json.dumps(nav_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    nav = {
        datetime.strptime(row["FSRQ"], "%Y-%m-%d").date(): float(row["LJJZ"])
        for row in nav_rows
        if row.get("LJJZ")
    }
    index = read_index()
    common_dates = sorted(day for day in set(nav) & set(index) if START_DATE <= day <= END_DATE)
    if not common_dates or common_dates[0] != START_DATE or common_dates[-1] != END_DATE:
        raise RuntimeError(f"共同区间异常：{common_dates[0]}—{common_dates[-1]}")

    start_nav, start_index = nav[START_DATE], index[START_DATE]
    aligned = [
        {
            "date": day,
            "fund_nav": nav[day],
            "index": index[day],
            "fund_normalized": nav[day] / start_nav * 100,
            "index_normalized": index[day] / start_index * 100,
            "cumulative_gap": nav[day] / start_nav * 100 - index[day] / start_index * 100,
        }
        for day in common_dates
    ]

    with DAILY_OUTPUT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["日期", "ETF累计净值", "全收益指数点位", "ETF归一化", "全收益指数归一化", "累计收益差(百分点)"],
        )
        writer.writeheader()
        for row in aligned:
            writer.writerow(
                {
                    "日期": row["date"].isoformat(),
                    "ETF累计净值": f'{row["fund_nav"]:.4f}',
                    "全收益指数点位": f'{row["index"]:.2f}',
                    "ETF归一化": f'{row["fund_normalized"]:.6f}',
                    "全收益指数归一化": f'{row["index_normalized"]:.6f}',
                    "累计收益差(百分点)": f'{row["cumulative_gap"]:.6f}',
                }
            )

    five_year_target = date(2021, 7, 31)
    five_year_start = max(day for day in common_dates if day <= five_year_target)
    summaries = [
        summarize(aligned, "上市以来", START_DATE, END_DATE),
        summarize(aligned, "近5年", five_year_start, END_DATE),
    ]
    with SUMMARY_OUTPUT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)

    print(
        json.dumps(
            {
                "净值记录": len(nav_rows),
                "共同交易日": len(aligned),
                "共同区间": [str(common_dates[0]), str(common_dates[-1])],
                "现金分红事件": len(cash_events),
                "拆分事件": [
                    row["FSRQ"]
                    for row in nav_rows
                    if "拆分" in (row.get("FHSP") or "") or "分拆" in (row.get("FHSP") or "")
                ],
                "汇总": summaries,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
