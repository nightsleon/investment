#!/usr/bin/env python3
"""Regenerate product and cash-position charts with company-specific labels."""
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"
OUT = BASE / "charts"
COLORS = {"blue": "#93C5FD", "green": "#16A34A", "red": "#DC2626", "gray": "#64748B"}


def get_font() -> FontProperties:
    for path in ["/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/Hiragino Sans GB.ttc", "/System/Library/Fonts/STHeiti Medium.ttc"]:
        if Path(path).exists():
            return FontProperties(fname=path)
    return FontProperties()


FONT = get_font()
plt.rcParams["axes.unicode_minus"] = False


def style(ax) -> None:
    ax.grid(axis="y", alpha=0.20)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontproperties(FONT)


def product_chart() -> None:
    p = pd.read_csv(DATA / "product_structure.csv")
    p["占比"] = p["收入_亿元"] / p["收入_亿元"].sum() * 100
    p["上年收入"] = p["收入_亿元"] / (1 + p["同比_%"] / 100)
    p["收入增量"] = p["收入_亿元"] - p["上年收入"]
    p = p.sort_values("收入_亿元", ascending=True)
    palette = ["#A7F3D0", "#FDE68A", "#93C5FD", "#CBD5E1", "#FDBA74", "#DDD6FE", "#60A5FA"]
    fig, axes = plt.subplots(1, 2, figsize=(16, 7), dpi=180, gridspec_kw={"width_ratios": [1.35, 1]})
    axes[0].barh(p["业务"], p["收入_亿元"], height=0.52, color=palette[:len(p)])
    for y, revenue, share, margin in zip(p["业务"], p["收入_亿元"], p["占比"], p["毛利率_%"]):
        margin_text = "" if pd.isna(margin) else f" / 毛利率{margin:.1f}%"
        axes[0].text(revenue + 0.35, y, f"{revenue:.1f}亿 / {share:.1f}%{margin_text}", va="center", fontproperties=FONT, fontsize=9)
    axes[0].set_xlim(0, p["收入_亿元"].max() * 1.42)
    axes[0].set_xlabel("收入（亿元）", fontproperties=FONT)
    style(axes[0])

    inc = p.sort_values("收入增量", ascending=True)
    bar_colors = [COLORS["green"] if value >= 0 else COLORS["red"] for value in inc["收入增量"]]
    bars = axes[1].barh(inc["业务"], inc["收入增量"], height=0.52, color=bar_colors)
    axes[1].axvline(0, color="#94A3B8", lw=0.9)
    for bar, value, yoy in zip(bars, inc["收入增量"], inc["同比_%"]):
        y = bar.get_y() + bar.get_height() / 2
        label = f"{value:+.1f}亿 / {yoy:+.1f}%"
        if value < -0.35:
            axes[1].text(value / 2, y, label, ha="center", va="center", color="white", fontproperties=FONT, fontsize=9, weight="bold")
        elif value < 0:
            axes[1].text(-0.15, y, label, ha="right", va="center", color=COLORS["red"], fontproperties=FONT, fontsize=9)
        else:
            axes[1].text(value + 0.20, y, label, ha="left", va="center", color=COLORS["green"], fontproperties=FONT, fontsize=9)
    min_value = inc["收入增量"].min()
    max_value = inc["收入增量"].max()
    axes[1].set_xlim(min_value * 1.25, max_value * 1.35)
    axes[1].set_xlabel("收入增量（亿元，按同比反推）", fontproperties=FONT)
    axes[1].set_title("收入增量贡献", fontproperties=FONT, fontsize=12, pad=10)
    style(axes[1])

    axes[0].set_title("盐津铺子：产品收入结构", fontproperties=FONT, fontsize=17, weight="bold", pad=18)
    axes[0].text(0.5, 1.01, "左图为收入/占比/毛利率；右图为按同比反推的收入增量贡献", transform=axes[0].transAxes, ha="center", va="bottom", fontproperties=FONT, fontsize=10, color=COLORS["gray"])
    fig.tight_layout()
    path = OUT / "002847_4.3_收入结构与产品增速图.png"
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(path)


def cash_chart() -> None:
    a = pd.read_csv(DATA / "annual_core.csv")
    x = np.arange(len(a))
    fig, ax1 = plt.subplots(figsize=(15, 7.5), dpi=180)
    ax2 = ax1.twinx()
    cash = a["现金头寸_近似"]
    lr = a["资产负债率"]
    bars = ax1.bar(x, cash, width=0.46, color=COLORS["blue"], label="现金头寸（亿元）")
    line, = ax2.plot(x, lr, marker="o", color=COLORS["red"], lw=2.2, label="资产负债率")
    ax1.axhline(0, color="#64748B", lw=0.9)
    for bar, value in zip(bars, cash):
        offset = 0.07 if value >= 0 else -0.08
        ax1.text(bar.get_x() + bar.get_width() / 2, value + offset, f"{value:.2f}亿", ha="center", va="bottom" if value >= 0 else "top", color="#2563EB", fontproperties=FONT, fontsize=9)
    for i, value in enumerate(lr):
        ax2.annotate(f"{value:.1f}%", xy=(i, value), xytext=(0, 10), textcoords="offset points", ha="center", fontproperties=FONT, fontsize=9, color=COLORS["red"])
    ax1.set_xticks(x); ax1.set_xticklabels(a["年份"].astype(str), fontproperties=FONT)
    ax1.set_ylabel("林奇现金头寸（亿元）", fontproperties=FONT)
    ax2.set_ylabel("资产负债率 %", fontproperties=FONT)
    ax2.set_ylim(0, 65)
    style(ax1); ax2.spines["top"].set_visible(False)
    for label in ax2.get_yticklabels():
        label.set_fontproperties(FONT)
    ax1.set_title("盐津铺子：现金头寸与资产负债率", fontproperties=FONT, fontsize=17, weight="bold", pad=18)
    ax1.text(0.5, 1.01, "现金头寸=货币资金+定期存款+交易性金融资产-长期有息负债；资产负债率右轴从0开始", transform=ax1.transAxes, ha="center", va="bottom", fontproperties=FONT, fontsize=10, color=COLORS["gray"])
    ax1.legend([bars, line], ["现金头寸（亿元）", "资产负债率"], loc="upper left", prop=FONT, frameon=False)
    fig.tight_layout()
    path = OUT / "002847_4.5_现金头寸拆解与资产负债安全垫图.png"
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(path)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    product_chart()
    cash_chart()
