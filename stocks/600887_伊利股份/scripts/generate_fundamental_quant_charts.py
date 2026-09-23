#!/usr/bin/env python3
"""Generate standardized chapter-four fundamental charts for Yili."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"
OUT = BASE / "charts"
CODE = "600887"
COMPANY = "伊利股份"
C = {"blue": "#2563EB", "light_blue": "#93C5FD", "orange": "#F97316", "green": "#16A34A", "red": "#DC2626", "purple": "#7C3AED", "gray": "#64748B", "light_gray": "#CBD5E1"}


def get_font() -> FontProperties:
    for path in ["/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/Hiragino Sans GB.ttc", "/System/Library/Fonts/STHeiti Medium.ttc"]:
        if Path(path).exists():
            return FontProperties(fname=path)
    return FontProperties()


FONT = get_font()
plt.rcParams["axes.unicode_minus"] = False


def style(ax) -> None:
    ax.grid(axis="y", alpha=0.2)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontproperties(FONT)


def label_axes(ax, xlabel: str | None = None, ylabel: str | None = None) -> None:
    if xlabel: ax.set_xlabel(xlabel, fontproperties=FONT)
    if ylabel: ax.set_ylabel(ylabel, fontproperties=FONT)


def set_title(ax, text: str, subtitle: str) -> None:
    ax.set_title(text, fontproperties=FONT, fontsize=17, weight="bold", pad=18)
    ax.text(0.5, 1.01, subtitle, transform=ax.transAxes, ha="center", va="bottom", fontproperties=FONT, fontsize=10, color=C["gray"])


def save(fig, filename: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / filename, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(OUT / filename)


def chart_41(df: pd.DataFrame) -> None:
    years = df["年份"].astype(str); x = np.arange(len(df))
    fig = plt.figure(figsize=(15, 8)); gs = fig.add_gridspec(2, 1, height_ratios=[1, 1], hspace=0.38)
    ax = fig.add_subplot(gs[0]); roe = df["净资产收益率"]
    ax.bar(x, roe, width=0.45, color=C["light_blue"])
    for i, value in enumerate(roe): ax.text(i, value + 0.5, f"{value:.1f}%", ha="center", fontproperties=FONT, fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels(years, fontproperties=FONT); label_axes(ax, ylabel="加权ROE（%）"); style(ax)
    set_title(ax, f"{COMPANY}：ROE与杜邦三因子趋势", "ROE采用公司披露加权口径；杜邦三因子首年=100，仅比较趋势")
    ax2 = fig.add_subplot(gs[1])
    for name, color in [("销售净利率", C["red"]), ("总资产周转率", C["green"]), ("权益乘数", C["purple"])]:
        values = df[name].astype(float); normalized = values / values.iloc[0] * 100
        ax2.plot(x, normalized, marker="o", lw=2.2, color=color, label=f"{name}（首年=100）")
        unit = "%" if name == "销售净利率" else "倍"
        ax2.annotate(f"{values.iloc[-1]:.2f}{unit}", (x[-1], normalized.iloc[-1]), xytext=(8, 0), textcoords="offset points", fontproperties=FONT, color=color)
    ax2.axhline(100, color=C["light_gray"], lw=1)
    ax2.set_xticks(x); ax2.set_xticklabels(years, fontproperties=FONT); label_axes(ax2, ylabel="归一化（2020=100）"); style(ax2)
    ax2.legend(prop=FONT, ncol=3, frameon=False, loc="upper left")
    save(fig, f"{CODE}_4.1_ROE与杜邦三因子趋势图.png")


def chart_42(df: pd.DataFrame) -> None:
    years = df["年份"].astype(str); x = np.arange(len(df)); profit = df["扣非净利润"]
    growth = profit.pct_change() * 100
    fig, ax = plt.subplots(figsize=(15, 8)); ax2 = ax.twinx()
    bars = ax.bar(x, profit, width=0.48, color=C["light_blue"], label="扣非净利润")
    line, = ax2.plot(x, growth, color=C["orange"], marker="o", lw=2.4, label="同比增速")
    for bar, value in zip(bars, profit): ax.text(bar.get_x() + bar.get_width()/2, value + 2, f"{value:.1f}", ha="center", fontproperties=FONT, fontsize=9)
    for i, value in enumerate(growth):
        if pd.notna(value): ax2.annotate(f"{value:+.1f}%", (i, value), xytext=(0, 9), textcoords="offset points", ha="center", fontproperties=FONT, fontsize=9, color=C["orange"])
    ax.set_xticks(x); ax.set_xticklabels(years, fontproperties=FONT); label_axes(ax, ylabel="扣非净利润（亿元）"); label_axes(ax2, ylabel="同比增速（%）")
    style(ax); style(ax2); set_title(ax, f"{COMPANY}：扣非净利润趋势与同比增速", "2024年受商誉减值影响，2025年恢复；需结合三年CAGR判断")
    ax.legend(handles=[bars, line], labels=["扣非净利润", "同比增速"], prop=FONT, frameon=False, loc="upper left")
    save(fig, f"{CODE}_4.2_利润趋势与同比增速图.png")


def chart_43(product: pd.DataFrame) -> None:
    p = product.sort_values("收入_亿元", ascending=True).copy(); total = p["收入_亿元"].sum(); p["占比"] = p["收入_亿元"] / total * 100
    previous = p["收入_亿元"] / (1 + p["同比_%"] / 100); p["收入增量"] = p["收入_亿元"] - previous
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(16, 7), gridspec_kw={"width_ratios": [1.25, 1]})
    colors = [C["blue"] if name == "液体乳" else C["orange"] if name in ("奶粉及奶制品", "冷饮产品") else C["light_gray"] for name in p["业务"]]
    bars = ax.barh(p["业务"], p["收入_亿元"], color=colors)
    for label in ax.get_yticklabels(): label.set_fontproperties(FONT)
    for bar, rev, share in zip(bars, p["收入_亿元"], p["占比"]): ax.text(rev + 8, bar.get_y()+bar.get_height()/2, f"{rev:.1f}亿 / {share:.1f}%", va="center", fontproperties=FONT, fontsize=9)
    label_axes(ax, xlabel="主营业务收入（亿元）"); style(ax); set_title(ax, f"{COMPANY}：2025年产品收入结构", "按年报主营业务分产品口径")
    delta_colors = [C["green"] if value >= 0 else C["red"] for value in p["收入增量"]]
    bars2 = ax2.barh(p["业务"], p["收入增量"], color=delta_colors)
    for label in ax2.get_yticklabels(): label.set_fontproperties(FONT)
    for bar, value, growth in zip(bars2, p["收入增量"], p["同比_%"]):
        ax2.text(value + (1.2 if value >= 0 else -1.2), bar.get_y()+bar.get_height()/2, f"{value:+.1f}亿 ({growth:+.1f}%)", va="center", ha="left" if value >= 0 else "right", fontproperties=FONT, fontsize=9)
    ax2.axvline(0, color=C["gray"], lw=0.8); label_axes(ax2, xlabel="同比收入增量（亿元）"); style(ax2); set_title(ax2, "2025年收入增量贡献", "增量由当年收入与披露同比反推")
    fig.tight_layout(); save(fig, f"{CODE}_4.3_收入结构与产品增速图.png")


def chart_44(df: pd.DataFrame) -> None:
    years = df["年份"].astype(str); x = np.arange(len(df)); width = 0.22
    fig, ax = plt.subplots(figsize=(15, 8)); ax2 = ax.twinx()
    for offset, col, color in [(-width, "净利润", C["blue"]), (0, "经营现金流", C["orange"]), (width, "自由现金流", C["green"])]:
        ax.bar(x + offset, df[col], width=width, color=color, label=col)
    coverage = df["经营现金流"] / df["净利润"] * 100
    line, = ax2.plot(x, coverage, color=C["purple"], marker="o", lw=2.2, label="CFO/净利润")
    for i, value in enumerate(coverage): ax2.annotate(f"{value:.0f}%", (i, value), xytext=(0, 8), textcoords="offset points", ha="center", fontproperties=FONT, fontsize=9, color=C["purple"])
    ax.set_xticks(x); ax.set_xticklabels(years, fontproperties=FONT); label_axes(ax, ylabel="亿元"); label_axes(ax2, ylabel="CFO/净利润（%）"); style(ax); style(ax2)
    set_title(ax, f"{COMPANY}：净利润、经营现金流与自由现金流", "自由现金流=经营现金流-购建长期资产现金支出")
    handles1, labels1 = ax.get_legend_handles_labels(); ax.legend(handles1 + [line], labels1 + ["CFO/净利润"], prop=FONT, frameon=False, ncol=4, loc="upper left")
    save(fig, f"{CODE}_4.4_净利润经营现金流自由现金流对比图.png")


def chart_45(df: pd.DataFrame) -> None:
    years = df["年份"].astype(str); x = np.arange(len(df))
    fig = plt.figure(figsize=(15, 8)); gs = fig.add_gridspec(2, 1, height_ratios=[1.25, 0.8], hspace=0.35)
    ax = fig.add_subplot(gs[0]); positives = ["货币资金", "大额存单及定期存款", "交易性金融资产"]
    bottom = np.zeros(len(df))
    for col, color in zip(positives, [C["blue"], C["green"], C["orange"]]):
        ax.bar(x, df[col], width=0.52, bottom=bottom, color=color, label=col); bottom += df[col].to_numpy()
    debt = df["长期借款"] + df["应付债券"]
    ax.bar(x, -debt, width=0.52, color=C["red"], alpha=0.75, label="长期借款+应付债券")
    for i, value in enumerate(df["现金头寸_近似"]): ax.annotate(f"净{value:.0f}", (i, max(bottom[i], 0)), xytext=(0, 7), textcoords="offset points", ha="center", fontproperties=FONT, fontsize=9)
    ax.axhline(0, color=C["gray"], lw=0.8); ax.set_xticks(x); ax.set_xticklabels(years, fontproperties=FONT); label_axes(ax, ylabel="亿元"); style(ax)
    set_title(ax, f"{COMPANY}：现金头寸拆解", "货币资金+经年报确认的大额存单/定存+交易性金融资产-长期借款-应付债券")
    ax.legend(prop=FONT, ncol=4, frameon=False, loc="upper left")
    ax2 = fig.add_subplot(gs[1]); ax2.plot(x, df["资产负债率"], color=C["purple"], marker="o", lw=2.4)
    ax2.fill_between(x, 0, df["资产负债率"], color=C["purple"], alpha=0.08)
    for i, value in enumerate(df["资产负债率"]): ax2.annotate(f"{value:.1f}%", (i, value), xytext=(0, 7), textcoords="offset points", ha="center", fontproperties=FONT, fontsize=9)
    ax2.set_ylim(0, 75); ax2.set_xticks(x); ax2.set_xticklabels(years, fontproperties=FONT); label_axes(ax2, ylabel="资产负债率（%）"); style(ax2)
    fig.tight_layout(); save(fig, f"{CODE}_4.5_现金头寸拆解与资产负债安全垫图.png")


def chart_46(df: pd.DataFrame) -> None:
    years = df["年份"].astype(str); x = np.arange(len(df)); width = 0.24
    fig = plt.figure(figsize=(15, 8)); gs = fig.add_gridspec(2, 1, height_ratios=[1.2, 0.85], hspace=0.35)
    ax = fig.add_subplot(gs[0])
    for offset, col, color in [(-width, "应收账款", C["blue"]), (0, "存货", C["orange"]), (width, "合同负债", C["green"])]: ax.bar(x + offset, df[col], width=width, color=color, label=col)
    ax.set_xticks(x); ax.set_xticklabels(years, fontproperties=FONT); label_axes(ax, ylabel="亿元"); style(ax)
    set_title(ax, f"{COMPANY}：应收、存货与合同负债变化", "合同负债主要为经销商预收货款；绝对值按年末口径")
    ax.legend(prop=FONT, frameon=False, ncol=3, loc="upper left")
    ax2 = fig.add_subplot(gs[1]); revenue_growth = df["营收"].pct_change() * 100; inventory_growth = df["存货"].pct_change() * 100; inventory_ratio = df["存货"] / df["营收"] * 100
    for series, color, label in [(revenue_growth, C["blue"], "营收同比"), (inventory_growth, C["red"], "存货同比"), (inventory_ratio, C["purple"], "存货/营收")]: ax2.plot(x, series, marker="o", lw=2.1, color=color, label=label)
    ax2.axhline(0, color=C["light_gray"], lw=0.8); ax2.set_xticks(x); ax2.set_xticklabels(years, fontproperties=FONT); label_axes(ax2, ylabel="百分比（%）"); style(ax2); ax2.legend(prop=FONT, frameon=False, ncol=3, loc="upper left")
    fig.tight_layout(); save(fig, f"{CODE}_4.6_应收存货合同负债变化图.png")


def main() -> None:
    annual = pd.read_csv(DATA / "annual_core.csv")
    product = pd.read_csv(DATA / "product_structure.csv")
    required = ["现金头寸_近似", "应收账款", "存货", "合同负债"]
    if annual[required].isna().any().any():
        raise ValueError(f"annual_core contains NaN: {annual[required].isna().sum().to_dict()}")
    chart_41(annual); chart_42(annual); chart_43(product); chart_44(annual); chart_45(annual); chart_46(annual)


if __name__ == "__main__":
    main()
