#!/usr/bin/env python3
"""指数行情回溯图表生成脚本模板。

生成三张图：
1. 归一化走势图（多指数 + 基准虚线）
2. 年度收益热力图
3. 回撤图（可选）

用法:
    python generate_backtest_charts.py --data-dir ./data --start 20160810 --end 20260810 --output-dir ./charts
"""
from __future__ import annotations

import argparse
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from matplotlib.colors import TwoSlopeNorm
from matplotlib.lines import Line2D

warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")

# ========== 图表配置 ==========
plt.rcParams.update({
    "font.sans-serif": ["PingFang SC", "Heiti SC", "STHeiti", "Arial Unicode MS", "sans-serif"],
    "axes.unicode_minus": False,
    "figure.dpi": 180,
    "savefig.dpi": 180,
})

# ========== 在这里配置要绘制的指数 ==========
# (显示名, 文件名, 颜色, 值列名)
SERIES: list[tuple[str, str, str, str]] = [
    # 示例：
    # ("中证红利", "000922_中证红利_全收益.csv", "#E63946", "收盘点位"),
    # ("中证红利低波动", "H30269_中证红利低波动_全收益.csv", "#457B9D", "收盘点位"),
]

# 基准线（灰色虚线，不参与图例排序）
BENCHMARK: tuple[str, str, str, str] | None = None
# 示例：("沪深300全收益", "H00300_沪深300全收益.csv", "#888888", "收盘点位")

# 简写名称映射（图例用）
SHORT_NAMES: dict[str, str] = {}
# 示例：{"中证红利": "中证红利", "中证红利低波动": "红利低波"}
# ============================================


def load_csv(filename: str, value_col: str, data_dir: Path, start: pd.Timestamp, end: pd.Timestamp) -> pd.Series:
    df = pd.read_csv(data_dir / filename)
    df["交易日期"] = pd.to_datetime(df["交易日期"].astype(str), format="mixed")
    df = df.sort_values("交易日期").drop_duplicates("交易日期", keep="last")
    s = df.set_index("交易日期")[value_col].astype(float)
    s = s.loc[start:end]
    return s / s.iloc[0] * 100  # 归一化到期初=100


def plot_trend(data_dir: Path, output_dir: Path, start: pd.Timestamp, end: pd.Timestamp) -> None:
    if not SERIES:
        print("请在脚本中配置 SERIES。")
        return

    data: dict[str, pd.Series] = {}
    for name, fn, _, vcol in SERIES:
        data[name] = load_csv(fn, vcol, data_dir, start, end)

    if BENCHMARK:
        bm_name, bm_fn, _, bm_vcol = BENCHMARK
        data[bm_name] = load_csv(bm_fn, bm_vcol, data_dir, start, end)

    # 统一到共同交易日
    common = None
    for s in data.values():
        common = s.index if common is None else common.intersection(s.index)
    for k in list(data):
        data[k] = data[k].loc[common]

    fig, ax = plt.subplots(figsize=(11, 7.5))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#FAFAFA")

    for name, _, color, _ in SERIES:
        ax.plot(data[name].index, data[name].values, color=color, linewidth=0.8, zorder=3)

    if BENCHMARK:
        bm_name, _, bm_color, _ = BENCHMARK
        ax.plot(data[bm_name].index, data[bm_name].values, color=bm_color, linewidth=0.8, linestyle="--", zorder=2)

    ax.axhline(100, color="#CCCCCC", linewidth=0.7, linestyle="--", zorder=1)

    ax.set_xlim(common[0], common[-1] + pd.Timedelta(days=280))
    top_y = max(s.iloc[-1] for s in data.values()) * 1.03
    all_min = min(s.min() for s in data.values())
    ax.set_ylim(all_min * 0.96, top_y)

    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.tick_params(axis="x", labelsize=9, colors="#555555")
    ax.tick_params(axis="y", labelsize=9, colors="#555555")
    ax.grid(True, color="#E8E8E8", linewidth=0.6, zorder=0)

    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    for spine in ["left", "bottom"]:
        ax.spines[spine].set_color("#CCCCCC")

    ax.set_ylabel("累计全收益（期初=100）", fontsize=10, color="#555555")
    ax.set_title(
        f"指数累计全收益走势（{start.date()} = 100）",
        fontsize=13, fontweight="bold", color="#333333", pad=12,
    )

    # 图例：简写 + 累计收益，按累计收益降序
    legend_entries = []
    for name, _, color, _ in SERIES:
        s = data[name]
        cum_ret = s.iloc[-1] - 100
        short = SHORT_NAMES.get(name, name)
        legend_entries.append((cum_ret, color, f"{short}  +{cum_ret:.0f}%"))
    legend_entries.sort(key=lambda x: -x[0])

    handles = [Line2D([0], [0], color=c, linewidth=1.8, label=l) for _, c, l in legend_entries]

    if BENCHMARK:
        bm_name, _, bm_color, _ = BENCHMARK
        bm_cum = data[bm_name].iloc[-1] - 100
        handles.append(Line2D(
            [0], [0], color=bm_color, linewidth=1.8, linestyle="--",
            label=f"{SHORT_NAMES.get(bm_name, bm_name)}（基准）  +{bm_cum:.0f}%",
        ))

    ax.legend(
        handles=handles, loc="upper left", fontsize=8.5,
        frameon=True, facecolor="white", edgecolor="#DDDDDD", framealpha=0.9,
        borderpad=0.6, labelspacing=0.4, handlelength=1.8, handletextpad=0.5,
    )

    plt.tight_layout()
    out_path = output_dir / "累计全收益走势.png"
    fig.savefig(out_path, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"走势图已保存: {out_path}")


def plot_heatmap(data_dir: Path, output_dir: Path, start: pd.Timestamp, end: pd.Timestamp) -> None:
    if not SERIES:
        return

    annual_data: dict[str, dict[int, float]] = {}
    for name, fn, _, vcol in SERIES:
        s = load_csv(fn, vcol, data_dir, start, end)
        year_end = s.resample("YE").last()
        annual = year_end.pct_change()
        start_year = start.year + 1
        end_year = end.year - 1
        complete = annual[(annual.index.year >= start_year) & (annual.index.year <= end_year)]
        annual_data[name] = {int(ts.year): float(v) * 100 for ts, v in complete.items()}

    df = pd.DataFrame(annual_data).T  # 行=指数, 列=年份
    short_names_list = [SHORT_NAMES.get(n, n) for n in df.index]
    df.index = short_names_list

    fig, ax = plt.subplots(figsize=(max(8, len(df.columns) * 1.2), max(4, len(df) * 0.8)))
    fig.patch.set_facecolor("white")

    vmax = max(abs(df.values.min()), abs(df.values.max()))
    norm = TwoSlopeNorm(vmin=-vmax, vcenter=0, vmax=vmax)
    im = ax.imshow(df.values, cmap="RdYlGn", norm=norm, aspect="auto")

    ax.set_xticks(range(len(df.columns)))
    ax.set_xticklabels(df.columns, fontsize=9)
    ax.set_yticks(range(len(df.index)))
    ax.set_yticklabels(df.index, fontsize=9)

    # 格内标数值
    for i in range(len(df.index)):
        for j in range(len(df.columns)):
            val = df.iloc[i, j]
            color = "white" if abs(val) > vmax * 0.6 else "#333333"
            ax.text(j, i, f"{val:.1f}%", ha="center", va="center", fontsize=8, color=color)

    # 最差年粗框
    for i, name in enumerate(df.index):
        worst_year = df.loc[name].idxmin()
        j = list(df.columns).index(worst_year)
        ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False, edgecolor="#333333", linewidth=2.5))

    ax.set_title("年度收益热力图（红涨绿跌）", fontsize=13, fontweight="bold", color="#333333", pad=12)
    plt.tight_layout()
    out_path = output_dir / "年度收益热力图.png"
    fig.savefig(out_path, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"热力图已保存: {out_path}")


def plot_drawdown(data_dir: Path, output_dir: Path, start: pd.Timestamp, end: pd.Timestamp) -> None:
    if not SERIES:
        return

    fig, ax = plt.subplots(figsize=(11, 5))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#FAFAFA")

    for name, fn, color, vcol in SERIES:
        df = pd.read_csv(data_dir / fn)
        df["交易日期"] = pd.to_datetime(df["交易日期"].astype(str), format="mixed")
        df = df.sort_values("交易日期").drop_duplicates("交易日期", keep="last")
        s = df.set_index("交易日期")[vcol].astype(float).loc[start:end]
        drawdown = s / s.cummax() - 1
        ax.plot(drawdown.index, drawdown.values * 100, color=color, linewidth=0.8, label=SHORT_NAMES.get(name, name))

    ax.axhline(0, color="#CCCCCC", linewidth=0.7, linestyle="--")
    ax.set_ylabel("回撤（%）", fontsize=10, color="#555555")
    ax.set_title("回撤路径", fontsize=13, fontweight="bold", color="#333333", pad=12)
    ax.tick_params(axis="both", labelsize=9, colors="#555555")
    ax.grid(True, color="#E8E8E8", linewidth=0.6)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    ax.legend(loc="lower left", fontsize=8.5, frameon=True, facecolor="white", edgecolor="#DDDDDD")

    plt.tight_layout()
    out_path = output_dir / "回撤路径.png"
    fig.savefig(out_path, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"回撤图已保存: {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="指数行情回溯图表生成")
    parser.add_argument("--data-dir", required=True, help="CSV 数据目录")
    parser.add_argument("--start", required=True, help="开始日期 YYYYMMDD")
    parser.add_argument("--end", required=True, help="结束日期 YYYYMMDD")
    parser.add_argument("--output-dir", default=".", help="输出目录")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    start = pd.Timestamp(args.start)
    end = pd.Timestamp(args.end)

    plot_trend(data_dir, output_dir, start, end)
    plot_heatmap(data_dir, output_dir, start, end)
    plot_drawdown(data_dir, output_dir, start, end)


if __name__ == "__main__":
    main()
