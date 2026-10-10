#!/usr/bin/env python3
"""通用基金分红再投净值采集与清洗脚本 (Collect Reinvested NAV).

通过东方财富接口采集基金历史单位净值、累计净值、分红与分拆记录，
并按照全收益财富指数口径自动复算分红再投净值，保存至 indices/sources/fund-nav-correct/。

接口: https://api.fund.eastmoney.com/f10/lsjz
字段: FSRQ=日期, DWJZ=单位净值, LJJZ=累计净值, FHSP=分红拆分说明
"""
from __future__ import annotations

import csv
import json
import math
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = Path(__file__).resolve().parents[2]
OUTPUT_DIR = BASE / "sources" / "fund-nav-correct"
API_URL = "https://api.fund.eastmoney.com/f10/lsjz"
HEADERS = {
    "Referer": "https://fundf10.eastmoney.com/",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}

DIVIDEND_RE = re.compile(r"每10份派现金([0-9.]+)元")
SPLIT_RE = re.compile(r"每(\d+)份分拆([0-9.]+)份|每份基金份额分拆([0-9.]+)份")


def parse_dividend_and_split(fhsp: str | None) -> tuple[float, float]:
    """解析分红和分拆。返回 (每份现金分红, 每份拆分后的新份额数)。"""
    if not fhsp:
        return 0.0, 1.0
    div = 0.0
    m = DIVIDEND_RE.search(fhsp)
    if m:
        div = float(m.group(1)) / 10

    split_ratio = 1.0
    m2 = SPLIT_RE.search(fhsp)
    if m2:
        if m2.group(3):
            split_ratio = float(m2.group(3))
        elif m2.group(1) and m2.group(2):
            split_ratio = float(m2.group(2)) / float(m2.group(1))
    return div, split_ratio


def fetch_nav_page(code: str, page_index: int, page_size: int = 200) -> dict:
    params = urlencode({
        "fundCode": code,
        "pageIndex": page_index,
        "pageSize": page_size,
        "startDate": "",
        "endDate": "",
    })
    request = Request(f"{API_URL}?{params}", headers=HEADERS)
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def fetch_all_nav(code: str) -> list[dict]:
    first = fetch_nav_page(code, 1)
    total = int(first["TotalCount"])
    page_size = int(first["PageSize"])
    rows = list(first["Data"]["LSJZList"])
    pages = math.ceil(total / page_size)
    for page in range(2, pages + 1):
        payload = fetch_nav_page(code, page)
        rows.extend(payload["Data"]["LSJZList"])
    rows.sort(key=lambda row: row["FSRQ"])
    if len(rows) != total:
        print(f"  警告: {code} 记录数不一致 expected={total}, actual={len(rows)}")
    return rows


def build_reinvested_nav(rows: list[dict]) -> tuple[dict[date, float], list[dict]]:
    """用单位净值+现金分红+分拆，复算分红再投净值（全收益口径）。"""
    obs = []
    for r in rows:
        if not r.get("DWJZ"):
            continue
        div, split_ratio = parse_dividend_and_split(r.get("FHSP") or "")
        try:
            d = datetime.strptime(r["FSRQ"], "%Y-%m-%d").date()
            nav = float(r["DWJZ"])
            cum = float(r["LJJZ"]) if r.get("LJJZ") else nav
        except (ValueError, KeyError):
            continue
        obs.append({
            "date": d,
            "unit_nav": nav,
            "cumulative_nav": cum,
            "dividend": div,
            "split_ratio": split_ratio,
            "raw_fhsp": r.get("FHSP") or "",
        })
    obs.sort(key=lambda x: x["date"])
    if not obs:
        return {}, []

    wealth = obs[0]["unit_nav"]
    prev_nav = obs[0]["unit_nav"]
    obs[0]["reinvested_nav"] = wealth
    adjusted = {obs[0]["date"]: wealth}

    for item in obs[1:]:
        nav = item["unit_nav"]
        split = item["split_ratio"]
        div = item["dividend"]
        wealth *= (nav * split + div) / prev_nav
        item["reinvested_nav"] = wealth
        adjusted[item["date"]] = wealth
        prev_nav = nav

    return adjusted, obs


def save_fund_csv(code: str, name: str, records: list[dict]) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUTPUT_DIR / f"{code}_{name}_净值.csv"
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "unit_nav", "cumulative_nav", "reinvested_nav", "dividend", "split_ratio", "event_note"])
        for r in records:
            writer.writerow([
                r["date"].isoformat(),
                f"{r['unit_nav']:.4f}",
                f"{r['cumulative_nav']:.4f}",
                f"{r['reinvested_nav']:.6f}",
                f"{r['dividend']:.6f}",
                f"{r['split_ratio']:.4f}",
                r["raw_fhsp"],
            ])
    return csv_path


def process_fund(code: str, name: str) -> Path | None:
    print(f"正在采集并清洗: {code} {name} ...")
    try:
        rows = fetch_all_nav(code)
    except Exception as e:
        print(f"  采集失败: {e}")
        return None

    adj_map, records = build_reinvested_nav(rows)
    if not records:
        print(f"  警告: 无法构建复权净值")
        return None

    path = save_fund_csv(code, name, records)
    print(f"  已保存至: {path.name} (共 {len(records)} 条日线记录, {records[0]['date']} ~ {records[-1]['date']})")
    return path


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        code_arg = sys.argv[1]
        name_arg = sys.argv[2]
        process_fund(code_arg, name_arg)
    else:
        print("用法: python3 collect_fund_nav_correct.py <基金代码> <基金名称>")
        print("示例: python3 collect_fund_nav_correct.py 515100 景顺长城中证红利低波动100ETF")
