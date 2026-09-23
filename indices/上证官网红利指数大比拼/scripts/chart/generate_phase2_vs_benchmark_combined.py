#!/usr/bin/env python3
"""重做二期每只基金的"对比基准"合并图。

上图（主图）：基金分红再投净值、基准512890、跟踪指数全收益，三者同区间同日归一=100。
下图（子图）：基金相对跟踪指数的累计收益差（百分点），正值=基金跑赢指数。

参考 scripts/chart/generate_512890_article_charts.py 的 plot_tracking_difference 配色与布局。
输出覆盖 charts/对比基准_{code}.png，替代原先分开的"对比基准"和"跟踪偏离"两张图。
"""
from __future__ import annotations

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import pandas as pd

# ── 路径 ──────────────────────────────────────────────
BASE = Path(__file__).resolve().parents[2]
NAV_DIR = BASE / "sources" / "fund-nav-correct"
INDEX_DIR = BASE / "sources" / "performance-data-30index"
OUT_DIR = BASE / "02_二期深度对比" / "charts"

BENCH = "512890"
BENCH_SHORT = "华泰柏瑞红利低波ETF（基准）"
FUND_COLOR = "#4C78A8"
INDEX_COLOR = "#F28E2B"
BENCH_COLOR = "#9A9A9A"

# code -> (short, index_code, group)
FUNDS = {
    # 5年组
    "510880": ("华泰柏瑞上证红利", "000015", "5y"),
    "515180": ("易方达中证红利", "000922", "5y"),
    "515300": ("嘉实300红利低波", "930740", "5y"),
    "007751": ("景顺长城红利成长低波", "931157", "5y"),
    "008928": ("宏利消费红利A", "H30094", "5y"),
    "512530": ("建信300红利", "000821", "5y"),
    "501307": ("银河沪港深高股息LOF", "930917", "5y"),
    "007178": ("浙商预期高股息增强", "CESFHY", "5y"),
    "007671": ("建信红利潜力", "H30089", "5y"),
    "3070HK": ("平安香港高息股ETF", "H11140", "5y"),
    # 3年组
    "012708": ("东方红红利低波A", "931446", "3y"),
    "513530": ("华泰柏瑞港股通高股息", "930914", "3y"),
    "159691": ("工银港股通高息精选", "930839", "3y"),
    "561580": ("华泰柏瑞央企红利", "000825", "3y"),
    "560700": ("广发央企股东回报", "932039", "3y"),
    "159758": ("华夏红利质量", "931468", "3y"),
    # 观察池重点观察
    "159209": ("招商中证全指红利质量", "932315", "obs"),
}

GROUP_START = {"5y": pd.Timestamp("2020-03-26"), "3y": pd.Timestamp("2023-05-26"), "obs": None}


def configure_style() -> None:
    candidates = ["PingFang SC", "Hiragino Sans GB", "Heiti SC", "Arial Unicode MS", "Noto Sans CJK SC"]
    available = {f.name for f in fm.fontManager.ttflist}
    family = next((n for n in candidates if n in available), "DejaVu Sans")
    plt.rcParams.update({
        "font.family": family,
        "axes.unicode_minus": False,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.edgecolor": "#D9DEE7",
        "axes.labelcolor": "#4B5563",
        "xtick.color": "#6B7280",
        "ytick.color": "#6B7280",
        "savefig.facecolor": "white",
    })


def load_nav(code: str) -> pd.Series:
    f = next(NAV_DIR.glob(f"{code}_*_净值.csv"))
    df = pd.read_csv(f, parse_dates=["date"], index_col="date", encoding="utf-8-sig")
    return df["reinvested_nav"].astype(float).sort_index()


def load_index(index_code: str) -> pd.Series:
    f = next(INDEX_DIR.glob(f"{index_code}_*_全收益.csv"))
    df = pd.read_csv(f, encoding="utf-8-sig")
    df.columns = [c.strip() for c in df.columns]
    date_col = next(c for c in df.columns if c.startswith("日期"))
    close_col = next(c for c in df.columns if c.startswith("收盘"))
    df[date_col] = pd.to_datetime(df[date_col])
    return df.set_index(date_col)[close_col].astype(float).sort_index()


def index_display_name(index_code: str) -> str:
    f = next(INDEX_DIR.glob(f"{index_code}_*_全收益.csv"))
    # 文件名形如 000922_中证红利_全收益.csv
    parts = f.stem.split("_")
    return parts[1] if len(parts) >= 2 else index_code


def plot_one(code: str, short: str, index_code: str, group: str,
             fund_nav: pd.Series, bench_nav: pd.Series, index_nav: pd.Series) -> Path:
    # 三者共同交易日
    common = fund_nav.index.intersection(bench_nav.index).intersection(index_nav.index)
    if group == "obs":
        # 观察池：从基金成立日开始
        common = common[common >= fund_nav.index[0]].sort_values()
    else:
        start = GROUP_START[group]
        common = common[common >= start].sort_values()

    f = fund_nav.loc[common]
    b = bench_nav.loc[common]
    idx = index_nav.loc[common]

    f_norm = f / f.iloc[0] * 100
    b_norm = b / b.iloc[0] * 100
    i_norm = idx / idx.iloc[0] * 100

    # 累计收益差（基金 - 指数），单位：百分点
    gap = (f_norm.values - i_norm.values)

    x = mdates.date2num(common.to_pydatetime())

    fig = plt.figure(figsize=(13.2, 7.6), dpi=150)
    grid = fig.add_gridspec(2, 1, height_ratios=[3.0, 1.15], hspace=0.08)
    ax = fig.add_subplot(grid[0])
    ax_gap = fig.add_subplot(grid[1], sharex=ax)

    idx_name = index_display_name(index_code)

    # ── 上图 ──
    ax.plot(x, f_norm.values, color=FUND_COLOR, linewidth=2.0,
            label=f"{short}（基金） {f_norm.iloc[-1]-100:+.1f}%")
    ax.plot(x, b_norm.values, color=BENCH_COLOR, linewidth=1.4, linestyle="--",
            label=f"{BENCH_SHORT} {b_norm.iloc[-1]-100:+.1f}%")
    ax.plot(x, i_norm.values, color=INDEX_COLOR, linewidth=1.8,
            label=f"{idx_name}全收益 {i_norm.iloc[-1]-100:+.1f}%")
    ax.axhline(100, color="#AAB2BF", linewidth=0.8, linestyle=":")
    ax.grid(axis="y", color="#E9EDF3", linewidth=0.8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_ylabel("归一化累计表现（起点=100）")
    ax.legend(loc="upper left", frameon=False, ncol=1, fontsize=10)
    ax.tick_params(axis="x", labelbottom=False)

    # ── 下图：基金 vs 跟踪指数 累计收益差 ──
    ax_gap.axhline(0, color="#9CA3AF", linewidth=0.9)
    ax_gap.fill_between(x, 0, gap, where=(gap >= 0), color=FUND_COLOR, alpha=0.28)
    ax_gap.fill_between(x, 0, gap, where=(gap < 0), color="#E15759", alpha=0.28)
    ax_gap.plot(x, gap, color="#5B6472", linewidth=1.1)
    ax_gap.grid(axis="y", color="#EEF1F5", linewidth=0.7)
    ax_gap.spines[["top", "right"]].set_visible(False)
    ax_gap.set_ylabel(f"相对{idx_name}\n累计收益差（百分点）", fontsize=9)
    end_txt = f"期末 {gap[-1]:+.1f}个百分点"
    ax_gap.text(0.985, 0.85 if gap[-1] >= 0 else 0.12, end_txt,
                transform=ax_gap.transAxes, ha="right",
                va="top" if gap[-1] >= 0 else "bottom",
                color="#374151", fontsize=10)
    ax_gap.xaxis.set_major_locator(mdates.YearLocator())
    ax_gap.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    note = "3070HK为港币计价前复权价格，与人民币全收益指数存在汇率偏差，收益差仅供参考。" if code == "3070HK" \
        else "下图正值表示基金跑赢跟踪指数，负值表示跑输；基金与指数均为分红再投全收益口径。"
    fig.suptitle(f"{short}（{code}）vs 基准与跟踪指数", x=0.075, y=0.965, ha="left", fontsize=16)
    fig.text(0.075, 0.915,
             f"区间 {common[0].date()} ~ {common[-1].date()}，同日起点归一为100｜{note}",
             fontsize=10, color="#6B7280")
    fig.subplots_adjust(left=0.09, right=0.98, top=0.86, bottom=0.08)

    out = OUT_DIR / f"对比基准_{code}.png"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    return out


def main() -> None:
    configure_style()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    bench_nav = load_nav(BENCH)
    for code, (short, index_code, group) in FUNDS.items():
        fund_nav = load_nav(code)
        index_nav = load_index(index_code)
        out = plot_one(code, short, index_code, group, fund_nav, bench_nav, index_nav)
        print(f"✓ {out.name}  ({short})")


if __name__ == "__main__":
    main()
