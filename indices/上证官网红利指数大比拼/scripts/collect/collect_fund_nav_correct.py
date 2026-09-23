#!/usr/bin/env python3
"""用东方财富基金净值接口采集所有二期基金的单位净值+分红，并手工复算分红再投净值。

接口: https://api.fund.eastmoney.com/f10/lsjz
字段: FSRQ=日期, DWJZ=单位净值, LJJZ=累计净值, FHSP=分红拆分说明
"""
from __future__ import annotations

import csv
import json
import math
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = Path(__file__).resolve().parents[2]
OUTPUT_DIR = BASE / "sources" / "fund-nav-correct"  # 正确口径的净值
API_URL = "https://api.fund.eastmoney.com/f10/lsjz"
HEADERS = {
    "Referer": "https://fundf10.eastmoney.com/",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}

DIVIDEND_RE = re.compile(r"每10份派现金([0-9.]+)元")
SPLIT_RE = re.compile(r"每(\d+)份分拆([0-9.]+)份|每份基金份额分拆([0-9.]+)份")


def parse_dividend_and_split(fhsp: str | None) -> tuple[float, float]:
    """解析分红和分拆。
    返回 (每份现金分红, 每份拆分后的新份额数)。
    例：每10份派现金1元 -> (0.1, 1.0)
        每份基金份额分拆2.0份 -> (0.0, 2.0)
        每10份分拆20份 -> (0.0, 2.0)
    """
    if not fhsp:
        return 0.0, 1.0
    # 现金分红
    div = 0.0
    m = DIVIDEND_RE.search(fhsp)
    if m:
        div = float(m.group(1)) / 10

    # 分拆
    split_ratio = 1.0
    m2 = SPLIT_RE.search(fhsp)
    if m2:
        if m2.group(3):  # 每份基金份额分拆X份
            split_ratio = float(m2.group(3))
        elif m2.group(1) and m2.group(2):  # 每N份分拆M份
            split_ratio = float(m2.group(2)) / float(m2.group(1))
    return div, split_ratio


@dataclass
class FundInfo:
    code: str
    name: str
    index_code: str  # 对应指数代码
    index_name: str  # 对应指数名称


# 二期主选池+观察池的基金，含对应指数代码
FUNDS = [
    FundInfo("512890", "华泰柏瑞中证红利低波动ETF", "H30269", "红利低波"),
    FundInfo("510880", "华泰柏瑞上证红利ETF", "000015", "上证红利"),
    FundInfo("515180", "易方达中证红利ETF", "000922", "中证红利"),
    FundInfo("515300", "嘉实沪深300红利低波动ETF", "930740", "300红利低波"),
    FundInfo("007751", "景顺长城沪港深红利成长低波动A", "931157", "SHS红利成长LV"),
    FundInfo("008928", "宏利主要消费红利A", "H30094", "消费红利"),
    FundInfo("510720", "国泰上证国有企业红利ETF", "000151", "上国红利"),
    FundInfo("513530", "华泰柏瑞港股通高股息ETF", "930914", "港股通高股息"),
    FundInfo("561580", "华泰柏瑞中证中央企业红利ETF", "000825", "央企红利"),
    FundInfo("159307", "博时中证红利低波动100ETF", "930955", "红利低波100"),
    FundInfo("159691", "工银瑞信港股通高股息精选ETF", "930839", "港股通高息精选"),
    FundInfo("560700", "广发国新央企股东回报ETF", "932039", "央企股东回报"),
    FundInfo("012708", "东方红中证红利低波动A", "930955", "红利低波100"),
    # 观察池
    FundInfo("560570", "国联安中证A500红利低波动ETF", "932422", "A500红利低波"),
]


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


def parse_dividend(fhsp: str | None) -> float:
    """解析每份分红金额（现金分红）。分拆等非现金事件返回0。"""
    if not fhsp:
        return 0.0
    m = DIVIDEND_RE.search(fhsp)
    if m:
        return float(m.group(1)) / 10  # 每10份 -> 每份
    return 0.0


def build_reinvested_nav(rows: list[dict]) -> dict[date, float]:
    """用单位净值+现金分红+分拆，复算分红再投净值（全收益口径）。

    分拆处理：每1份拆成N份，单位净值变为原来的1/N，但总资产不变。
    所以当天的等效价值 = 单位净值 × 拆分比例 + 现金分红。
    """
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
        # 当天的等效价值 = 净值 × 分拆比例 + 现金分红
        # 然后除以前一天净值，得到当日收益
        wealth *= (nav * split + div) / prev_nav
        adjusted[day] = wealth
        prev_nav = nav
    return adjusted


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    summary = []
    for fund in FUNDS:
        print(f"处理 {fund.code} {fund.name}...")
        try:
            rows = fetch_all_nav(fund.code)
        except Exception as e:
            print(f"  采集失败: {e}")
            continue

        print(f"  净值记录: {len(rows)}条")

        # 分红统计
        div_events = [r for r in rows if r.get("FHSP") and "派现金" in (r["FHSP"] or "")]
        split_events = [r for r in rows if r.get("FHSP") and ("分拆" in (r["FHSP"] or "") or "拆分" in (r["FHSP"] or ""))]
        print(f"  现金分红: {len(div_events)}次, 分拆: {len(split_events)}次")

        # 复算分红再投净值
        reinvested = build_reinvested_nav(rows)
        if not reinvested:
            print(f"  警告: 无法构建复权净值")
            continue

        dates = sorted(reinvested.keys())
        print(f"  复权净值区间: {dates[0]} ~ {dates[-1]} ({len(dates)}条)")

        # 保存CSV：date, nav_dwjz（单位净值）, nav_reinvested（分红再投）, dividend（当日分红）
        csv_path = OUTPUT_DIR / f"{fund.code}_{fund.name}_净值.csv"
        # 构建完整数据表
        nav_map = {}
        for r in rows:
            if not r.get("DWJZ"):
                continue
            try:
                d = datetime.strptime(r["FSRQ"], "%Y-%m-%d").date()
                nav_map[d] = {
                    "dwjz": float(r["DWJZ"]),
                    "ljjz": float(r["LJJZ"]) if r.get("LJJZ") else None,
                    "dividend": parse_dividend_and_split(r.get("FHSP") or "")[0],
                    "split_ratio": parse_dividend_and_split(r.get("FHSP") or "")[1],
                    "fhsp": r.get("FHSP") or "",
                }
            except (ValueError, KeyError):
                continue

        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["date", "unit_nav", "cumulative_nav", "reinvested_nav", "dividend", "split_ratio", "event_note"])
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

        print(f"  已保存: {csv_path.name}")

        # 汇总信息
        start_nav = reinvested[dates[0]]
        end_nav = reinvested[dates[-1]]
        total_return = (end_nav / start_nav - 1) * 100
        years = (dates[-1] - dates[0]).days / 365.25
        cagr = ((end_nav / start_nav) ** (1 / years) - 1) * 100 if years > 0 else 0

        summary.append({
            "fund_code": fund.code,
            "fund_name": fund.name,
            "index_code": fund.index_code,
            "index_name": fund.index_name,
            "data_points": len(dates),
            "start_date": dates[0].isoformat(),
            "end_date": dates[-1].isoformat(),
            "start_reinvested_nav": round(start_nav, 6),
            "end_reinvested_nav": round(end_nav, 6),
            "total_return_pct": round(total_return, 2),
            "cagr_pct": round(cagr, 2),
            "dividend_count": len(div_events),
            "split_count": len(split_events),
        })
        print(f"  累计收益: {total_return:.2f}%, CAGR: {cagr:.2f}%")
        print()

    # 保存汇总
    summary_path = OUTPUT_DIR / "_汇总_基金净值.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\n✓ 全部完成，共{len(summary)}只基金")
    print(f"  汇总文件: {summary_path}")


if __name__ == "__main__":
    main()
