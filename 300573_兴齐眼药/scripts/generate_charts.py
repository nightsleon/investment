#!/usr/bin/env python3
"""生成兴齐眼药季度利润、股价对比图。

数据源：
- 财务：data/300573_main_simple.xls（同花顺单季度数据）
- 股价：yfinance 300573.SZ，前复权收盘价 Adj Close
"""

from pathlib import Path
from datetime import datetime
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import yfinance as yf
from python_calamine import CalamineWorkbook

warnings.filterwarnings("ignore")

CODE = "300573"
MARKET = "SZ"
YF_CODE = "300573.SZ"
STOCK_NAME = "兴齐眼药"
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = BASE_DIR / "data" / "300573_main_simple.xls"
OUT_DIR = BASE_DIR / "charts"
OUT_DIR.mkdir(exist_ok=True)
START_DATE = "2016-01-01"
END_DATE = datetime.now().strftime("%Y-%m-%d")

FONT_CANDIDATES = [
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/System/Library/Fonts/PingFang.ttc",
]
FONT_PROP = None
for font_path in FONT_CANDIDATES:
    if Path(font_path).exists():
        FONT_PROP = fm.FontProperties(fname=font_path)
        plt.rcParams["font.family"] = FONT_PROP.get_name()
        break
plt.rcParams["axes.unicode_minus"] = False


def to_number(v):
    if v is None or v == "" or v == "--":
        return np.nan
    if isinstance(v, str):
        s = v.strip().replace(",", "")
        if s.endswith("%"):
            return float(s[:-1]) / 100
        return float(s)
    return float(v)


def read_excel_financials():
    book = CalamineWorkbook.from_path(str(DATA_PATH))
    rows = book.get_sheet_by_index(0).to_python()
    headers = rows[0][1:]
    row_map = {r[0]: r[1:] for r in rows[1:]}

    records = []
    for idx, date_text in enumerate(headers):
        date = pd.to_datetime(date_text)
        net_profit = to_number(row_map["净利润(元)"][idx]) / 1e8
        non_gaap = to_number(row_map["扣非净利润(元)"][idx]) / 1e8
        revenue = to_number(row_map["营业总收入(元)"][idx]) / 1e8
        eps = to_number(row_map["基本每股收益(元)"][idx])
        records.append({
            "date": date,
            "quarter": f"{date.year}Q{date.quarter}",
            "net_profit_yi": net_profit,
            "non_gaap_yi": non_gaap,
            "revenue_yi": revenue,
            "eps": eps,
        })

    fin = pd.DataFrame(records).sort_values("date").reset_index(drop=True)
    fin = fin.dropna(subset=["non_gaap_yi"])
    fin["net_profit_ttm_yi"] = fin["net_profit_yi"].rolling(4, min_periods=4).sum()
    fin["non_gaap_ttm_yi"] = fin["non_gaap_yi"].rolling(4, min_periods=4).sum()
    fin["eps_ttm"] = fin["eps"].rolling(4, min_periods=4).sum()
    return fin


def fetch_price():
    raw = yf.download(YF_CODE, start=START_DATE, end=END_DATE, auto_adjust=False, progress=False)
    if raw.empty:
        raise RuntimeError(f"yfinance 未返回股价数据：{YF_CODE}")
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    price = raw.reset_index()[["Date", "Adj Close", "Close"]].rename(columns={
        "Date": "trade_date",
        "Adj Close": "adj_close",
        "Close": "close",
    })
    price["trade_date"] = pd.to_datetime(price["trade_date"]).dt.tz_localize(None)
    return price


def match_price(fin, price):
    matched = []
    for _, row in fin.dropna(subset=["non_gaap_ttm_yi"]).iterrows():
        sub = price[price["trade_date"] <= row["date"]]
        if sub.empty:
            continue
        last = sub.iloc[-1]
        item = row.to_dict()
        item.update({
            "trade_date": last["trade_date"],
            "adj_close": float(last["adj_close"]),
            "close": float(last["close"]),
        })
        matched.append(item)
    return pd.DataFrame(matched)


def set_common_axis(ax, ticks, labels):
    ax.set_xticks(ticks)
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=9, fontproperties=FONT_PROP)
    ax.grid(True, alpha=0.22, linewidth=0.8)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)


def savefig(fig, path):
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def plot_charts(merged):
    title_prefix = f"{STOCK_NAME}({CODE})"
    x = np.arange(len(merged))
    step = max(1, len(merged) // 12)
    ticks = list(range(0, len(merged), step))
    labels = [merged["quarter"].iloc[i] for i in ticks]

    # 1. 归一化图
    fig, ax = plt.subplots(figsize=(16, 8), dpi=160)
    norm_price = merged["adj_close"] / merged["adj_close"].iloc[0]
    norm_profit = merged["non_gaap_ttm_yi"] / merged["non_gaap_ttm_yi"].iloc[0]
    ax.plot(x, norm_price, "o-", color="#1976D2", linewidth=2.6, markersize=5, label="股价（前复权，基期=1）")
    ax.plot(x, norm_profit, "s-", color="#D32F2F", linewidth=2.6, markersize=5, label="扣非TTM利润（基期=1）")
    ax.fill_between(x, norm_price, norm_profit, color="#90A4AE", alpha=0.10)
    ax.set_title(f"{title_prefix} 归一化对比：股价 vs 扣非TTM利润", fontsize=17, fontweight="bold", fontproperties=FONT_PROP)
    ax.set_ylabel("归一化值", fontsize=12, fontproperties=FONT_PROP)
    set_common_axis(ax, ticks, labels)
    ax.legend(loc="upper left", prop=FONT_PROP, frameon=True)
    corr = merged["adj_close"].corr(merged["non_gaap_ttm_yi"])
    price_mult = merged["adj_close"].iloc[-1] / merged["adj_close"].iloc[0]
    profit_mult = merged["non_gaap_ttm_yi"].iloc[-1] / merged["non_gaap_ttm_yi"].iloc[0]
    ax.text(0.02, 0.93, f"相关系数：{corr:.3f}\n股价涨幅：{price_mult:.1f}x\n扣非TTM涨幅：{profit_mult:.1f}x",
            transform=ax.transAxes, va="top", fontsize=11, fontproperties=FONT_PROP,
            bbox=dict(boxstyle="round,pad=0.45", facecolor="#FFF8E1", edgecolor="#FFE082", alpha=0.95))
    savefig(fig, OUT_DIR / f"{CODE}_归一化_股价vs扣非TTM.png")

    # 2. 股价 + TTM扣非利润（主图）
    fig, ax1 = plt.subplots(figsize=(17, 8.5), dpi=160)
    ax2 = ax1.twinx()
    l1, = ax1.plot(x, merged["adj_close"], "o-", color="#1565C0", linewidth=2.8, markersize=5, label="股价（前复权，元）")
    l2, = ax2.plot(x, merged["non_gaap_ttm_yi"], "s-", color="#C62828", linewidth=2.8, markersize=5, label="扣非TTM净利润（亿元）")
    ax2.fill_between(x, merged["non_gaap_ttm_yi"], color="#EF9A9A", alpha=0.14)
    ax1.set_title(f"{title_prefix} 股价 vs 扣非净利润TTM", fontsize=17, fontweight="bold", fontproperties=FONT_PROP)
    ax1.set_ylabel("股价（元，前复权）", color="#1565C0", fontsize=12, fontweight="bold", fontproperties=FONT_PROP)
    ax2.set_ylabel("扣非TTM净利润（亿元）", color="#C62828", fontsize=12, fontweight="bold", fontproperties=FONT_PROP)
    ax1.tick_params(axis="y", labelcolor="#1565C0")
    ax2.tick_params(axis="y", labelcolor="#C62828")
    set_common_axis(ax1, ticks, labels)
    ax1.legend([l1, l2], [l1.get_label(), l2.get_label()], loc="upper left", prop=FONT_PROP)
    ax1.text(0.01, -0.18, "注：利润为同花顺单季度数据滚动4季；股价取季度末前复权收盘价。趋势对比看斜率，不看双轴绝对位置。",
             transform=ax1.transAxes, fontsize=10, color="#555", fontproperties=FONT_PROP)
    savefig(fig, OUT_DIR / f"{CODE}_股价vs扣非净利润TTM_双Y轴.png")

    # 3. 股价 + 单季度扣非利润
    fig, ax1 = plt.subplots(figsize=(17, 8.5), dpi=160)
    ax2 = ax1.twinx()
    l1, = ax1.plot(x, merged["adj_close"], "o-", color="#1565C0", linewidth=2.5, markersize=5, label="股价（前复权，元）")
    l2, = ax2.plot(x, merged["non_gaap_yi"], "^-", color="#F57C00", linewidth=2.5, markersize=5, label="单季度扣非净利润（亿元）")
    ax2.fill_between(x, merged["non_gaap_yi"], color="#FFB74D", alpha=0.16)
    ax1.set_title(f"{title_prefix} 股价 vs 单季度扣非净利润", fontsize=17, fontweight="bold", fontproperties=FONT_PROP)
    ax1.set_ylabel("股价（元，前复权）", color="#1565C0", fontsize=12, fontweight="bold", fontproperties=FONT_PROP)
    ax2.set_ylabel("单季度扣非净利润（亿元）", color="#F57C00", fontsize=12, fontweight="bold", fontproperties=FONT_PROP)
    ax1.tick_params(axis="y", labelcolor="#1565C0")
    ax2.tick_params(axis="y", labelcolor="#F57C00")
    set_common_axis(ax1, ticks, labels)
    ax1.legend([l1, l2], [l1.get_label(), l2.get_label()], loc="upper left", prop=FONT_PROP)
    savefig(fig, OUT_DIR / f"{CODE}_股价vs扣非净利润_单季度.png")

    return corr, price_mult, profit_mult


def main():
    print(f"读取财务数据：{DATA_PATH}")
    fin = read_excel_financials()
    print(f"财务季度数：{len(fin)}，区间：{fin['quarter'].iloc[0]} ~ {fin['quarter'].iloc[-1]}")

    print(f"下载股价：{YF_CODE}")
    price = fetch_price()
    print(f"交易日数：{len(price)}")

    merged = match_price(fin, price)
    print(f"对齐后季度数：{len(merged)}，区间：{merged['quarter'].iloc[0]} ~ {merged['quarter'].iloc[-1]}")

    csv_path = OUT_DIR / f"{CODE}_季度数据.csv"
    merged.to_csv(csv_path, index=False, encoding="utf-8-sig")
    corr, price_mult, profit_mult = plot_charts(merged)

    print("\n输出文件：")
    for p in [
        OUT_DIR / f"{CODE}_归一化_股价vs扣非TTM.png",
        OUT_DIR / f"{CODE}_股价vs扣非净利润TTM_双Y轴.png",
        OUT_DIR / f"{CODE}_股价vs扣非净利润_单季度.png",
        csv_path,
    ]:
        print(p)
    print(f"\n统计：相关系数={corr:.3f}，股价涨幅={price_mult:.1f}x，扣非TTM涨幅={profit_mult:.1f}x")


if __name__ == "__main__":
    main()
