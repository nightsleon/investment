#!/usr/bin/env python3
"""采集三只红利ETF官方净值，复算相对各自全收益指数的跟踪差。"""

from __future__ import annotations

import csv
import json
import math
import re
import statistics
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = Path(__file__).resolve().parents[1]
PRICE_DIR = BASE / "sources" / "etf-hisotry-price"
PERFORMANCE_DIR = BASE / "sources" / "performance-data"
API_URL = "https://api.fund.eastmoney.com/f10/lsjz"
END_DATE = date(2026, 7, 31)
DIVIDEND_RE = re.compile(r"每10份派现金([0-9.]+)元")


@dataclass(frozen=True)
class FundConfig:
    code: str
    fund_name: str
    index_name: str
    index_file: str
    start_date: date
    index_date_format: str


FUNDS = (
    FundConfig(
        code="515450",
        fund_name="南方红利低波50ETF",
        index_name="标普中国A股大盘红利低波50全收益指数",
        index_file="SPDJI_标普中国A股大盘红利低波50_CNY_TR_2016-06-30_2026-07-31.csv",
        start_date=date(2020, 2, 26),
        index_date_format="%Y-%m-%d",
    ),
    FundConfig(
        code="515180",
        fund_name="易方达红利ETF",
        index_name="中证红利全收益指数",
        index_file="000922_中证红利_全收益_2016-06-30_2026-07-31.csv",
        start_date=date(2019, 12, 20),
        index_date_format="%Y%m%d",
    ),
    FundConfig(
        code="515100",
        fund_name="景顺红利低波100ETF",
        index_name="中证红利低波动100全收益指数",
        index_file="930955_中证红利低波动100_全收益_2016-06-30_2026-07-31.csv",
        start_date=date(2020, 7, 3),
        index_date_format="%Y%m%d",
    ),
)


def fetch_page(code: str, page_index: int, page_size: int = 200) -> dict:
    params = urlencode(
        {
            "fundCode": code,
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


def fetch_all_nav(code: str) -> list[dict]:
    first = fetch_page(code, 1)
    total = int(first["TotalCount"])
    page_size = int(first["PageSize"])
    rows = list(first["Data"]["LSJZList"])
    pages = math.ceil(total / page_size)
    for page in range(2, pages + 1):
        rows.extend(fetch_page(code, page)["Data"]["LSJZList"])
    rows.sort(key=lambda row: row["FSRQ"])
    if len(rows) != total:
        raise RuntimeError(f"{code}净值记录数不一致：expected={total}, actual={len(rows)}")
    return rows


def parse_dividend(text: str) -> float:
    if not text:
        return 0.0
    match = DIVIDEND_RE.fullmatch(text)
    if not match:
        raise RuntimeError(f"未识别的基金份额事件：{text}")
    return float(match.group(1)) / 10


def build_adjusted_nav(rows: list[dict]) -> dict[date, float]:
    observations = []
    for row in rows:
        if not row.get("DWJZ"):
            continue
        observations.append(
            (
                datetime.strptime(row["FSRQ"], "%Y-%m-%d").date(),
                float(row["DWJZ"]),
                parse_dividend(row.get("FHSP") or ""),
            )
        )
    observations.sort()
    if not observations:
        raise RuntimeError("没有可用单位净值")

    adjusted = {observations[0][0]: observations[0][1]}
    wealth_index = observations[0][1]
    previous_nav = observations[0][1]
    for day, nav, dividend in observations[1:]:
        wealth_index *= (nav + dividend) / previous_nav
        adjusted[day] = wealth_index
        previous_nav = nav
    return adjusted


def read_index(config: FundConfig) -> dict[date, float]:
    path = PERFORMANCE_DIR / config.index_file
    with path.open(encoding="utf-8-sig") as handle:
        return {
            datetime.strptime(row["交易日期"], config.index_date_format).date(): float(row["收盘点位"])
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


def collect_one(config: FundConfig) -> dict:
    nav_rows = fetch_all_nav(config.code)
    raw_output = PRICE_DIR / f"{config.code}_历史净值_东方财富_{nav_rows[0]['FSRQ']}_{nav_rows[-1]['FSRQ']}.json"
    raw_output.write_text(json.dumps(nav_rows, ensure_ascii=False, indent=2), encoding="utf-8")

    adjusted_nav = build_adjusted_nav(nav_rows)
    index = read_index(config)
    common_dates = sorted(
        day for day in set(adjusted_nav) & set(index) if config.start_date <= day <= END_DATE
    )
    if not common_dates or common_dates[0] != config.start_date or common_dates[-1] != END_DATE:
        raise RuntimeError(f"{config.code}共同区间异常：{common_dates[0]}—{common_dates[-1]}")

    start_nav = adjusted_nav[config.start_date]
    start_index = index[config.start_date]
    aligned = [
        {
            "date": day,
            "fund_nav": adjusted_nav[day],
            "index": index[day],
            "fund_normalized": adjusted_nav[day] / start_nav * 100,
            "index_normalized": index[day] / start_index * 100,
            "cumulative_gap": adjusted_nav[day] / start_nav * 100 - index[day] / start_index * 100,
        }
        for day in common_dates
    ]

    daily_output = PRICE_DIR / (
        f"{config.code}_vs_{config.index_name}_{config.start_date}_{END_DATE}.csv"
    )
    with daily_output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["日期", "ETF复权净值", "全收益指数点位", "ETF归一化", "全收益指数归一化", "累计收益差(百分点)"],
        )
        writer.writeheader()
        for row in aligned:
            writer.writerow(
                {
                    "日期": row["date"].isoformat(),
                    "ETF复权净值": f'{row["fund_nav"]:.8f}',
                    "全收益指数点位": f'{row["index"]:.4f}',
                    "ETF归一化": f'{row["fund_normalized"]:.6f}',
                    "全收益指数归一化": f'{row["index_normalized"]:.6f}',
                    "累计收益差(百分点)": f'{row["cumulative_gap"]:.6f}',
                }
            )

    five_year_target = date(2021, 7, 31)
    five_year_start = max(day for day in common_dates if day <= five_year_target)
    summaries = [
        summarize(aligned, "上市以来", config.start_date, END_DATE),
        summarize(aligned, "近5年", five_year_start, END_DATE),
    ]
    summary_output = PRICE_DIR / f"{config.code}_vs_{config.index_name}_跟踪差汇总.csv"
    with summary_output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)

    events = [
        {"日期": row["FSRQ"], "事件": row["FHSP"]}
        for row in nav_rows
        if row.get("FHSP")
    ]
    return {
        "代码": config.code,
        "共同交易日": len(aligned),
        "共同区间": [str(common_dates[0]), str(common_dates[-1])],
        "份额事件": events,
        "日线输出": str(daily_output),
        "汇总输出": str(summary_output),
        "汇总": summaries,
    }


def main() -> None:
    print(json.dumps([collect_one(config) for config in FUNDS], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
