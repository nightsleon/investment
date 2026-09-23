#!/usr/bin/env python3
"""重做5年组组内对比图：每大类型选最优代表 + 基准，4条线。

类型代表：
- 红利低波（基准）：512890 华泰柏瑞红利低波
- 经典红利：515180 易方达中证红利
- 红利成长：007751 景顺长城红利成长低波
- 跨市场港股：3070HK 平安香港高息股ETF

红利质量类（159758）成立不满5年，不纳入。
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
    ("512890", "华泰柏瑞红利低波", "#999999", True),   # 基准/红利低波
    ("515180", "易方达中证红利", "#dc2626", False),    # 经典红利
    ("007751", "景顺长城红利成长低波", "#2563eb", False),  # 红利成长
    ("3070HK", "平安香港高息股ETF", "#16a34a", False),  # 跨市场港股
]


def load_nav(code: str) -> pd.Series:
    files = list(NAV_DIR.glob(f"{code}_*_净值.csv"))
    if not files:
        raise FileNotFoundError(f"未找到 {code} 净值文件")
    df = pd.read_csv(files[0], parse_dates=["date"], index_col="date", encoding="utf-8-sig")
    return df["reinvested_nav"].astype(float).sort_index()


def main() -> None:
    navs = {code: load_nav(code) for code, _, _, _ in FUNDS}

    # 共同区间。起始日与报告5年组表格一致（2020-03-26，原受008928成立限制），
    # 保证图上收益数字与表格列口径一致；结束取4只基金数据最早末日。
    START = pd.Timestamp("2020-03-26")
    common = None
    for s in navs.values():
        sl = s[s.index >= START]
        common = sl.index if common is None else common.intersection(sl.index)
    common = common.sort_values()
    print(f"共同区间: {common[0].date()} ~ {common[-1].date()}, {len(common)}个交易日")

    # 归一化
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

    # 先画非基准（按收益降序），基准最后画在最上层
    non_bench = [(c, n, col) for c, n, col, is_b in FUNDS if not is_b]
    non_bench.sort(key=lambda x: -rets[x[0]])
    for code, short, color in non_bench:
        ax.plot(norms[code].index, norms[code].values,
                color=color, linewidth=1.2,
                label=f"{short}  +{rets[code]:.1f}%")
        # 线尾标注
        ax.annotate(f"{short} +{rets[code]:.1f}%",
                    xy=(norms[code].index[-1], norms[code].iloc[-1]),
                    xytext=(6, 0), textcoords="offset points",
                    fontsize=9, color=color, va="center")

    # 基准灰色虚线，置顶
    b_code, b_short, b_color, _ = next(f for f in FUNDS if f[3])
    ax.plot(norms[b_code].index, norms[b_code].values,
            color=b_color, linewidth=1.6, linestyle="--", zorder=10,
            label=f"★{b_short}（基准）  +{rets[b_code]:.1f}%")
    ax.annotate(f"★{b_short}（基准） +{rets[b_code]:.1f}%",
                xy=(norms[b_code].index[-1], norms[b_code].iloc[-1]),
                xytext=(6, 0), textcoords="offset points",
                fontsize=9, color=b_color, va="center", fontweight="bold")

    # 图例：基准固定最上，其余按收益降序
    handles, labels = ax.get_legend_handles_labels()
    # 当前顺序：non_bench 收益降序 + 基准最后；重排为基准第一
    order = list(range(len(handles)))
    bench_idx = next(i for i, l in enumerate(labels) if l.startswith("★"))
    new_order = [bench_idx] + [i for i in order if i != bench_idx]
    ax.legend([handles[i] for i in new_order], [labels[i] for i in new_order],
              loc="upper left", fontsize=10, framealpha=0.9, edgecolor="#cccccc")

    ax.set_title("红利类基金5年实盘对比（按类型选代表，归一化=100）", fontsize=14, pad=12)
    ax.set_ylabel("分红再投归一化净值", fontsize=11)
    ax.set_xlabel("")
    ax.grid(True, alpha=0.3)
    ax.set_xlim(common[0], common[-1] + pd.Timedelta(days=180))  # 右侧留标注空间

    # 区间注脚
    ax.text(0.01, -0.08,
            f"共同区间 {common[0].date()} ~ {common[-1].date()}，约{len(common)}个交易日；"
            f"净值为手工复算分红再投口径，3070HK为港币计价前复权价格。",
            transform=ax.transAxes, fontsize=8.5, color="#666666")

    plt.tight_layout()
    out = OUT_DIR / "组内对比_5年组.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"✓ 已保存: {out}")


if __name__ == "__main__":
    main()
