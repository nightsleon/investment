#!/usr/bin/env python3
"""生成另外三只红利ETF文章的持仓、价格、跟踪差和盈利分红图。"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import PchipInterpolator

BASE = Path(__file__).resolve().parents[1]
POSITION_BASE = BASE / "sources" / "etf-position-proxy"
PRICE_DIR = BASE / "sources" / "etf-hisotry-price"
CHART_DIR = BASE / "charts"
SHANGHAI = ZoneInfo("Asia/Shanghai")


@dataclass(frozen=True)
class FundConfig:
    code: str
    fund_label: str
    index_label: str
    price_file: str
    tracking_file: str


FUNDS = (
    FundConfig(
        code="515450",
        fund_label="南方红利低波50ETF复权净值",
        index_label="标普中国A股大盘红利低波50全收益指数",
        price_file="红利低波50ETF南方-515450行情走势.json",
        tracking_file="515450_vs_标普中国A股大盘红利低波50全收益指数_2020-02-26_2026-07-31.csv",
    ),
    FundConfig(
        code="515180",
        fund_label="易方达红利ETF复权净值",
        index_label="中证红利全收益指数",
        price_file="红利ETF易方达-515180行情走势.json",
        tracking_file="515180_vs_中证红利全收益指数_2019-12-20_2026-07-31.csv",
    ),
    FundConfig(
        code="515100",
        fund_label="景顺红利低波100ETF复权净值",
        index_label="中证红利低波动100全收益指数",
        price_file="景顺长城中证红利低波动100ETF-515100行情走势.json",
        tracking_file="515100_vs_中证红利低波动100全收益指数_2020-07-03_2026-07-31.csv",
    ),
)

CATEGORY_ORDER = ["基建", "周期", "金融", "制造", "消费", "科技", "医疗", "其他"]
CATEGORY_COLORS = {
    "基建": "#5B84B1",
    "周期": "#F28E2B",
    "金融": "#8064A2",
    "制造": "#59A14F",
    "消费": "#E15759",
    "科技": "#2F6B7C",
    "医疗": "#76B7B2",
    "其他": "#9AA0A6",
}
STAGE_COLORS = ["#DDEAF7", "#FCE8D2", "#E9E0F3", "#DFF0E1", "#F8E1E1"]


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


def quarter_label(period: str) -> str:
    month = int(period[4:6])
    return f"{period[:4]}Q{month // 3}"


def plot_industry(config: FundConfig) -> None:
    rows = read_csv(POSITION_BASE / config.code / f"{config.code}_前十大持仓行业构成.csv")
    periods = sorted({row["报告期"] for row in rows})
    raw_categories = {row["同花顺行业大类"] for row in rows}
    categories = [name for name in CATEGORY_ORDER if name in raw_categories]
    categories.extend(sorted(raw_categories - set(categories)))
    lookup = {(row["报告期"], row["同花顺行业大类"]): float(row["前十大中占比(%)"]) for row in rows}
    values = np.array([[lookup.get((period, category), 0.0) for period in periods] for category in categories])

    x = np.arange(len(periods), dtype=float)
    dense_x = np.linspace(0, len(periods) - 1, max(400, len(periods) * 24))
    smooth = np.vstack([np.clip(PchipInterpolator(x, series)(dense_x), 0, None) for series in values])
    smooth *= 100 / smooth.sum(axis=0)

    fig, ax = plt.subplots(figsize=(13.2, 7.4), dpi=180)
    ax.stackplot(dense_x, smooth, labels=categories, colors=[CATEGORY_COLORS.get(name, "#9AA0A6") for name in categories], alpha=0.88)
    ax.set_xlim(0, len(periods) - 1)
    ax.set_ylim(0, 100)
    ax.set_ylabel("前十大内部占比（%）")
    ax.grid(axis="y", color="#EEF1F5", linewidth=0.7)
    ax.spines[["top", "right", "left"]].set_visible(False)

    tick_positions = [i for i, period in enumerate(periods) if period[4:6] == "03"]
    if len(periods) - 1 not in tick_positions:
        tick_positions = [i for i in tick_positions if periods[i][:4] != periods[-1][:4]]
        tick_positions.append(len(periods) - 1)
    ax.set_xticks(tick_positions, [quarter_label(periods[i]) for i in tick_positions])
    ax.legend(loc="upper right", frameon=False, ncol=min(4, len(categories)), bbox_to_anchor=(1, 1.17))
    ax.set_title("季度前十大行业构成", loc="left", fontsize=17, pad=36)
    ax.text(0, 1.04, "季度原始数据，曲线只作平滑连接｜前十大内部归一化，不是完整ETF行业权重", transform=ax.transAxes, fontsize=10.5, color="#6B7280")

    latest = [(category, values[i, -1]) for i, category in enumerate(categories) if values[i, -1] > 0]
    latest.sort(key=lambda item: item[1], reverse=True)
    latest_text = "　".join(f"{name} {value:.1f}%" for name, value in latest[:5])
    ax.text(0.995, 1.005, f"最新原始值：{latest_text}", transform=ax.transAxes, ha="right", va="bottom", fontsize=9.8, color="#4B5563")

    fig.subplots_adjust(left=0.08, right=0.98, top=0.83, bottom=0.09)
    output_dir = CHART_DIR / config.code
    output_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_dir / "季度前十大行业构成.png", bbox_inches="tight")
    plt.close(fig)


def load_prices(config: FundConfig) -> tuple[np.ndarray, np.ndarray]:
    payload = json.loads((PRICE_DIR / config.price_file).read_text())["data"]
    close_index = payload["column"].index("close")
    rows = [
        (datetime.fromtimestamp(item[0] / 1000, tz=SHANGHAI).replace(tzinfo=None), float(item[close_index]))
        for item in payload["item"]
    ]
    return np.array([row[0] for row in rows]), np.array([row[1] for row in rows], dtype=float)


def plot_price_drawdown(config: FundConfig) -> None:
    dates, close = load_prices(config)
    normalized = close / close[0] * 100
    drawdown = (close / np.maximum.accumulate(close) - 1) * 100
    stage_rows = [
        row for row in read_csv(PRICE_DIR / f"{config.code}_持仓阶段收益回撤.csv") if row["阶段"] != "上市以来"
    ]

    fig, (ax, dd_ax) = plt.subplots(2, 1, figsize=(13.2, 8.2), dpi=180, sharex=True, gridspec_kw={"height_ratios": [2.4, 1], "hspace": 0.08})
    for i, row in enumerate(stage_rows):
        start = datetime.strptime(row["起始日"], "%Y-%m-%d")
        end = datetime.strptime(row["结束日"], "%Y-%m-%d")
        ax.axvspan(start, end, color=STAGE_COLORS[i % len(STAGE_COLORS)], alpha=0.58, linewidth=0)
        midpoint = start + (end - start) / 2
        ax.text(midpoint, 0.91, row["阶段"], transform=ax.get_xaxis_transform(), ha="center", va="top", fontsize=9.2, color="#4B5563")

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
    output_dir = CHART_DIR / config.code
    output_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_dir / "前复权价格与回撤.png", bbox_inches="tight")
    plt.close(fig)


def plot_profit_dividend(config: FundConfig) -> None:
    rows = read_csv(POSITION_BASE / config.code / f"{config.code}_2026Q2前十大盈利分红_2025.csv")
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
    span = max(abs(float(np.min(growth))), abs(float(np.max(growth))), 10)
    ax1.set_xlim(min(-10, float(np.min(growth)) - span * 0.08), max(10, float(np.max(growth)) + span * 0.15))
    ax1.grid(axis="x", color="#E9EDF3", linewidth=0.8)
    ax1.spines[["top", "right", "left"]].set_visible(False)
    for bar, value in zip(bars1, growth):
        offset = span * 0.015
        ax1.text(value + (offset if value >= 0 else -offset), bar.get_y() + bar.get_height() / 2, f"{value:.1f}%", va="center", ha="left" if value >= 0 else "right", fontsize=9.2, color="#374151")

    bars2 = ax2.barh(y, payout, color="#F28E2B", height=0.58)
    ax2.axvline(100, color="#C94B50", linewidth=1.0, linestyle="--")
    ax2.set_xlim(0, max(110, float(np.max(payout)) + 12))
    ax2.set_xlabel("2025年分红支付率（%）")
    ax2.grid(axis="x", color="#E9EDF3", linewidth=0.8)
    ax2.spines[["top", "right", "left"]].set_visible(False)
    ax2.tick_params(axis="y", left=False, labelleft=False)
    for bar, value in zip(bars2, payout):
        ax2.text(value + 1.2, bar.get_y() + bar.get_height() / 2, f"{value:.1f}%", va="center", ha="left", fontsize=9.2, color="#374151")

    fig.suptitle("当前前十大盈利与分红", x=0.07, y=0.99, ha="left", fontsize=17, weight="semibold")
    fig.text(0.07, 0.945, "2025年年报数据｜按2026Q2基金净值权重排序；名称后为持仓权重", fontsize=10.5, color="#6B7280")
    fig.subplots_adjust(left=0.12, right=0.98, top=0.84, bottom=0.1, wspace=0.08)
    output_dir = CHART_DIR / config.code
    output_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_dir / "当前前十大盈利与分红.png", bbox_inches="tight")
    plt.close(fig)


def plot_tracking_difference(config: FundConfig) -> None:
    rows = read_csv(PRICE_DIR / config.tracking_file)
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
    fund_color, index_color = "#4C78A8", "#F28E2B"

    ax.plot(x, fund, color=fund_color, linewidth=2.2, label=config.fund_label)
    ax.plot(x, index, color=index_color, linewidth=2.0, label=config.index_label)
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
    fig.text(0.075, 0.91, "同日起点归一为100｜现金分红按除息日复投｜下图正值表示ETF领先", fontsize=10.5, color="#6B7280")
    fig.subplots_adjust(left=0.09, right=0.98, top=0.86, bottom=0.08)
    output_dir = CHART_DIR / config.code
    output_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_dir / "ETF与全收益指数累计表现.png", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    configure_style()
    result = {}
    for config in FUNDS:
        plot_industry(config)
        plot_price_drawdown(config)
        plot_tracking_difference(config)
        plot_profit_dividend(config)
        result[config.code] = sorted(path.name for path in (CHART_DIR / config.code).glob("*.png"))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
