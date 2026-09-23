#!/usr/bin/env python3
"""Build Tencent financial, operating, market and valuation datasets."""
from __future__ import annotations

import json
import math
import re
from bisect import bisect_right
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf
from python_calamine import CalamineWorkbook

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"
DATA.mkdir(parents=True, exist_ok=True)
XLS = DATA / "HK0700_keyindex_report.xls"


def number(value: object) -> float:
    match = re.search(r"[-+]?\d[\d,.]*", str(value))
    return float(match.group().replace(",", "")) if match else math.nan


# 同花顺关键指标表：季度列为年初至报告期累计，年度列为全年。
rows = CalamineWorkbook.from_path(XLS).get_sheet_by_index(0).to_python()
headers = [str(v) for v in rows[0]]
lookup = {str(row[0]): row[1:] for row in rows[1:]}
raw = pd.DataFrame({"报告期": pd.to_datetime(headers[1:])})
for src, dst in [
    ("营业收入", "营收累计_百万元"),
    ("归母净利润", "GAAP归母累计_百万元"),
    ("毛利", "毛利累计_百万元"),
    ("每股收益-基本", "基本EPS累计_人民币"),
]:
    raw[dst] = [number(v) / (1e6 if "百万元" in dst else 1) for v in lookup[src]]
raw = raw.sort_values("报告期").reset_index(drop=True)
raw = raw[raw["报告期"] >= "2015-03-31"].copy()
raw["年份"] = raw["报告期"].dt.year
raw["季度"] = raw["报告期"].dt.quarter
for cumulative, single in [
    ("营收累计_百万元", "营收单季_百万元"),
    ("GAAP归母累计_百万元", "GAAP归母单季_百万元"),
    ("毛利累计_百万元", "毛利单季_百万元"),
    ("基本EPS累计_人民币", "基本EPS单季_人民币"),
]:
    raw[single] = raw.groupby("年份")[cumulative].diff()
    raw.loc[raw["季度"].eq(1), single] = raw.loc[raw["季度"].eq(1), cumulative]

# 官方业绩公告披露日，利润只能在披露日之后用于点时估值。
ledger = pd.read_csv(DATA / "official_filings.csv")
events = []
for _, row in ledger.iterrows():
    period = str(row["报告期"])
    match = re.match(r"(20\d{2})\s+(.+)", period)
    if not match:
        continue
    year, label = int(match.group(1)), match.group(2).lower()
    if "first quarter" in label:
        quarter = 1
    elif "second quarter" in label:
        quarter = 2
    elif "third quarter" in label:
        quarter = 3
    elif "annual" in label or "fourth quarter" in label:
        quarter = 4
    else:
        continue
    events.append({"年份": year, "季度": quarter, "披露日": pd.Timestamp(row["披露日"]), "官方URL": row["官方URL"]})
events_df = pd.DataFrame(events).drop_duplicates(["年份", "季度"], keep="first")
quarterly = raw.merge(events_df, on=["年份", "季度"], how="inner").sort_values("报告期")
quarterly["GAAP归母TTM_百万元"] = quarterly["GAAP归母单季_百万元"].rolling(4).sum()
quarterly["基本EPS_TTM_人民币"] = quarterly["基本EPS单季_人民币"].rolling(4).sum()

# 腾讯官方季度业绩公告中的单季 Non-IFRS 股东应占溢利（人民币百万元）。
non_ifrs = {
    (2020, 1): 27079, (2020, 2): 30153, (2020, 3): 32303, (2020, 4): 33207,
    (2021, 1): 33118, (2021, 2): 34039, (2021, 3): 31751, (2021, 4): 24880,
    (2022, 1): 25545, (2022, 2): 28139, (2022, 3): 32254, (2022, 4): 29711,
    (2023, 1): 32538, (2023, 2): 37548, (2023, 3): 44921, (2023, 4): 42681,
    (2024, 1): 50265, (2024, 2): 57313, (2024, 3): 59813, (2024, 4): 55312,
    (2025, 1): 61329, (2025, 2): 63052, (2025, 3): 70551, (2025, 4): 64694,
    (2026, 1): 67905,
}
quarterly["NonIFRS归母单季_百万元"] = [non_ifrs.get((int(y), int(q)), math.nan) for y, q in zip(quarterly["年份"], quarterly["季度"])]
quarterly["NonIFRS归母TTM_百万元"] = quarterly["NonIFRS归母单季_百万元"].rolling(4).sum()
quarterly.to_csv(DATA / "quarterly_profit.csv", index=False, encoding="utf-8-sig", float_format="%.6f")

# 年度核心底稿，金额均为人民币亿元。
years = [2020, 2021, 2022, 2023, 2024, 2025]
annual_values = {
    "营收": [4820.64, 5601.18, 5545.52, 6090.15, 6602.57, 7517.66],
    "毛利": [2215.32, 2459.44, 2387.46, 2931.09, 3492.46, 4225.93],
    "GAAP归母净利润": [1598.47, 2248.22, 1882.43, 1152.16, 1940.73, 2248.42],
    "NonIFRS归母净利润": [1227.42, 1237.88, 1156.49, 1576.88, 2227.03, 2596.26],
    "总资产": [13334.25, 16123.64, 15781.31, 15772.46, 17809.95, 20389.86],
    "总负债": [5553.82, 7356.71, 7952.71, 7035.65, 7270.99, 7979.21],
    "权益": [7780.43, 8766.93, 7828.60, 8736.81, 10538.96, 12410.65],
    "加权ROE": [22.71, 27.88, 26.09, 14.25, 19.93, 19.48],
    "总现金": [2595.07, 2812.86, 3196.0, 4033.0, 4154.0, 4949.0],
    "长期借款及票据": [2342.02, 2825.26, 3123.37, 2929.20, 2771.07, 3345.73],
    "自由现金流": [1234.52, 1081.50, 884.0, 1670.0, 1553.0, 1826.0],
    "资本开支": [339.60, 333.61, 181.0, 244.0, 767.60, 791.98],
    "应收账款": [449.81, 493.31, 454.67, 466.06, 482.03, 499.30],
    "存货": [8.14, 10.63, 23.33, 4.56, 4.40, 5.30],
    "递延收入": [895.05, 923.72, 857.19, 896.03, 1063.33, 1125.19],
}
annual = pd.DataFrame({"年份": years, **annual_values})
# OCF由同花顺每股现金流/每股营收比例乘官方营收反推，避免股数变化误差。
annual_raw = raw[raw["季度"].eq(4) & raw["年份"].isin(years)].set_index("年份")
per_share_cf = {int(headers[i][:4]): number(lookup["每股现金流"][i - 1]) for i in range(1, len(headers)) if headers[i].endswith("12-31") and headers[i][:4].isdigit()}
per_share_rev = {int(headers[i][:4]): number(lookup["每股营业总收入"][i - 1]) for i in range(1, len(headers)) if headers[i].endswith("12-31") and headers[i][:4].isdigit()}
annual["经营现金流"] = [annual.loc[annual["年份"].eq(y), "营收"].iloc[0] * per_share_cf[y] / per_share_rev[y] for y in years]
annual["毛利率"] = annual["毛利"] / annual["营收"] * 100
annual["GAAP净利率"] = annual["GAAP归母净利润"] / annual["营收"] * 100
annual["核心净利率"] = annual["NonIFRS归母净利润"] / annual["营收"] * 100
annual["净利率"] = annual["核心净利率"]
annual["总资产周转率"] = annual["营收"] / annual["总资产"]
annual["权益乘数"] = annual["总资产"] / annual["权益"]
annual["简单ROE"] = annual["GAAP归母净利润"] / annual["权益"] * 100
annual["核心ROE近似"] = annual["NonIFRS归母净利润"] / annual["权益"] * 100
annual["资产负债率"] = annual["总负债"] / annual["总资产"] * 100
annual["现金头寸"] = annual["总现金"] - annual["长期借款及票据"]
annual["经营现金流净利比"] = annual["经营现金流"] / annual["NonIFRS归母净利润"]
annual["自由现金流净利比"] = annual["自由现金流"] / annual["NonIFRS归母净利润"]
annual["存货营收比"] = annual["存货"] / annual["营收"] * 100
annual["营收同比"] = annual["营收"].pct_change() * 100
annual["净利润同比"] = annual["NonIFRS归母净利润"].pct_change() * 100
annual["存货同比"] = annual["存货"].pct_change() * 100
annual["合同负债"] = annual["递延收入"]
annual["应收账款及票据"] = annual["应收账款"]
annual["归母净利润"] = annual["NonIFRS归母净利润"]
annual["来源"] = "腾讯官方年度业绩公告；同花顺关键指标表仅辅助经营现金流与加权ROE"
annual.to_csv(DATA / "annual_core.csv", index=False, encoding="utf-8-sig", float_format="%.6f")

products = pd.DataFrame([
    (2020, "增值服务", 2642.12), (2020, "营销服务", 822.71), (2020, "金融科技及企业服务", 1280.86), (2020, "其他", 74.95),
    (2021, "增值服务", 2915.72), (2021, "营销服务", 886.66), (2021, "金融科技及企业服务", 1721.95), (2021, "其他", 76.85),
    (2022, "增值服务", 2875.65), (2022, "营销服务", 827.29), (2022, "金融科技及企业服务", 1770.64), (2022, "其他", 71.94),
    (2023, "增值服务", 2983.75), (2023, "营销服务", 1014.82), (2023, "金融科技及企业服务", 2037.63), (2023, "其他", 53.95),
    (2024, "增值服务", 3191.68), (2024, "营销服务", 1213.74), (2024, "金融科技及企业服务", 2119.56), (2024, "其他", 77.59),
    (2025, "增值服务", 3692.81), (2025, "营销服务", 1449.73), (2025, "金融科技及企业服务", 2294.35), (2025, "其他", 80.77),
], columns=["年份", "业务", "收入_亿元"])
products["占比_%"] = products["收入_亿元"] / products.groupby("年份")["收入_亿元"].transform("sum") * 100
products["同比_%"] = products.groupby("业务")["收入_亿元"].pct_change() * 100
products["来源"] = "腾讯官方年度业绩公告分部收入表"
products.to_csv(DATA / "product_structure.csv", index=False, encoding="utf-8-sig", float_format="%.4f")
products.loc[products["年份"].eq(2025), ["业务", "收入_亿元", "同比_%", "来源"]].to_csv(DATA / "product_structure_2025.csv", index=False, encoding="utf-8-sig", float_format="%.4f")

# 行情、汇率与点时PE。
now_hk = datetime.now(ZoneInfo("Asia/Hong_Kong"))
cutoff = now_hk.date() if now_hk.time() >= time(16, 10) else now_hk.date() - timedelta(days=1)
prices = yf.Ticker("0700.HK").history(start="2015-01-01", auto_adjust=False)[["Close"]]
fx = yf.Ticker("HKDCNY=X").history(start="2015-01-01", auto_adjust=False)[["Close"]]
for frame in (prices, fx):
    frame.index = pd.to_datetime(frame.index).tz_localize(None).normalize()
prices = prices[prices.index.date <= cutoff].rename(columns={"Close": "收盘价_HKD"})
fx = fx[fx.index.date <= cutoff].rename(columns={"Close": "HKD_CNY"})
market = prices.join(fx, how="left")
market["HKD_CNY"] = market["HKD_CNY"].ffill().bfill()
profit_events = quarterly.dropna(subset=["披露日", "GAAP归母TTM_百万元", "基本EPS_TTM_人民币"])[
    ["披露日", "报告期", "GAAP归母TTM_百万元", "NonIFRS归母TTM_百万元", "基本EPS_TTM_人民币", "官方URL"]
].sort_values("披露日")
# 业绩公告通常在收市后发布；新利润从公告后的下一个交易日才进入点时估值，避免未来函数。
trading_days = [pd.Timestamp(value).to_pydatetime() for value in prices.index.tolist()]


def next_trading_day(disclosed):
    position = bisect_right(trading_days, disclosed.to_pydatetime())
    return trading_days[position] if position < len(trading_days) else pd.NaT


profit_events["生效日"] = profit_events["披露日"].map(next_trading_day)
effective_events = profit_events.dropna(subset=["生效日"]).rename(columns={"生效日": "日期"}).sort_values("日期")
market = pd.merge_asof(
    market.reset_index().rename(columns={"Date": "日期", "index": "日期"}).sort_values("日期"),
    effective_events,
    on="日期",
    direction="backward",
)
market["GAAP_PE_TTM"] = market["收盘价_HKD"] * market["HKD_CNY"] / market["基本EPS_TTM_人民币"]
shares = 9_092_516_289
market["总股本"] = shares
market["市值_亿港元"] = market["收盘价_HKD"] * shares / 1e8
market["市值_亿人民币"] = market["市值_亿港元"] * market["HKD_CNY"]
market["NonIFRS_PE_TTM"] = market["市值_亿人民币"] / (market["NonIFRS归母TTM_百万元"] / 100)
market.to_csv(DATA / "historical_valuation.csv", index=False, encoding="utf-8-sig", float_format="%.6f")

latest = market.dropna(subset=["NonIFRS_PE_TTM"]).iloc[-1]
last_10y = market[(market["日期"] >= latest["日期"] - pd.DateOffset(years=10)) & market["GAAP_PE_TTM"].notna()].copy()
current_gaap_pe = float(latest["GAAP_PE_TTM"])
current_nonifrs_pe = float(latest["NonIFRS_PE_TTM"])
gaap_pct = float((last_10y["GAAP_PE_TTM"] <= current_gaap_pe).mean() * 100)
core_profit_ttm_yi = float(latest["NonIFRS归母TTM_百万元"] / 100)
market_cap_rmb = float(latest["市值_亿人民币"])
latest_dividends = yf.Ticker("0700.HK").dividends
latest_dividend = float(latest_dividends.iloc[-1]) if not latest_dividends.empty else math.nan
dividend_yield = latest_dividend / float(latest["收盘价_HKD"]) * 100
profit_cagr = (2596.26 / 1156.49) ** (1 / 3) - 1
latest_net_cash = 1468.60

snapshot = {
    "交易日": latest["日期"].strftime("%Y-%m-%d"),
    "股价_HKD": round(float(latest["收盘价_HKD"]), 2),
    "HKD_CNY": round(float(latest["HKD_CNY"]), 6),
    "总股本": shares,
    "市值_亿港元": round(float(latest["市值_亿港元"]), 2),
    "市值_亿人民币": round(market_cap_rmb, 2),
    "GAAP_TTM归母净利润_亿元": round(float(latest["GAAP归母TTM_百万元"] / 100), 2),
    "NonIFRS_TTM归母净利润_亿元": round(core_profit_ttm_yi, 2),
    "GAAP_PE_TTM": round(current_gaap_pe, 2),
    "NonIFRS_PE_TTM": round(current_nonifrs_pe, 2),
    "近十年GAAP点时PE百分位_%": round(gaap_pct, 2),
    "2022至2025核心利润3年CAGR_%": round(profit_cagr * 100, 2),
    "PEG_NonIFRS": round(current_nonifrs_pe / (profit_cagr * 100), 2),
    "2026Q1公司净现金_亿元": latest_net_cash,
    "扣净现金后NonIFRS_PE": round((market_cap_rmb - latest_net_cash) / core_profit_ttm_yi, 2),
    "最新每股年度股息_HKD": round(latest_dividend, 3),
    "静态股息率_%": round(dividend_yield, 2),
    "2025上市投资公允价值_亿元": 6727.0,
    "2025非上市投资账面价值_亿元": 3631.0,
    "2025回购金额_亿港元": 800.0,
    "2026Q1回购金额_亿港元": 76.0,
    "2026-07-09回购股数": 1_065_000,
    "2026-07-09回购金额_亿港元": 5.00688876,
    "数据源": "yfinance收盘价/汇率/股息；港交所2026-07-09翌日披露报表股本；腾讯官方业绩公告利润与现金",
}
(DATA / "market_snapshot.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

scenarios = []
for name, growth, pe in [("压力", -0.05, 12.0), ("保守", 0.05, 15.0), ("中性", 0.09, 18.0), ("乐观", 0.13, 22.0)]:
    future_profit = core_profit_ttm_yi * (1 + growth) ** 3
    # 核心净利润已包含现金产生的利息收入；PE法不再额外加回净现金，避免重复计算。
    future_value = future_profit * pe
    annualized = (future_value / market_cap_rmb) ** (1 / 3) - 1
    scenarios.append({"情景": name, "未来3年核心利润增速": growth, "2029核心利润_亿元": future_profit, "目标PE": pe, "2029股权价值_亿元": future_value, "三年总回报": future_value / market_cap_rmb - 1, "隐含年化回报": annualized})
pd.DataFrame(scenarios).to_csv(DATA / "valuation_scenarios.csv", index=False, encoding="utf-8-sig", float_format="%.6f")

# 同业快照只用于数量级比较，市场口径来自同一批次 yfinance。
peers = []
for name, ticker in [("腾讯", "0700.HK"), ("网易", "9999.HK"), ("阿里巴巴", "9988.HK"), ("百度", "9888.HK"), ("Meta", "META"), ("拼多多", "PDD")]:
    info = yf.Ticker(ticker).info
    peers.append({"公司": name, "代码": ticker, "币种": info.get("currency"), "市值": info.get("marketCap"), "PE_TTM": info.get("trailingPE"), "抓取日": latest["日期"].strftime("%Y-%m-%d"), "来源": "yfinance同批次行情；不采用预测PE"})
pd.DataFrame(peers).to_csv(DATA / "peer_snapshot.csv", index=False, encoding="utf-8-sig")

assert annual["年份"].tolist() == years
assert abs(annual.loc[annual["年份"].eq(2025), "现金头寸"].iloc[0] - 1603.27) < 0.01
assert shares == 9_092_516_289
assert quarterly.loc[(quarterly["年份"].eq(2026)) & (quarterly["季度"].eq(1)), "NonIFRS归母TTM_百万元"].iloc[0] == 266202
print(json.dumps(snapshot, ensure_ascii=False, indent=2))
