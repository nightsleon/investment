#!/usr/bin/env python3
"""采集二期30只代表基金的净值数据。

5年组(≥5年): 11只
3年组(3-5年): 6只
观察池(<3年): 13只
"""
from __future__ import annotations

import csv
import json
import math
import re
import time
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

# 30只代表基金
FUNDS = [
    # 5年组 (11只)
    {"code": "512890", "name": "华泰柏瑞中证红利低波动ETF", "index_code": "H30269", "index_name": "红利低波", "group": "5年组"},
    {"code": "510880", "name": "华泰柏瑞上证红利ETF", "index_code": "000015", "index_name": "上证红利", "group": "5年组"},
    {"code": "515180", "name": "易方达中证红利ETF", "index_code": "000922", "index_name": "中证红利", "group": "5年组"},
    {"code": "515300", "name": "嘉实沪深300红利低波动ETF", "index_code": "930740", "index_name": "300红利低波", "group": "5年组"},
    {"code": "007751", "name": "景顺长城沪港深红利成长低波动A", "index_code": "931157", "index_name": "SHS红利成长LV", "group": "5年组"},
    {"code": "008928", "name": "宏利中证主要消费红利A", "index_code": "H30094", "index_name": "消费红利", "group": "5年组"},
    {"code": "512530", "name": "建信沪深300红利ETF", "index_code": "000821", "index_name": "300红利", "group": "5年组"},
    {"code": "501307", "name": "银河中证沪港深高股息LOF", "index_code": "930917", "index_name": "SHS高股息", "group": "5年组"},
    {"code": "007178", "name": "浙商港股通中华预期高股息指数增强", "index_code": "CESFHY", "index_name": "中华预期高股息", "group": "5年组"},
    {"code": "007671", "name": "建信中证红利潜力指数", "index_code": "H30089", "index_name": "红利潜力", "group": "5年组"},
    # 3070 HK 单独处理

    # 3年组 (6只)
    {"code": "012708", "name": "东方红中证红利低波动A", "index_code": "931446", "index_name": "东证红利低波", "group": "3年组"},
    {"code": "513530", "name": "华泰柏瑞港股通高股息ETF", "index_code": "930914", "index_name": "港股通高股息", "group": "3年组"},
    {"code": "159691", "name": "工银瑞信港股通高股息精选ETF", "index_code": "930839", "index_name": "港股通高息精选", "group": "3年组"},
    {"code": "561580", "name": "华泰柏瑞中央企业红利ETF", "index_code": "000825", "index_name": "央企红利", "group": "3年组"},
    {"code": "560700", "name": "广发国新央企股东回报ETF", "index_code": "932039", "index_name": "央企股东回报", "group": "3年组"},
    {"code": "159758", "name": "华夏中证红利质量ETF", "index_code": "931468", "index_name": "红利质量", "group": "3年组"},

    # 观察池 (13只)
    {"code": "561060", "name": "华安中证国有企业红利ETF", "index_code": "000824", "index_name": "国企红利", "group": "观察池"},
    {"code": "513910", "name": "华夏中证港股通央企红利ETF", "index_code": "931233", "index_name": "港股通央企红利", "group": "观察池"},
    {"code": "510720", "name": "国泰上证国有企业红利ETF", "index_code": "000151", "index_name": "上国红利", "group": "观察池"},
    {"code": "159307", "name": "博时中证红利低波动100ETF", "index_code": "930955", "index_name": "红利低波100", "group": "观察池"},
    {"code": "020456", "name": "平安上证红利低波动指数", "index_code": "H50040", "index_name": "上红低波", "group": "观察池"},
    {"code": "563180", "name": "银华中证高股息策略ETF", "index_code": "H30366", "index_name": "高息策略", "group": "观察池"},
    {"code": "520990", "name": "景顺长城国新港股通央企红利ETF", "index_code": "931722", "index_name": "国新港股通央企红利", "group": "观察池"},
    {"code": "021561", "name": "天弘中证央企红利50指数", "index_code": "931231", "index_name": "央企红利50", "group": "观察池"},
    {"code": "159336", "name": "融通中证诚通央企红利ETF", "index_code": "931132", "index_name": "诚通央企红利", "group": "观察池"},
    {"code": "159209", "name": "招商中证全指红利质量ETF", "index_code": "932315", "index_name": "中证红利质量", "group": "观察池"},
    {"code": "159207", "name": "广发中证智选高股息策略ETF", "index_code": "932305", "index_name": "智选高股息", "group": "观察池"},
    {"code": "563700", "name": "易方达中证红利价值ETF", "index_code": "H30270", "index_name": "红利价值", "group": "观察池"},
    {"code": "560570", "name": "国联安中证A500红利低波动ETF", "index_code": "932422", "index_name": "A500红利低波", "group": "观察池"},
]


def parse_dividend_and_split(fhsp):
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


def fetch_nav_page(code, page_index, page_size=200):
    params = urlencode({
        "fundCode": code, "pageIndex": page_index, "pageSize": page_size,
        "startDate": "", "endDate": "",
    })
    req = Request(f"{API_URL}?{params}", headers=HEADERS)
    with urlopen(req, timeout=30) as resp:
        return json.load(resp)


def fetch_all_nav(code):
    first = fetch_nav_page(code, 1)
    total = int(first["TotalCount"])
    page_size = int(first["PageSize"])
    rows = list(first["Data"]["LSJZList"])
    pages = math.ceil(total / page_size)
    for page in range(2, pages + 1):
        payload = fetch_nav_page(code, page)
        rows.extend(payload["Data"]["LSJZList"])
        time.sleep(0.1)
    rows.sort(key=lambda r: r["FSRQ"])
    return rows


def build_reinvested_nav(rows):
    obs = []
    for r in rows:
        if not r.get("DWJZ"):
            continue
        div, split = parse_dividend_and_split(r.get("FHSP") or "")
        try:
            d = datetime.strptime(r["FSRQ"], "%Y-%m-%d").date()
            nav = float(r["DWJZ"])
        except (ValueError, KeyError):
            continue
        obs.append((d, nav, div, split))
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


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = []

    for i, fund in enumerate(FUNDS):
        code = fund["code"]
        name = fund["name"]
        short = name[:20]

        existing = list(OUTPUT_DIR.glob(f"{code}_*_净值.csv"))
        if existing:
            print(f"[{i+1}/{len(FUNDS)}] {code} {short} 已存在，跳过")
            with open(existing[0], encoding="utf-8-sig") as f:
                reader = list(csv.DictReader(f))
            if reader:
                summary.append({
                    **fund, "short_name": short,
                    "data_points": len(reader),
                    "start_date": reader[0]["date"],
                    "end_date": reader[-1]["date"],
                    "csv_file": existing[0].name,
                })
            continue

        print(f"[{i+1}/{len(FUNDS)}] 采集 {code} {short}...")
        try:
            rows = fetch_all_nav(code)
        except Exception as e:
            print(f"  ❌ 失败: {e}")
            continue

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
                    "dividend": div, "split_ratio": split,
                    "fhsp": r.get("FHSP") or "",
                }
            except (ValueError, KeyError):
                continue

        csv_path = OUTPUT_DIR / f"{code}_{short}_净值.csv"
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["date", "unit_nav", "cumulative_nav", "reinvested_nav",
                       "dividend", "split_ratio", "event_note"])
            for d in sorted(nav_map.keys() & reinvested.keys()):
                info = nav_map[d]
                w.writerow([
                    d.isoformat(),
                    f'{info["dwjz"]:.4f}',
                    f'{info["ljjz"]:.4f}' if info["ljjz"] else "",
                    f'{reinvested[d]:.6f}',
                    f'{info["dividend"]:.6f}',
                    f'{info["split_ratio"]:.4f}',
                    info["fhsp"],
                ])

        dates = sorted(reinvested.keys())
        div_count = sum(1 for r in rows if r.get("FHSP") and "派现金" in (r["FHSP"] or ""))
        print(f"  ✓ {len(dates)}条, {dates[0]}~{dates[-1]}, 分红{div_count}次")

        summary.append({
            **fund, "short_name": short,
            "data_points": len(dates),
            "start_date": dates[0].isoformat(),
            "end_date": dates[-1].isoformat(),
            "dividend_count": div_count,
            "csv_file": csv_path.name,
        })
        time.sleep(0.3)

    # 处理3070 HK（香港红利）
    print("\n[30/30] 处理 3070 HK 中国平安CSI香港高息股ETF...")
    hk_path = OUTPUT_DIR / "3070HK_中国平安CSI香港高息股ETF_净值.csv"
    if hk_path.exists():
        print("  已存在，跳过")
        with open(hk_path, encoding="utf-8-sig") as f:
            reader = list(csv.DictReader(f))
        if reader:
            summary.append({
                "code": "3070HK", "name": "中国平安CSI香港高息股ETF",
                "short_name": "平安香港高息股ETF",
                "index_code": "H11140", "index_name": "香港红利", "group": "5年组",
                "data_points": len(reader),
                "start_date": reader[0]["date"], "end_date": reader[-1]["date"],
                "csv_file": hk_path.name,
            })
    else:
        # 尝试从Yahoo Finance获取
        try:
            import yfinance as yf
            tk = yf.Ticker("3070.HK")
            hist = tk.history(period="max", auto_adjust=True)
            if len(hist) > 0:
                with open(hk_path, "w", encoding="utf-8-sig", newline="") as f:
                    w = csv.writer(f)
                    w.writerow(["date", "unit_nav", "cumulative_nav", "reinvested_nav",
                               "dividend", "split_ratio", "event_note"])
                    for idx, row in hist.iterrows():
                        d = idx.date()
                        close = row["Close"]
                        w.writerow([d.isoformat(), f"{close:.4f}", f"{close:.4f}",
                                   f"{close:.6f}", "0.000000", "1.0000", "Yahoo前复权"])
                print(f"  ✓ Yahoo Finance: {len(hist)}条, {hist.index[0].date()}~{hist.index[-1].date()}")
                summary.append({
                    "code": "3070HK", "name": "中国平安CSI香港高息股ETF",
                    "short_name": "平安香港高息股ETF",
                    "index_code": "H11140", "index_name": "香港红利", "group": "5年组",
                    "data_points": len(hist),
                    "start_date": str(hist.index[0].date()),
                    "end_date": str(hist.index[-1].date()),
                    "csv_file": hk_path.name,
                })
            else:
                print("  ⚠ Yahoo Finance无数据")
        except Exception as e:
            print(f"  ❌ Yahoo Finance失败: {e}")
            print("  香港红利ETF将标记为数据不可用")

    summary_path = OUTPUT_DIR / "_汇总_基金净值.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n✓ 完成，共{len(summary)}只基金")
    for g in ["5年组", "3年组", "观察池"]:
        gf = [s for s in summary if s["group"] == g]
        print(f"  {g}: {len(gf)}只")


if __name__ == "__main__":
    main()
