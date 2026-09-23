#!/usr/bin/env python3
"""生成第三节"十年成绩单"三只代表红利指数十年累计走势对比图。

三只代表：香港红利（港股）、红利低波（A股经典低波）、消费红利（行业主题/冲高回落）。
展示路径节奏错位。窗口：2016-08-08 至 2026-08-07，与文章主口径一致。
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
DATA_DIR = BASE / "sources" / "performance-data-30index" / "generation-full-history"
CHART_DIR = BASE / "01_主报告" / "charts"
CHART_DIR.mkdir(parents=True, exist_ok=True)

START = pd.Timestamp("2016-08-08")
END = pd.Timestamp("2026-08-07")

# (显示名, 文件名, 颜色, 线尾标注垂直偏移pt)
SERIES = [
    ("香港红利",     "H11140_香港红利_基日至今.csv",     "#c0392b", 0),
    ("消费红利",     "H30094_消费红利_基日至今.csv",     "#2e86c1", 9),
    ("红利低波",     "H30269_红利低波_基日至今.csv",     "#27ae60", -9),
]


def load(filename: str) -> pd.Series:
    df = pd.read_csv(DATA_DIR / filename, dtype={"date": str})
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
    df = df.sort_values("date").drop_duplicates("date", keep="last")
    s = df.set_index("date")["close"].astype(float)
    s = s.loc[START:END]
    return s / s.iloc[0] * 100  # 期初=100


def main() -> None:
    data: dict[str, pd.Series] = {}
    for name, fn, _, _ in SERIES:
        data[name] = load(fn)

    # 共同交易日对齐
    common = data["红利低波"].index
    for k, s in data.items():
        common = common.intersection(s.index)
    for k in list(data):
        data[k] = data[k].loc[common]

    print(f"共同交易日数: {len(common)}, {common[0].date()} ~ {common[-1].date()}")
    for name, s in data.items():
        print(f"  {name}: 期末={s.iloc[-1]:.1f}, 累计={s.iloc[-1]-100:.1f}%")

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

    for name, _, color, _ in SERIES:
        s = data[name]
        ax.plot(s.index, s.values, color=color, linewidth=0.8, zorder=3)

    ax.axhline(100, color="#CCCCCC", linewidth=0.7, linestyle="--", zorder=1)

    ax.set_xlim(common[0], common[-1] + pd.Timedelta(days=340))
    top_y = max(s.max() for s in data.values()) * 1.02
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
        "三只代表红利指数：十年累计走势（2016-08-08 = 100）",
        fontsize=13, fontweight="bold", color="#333333", pad=12,
    )

    # 左上角图例：简写 + 累计收益，按期末累计降序
    from matplotlib.lines import Line2D
    order = sorted(SERIES, key=lambda t: -data[t[0]].iloc[-1])
    handles = []
    for name, _, color, _ in order:
        cum = data[name].iloc[-1] - 100
        handles.append(Line2D([0], [0], color=color, linewidth=1.8, label=f"{name}  +{cum:.0f}%"))
    ax.legend(
        handles=handles, loc="upper left", fontsize=9.5,
        frameon=True, facecolor="white", edgecolor="#DDDDDD",
        framealpha=0.9, borderpad=0.6, labelspacing=0.4,
        handlelength=1.8, handletextpad=0.5,
    )

    # 线尾标注：简称 + 区间收益（垂直偏移防重叠）
    for name, _, color, dy in SERIES:
        s = data[name]
        cum = s.iloc[-1] - 100
        ax.annotate(
            f"{name} +{cum:.0f}%",
            xy=(s.index[-1], s.iloc[-1]),
            xytext=(10, dy), textcoords="offset points",
            fontsize=9, color=color,
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
    out_path = CHART_DIR / "三只代表红利指数_十年走势.png"
    fig.savefig(out_path, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"\n图表已保存: {out_path}")


if __name__ == "__main__":
    main()
