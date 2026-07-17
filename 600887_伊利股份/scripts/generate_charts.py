#!/usr/bin/env python3
"""Generate Yili quarterly price vs profit charts from Tonghuashun single-quarter XLS."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import pandas as pd
from python_calamine import CalamineWorkbook
import yfinance as yf

BASE = Path(__file__).resolve().parents[1]
CHARTS = BASE / "charts"
DATA = BASE / "data"
XLS = BASE / "600887_main_simple.xls"
CODE = "600887"
COMPANY = "伊利股份"


def font() -> FontProperties:
    for path in [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
    ]:
        if Path(path).exists():
            return FontProperties(fname=path)
    return FontProperties()


FONT = font()
plt.rcParams["axes.unicode_minus"] = False


def read_financials() -> pd.DataFrame:
    rows = CalamineWorkbook.from_path(str(XLS)).get_sheet_by_index(0).to_python()
    dates = pd.to_datetime(rows[0][1:])
    metrics = {str(row[0]): row[1 : 1 + len(dates)] for row in rows[1:] if row and row[0]}
    frame = pd.DataFrame(
        {
            "date": dates,
            "net_profit_yi": pd.to_numeric(metrics["净利润(元)"], errors="coerce") / 1e8,
            "non_gaap_yi": pd.to_numeric(metrics["扣非净利润(元)"], errors="coerce") / 1e8,
        }
    ).dropna()
    frame = frame.sort_values("date").drop_duplicates("date", keep="last").reset_index(drop=True)
    frame["net_profit_ttm_yi"] = frame["net_profit_yi"].rolling(4, min_periods=4).sum()
    frame["non_gaap_ttm_yi"] = frame["non_gaap_yi"].rolling(4, min_periods=4).sum()
    frame["quarter"] = frame["date"].dt.year.astype(str) + "Q" + frame["date"].dt.quarter.astype(str)
    return frame


def fetch_price() -> pd.DataFrame:
    raw = yf.download("600887.SS", start="2014-01-01", auto_adjust=False, progress=False)
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    price = raw.reset_index()[["Date", "Adj Close", "Close"]]
    price.columns = ["trade_date", "adj_close", "close"]
    price["trade_date"] = pd.to_datetime(price["trade_date"]).dt.tz_localize(None)
    return price


def match_price(financials: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in financials.dropna(subset=["non_gaap_ttm_yi"]).iterrows():
        available = prices[prices["trade_date"] <= row["date"]]
        if available.empty:
            continue
        latest = available.iloc[-1]
        rows.append({**row.to_dict(), **latest.to_dict()})
    return pd.DataFrame(rows)


def style(ax) -> None:
    ax.grid(axis="y", alpha=0.22)
    ax.spines["top"].set_visible(False)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontproperties(FONT)


def title(ax, text: str, subtitle: str) -> None:
    ax.set_title(text, fontproperties=FONT, fontsize=17, weight="bold", pad=18)
    ax.text(0.5, 1.01, subtitle, transform=ax.transAxes, ha="center", va="bottom", fontproperties=FONT, fontsize=10, color="#64748B")


def save(fig, name: str) -> None:
    CHARTS.mkdir(parents=True, exist_ok=True)
    fig.savefig(CHARTS / name, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(CHARTS / name)


def plot_dual(frame: pd.DataFrame) -> None:
    x = range(len(frame))
    fig, ax1 = plt.subplots(figsize=(16, 8))
    ax2 = ax1.twinx()
    p1, = ax1.plot(x, frame["adj_close"], color="#2563EB", lw=2.4, marker="o", ms=3.5, label="股价（前复权）")
    p2, = ax2.plot(x, frame["non_gaap_ttm_yi"], color="#F97316", lw=2.4, marker="s", ms=3.5, label="扣非净利润TTM")
    ax2.fill_between(x, frame["non_gaap_ttm_yi"], color="#FDBA74", alpha=0.12)
    ticks = list(range(0, len(frame), max(1, len(frame) // 12)))
    if len(frame) - 1 not in ticks:
        ticks.append(len(frame) - 1)
    ax1.set_xticks(ticks); ax1.set_xticklabels(frame.iloc[ticks]["quarter"], rotation=35, ha="right", fontproperties=FONT)
    ax1.set_ylabel("前复权股价（元）", fontproperties=FONT); ax2.set_ylabel("扣非净利润TTM（亿元）", fontproperties=FONT)
    title(ax1, f"{COMPANY}：股价与扣非净利润TTM", "双Y轴仅比较趋势方向和增幅，不比较两条线的绝对高低")
    style(ax1); style(ax2)
    ax1.legend(handles=[p1, p2], prop=FONT, loc="upper left", frameon=False)
    save(fig, f"{CODE}_股价vs扣非净利润TTM_双Y轴.png")


def plot_normalized(frame: pd.DataFrame) -> None:
    positive = frame[frame["non_gaap_ttm_yi"] > 0].copy()
    base = positive.iloc[0]
    positive["price_norm"] = positive["adj_close"] / base["adj_close"]
    positive["profit_norm"] = positive["non_gaap_ttm_yi"] / base["non_gaap_ttm_yi"]
    x = range(len(positive))
    fig, ax = plt.subplots(figsize=(16, 8))
    ax.plot(x, positive["price_norm"], color="#2563EB", lw=2.4, label="股价（基期=1）")
    ax.plot(x, positive["profit_norm"], color="#F97316", lw=2.4, label="扣非TTM（基期=1）")
    ticks = list(range(0, len(positive), max(1, len(positive) // 12)))
    if len(positive) - 1 not in ticks: ticks.append(len(positive) - 1)
    ax.set_xticks(ticks); ax.set_xticklabels(positive.iloc[ticks]["quarter"], rotation=35, ha="right", fontproperties=FONT)
    ax.set_ylabel("归一化值", fontproperties=FONT)
    title(ax, f"{COMPANY}：股价与扣非净利润TTM归一化趋势", "辅助观察长期同步性；基期估值会影响相对位置，不能据此判断高低估")
    style(ax); ax.legend(prop=FONT, frameon=False)
    save(fig, f"{CODE}_归一化_股价vs扣非TTM.png")


def plot_single_quarter(frame: pd.DataFrame) -> None:
    x = range(len(frame))
    fig, ax1 = plt.subplots(figsize=(16, 8))
    ax2 = ax1.twinx()
    p1, = ax1.plot(x, frame["adj_close"], color="#2563EB", lw=2.2, label="股价（前复权）")
    p2, = ax2.plot(x, frame["non_gaap_yi"], color="#16A34A", lw=2.2, label="单季度扣非净利润")
    ax2.axhline(0, color="#94A3B8", lw=0.8)
    ticks = list(range(0, len(frame), max(1, len(frame) // 12)))
    if len(frame) - 1 not in ticks: ticks.append(len(frame) - 1)
    ax1.set_xticks(ticks); ax1.set_xticklabels(frame.iloc[ticks]["quarter"], rotation=35, ha="right", fontproperties=FONT)
    ax1.set_ylabel("前复权股价（元）", fontproperties=FONT); ax2.set_ylabel("单季度扣非净利润（亿元）", fontproperties=FONT)
    title(ax1, f"{COMPANY}：股价与单季度扣非净利润", "单季度波动包含季节性和减值影响，TTM图为主要判断依据")
    style(ax1); style(ax2); ax1.legend(handles=[p1, p2], prop=FONT, frameon=False)
    save(fig, f"{CODE}_股价vs扣非净利润_单季度.png")


def main() -> None:
    financials = read_financials()
    merged = match_price(financials, fetch_price())
    DATA.mkdir(parents=True, exist_ok=True)
    merged.to_csv(DATA / f"{CODE}_季度数据.csv", index=False)
    plot_dual(merged)
    plot_normalized(merged)
    plot_single_quarter(merged)
    print(merged.tail(6).to_string(index=False))


if __name__ == "__main__":
    main()
