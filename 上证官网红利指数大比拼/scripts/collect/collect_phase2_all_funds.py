#!/usr/bin/env python3
"""批量采集二期所有基金的单位净值+分红，手工复算分红再投净值。

基于中证官网跟踪产品全量数据，按成立时间分组：
- 5年组: 成立于2021-08-07之前
- 3年组: 成立于2021-08-08至2023-08-07
- 观察池: 成立于2023-08-08之后，且规模≥1亿（避免微型基金噪音）

排除：联接基金、境外上市ETF、指数增强（单独标注）
"""
from __future__ import annotations

import csv
import json
import math
import re
import time
from dataclasses import dataclass, asdict
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = Path(__file__).resolve().parents[2]
OUTPUT_DIR = BASE / "sources" / "fund-nav-correct"
TRACKING_JSON = BASE / "sources" / "tracking-products-verify" / "all.json"
API_URL = "https://api.fund.eastmoney.com/f10/lsjz"
HEADERS = {
    "Referer": "https://fundf10.eastmoney.com/",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}

DIVIDEND_RE = re.compile(r"每10份派现金([0-9.]+)元")
SPLIT_RE = re.compile(r"每(\d+)份分拆([0-9.]+)份|每份基金份额分拆([0-9.]+)份")

CUTOFF = datetime(2026, 8, 7)
FIVE_YR_CUTOFF = datetime(2021, 8, 7)
THREE_YR_CUTOFF = datetime(2023, 8, 7)

# 排除的境外代码
EXCLUDE_CODES = {"3070 HK Equity", "SIC300I TT Equity", "SHD SP Equity",
                 "INCSGD SP Equity", "3437 HK Equity"}


def parse_dividend_and_split(fhsp: str | None) -> tuple[float, float]:
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
        time.sleep(0.1)
    rows.sort(key=lambda row: row["FSRQ"])
    return rows


def build_reinvested_nav(rows: list[dict]) -> dict[date, float]:
    obs = []
    for r in rows:
        if not r.get("DWJZ"):
            continue
        div, split_ratio = parse_dividend_and_split(r.get("FHSP") or "")
        try:
            d = datetime.strptime(r["FSRQ"], "%Y-%m-%d").date()
            nav = float(r["DWJZ"])
        except (ValueError, KeyError):
            continue
        obs.append((d, nav, div, split_ratio))
    obs.sort()
    if not obs:
        return {}
    adjusted = {obs[0][0]: obs[0][1]}
    wealth = obs[0][1]
    prev_nav = obs[0][1]
    for day, nav, div, split in obs[1:]:
        wealth *= (nav * split + div) / prev_nav
        adjusted[day] = wealth
        prev_nav = nav
    return adjusted


def build_fund_list() -> list[dict]:
    """从中证跟踪产品数据构建基金清单。"""
    with open(TRACKING_JSON, encoding="utf-8") as f:
        data = json.load(f)

    index_names = {
        "000821": "300红利", "930740": "300红利低波", "932422": "A500红利低波",
        "931157": "SHS红利成长LV", "930917": "SHS高股息", "000151": "上国红利",
        "H50040": "上红低波", "000015": "上证红利", "931446": "东证红利低波",
        "CESFHY": "中华预期高股息", "000922": "中证红利", "932315": "中证红利质量",
        "000824": "国企红利", "931722": "国新港股通央企红利", "000825": "央企红利",
        "931231": "央企红利50", "932039": "央企股东回报", "932305": "智选高股息",
        "H30094": "消费红利", "931233": "港股通央企红利", "930839": "港股通高息精选",
        "930914": "港股通高股息", "H30270": "红利价值", "H30269": "红利低波",
        "930955": "红利低波100", "H30089": "红利潜力", "931468": "红利质量",
        "931132": "诚通央企红利", "H11140": "香港红利", "H30366": "高息策略",
    }

    funds = []
    for idx_code, products in data.items():
        for p in products:
            code = p["productCode"]
            if code in EXCLUDE_CODES:
                continue
            if p["fundType"] == "联接基金":
                continue
            inception = datetime.strptime(p["inceptionDate"], "%Y-%m-%d")
            aum = float(p.get("aum") or 0)

            if inception <= FIVE_YR_CUTOFF:
                group = "5年组"
            elif inception <= THREE_YR_CUTOFF:
                group = "3年组"
            else:
                group = "观察池"
                # 观察池只保留规模≥1亿的
                if aum < 1.0:
                    continue

            funds.append({
                "code": code,
                "name": p["fundName"],
                "type": p["fundType"],
                "aum": aum,
                "inception": p["inceptionDate"],
                "index_code": idx_code,
                "index_name": index_names.get(idx_code, idx_code),
                "group": group,
            })

    funds.sort(key=lambda x: (x["group"], -x["aum"]))
    return funds


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    funds = build_fund_list()

    print(f"共 {len(funds)} 只基金待处理")
    for g in ["5年组", "3年组", "观察池"]:
        gfunds = [f for f in funds if f["group"] == g]
        print(f"  {g}: {len(gfunds)}只")

    summary = []
    for i, fund in enumerate(funds):
        code = fund["code"]
        name = fund["name"]
        short_name = name.replace("交易型开放式指数证券投资基金", "ETF").replace("中证", "")[:20]

        # 检查是否已采集
        existing = list(OUTPUT_DIR.glob(f"{code}_*_净值.csv"))
        if existing:
            print(f"[{i+1}/{len(funds)}] {code} {short_name} 已存在，跳过")
            # 仍读入汇总
            df_rows = []
            with open(existing[0], encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    df_rows.append(row)
            if df_rows:
                start_date = df_rows[0]["date"]
                end_date = df_rows[-1]["date"]
                end_nav = float(df_rows[-1]["reinvested_nav"])
                start_nav = float(df_rows[0]["reinvested_nav"])
                days = (datetime.strptime(end_date, "%Y-%m-%d") - datetime.strptime(start_date, "%Y-%m-%d")).days
                years = days / 365.25
                total_ret = (end_nav / start_nav - 1) * 100
                cagr = ((end_nav / start_nav) ** (1 / years) - 1) * 100 if years > 0 else 0
                summary.append({
                    **fund,
                    "short_name": short_name,
                    "data_points": len(df_rows),
                    "start_date": start_date,
                    "end_date": end_date,
                    "total_return_pct": round(total_ret, 2),
                    "cagr_pct": round(cagr, 2),
                    "csv_file": existing[0].name,
                })
            continue

        print(f"[{i+1}/{len(funds)}] 采集 {code} {short_name}...")
        try:
            rows = fetch_all_nav(code)
        except Exception as e:
            print(f"  ❌ 采集失败: {e}")
            continue

        print(f"  {len(rows)}条净值记录")

        reinvested = build_reinvested_nav(rows)
        if not reinvested:
            print(f"  ⚠ 无法构建复权净值")
            continue

        nav_map = {}
        for r in rows:
            if not r.get("DWJZ"):
                continue
            try:
                d = datetime.strptime(r["FSRQ"], "%Y-%m-%d").date()
                div, split = parse_dividend_and_split(r.get("FHSP") or "")
                nav_map[d] = {
                    "dwjz": float(r["DWJZ"]),
                    "ljjz": float(r["LJJZ"]) if r.get("LJJZ") else None,
                    "dividend": div,
                    "split_ratio": split,
                    "fhsp": r.get("FHSP") or "",
                }
            except (ValueError, KeyError):
                continue

        csv_path = OUTPUT_DIR / f"{code}_{short_name}_净值.csv"
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["date", "unit_nav", "cumulative_nav", "reinvested_nav",
                           "dividend", "split_ratio", "event_note"])
            for d in sorted(nav_map.keys() & reinvested.keys()):
                info = nav_map[d]
                writer.writerow([
                    d.isoformat(),
                    f'{info["dwjz"]:.4f}',
                    f'{info["ljjz"]:.4f}' if info["ljjz"] else "",
                    f'{reinvested[d]:.6f}',
                    f'{info["dividend"]:.6f}',
                    f'{info["split_ratio"]:.4f}',
                    info["fhsp"],
                ])

        dates = sorted(reinvested.keys())
        start_nav = reinvested[dates[0]]
        end_nav = reinvested[dates[-1]]
        days = (dates[-1] - dates[0]).days
        years = days / 365.25
        total_ret = (end_nav / start_nav - 1) * 100
        cagr = ((end_nav / start_nav) ** (1 / years) - 1) * 100 if years > 0 else 0

        div_count = sum(1 for r in rows if r.get("FHSP") and "派现金" in (r["FHSP"] or ""))

        summary.append({
            **fund,
            "short_name": short_name,
            "data_points": len(dates),
            "start_date": dates[0].isoformat(),
            "end_date": dates[-1].isoformat(),
            "total_return_pct": round(total_ret, 2),
            "cagr_pct": round(cagr, 2),
            "dividend_count": div_count,
            "csv_file": csv_path.name,
        })
        print(f"  ✓ {dates[0]}~{dates[-1]}, {len(dates)}条, CAGR={cagr:.2f}%")
        time.sleep(0.3)

    summary_path = OUTPUT_DIR / "_汇总_基金净值.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\n✓ 全部完成，共{len(summary)}只基金")


if __name__ == "__main__":
    main()
