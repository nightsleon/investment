#!/usr/bin/env python3
"""生成农夫山泉投资分析所需的结构化底稿与行情估值数据。"""
from __future__ import annotations

from pathlib import Path
import json
import math
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
import pandas as pd
import yfinance as yf

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"
DATA.mkdir(parents=True, exist_ok=True)

# 单位均为人民币亿元；来自各年度官方年报合并报表，2025归母利润以年报为准。
ANNUAL = [
    # 年, 营收, 毛利, 归母, 资产, 负债, 权益, 现金银行, 长期存款, FVTPL, 流动借款, OCF, CAPEX, 存货, 应收, 合同负债, 已付股息
    (2020, 228.77297, 135.08327, 52.77426, 258.59412, 103.67130, 154.92282, 91.18880, 0.00000, 0.00000, 24.13957, 84.29173, 22.36039, 18.05454, 3.57564, 22.47323, 79.79760),
    (2021, 296.96406, 176.56218, 71.61794, 328.96096, 121.54462, 207.41634, 147.83577, 11.21461, 2.04754, 25.00108, 114.00270, 24.62418, 18.09230, 4.76276, 23.50952, 19.11899),
    (2022, 332.39187, 190.95411, 84.95250, 392.54841, 151.70765, 240.84076, 152.11156, 41.01670, 0.00000, 24.25093, 120.41510, 41.93347, 21.08372, 4.78587, 26.77190, 50.59118),
    (2023, 426.67221, 254.06829, 120.79498, 491.37130, 205.66225, 285.70905, 241.25210, 15.10722, 0.00000, 31.20619, 173.04937, 47.14113, 30.91729, 5.47021, 35.84921, 76.46313),
    (2024, 428.95992, 249.15715, 121.23304, 531.60312, 208.73148, 322.87164, 107.22048, 106.30882, 15.29438, 36.25433, 110.22144, 64.05992, 50.13047, 5.81372, 35.65558, 84.34850),
    (2025, 525.52910, 318.08104, 158.68274, 651.69128, 256.99148, 394.69980, 111.77574, 110.87643, 75.55354, 43.90000, 211.41652, 64.81304, 58.46475, 5.98151, 41.94560, 85.47314),
]
COLUMNS = ["年份", "营收", "毛利", "归母净利润", "总资产", "总负债", "权益", "现金及银行结余", "长期银行存款", "FVTPL金融资产", "流动计息借款", "经营现金流", "资本开支", "存货", "应收账款及票据", "合同负债", "已付股息"]
annual = pd.DataFrame(ANNUAL, columns=COLUMNS)
annual["毛利率"] = annual["毛利"] / annual["营收"] * 100
annual["净利率"] = annual["归母净利润"] / annual["营收"] * 100
annual["总资产周转率"] = annual["营收"] / annual["总资产"]
annual["权益乘数"] = annual["总资产"] / annual["权益"]
annual["简单ROE"] = annual["归母净利润"] / annual["权益"] * 100
annual["资产负债率"] = annual["总负债"] / annual["总资产"] * 100
annual["自由现金流"] = annual["经营现金流"] - annual["资本开支"]
annual["经营现金流净利比"] = annual["经营现金流"] / annual["归母净利润"]
annual["自由现金流净利比"] = annual["自由现金流"] / annual["归母净利润"]
annual["现金头寸"] = annual["现金及银行结余"] + annual["长期银行存款"] + annual["FVTPL金融资产"]
annual["应收账款"] = annual["应收账款及票据"]
annual["存货营收比"] = annual["存货"] / annual["营收"] * 100
annual["营收同比"] = annual["营收"].pct_change() * 100
annual["净利润同比"] = annual["归母净利润"].pct_change() * 100
annual["存货同比"] = annual["存货"].pct_change() * 100
annual["合同负债同比"] = annual["合同负债"].pct_change() * 100
annual["来源"] = "港交所官方年报合并报表；金额由人民币千元换算为亿元"
annual.to_csv(DATA / "annual_core.csv", index=False, encoding="utf-8-sig", float_format="%.6f")

products = pd.DataFrame([
    (2020, "包装饮用水", 139.66), (2020, "茶饮料", 30.88), (2020, "功能饮料", 27.92), (2020, "果汁饮料", 19.77), (2020, "其他", 10.54),
    (2021, "包装饮用水", 170.58), (2021, "茶饮料", 45.79), (2021, "功能饮料", 36.95), (2021, "果汁饮料", 26.14), (2021, "其他", 17.50),
    (2022, "包装饮用水", 182.63), (2022, "茶饮料", 69.06), (2022, "功能饮料", 38.38), (2022, "果汁饮料", 28.79), (2022, "其他", 13.53),
    (2023, "包装饮用水", 202.62), (2023, "茶饮料", 126.59), (2023, "功能饮料", 49.02), (2023, "果汁饮料", 35.33), (2023, "其他", 13.11),
    (2024, "包装饮用水", 159.52), (2024, "茶饮料", 167.45), (2024, "功能饮料", 49.32), (2024, "果汁饮料", 40.85), (2024, "其他", 11.82),
    (2025, "包装饮用水", 187.09), (2025, "茶饮料", 215.96), (2025, "功能饮料", 57.62), (2025, "果汁饮料", 51.76), (2025, "其他", 13.09),
], columns=["年份", "产品", "收入_亿元"])
products["占比_%"] = products["收入_亿元"] / products.groupby("年份")["收入_亿元"].transform("sum") * 100
products["同比_%"] = products.groupby("产品")["收入_亿元"].pct_change() * 100
products["来源"] = "各年度港交所官方年报管理层讨论与分析产品收入表"
products.to_csv(DATA / "product_structure.csv", index=False, encoding="utf-8-sig", float_format="%.4f")
product_2025 = products.loc[products["年份"].eq(2025), ["产品", "收入_亿元", "同比_%", "来源"]].rename(columns={"产品": "业务"})
product_2025.to_csv(DATA / "product_structure_2025.csv", index=False, encoding="utf-8-sig", float_format="%.4f")

# 财报披露日之后市场才知道新的利润数字；半年TTM=上年全年+本年H1-上年H1。
h1 = {2019: 28.76745, 2020: 28.64498, 2021: 40.12918, 2022: 46.08325, 2023: 57.75421, 2024: 62.39579, 2025: 76.22082}
full = {2019: 49.48568, 2020: 52.77426, 2021: 71.61794, 2022: 84.95250, 2023: 120.79498, 2024: 121.23304, 2025: 158.68274}
profit_events = [
    ("2020-09-08", full[2019], "上市初始：2019全年"),
    ("2020-09-24", full[2019] + h1[2020] - h1[2019], "2020中报发布"),
    ("2021-03-25", full[2020], "2020全年业绩公告"),
    ("2021-08-25", full[2020] + h1[2021] - h1[2020], "2021中期业绩公告"),
    ("2022-03-28", full[2021], "2021全年业绩公告"),
    ("2022-08-24", full[2021] + h1[2022] - h1[2021], "2022中期业绩公告"),
    ("2023-03-28", full[2022], "2022全年业绩公告"),
    ("2023-08-29", full[2022] + h1[2023] - h1[2022], "2023中期业绩公告"),
    ("2024-03-26", full[2023], "2023全年业绩公告"),
    ("2024-08-27", full[2023] + h1[2024] - h1[2023], "2024中期业绩公告"),
    ("2025-03-25", full[2024], "2024全年业绩公告"),
    ("2025-08-26", full[2024] + h1[2025] - h1[2024], "2025中期业绩公告"),
    ("2026-03-24", full[2025], "2025全年业绩公告"),
]
events = pd.DataFrame(profit_events, columns=["日期", "TTM归母净利润_亿元", "披露口径"])
events["日期"] = pd.to_datetime(events["日期"])
events.to_csv(DATA / "profit_disclosure_events.csv", index=False, encoding="utf-8-sig", float_format="%.6f")

start = "2020-09-08"
price = yf.Ticker("9633.HK").history(start=start, auto_adjust=False)
fx = yf.Ticker("HKDCNY=X").history(start=start, auto_adjust=False)
if price.empty or fx.empty:
    raise RuntimeError("yfinance未返回股价或汇率数据")
price = price[["Close"]].rename(columns={"Close": "收盘价_HKD"})
fx = fx[["Close"]].rename(columns={"Close": "HKD_CNY"})
price.index = pd.to_datetime(price.index).tz_localize(None).normalize()
fx.index = pd.to_datetime(fx.index).tz_localize(None).normalize()
now_hk = datetime.now(ZoneInfo("Asia/Hong_Kong"))
latest_complete_date = now_hk.date() if now_hk.time() >= time(16, 10) else now_hk.date() - timedelta(days=1)
price = price.loc[price.index.date <= latest_complete_date]
fx = fx.loc[fx.index.date <= latest_complete_date]
market = price.join(fx, how="left")
market["HKD_CNY"] = market["HKD_CNY"].ffill().bfill()
market = pd.merge_asof(
    market.reset_index().rename(columns={"Date": "日期", "index": "日期"}).sort_values("日期"),
    events.sort_values("日期"), on="日期", direction="backward"
)
shares = 11_246_466_400
market["总股本"] = shares
market["市值_亿港元"] = market["收盘价_HKD"] * shares / 1e8
market["市值_亿人民币"] = market["市值_亿港元"] * market["HKD_CNY"]
market["PE_TTM"] = market["市值_亿人民币"] / market["TTM归母净利润_亿元"]
market.to_csv(DATA / "historical_valuation.csv", index=False, encoding="utf-8-sig", float_format="%.6f")

latest = market.dropna(subset=["PE_TTM"]).iloc[-1]
current_pe = float(latest["PE_TTM"])
pe_percentile = float((market["PE_TTM"].dropna() <= current_pe).mean() * 100)
profit_cagr_3y = (full[2025] / full[2022]) ** (1 / 3) - 1
cash_position = float(annual.loc[annual["年份"].eq(2025), "现金头寸"].iloc[0])
market_cap_rmb = float(latest["市值_亿人民币"])
market_cap_hkd = float(latest["市值_亿港元"])
cash_adjusted_pe = (market_cap_rmb - cash_position) / full[2025]
dividend_per_share_rmb = 0.99
dividend_yield = dividend_per_share_rmb / float(latest["HKD_CNY"]) / float(latest["收盘价_HKD"]) * 100

scenarios = []
for name, growth, pe in [("保守", 0.08, 20.0), ("中性", 0.13, 24.0)]:
    future_profit = full[2025] * (1 + growth) ** 3
    future_value_rmb = future_profit * pe
    annualized_return = (future_value_rmb / market_cap_rmb) ** (1 / 3) - 1
    scenarios.append({"情景": name, "未来3年利润增速": growth, "2028归母净利润_亿元": future_profit, "目标PE": pe, "2028市值_亿人民币": future_value_rmb, "相对当前总回报": future_value_rmb / market_cap_rmb - 1, "隐含年化回报": annualized_return})
pd.DataFrame(scenarios).to_csv(DATA / "valuation_scenarios.csv", index=False, encoding="utf-8-sig", float_format="%.6f")

snapshot = {
    "交易日": latest["日期"].strftime("%Y-%m-%d"),
    "股价_HKD": round(float(latest["收盘价_HKD"]), 4),
    "HKD_CNY": round(float(latest["HKD_CNY"]), 6),
    "总股本": shares,
    "市值_亿港元": round(market_cap_hkd, 2),
    "市值_亿人民币": round(market_cap_rmb, 2),
    "TTM归母净利润_亿元": round(full[2025], 6),
    "PE_TTM": round(current_pe, 2),
    "上市以来点时PE百分位_%": round(pe_percentile, 2),
    "3年利润CAGR_%": round(profit_cagr_3y * 100, 2),
    "PEG": round(current_pe / (profit_cagr_3y * 100), 2),
    "2025现金头寸_亿元": round(cash_position, 2),
    "每股现金头寸_人民币": round(cash_position * 1e8 / shares, 3),
    "扣现金后PE": round(cash_adjusted_pe, 2),
    "2025末期股息_人民币每股": dividend_per_share_rmb,
    "静态股息率_%": round(dividend_yield, 2),
    "数据源": "yfinance收盘价/汇率；港交所月报总股本；港交所2025年报利润与现金头寸",
}
(DATA / "market_snapshot.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

# 关键内部一致性检查。
assert annual["年份"].tolist() == list(range(2020, 2026))
assert (annual["总资产"] - annual["总负债"] - annual["权益"]).abs().max() < 0.001
assert abs(products.groupby("年份")["收入_亿元"].sum().loc[2025] - 525.52) < 0.1
assert math.isclose(full[2025], 158.68274, rel_tol=0, abs_tol=1e-6)
print(json.dumps(snapshot, ensure_ascii=False, indent=2))
