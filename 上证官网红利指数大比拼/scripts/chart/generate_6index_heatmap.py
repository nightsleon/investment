#!/usr/bin/env python3
"""生成六只代表性红利指数年度收益热力图。"""
from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")

BASE = Path(__file__).resolve().parent.parent
PERF = BASE / "sources" / "performance-data"
CHART_DIR = BASE / "charts"

# 六只指数的显示顺序与简写名（与走势图一致）
SELECTED = [
    ("中证全指红利质量", "全指红利质量"),
    ("中证沪港深红利成长低波动", "沪港深成长低波"),
    ("标普中国A股大盘红利低波50", "标普大盘低波50"),
    ("中证红利低波动", "红利低波"),
    ("中证红利", "中证红利"),
    ("深证红利（159905复权净值代理）", "深证红利(代理)"),
]


def main() -> None:
    df = pd.read_csv(PERF / "年度收益_2017_2025.csv", index_col="年度")

    # 提取六只指数，按选定顺序排列
    labels = [short for _, short in SELECTED]
    col_names = [full for full, _ in SELECTED]
    data = df[col_names].copy()  # 行=年份, 列=指数
    data.columns = labels

    # 转置：行=指数, 列=年份
    heat = data.T * 100  # 转为百分比

    print("=== 热力图数据（%）===")
    print(heat.round(1).to_string())
    print()

    # 标记每行最差年份
    worst_years = heat.idxmin(axis=1)
    worst_vals = heat.min(axis=1)
    print("最差年度：")
    for idx in heat.index:
        print(f"  {idx}: {worst_years[idx]} = {worst_vals[idx]:.1f}%")

    # ========== 绘图 ==========
    plt.rcParams.update({
        "font.sans-serif": ["PingFang SC", "Heiti SC", "STHeiti", "Arial Unicode MS", "sans-serif"],
        "axes.unicode_minus": False,
        "figure.dpi": 180,
        "savefig.dpi": 180,
    })

    n_rows, n_cols = heat.shape
    fig, ax = plt.subplots(figsize=(n_cols * 1.3 + 3.5, n_rows * 0.7 + 2.5))
    fig.patch.set_facecolor("white")

    # A股惯例色阶：红涨绿跌，0为白
    cmap = mcolors.LinearSegmentedColormap.from_list(
        "gn_rd",
        ["#1E8449", "#27AE60", "#ABEBC6", "#FFFFFF", "#F5B7B1", "#E74C3C", "#C0392B"],
    )
    vmax = max(abs(heat.values.min()), abs(heat.values.max()))
    norm = mcolors.TwoSlopeNorm(vmin=-vmax, vcenter=0, vmax=vmax)

    im = ax.imshow(heat.values, cmap=cmap, norm=norm, aspect="auto")

    # 坐标轴
    ax.set_xticks(range(n_cols))
    ax.set_xticklabels(heat.columns, fontsize=10, color="#555555")
    ax.set_yticks(range(n_rows))
    ax.set_yticklabels(heat.index, fontsize=10, color="#555555")
    ax.tick_params(axis="both", length=0)

    # 网格线
    for i in range(n_rows + 1):
        ax.axhline(i - 0.5, color="white", linewidth=2)
    for j in range(n_cols + 1):
        ax.axvline(j - 0.5, color="white", linewidth=2)

    # 单元格数值
    for i in range(n_rows):
        for j in range(n_cols):
            val = heat.iloc[i, j]
            # 文字颜色：深色背景用白字，浅色背景用黑字
            text_color = "white" if abs(val) > vmax * 0.55 else "#333333"
            # 最差年份加粗
            fontweight = "bold" if heat.columns[j] == worst_years.iloc[i] else "normal"
            sign = "+" if val >= 0 else ""
            ax.text(j, i, f"{sign}{val:.1f}%",
                    ha="center", va="center",
                    fontsize=9, color=text_color, fontweight=fontweight)

    # 最差年份加粗框
    for i in range(n_rows):
        j = list(heat.columns).index(worst_years.iloc[i])
        rect = plt.Rectangle((j - 0.5, i - 0.5), 1, 1,
                             linewidth=2.5, edgecolor="#2C3E50",
                             facecolor="none", zorder=5)
        ax.add_patch(rect)

    # 标题
    ax.set_title("六只红利指数年度收益热力图（2017-2025）",
                 fontsize=13, fontweight="bold", color="#333333", pad=14)

    # 色条
    cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
    cbar.ax.tick_params(labelsize=8, colors="#555555")
    cbar.set_label("年度收益率", fontsize=9, color="#555555")
    cbar.outline.set_edgecolor("#CCCCCC")

    # 底部注释
    ax.text(
        0.0, -0.12,
        "深色框标注每只指数九年中最差的年度。口径：前五只为人民币全收益指数，深证红利为159905复权净值代理（已扣费）。\n"
        "完整年度为2017-2025年共九年，2016和2026因不完整未纳入。",
        transform=ax.transAxes, fontsize=7.5, color="#999999",
        va="top", ha="left", linespacing=1.5,
    )

    for spine in ax.spines.values():
        spine.set_visible(False)

    plt.tight_layout()
    out_path = CHART_DIR / "六指数年度收益热力图.png"
    fig.savefig(out_path, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"\n图表已保存: {out_path}")


if __name__ == "__main__":
    main()
