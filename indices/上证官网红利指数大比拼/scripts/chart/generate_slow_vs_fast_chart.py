#!/usr/bin/env python3
"""生成"慢公司反而赢"两线对比图：红利低波全收益 vs 沪深300全收益（近十年累计走势）。

口径：人民币全收益指数（现金分红再投资），期初归一化=100，共同交易日对齐。
窗口：2016-08-08 至 2026-07-31（沪深300全收益归档数据末端，文章主表窗口的近似）。
"""
from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")

BASE = Path(__file__).resolve().parent.parent.parent
PERF_DIR = BASE / "sources" / "performance-data"
PERF30_DIR = BASE / "sources" / "performance-data-30index"
CHART_DIR = BASE / "01_主报告" / "charts"
CHART_DIR.mkdir(parents=True, exist_ok=True)

START = pd.Timestamp("2016-08-08")
END = pd.Timestamp("2026-08-07")

SERIES = [
    ("红利低波",       PERF30_DIR / "H30269_红利低波_全收益.csv",       "日期Date", "收盘Close",   "#E63946", False),
    ("沪深300全收益",   PERF_DIR / "H00300_沪深300全收益_2016-06-30_2026-08-07.csv", "交易日期", "收盘点位", "#888888", True),
]


def load(path: Path, date_col: str, val_col: str) -> pd.Series:
    df = pd.read_csv(path)
    df[date_col] = pd.to_datetime(df[date_col].astype(str), format="mixed")
    df = df.sort_values(date_col).drop_duplicates(date_col, keep="last")
    s = df.set_index(date_col)[val_col].astype(float)
    return s.loc[START:END]


def main() -> None:
    data: dict[str, pd.Series] = {}
    for name, path, dcol, vcol, _, _ in SERIES:
        data[name] = load(path, dcol, vcol)

    # 共同交易日对齐
    common = data["红利低波"].index.intersection(data["沪深300全收益"].index)
    for k in list(data):
        data[k] = data[k].loc[common]
    for k, s in data.items():
        data[k] = s / s.iloc[0] * 100

    print(f"共同交易日数: {len(common)}, {common[0].date()} ~ {common[-1].date()}")
    for name, s in data.items():
        cum = s.iloc[-1] - 100
        cagr = (s.iloc[-1] / 100) ** (365.2425 / (s.index[-1] - s.index[0]).days) - 1
        print(f"  {name}: 期末={s.iloc[-1]:.1f}, 累计={cum:.1f}%, 年化={cagr * 100:.2f}%")

    # ========== 绘图 ==========
    plt.rcParams.update({
        "font.sans-serif": ["PingFang SC", "Heiti SC", "STHeiti", "Arial Unicode MS", "sans-serif"],
        "axes.unicode_minus": False,
        "figure.dpi": 180,
        "savefig.dpi": 180,
    })

    fig, ax = plt.subplots(figsize=(11, 6))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#FAFAFA")

    for name, _, _, _, color, is_bench in SERIES:
        s = data[name]
        ax.plot(s.index, s.values, color=color, linewidth=0.8,
                linestyle="--" if is_bench else "-", zorder=2 if is_bench else 3)

    # 期初基准线
    ax.axhline(100, color="#CCCCCC", linewidth=0.7, linestyle="--", zorder=1)

    # 坐标轴
    ax.set_xlim(common[0], common[-1] + pd.Timedelta(days=420))
    top_y = max(s.iloc[-1] for s in data.values()) * 1.02
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
        "红利低波 vs 沪深300全收益：十年累计走势（2016-08-08 = 100）",
        fontsize=13, fontweight="bold", color="#333333", pad=12,
    )

    # 左上角图例：简写 + 累计收益，降序（基准排末尾、虚线不参与排序）
    from matplotlib.lines import Line2D
    order = sorted(SERIES, key=lambda t: -data[t[0]].iloc[-1])
    handles = []
    for name, _, _, _, color, is_bench in order:
        cum = data[name].iloc[-1] - 100
        handles.append(Line2D([0], [0], color=color, linewidth=1.8,
                              linestyle="--" if is_bench else "-",
                              label=f"{name}  +{cum:.0f}%"))
    ax.legend(
        handles=handles, loc="upper left", fontsize=10,
        frameon=True, facecolor="white", edgecolor="#DDDDDD",
        framealpha=0.9, borderpad=0.6, labelspacing=0.4,
        handlelength=1.8, handletextpad=0.5,
    )

    # 线尾标注：简称 + 区间收益
    for name, _, _, _, color, is_bench in SERIES:
        s = data[name]
        cum = s.iloc[-1] - 100
        ax.annotate(
            f"{name} +{cum:.0f}%",
            xy=(s.index[-1], s.iloc[-1]),
            xytext=(10, 0), textcoords="offset points",
            fontsize=9.5, color=color,
            va="center", ha="left",
        )

    # 图内左下角口径注释（非小结）
    ax.text(
        0.01, -0.09,
        "口径：人民币全收益指数（现金分红再投资），期初归一化=100；截至2026年8月7日。",
        transform=ax.transAxes, fontsize=7.5, color="#999999",
        va="top", ha="left",
    )

    plt.tight_layout()
    out_path = CHART_DIR / "红利低波vs沪深300全收益_十年走势.png"
    fig.savefig(out_path, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"\n图表已保存: {out_path}")


if __name__ == "__main__":
    main()
