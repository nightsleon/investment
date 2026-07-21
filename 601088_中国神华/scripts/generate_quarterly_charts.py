#!/usr/bin/env python3
"""Generate China Shenhua quarterly price-vs-profit charts from Tonghuashun XLS."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import pandas as pd
from python_calamine import CalamineWorkbook
import yfinance as yf

BASE = Path(__file__).resolve().parents[1]
DATA, CHARTS = BASE / "data", BASE / "charts"
CODE, COMPANY = "601088", "中国神华"


def get_font() -> FontProperties:
    for path in ("/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/Hiragino Sans GB.ttc", "/System/Library/Fonts/STHeiti Medium.ttc"):
        if Path(path).exists():
            return FontProperties(fname=path)
    return FontProperties()


FONT = get_font()
plt.rcParams["axes.unicode_minus"] = False


def financials() -> pd.DataFrame:
    rows = CalamineWorkbook.from_path(str(DATA / "601088_main_simple.xls")).get_sheet_by_index(0).to_python()
    dates = pd.to_datetime(rows[0][1:])
    metrics = {str(row[0]): row[1 : 1 + len(dates)] for row in rows[1:] if row and row[0]}
    frame = pd.DataFrame({"date": dates,
                          "net_profit_yi": pd.to_numeric(metrics["净利润(元)"], errors="coerce") / 1e8,
                          "non_gaap_yi": pd.to_numeric(metrics["扣非净利润(元)"], errors="coerce") / 1e8}).dropna()
    frame = frame.sort_values("date").drop_duplicates("date", keep="last")
    frame = frame[frame["date"] >= "2015-01-01"].reset_index(drop=True)
    frame["net_profit_ttm_yi"] = frame["net_profit_yi"].rolling(4, min_periods=4).sum()
    frame["non_gaap_ttm_yi"] = frame["non_gaap_yi"].rolling(4, min_periods=4).sum()
    frame["quarter"] = frame["date"].dt.year.astype(str) + "Q" + frame["date"].dt.quarter.astype(str)
    return frame


def prices() -> pd.DataFrame:
    raw = yf.download("601088.SS", start="2015-01-01", end="2026-07-22", auto_adjust=False, progress=False)
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    price = raw.reset_index()[["Date", "Adj Close", "Close"]]
    price.columns = ["trade_date", "adj_close", "close"]
    price["trade_date"] = pd.to_datetime(price["trade_date"]).dt.tz_localize(None)
    return price


def merge(fin: pd.DataFrame, price: pd.DataFrame) -> pd.DataFrame:
    out = []
    for _, row in fin.dropna(subset=["non_gaap_ttm_yi"]).iterrows():
        available = price[price["trade_date"] <= row["date"]]
        if not available.empty:
            out.append({**row.to_dict(), **available.iloc[-1].to_dict()})
    return pd.DataFrame(out)


def style(ax) -> None:
    ax.grid(axis="y", alpha=0.22); ax.spines["top"].set_visible(False)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontproperties(FONT)


def title(ax, main: str, sub: str) -> None:
    ax.set_title(main, fontproperties=FONT, fontsize=17, weight="bold", pad=18)
    ax.text(0.5, 1.01, sub, transform=ax.transAxes, ha="center", va="bottom", fontproperties=FONT, fontsize=10, color="#64748B")


def save(fig, name: str) -> None:
    CHARTS.mkdir(parents=True, exist_ok=True)
    fig.savefig(CHARTS / name, dpi=180, bbox_inches="tight", facecolor="white"); plt.close(fig)
    print(CHARTS / name)


def ticks(frame: pd.DataFrame) -> list[int]:
    values = list(range(0, len(frame), max(1, len(frame) // 11)))
    if len(frame) - 1 not in values:
        values.append(len(frame) - 1)
    return values


def dual(frame: pd.DataFrame) -> None:
    x = range(len(frame)); marks = ticks(frame)
    fig, ax1 = plt.subplots(figsize=(16, 8)); ax2 = ax1.twinx()
    p1, = ax1.plot(x, frame["adj_close"], color="#2563EB", lw=2.4, marker="o", ms=3.5, label="股价（前复权）")
    p2, = ax2.plot(x, frame["non_gaap_ttm_yi"], color="#F97316", lw=2.4, marker="s", ms=3.5, label="扣非净利润TTM")
    ax2.fill_between(x, frame["non_gaap_ttm_yi"], color="#FDBA74", alpha=0.12)
    ax1.set_xticks(marks); ax1.set_xticklabels(frame.iloc[marks]["quarter"], rotation=35, ha="right", fontproperties=FONT)
    ax1.set_ylabel("前复权股价（元）", fontproperties=FONT); ax2.set_ylabel("扣非净利润TTM（亿元）", fontproperties=FONT)
    title(ax1, f"{COMPANY}：股价与扣非净利润TTM", "仅比较趋势方向和增幅；2026Q1利润尚未反映4月起并入的重组资产")
    style(ax1); style(ax2); ax1.legend(handles=[p1, p2], prop=FONT, loc="upper left", frameon=False)
    save(fig, f"{CODE}_股价vs扣非净利润TTM_双Y轴.png")


def normalized(frame: pd.DataFrame) -> None:
    frame = frame[frame["non_gaap_ttm_yi"] > 0].copy(); base = frame.iloc[0]
    frame["price_norm"] = frame["adj_close"] / base["adj_close"]; frame["profit_norm"] = frame["non_gaap_ttm_yi"] / base["non_gaap_ttm_yi"]
    x = range(len(frame)); marks = ticks(frame)
    fig, ax = plt.subplots(figsize=(16, 8))
    ax.plot(x, frame["price_norm"], color="#2563EB", lw=2.4, label="股价（基期=1）")
    ax.plot(x, frame["profit_norm"], color="#F97316", lw=2.4, label="扣非TTM（基期=1）")
    ax.set_xticks(marks); ax.set_xticklabels(frame.iloc[marks]["quarter"], rotation=35, ha="right", fontproperties=FONT)
    title(ax, f"{COMPANY}：股价与扣非净利润TTM归一化趋势", "辅助观察同步性；基期估值会扭曲相对位置，不能据此判断高低估")
    style(ax); ax.legend(prop=FONT, frameon=False)
    save(fig, f"{CODE}_归一化_股价vs扣非TTM.png")


def single_quarter(frame: pd.DataFrame) -> None:
    x = range(len(frame)); marks = ticks(frame)
    fig, ax1 = plt.subplots(figsize=(16, 8)); ax2 = ax1.twinx()
    p1, = ax1.plot(x, frame["adj_close"], color="#2563EB", lw=2.2, label="股价（前复权）")
    p2, = ax2.plot(x, frame["non_gaap_yi"], color="#16A34A", lw=2.2, label="单季度扣非净利润")
    ax1.set_xticks(marks); ax1.set_xticklabels(frame.iloc[marks]["quarter"], rotation=35, ha="right", fontproperties=FONT)
    title(ax1, f"{COMPANY}：股价与单季度扣非净利润", "单季度波动受煤价、电价、季节性和减值影响，TTM图为主")
    style(ax1); style(ax2); ax1.legend(handles=[p1, p2], prop=FONT, frameon=False)
    save(fig, f"{CODE}_股价vs扣非净利润_单季度.png")


def main() -> None:
    frame = merge(financials(), prices())
    if frame.empty:
        raise RuntimeError("No matched quarterly data")
    frame.to_csv(DATA / f"{CODE}_季度数据.csv", index=False)
    dual(frame); normalized(frame); single_quarter(frame)
    print(frame.tail(6).to_string(index=False))


if __name__ == "__main__":
    main()
