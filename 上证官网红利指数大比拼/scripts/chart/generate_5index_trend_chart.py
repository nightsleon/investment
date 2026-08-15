#!/usr/bin/env python3
"""生成五只代表性红利指数十年累计全收益走势图。"""
from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")

BASE = Path(__file__).resolve().parent.parent.parent
PERF = BASE / "sources" / "performance-data"
CHART_DIR = BASE / "charts"
START = pd.Timestamp("2016-06-30")
END = pd.Timestamp("2026-07-31")

# 六只指数：(显示名, 文件名, 颜色, 值列名)
SERIES = [
    ("中证全指红利质量",       "932315_中证全指红利质量_全收益_2016-06-30_2026-07-31.csv",           "#E63946", "收盘点位"),
    ("中证沪港深红利成长低波动", "931157_沪港深红利成长低波动_全收益_2016-06-30_2026-07-31.csv",     "#457B9D", "收盘点位"),
    ("中证红利低波动",         "H30269_中证红利低波动_全收益_2016-06-30_2026-07-31.csv",           "#2A9D8F", "收盘点位"),
    ("标普大盘红利低波50",     "SPDJI_标普中国A股大盘红利低波50_CNY_TR_2016-06-30_2026-07-31.csv", "#F4A261", "收盘点位"),
    ("中证红利",               "000922_中证红利_全收益_2016-06-30_2026-07-31.csv",                 "#6D6875", "收盘点位"),
    ("深证红利（ETF代理）",     "399324_深证红利_159905复权净值代理_2016-06-30_2026-07-31.csv",     "#9D4EDD", "复权单位净值"),
]

# 基准线：沪深300全收益（虚线，不参与图例排序）
BENCHMARK = (
    "沪深300全收益",
    "H00300_沪深300全收益_2016-06-30_2026-07-31.csv",
    "#888888",
    "收盘点位",
)


def load_csv(filename: str, value_col: str) -> pd.Series:
    df = pd.read_csv(PERF / filename)
    df["交易日期"] = pd.to_datetime(df["交易日期"].astype(str), format="mixed")
    df = df.sort_values("交易日期").drop_duplicates("交易日期", keep="last")
    s = df.set_index("交易日期")[value_col].astype(float)
    s = s.loc[START:END]
    return s / s.iloc[0] * 100  # 归一化到期初=100


def main() -> None:
    data: dict[str, pd.Series] = {}
    for name, fn, _, vcol in SERIES:
        data[name] = load_csv(fn, vcol)

    # 加载沪深300基准
    bm_name, bm_fn, _, bm_vcol = BENCHMARK
    data[bm_name] = load_csv(bm_fn, bm_vcol)

    # 统一到共同交易日
    common = None
    for s in data.values():
        common = s.index if common is None else common.intersection(s.index)
    for k in list(data):
        data[k] = data[k].loc[common]

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

    fig, ax = plt.subplots(figsize=(11, 7.5))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#FAFAFA")

    for name, _, color, _ in SERIES:
        s = data[name]
        ax.plot(s.index, s.values, color=color, linewidth=0.8, zorder=3)

    # 沪深300基准虚线
    bm_s = data[bm_name]
    ax.plot(bm_s.index, bm_s.values, color=BENCHMARK[2], linewidth=0.8, linestyle="--", zorder=2)

    # 基准线
    ax.axhline(100, color="#CCCCCC", linewidth=0.7, linestyle="--", zorder=1)

    # 坐标轴
    ax.set_xlim(common[0], common[-1] + pd.Timedelta(days=280))
    top_y = data["中证全指红利质量"].iloc[-1] * 1.03
    # 下限取深证红利ETF代理的最低点，留一点余量
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
        "六只代表性红利指数 vs 沪深300全收益：十年累计走势（2016-06-30 = 100）",
        fontsize=13, fontweight="bold", color="#333333", pad=12,
    )

    # 左上角图例：简写名称 + 累计收益
    short_names = {
        "中证全指红利质量": "全指红利质量",
        "中证沪港深红利成长低波动": "沪港深成长低波",
        "中证红利低波动": "红利低波",
        "标普大盘红利低波50": "标普大盘低波50",
        "中证红利": "中证红利",
        "深证红利（ETF代理）": "深证红利(代理)",
    }
    legend_handles = []
    from matplotlib.lines import Line2D
    legend_entries = []
    for name, _, color, _ in SERIES:
        s = data[name]
        cum_ret = s.iloc[-1] - 100
        legend_entries.append((cum_ret, color, f"{short_names[name]}  +{cum_ret:.0f}%"))
    # 按累计收益由高到低排序
    legend_entries.sort(key=lambda x: -x[0])
    for cum_ret, color, label in legend_entries:
        legend_handles.append(Line2D(
            [0], [0], color=color, linewidth=1.8,
            label=label,
        ))
    # 沪深300基准加在图例末尾
    bm_cum = bm_s.iloc[-1] - 100
    legend_handles.append(Line2D(
        [0], [0], color=BENCHMARK[2], linewidth=1.8, linestyle="--",
        label=f"沪深300全收益（基准）  +{bm_cum:.0f}%",
    ))
    ax.legend(
        handles=legend_handles,
        loc="upper left",
        fontsize=8.5,
        frameon=True,
        facecolor="white",
        edgecolor="#DDDDDD",
        framealpha=0.9,
        borderpad=0.6,
        labelspacing=0.4,
        handlelength=1.8,
        handletextpad=0.5,
    )

    # 注释
    ax.text(
        0.01, -0.10,
        "口径：前五只为人民币全收益指数（现金分红再投资），深证红利使用工银深证红利ETF（159905）复权净值代理（已扣费，非官方全收益），沪深300全收益为宽基基准。2016-06-30至2026-07-31。\n"
        "走势只呈现累计收益路径；低波与抗跌应以波动率、最大回撤表判断，不能把曲线平缓程度当作精确风险指标。",
        transform=ax.transAxes, fontsize=7.5, color="#999999",
        va="top", ha="left", linespacing=1.5,
    )

    plt.tight_layout()
    out_path = CHART_DIR / "summary" / "六指数vs沪深300累计全收益走势.png"
    fig.savefig(out_path, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"\n图表已保存: {out_path}")


if __name__ == "__main__":
    main()
