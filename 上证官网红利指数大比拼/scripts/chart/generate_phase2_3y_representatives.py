#!/usr/bin/env python3
"""重做3年组组内对比图：每大类型选最优代表 + 基准，4条线。

类型代表：
- 红利低波（基准）：512890 华泰柏瑞红利低波
- 跨市场港股：513530 华泰柏瑞港股通高股息
- 红利质量：159758 华夏红利质量
- 央企/股东回报：561580 华泰柏瑞央企红利

012708（东证红利低波）与基准同属红利低波，560700与561580同属央企/股东回报，
159691与513530同属跨市场港股，均取组内排名/规模更优者，不重复入图。
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

matplotlib.rcParams["font.sans-serif"] = ["Arial Unicode MS", "PingFang SC", "Heiti SC"]
matplotlib.rcParams["axes.unicode_minus"] = False

BASE = Path(__file__).resolve().parents[2]
NAV_DIR = BASE / "sources" / "fund-nav-correct"
OUT_DIR = BASE / "02_二期深度对比" / "charts"
OUT_DIR.mkdir(parents=True, exist_ok=True)

BENCHMARK = "512890"

# (code, 简称, 颜色, 是否基准)
FUNDS = [
    ("512890", "华泰柏瑞红利低波", "#999999", True),    # 基准/红利低波
    ("513530", "华泰柏瑞港股通高股息", "#16a34a", False),  # 跨市场港股
    ("159758", "华夏红利质量", "#2563eb", False),        # 红利质量
    ("561580", "华泰柏瑞央企红利", "#dc2626", False),    # 央企/股东回报
]


def load_nav(code: str) -> pd.Series:
    files = list(NAV_DIR.glob(f"{code}_*_净值.csv"))
    if not files:
        raise FileNotFoundError(f"未找到 {code} 净值文件")
    df = pd.read_csv(files[0], parse_dates=["date"], index_col="date", encoding="utf-8-sig")
    return df["reinvested_nav"].astype(float).sort_index()


def main() -> None:
    # 所有3年组基金（含未入图的012708/560700/159691），用于确定与报告表格一致的共同区间
    ALL_3Y = ["512890", "513530", "159691", "561580", "560700", "012708", "159758"]
    all_navs = {code: load_nav(code) for code in ALL_3Y}

    START = pd.Timestamp("2023-05-26")
    common = None
    for s in all_navs.values():
        sl = s[s.index >= START]
        common = sl.index if common is None else common.intersection(sl.index)
    common = common.sort_values()
    print(f"共同区间(7只基金): {common[0].date()} ~ {common[-1].date()}, {len(common)}个交易日")

    navs = {code: all_navs[code] for code, _, _, _ in FUNDS}
    norms = {}
    rets = {}
    for code, _, _, _ in FUNDS:
        s = navs[code].loc[common]
        n = s / s.iloc[0] * 100
        norms[code] = n
        rets[code] = n.iloc[-1] - 100

    fig, ax = plt.subplots(figsize=(12, 7.5))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    non_bench = [(c, n, col) for c, n, col, is_b in FUNDS if not is_b]
    non_bench.sort(key=lambda x: -rets[x[0]])
    for code, short, color in non_bench:
        ax.plot(norms[code].index, norms[code].values,
                color=color, linewidth=1.2,
                label=f"{short}  +{rets[code]:.1f}%")
        ax.annotate(f"{short} +{rets[code]:.1f}%",
                    xy=(norms[code].index[-1], norms[code].iloc[-1]),
                    xytext=(6, 0), textcoords="offset points",
                    fontsize=9, color=color, va="center")

    b_code, b_short, b_color, _ = next(f for f in FUNDS if f[3])
    ax.plot(norms[b_code].index, norms[b_code].values,
            color=b_color, linewidth=1.6, linestyle="--", zorder=10,
            label=f"★{b_short}（基准）  +{rets[b_code]:.1f}%")
    ax.annotate(f"★{b_short}（基准） +{rets[b_code]:.1f}%",
                xy=(norms[b_code].index[-1], norms[b_code].iloc[-1]),
                xytext=(6, 0), textcoords="offset points",
                fontsize=9, color=b_color, va="center", fontweight="bold")

    handles, labels = ax.get_legend_handles_labels()
    bench_idx = next(i for i, l in enumerate(labels) if l.startswith("★"))
    new_order = [bench_idx] + [i for i in range(len(handles)) if i != bench_idx]
    ax.legend([handles[i] for i in new_order], [labels[i] for i in new_order],
              loc="upper left", fontsize=10, framealpha=0.9, edgecolor="#cccccc")

    ax.set_title("红利类基金3年实盘对比（按类型选代表，归一化=100）", fontsize=14, pad=12)
    ax.set_ylabel("分红再投归一化净值", fontsize=11)
    ax.set_xlabel("")
    ax.grid(True, alpha=0.3)
    ax.set_xlim(common[0], common[-1] + pd.Timedelta(days=120))

    ax.text(0.01, -0.08,
            f"共同区间 {common[0].date()} ~ {common[-1].date()}，约{len(common)}个交易日；"
            f"净值为手工复算分红再投口径。该区间恰逢央企估值重塑与红利风格占优，表现可能偏乐观。",
            transform=ax.transAxes, fontsize=8.5, color="#666666")

    plt.tight_layout()
    out = OUT_DIR / "组内对比_3年组.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"✓ 已保存: {out}")


if __name__ == "__main__":
    main()
