#!/usr/bin/env python3
"""生成华泰柏瑞红利低波ETF文章的价格回撤与盈利分红图。"""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np

BASE = Path(__file__).resolve().parents[1]
POSITION_DIR = BASE / "sources" / "etf-position-proxy" / "512890"
PRICE_DIR = BASE / "sources" / "etf-hisotry-price"
OUTPUT_DIR = BASE / "charts" / "512890"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FUNDAMENTAL_FILE = POSITION_DIR / "512890_2026Q2前十大盈利分红_2025.csv"
PRICE_FILE = PRICE_DIR / "512890_前复权日线_2019-01-18_2026-08-03.json"
TRACKING_FILE = PRICE_DIR / "512890_vs_中证红利低波动全收益_2019-01-18_2026-07-31.csv"


def configure_style() -> None:
    candidates = ["PingFang SC", "Hiragino Sans GB", "Heiti SC", "Arial Unicode MS", "Noto Sans CJK SC"]
    available = {font.name for font in fm.fontManager.ttflist}
    family = next((name for name in candidates if name in available), "DejaVu Sans")
    plt.rcParams.update(
        {
            "font.family": family,
            "axes.unicode_minus": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "#D9DEE7",
            "axes.labelcolor": "#4B5563",
            "xtick.color": "#6B7280",
            "ytick.color": "#6B7280",
            "axes.titleweight": "semibold",
            "savefig.facecolor": "white",
        }
    )


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def load_prices() -> tuple[np.ndarray, np.ndarray]:
    payload = json.loads(PRICE_FILE.read_text())
    rows = []
    for line in payload["data"]["klines"]:
        fields = line.split(",")
        rows.append((datetime.strptime(fields[0], "%Y-%m-%d"), float(fields[2])))
    dates = np.array([row[0] for row in rows])
    close = np.array([row[1] for row in rows], dtype=float)
    return dates, close


def plot_price_drawdown() -> None:
    dates, close = load_prices()
    normalized = close / close[0] * 100
    running_max = np.maximum.accumulate(close)
    drawdown = (close / running_max - 1) * 100

    fig, (ax, dd_ax) = plt.subplots(2, 1, figsize=(13.2, 8.2), dpi=180, sharex=True, gridspec_kw={"height_ratios": [2.4, 1], "hspace": 0.08})
    stages = [
        (datetime(2019, 1, 18), datetime(2020, 9, 30), "基建主导", "#DDEAF7"),
        (datetime(2020, 9, 30), datetime(2024, 6, 28), "周期与基建轮动", "#FCE8D2"),
        (datetime(2024, 6, 28), datetime(2026, 8, 3), "向金融迁移", "#E9E0F3"),
    ]
    for start, end, label, color in stages:
        ax.axvspan(start, end, color=color, alpha=0.58, linewidth=0)
        midpoint = start + (end - start) / 2
        ax.text(midpoint, 0.91, label, transform=ax.get_xaxis_transform(), ha="center", va="top", fontsize=10, color="#4B5563")

    ax.plot(dates, normalized, color="#2563A6", linewidth=2.0)
    ax.axhline(100, color="#AAB2BF", linewidth=0.8, linestyle="--")
    ax.set_ylabel("前复权价格指数（上市日=100）")
    ax.grid(axis="y", color="#E9EDF3", linewidth=0.8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_title("前复权价格与回撤", loc="left", fontsize=17, pad=30)
    ax.text(0, 1.03, "阶段边界来自季度前十大持仓，仅用于观察同步关系", transform=ax.transAxes, fontsize=10.5, color="#6B7280")
    ax.text(0.98, 0.78, f"累计收益 {normalized[-1] - 100:.1f}%", transform=ax.transAxes, ha="right", color="#2563A6", fontsize=10.5, weight="semibold", bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.82, "pad": 2})

    dd_ax.fill_between(dates, drawdown, 0, color="#E15759", alpha=0.28)
    dd_ax.plot(dates, drawdown, color="#C94B50", linewidth=1.1)
    dd_ax.axhline(0, color="#AAB2BF", linewidth=0.8)
    dd_ax.set_ylabel("回撤（%）")
    dd_ax.grid(axis="y", color="#E9EDF3", linewidth=0.8)
    dd_ax.spines[["top", "right"]].set_visible(False)
    trough = int(np.argmin(drawdown))
    dd_ax.annotate(f"{drawdown[trough]:.1f}%", xy=(dates[trough], drawdown[trough]), xytext=(0, 10), textcoords="offset points", ha="center", va="bottom", color="#B43C42", fontsize=10.5, weight="semibold")
    dd_ax.xaxis.set_major_locator(mdates.YearLocator())
    dd_ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    fig.subplots_adjust(left=0.09, right=0.98, top=0.86, bottom=0.08, hspace=0.08)
    fig.savefig(OUTPUT_DIR / "前复权价格与回撤.png", bbox_inches="tight")
    plt.close(fig)


def plot_profit_dividend() -> None:
    rows = read_csv(FUNDAMENTAL_FILE)
    names = [f"{row['证券名称']}  {float(row['2026Q2基金净值权重(%)']):.2f}%" for row in rows]
    growth = np.array([float(row["2025归母净利同比(%)"]) for row in rows])
    payout = np.array([float(row["2025分红支付率(%)"]) for row in rows])
    y = np.arange(len(rows))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.2, 7.4), dpi=180, sharey=True, gridspec_kw={"wspace": 0.08})
    growth_colors = np.where(growth >= 0, "#4C78A8", "#E15759")
    bars1 = ax1.barh(y, growth, color=growth_colors, height=0.58)
    ax1.axvline(0, color="#9CA3AF", linewidth=0.9)
    ax1.set_yticks(y, names)
    ax1.invert_yaxis()
    ax1.set_xlabel("2025年归母净利润同比（%）")
    ax1.set_xlim(-35, 10)
    ax1.grid(axis="x", color="#E9EDF3", linewidth=0.8)
    ax1.spines[["top", "right", "left"]].set_visible(False)
    for bar, value in zip(bars1, growth):
        if value < -15:
            ax1.text(value + 1.0, bar.get_y() + bar.get_height() / 2, f"{value:.1f}%", va="center", ha="left", fontsize=9.5, color="white", weight="semibold")
        else:
            offset = 0.45 if value >= 0 else -0.45
            ax1.text(value + offset, bar.get_y() + bar.get_height() / 2, f"{value:.1f}%", va="center", ha="left" if value >= 0 else "right", fontsize=9.5, color="#374151")

    bars2 = ax2.barh(y, payout, color="#F28E2B", height=0.58)
    ax2.axvline(100, color="#C94B50", linewidth=1.0, linestyle="--")
    ax2.set_xlim(0, max(110, float(np.max(payout)) + 12))
    ax2.set_xlabel("2025年分红支付率（%）")
    ax2.grid(axis="x", color="#E9EDF3", linewidth=0.8)
    ax2.spines[["top", "right", "left"]].set_visible(False)
    ax2.tick_params(axis="y", left=False, labelleft=False)
    for bar, value in zip(bars2, payout):
        ax2.text(value + 1.2, bar.get_y() + bar.get_height() / 2, f"{value:.1f}%", va="center", ha="left", fontsize=9.5, color="#374151")

    fig.suptitle("当前前十大盈利与分红", x=0.07, y=0.99, ha="left", fontsize=17, weight="semibold")
    fig.text(0.07, 0.945, "2025年年报数据｜按2026Q2基金净值权重排序；名称后为持仓权重", fontsize=10.5, color="#6B7280")
    fig.subplots_adjust(left=0.12, right=0.98, top=0.84, bottom=0.1, wspace=0.08)
    fig.savefig(OUTPUT_DIR / "当前前十大盈利与分红.png", bbox_inches="tight")
    plt.close(fig)


def plot_tracking_difference() -> None:
    rows = read_csv(TRACKING_FILE)
    dates = np.array([datetime.strptime(row["日期"], "%Y-%m-%d") for row in rows])
    fund = np.array([float(row["ETF归一化"]) for row in rows])
    index = np.array([float(row["全收益指数归一化"]) for row in rows])
    gap = np.array([float(row["累计收益差(百分点)"]) for row in rows])
    five_year_start = datetime(2021, 7, 30)
    x = np.array([mdates.date2num(value) for value in dates])
    five_year_x = float(mdates.date2num(five_year_start))

    fig = plt.figure(figsize=(13.2, 7.4), dpi=180)
    grid = fig.add_gridspec(2, 1, height_ratios=[3.1, 1.15], hspace=0.08)
    ax = fig.add_subplot(grid[0])
    ax_gap = fig.add_subplot(grid[1], sharex=ax)
    fund_color = "#4C78A8"
    index_color = "#F28E2B"

    ax.plot(x, fund, color=fund_color, linewidth=2.2, label="华泰柏瑞红利低波ETF复权净值")
    ax.plot(x, index, color=index_color, linewidth=2.0, label="中证红利低波动全收益指数")
    ax.axvline(five_year_x, color="#9CA3AF", linestyle="--", linewidth=1.0)
    ax.grid(axis="y", color="#E9EDF3", linewidth=0.8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_ylabel("归一化累计表现（上市日=100）")
    ax.legend(loc="upper left", frameon=False, ncol=2)
    ax.tick_params(axis="x", labelbottom=False)
    ax.text(0.985, 0.91, f"ETF {fund[-1]:.1f}", transform=ax.transAxes, ha="right", color=fund_color, fontsize=10.5, bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.84, "pad": 2})
    ax.text(0.985, 0.82, f"全收益指数 {index[-1]:.1f}", transform=ax.transAxes, ha="right", color=index_color, fontsize=10.5, bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.84, "pad": 2})
    ax.text(five_year_x, 0.03, "近5年起点", transform=ax.get_xaxis_transform(), color="#6B7280", fontsize=9.5, ha="left", va="bottom")

    ax_gap.axhline(0, color="#9CA3AF", linewidth=0.9)
    ax_gap.fill_between(x, 0, gap, where=(gap >= 0).tolist(), color=fund_color, alpha=0.28)
    ax_gap.fill_between(x, 0, gap, where=(gap < 0).tolist(), color="#E15759", alpha=0.28)
    ax_gap.plot(x, gap, color="#5B6472", linewidth=1.15)
    ax_gap.axvline(five_year_x, color="#9CA3AF", linestyle="--", linewidth=1.0)
    ax_gap.grid(axis="y", color="#EEF1F5", linewidth=0.7)
    ax_gap.spines[["top", "right"]].set_visible(False)
    ax_gap.set_ylabel("累计收益差\n（百分点）")
    ax_gap.xaxis.set_major_locator(mdates.YearLocator())
    ax_gap.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax_gap.text(0.985, 0.82 if gap[-1] >= 0 else 0.12, f"上市以来 {gap[-1]:+.1f}个百分点", transform=ax_gap.transAxes, ha="right", va="top" if gap[-1] >= 0 else "bottom", color="#374151", fontsize=10)

    fig.suptitle("ETF复权净值与全收益指数", x=0.075, y=0.965, ha="left", fontsize=17)
    fig.text(0.075, 0.91, "同日起点归一为100｜基金累计净值对比税前全收益指数｜下图正值表示ETF领先", fontsize=10.5, color="#6B7280")
    fig.subplots_adjust(left=0.09, right=0.98, top=0.86, bottom=0.08)
    fig.savefig(OUTPUT_DIR / "ETF与全收益指数累计表现.png", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    configure_style()
    plot_price_drawdown()
    plot_tracking_difference()
    plot_profit_dividend()
    print(json.dumps({"输出目录": str(OUTPUT_DIR), "图表": sorted(path.name for path in OUTPUT_DIR.glob("*.png"))}, ensure_ascii=False))


if __name__ == "__main__":
    main()
