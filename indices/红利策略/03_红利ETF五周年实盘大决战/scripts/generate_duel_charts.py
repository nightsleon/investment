#!/usr/bin/env python3
"""《红利 ETF 五周年实盘大决战》专属图表生成脚本。

功能：
1. 基准篇：华泰柏瑞红利低波 ETF（512890） vs 华泰柏瑞沪深300 ETF（510300）全周期走势对比（双子图）。
2. 对战篇：华泰柏瑞红利低波 ETF（512890） vs 参赛 ETF（1v1 走势对比与超额收益差双子图）。

统一风格：
- 白底专业金融量化图表
- 上图（主图）：分红再投全收益净值（起点同日归一=100）
- 下图（子图）：相对基准的累计超额收益差（百分点）
- 自动适配 Mac/Linux 中文字体
"""
from __future__ import annotations

import argparse
import math
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.font_manager as fm
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# ── 路径配置 ──────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCES_DIR = PROJECT_ROOT.parent.parent / "sources"
NAV_DIR = SOURCES_DIR / "fund-nav-correct"
CHARTS_DIR = PROJECT_ROOT / "charts"
CHARTS_DIR.mkdir(parents=True, exist_ok=True)


def configure_style() -> str:
    """配置 matplotlib 样式和中文字体。"""
    candidates = ["PingFang SC", "Hiragino Sans GB", "Heiti SC", "Arial Unicode MS", "Noto Sans CJK SC", "SimHei"]
    available = {font.name for font in fm.fontManager.ttflist}
    family = next((name for name in candidates if name in available), "sans-serif")
    plt.rcParams.update(
        {
            "font.family": family,
            "axes.unicode_minus": False,
            "figure.facecolor": "#FFFFFF",
            "axes.facecolor": "#FFFFFF",
            "axes.edgecolor": "#D1D5DB",
            "axes.linewidth": 0.8,
            "axes.labelcolor": "#1F2937",
            "xtick.color": "#4B5563",
            "ytick.color": "#4B5563",
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "grid.color": "#F3F4F6",
            "grid.linestyle": "--",
            "grid.linewidth": 0.6,
            "savefig.facecolor": "#FFFFFF",
        }
    )
    return family


def load_nav_series(code: str, name_hint: str = "") -> pd.Series:
    """从 fund-nav-correct 目录加载基金分红再投净值序列。"""
    matches = list(NAV_DIR.glob(f"{code}_*_净值.csv"))
    if not matches:
        raise FileNotFoundError(f"未找到代码为 {code} 的净值文件 (目录: {NAV_DIR})")
    csv_path = matches[0]
    df = pd.read_csv(csv_path)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").dropna(subset=["reinvested_nav"])
    s = pd.Series(df["reinvested_nav"].values, index=df["date"], name=code)
    return s


def plot_benchmark_vs_hs300(output_path: Path | None = None) -> Path:
    """生成基准篇：512890 红利低波 vs 510300 沪深300 全周期走势对比图。"""
    configure_style()

    s_512890 = load_nav_series("512890")
    s_510300 = load_nav_series("510300")

    # 对齐共同区间 (从 512890 成立/有净值开始)
    common_idx = s_512890.index.intersection(s_510300.index)
    df = pd.DataFrame({"512890": s_512890.loc[common_idx], "510300": s_510300.loc[common_idx]}).sort_index()

    # 归一化为 100
    df["norm_512890"] = df["512890"] / df["512890"].iloc[0] * 100.0
    df["norm_510300"] = df["510300"] / df["510300"].iloc[0] * 100.0
    df["excess"] = df["norm_512890"] - df["norm_510300"]

    start_date = df.index[0].strftime("%Y-%m-%d")
    end_date = df.index[-1].strftime("%Y-%m-%d")
    years = (df.index[-1] - df.index[0]).days / 365.25

    ret_512890 = (df["norm_512890"].iloc[-1] / 100.0 - 1.0) * 100
    ret_510300 = (df["norm_510300"].iloc[-1] / 100.0 - 1.0) * 100
    cagr_512890 = ((df["norm_512890"].iloc[-1] / 100.0) ** (1 / years) - 1.0) * 100
    cagr_510300 = ((df["norm_510300"].iloc[-1] / 100.0) ** (1 / years) - 1.0) * 100

    # 计算最大回撤
    peak_512890 = df["norm_512890"].cummax()
    dd_512890 = (df["norm_512890"] - peak_512890) / peak_512890
    max_dd_512890 = dd_512890.min() * 100

    peak_510300 = df["norm_510300"].cummax()
    dd_510300 = (df["norm_510300"] - peak_510300) / peak_510300
    max_dd_510300 = dd_510300.min() * 100

    fig, (ax_main, ax_sub) = plt.subplots(
        2, 1, figsize=(11, 7.5), sharex=True, gridspec_kw={"height_ratios": [3, 1.2], "hspace": 0.08}
    )

    # 颜色
    c_red = "#C0392B"   # 512890 鲜明红/珊瑚红
    c_blue = "#2980B9"  # 沪深300 稳重深蓝

    # ── 主图：归一化走势 ──
    ax_main.plot(df.index, df["norm_512890"], color=c_red, linewidth=2.2, label=f"红利低波ETF (512890): +{ret_512890:.1f}% (年化 {cagr_512890:.2f}%, 最大回撤 {max_dd_512890:.1f}%)")
    ax_main.plot(df.index, df["norm_510300"], color=c_blue, linewidth=1.8, linestyle="--", label=f"沪深300ETF (510300): +{ret_510300:.1f}% (年化 {cagr_510300:.2f}%, 最大回撤 {max_dd_510300:.1f}%)")
    ax_main.axhline(100, color="#9CA3AF", linestyle=":", linewidth=0.8)

    ax_main.set_title("华泰柏瑞红利低波 ETF vs 华泰柏瑞沪深300 ETF 全周期实盘走势对比", fontsize=14, pad=14, weight="bold", color="#111827")
    ax_main.set_ylabel("分红再投累计净值 (起点=100)", fontsize=10, weight="medium")
    ax_main.legend(loc="upper left", frameon=True, facecolor="#FFFFFF", edgecolor="#E5E7EB", fontsize=9.5)
    ax_main.grid(True, linestyle="--", alpha=0.5)

    # 标注终点数值
    last_dt = df.index[-1]
    ax_main.annotate(f"{df['norm_512890'].iloc[-1]:.1f}", xy=(last_dt, df["norm_512890"].iloc[-1]), xytext=(8, -2), textcoords="offset points", color=c_red, weight="bold", fontsize=9.5)
    ax_main.annotate(f"{df['norm_510300'].iloc[-1]:.1f}", xy=(last_dt, df["norm_510300"].iloc[-1]), xytext=(8, -2), textcoords="offset points", color=c_blue, weight="bold", fontsize=9.5)

    # 关键行情阶段高亮标注
    # 2021-2024 红利逆势牛
    ax_main.axvspan(pd.Timestamp("2021-02-18"), pd.Timestamp("2024-05-20"), color="#FEF3C7", alpha=0.25, label="_大盘单边走弱 vs 红利超额主升")
    ax_main.text(pd.Timestamp("2022-09-01"), 190, "核心资产泡沫破裂\n红利低波逆势拉升超额", color="#B45309", fontsize=9, ha="center", weight="semibold", bbox=dict(boxstyle="round,pad=0.3", facecolor="#FFFBEB", edgecolor="#FCD34D", linewidth=0.8))

    # ── 子图：累计超额差 ──
    ax_sub.plot(df.index, df["excess"], color="#059669", linewidth=1.5, label="红利低波相对沪深300累计超额 (百分点)")
    ax_sub.fill_between(df.index, 0, df["excess"], where=(df["excess"] >= 0), color="#10B981", alpha=0.25)
    ax_sub.fill_between(df.index, 0, df["excess"], where=(df["excess"] < 0), color="#EF4444", alpha=0.25)
    ax_sub.axhline(0, color="#6B7280", linestyle="-", linewidth=0.8)

    ax_sub.set_ylabel("累计超额 (pp)", fontsize=9.5, weight="medium")
    ax_sub.set_xlabel(f"实盘交易日期 ({start_date} ~ {end_date})", fontsize=9.5, labelpad=8)
    ax_sub.legend(loc="upper left", frameon=True, facecolor="#FFFFFF", edgecolor="#E5E7EB", fontsize=8.5)
    ax_sub.grid(True, linestyle="--", alpha=0.5)

    # 标注最新超额
    latest_excess = df["excess"].iloc[-1]
    ax_sub.annotate(f"+{latest_excess:.1f}%", xy=(last_dt, latest_excess), xytext=(8, -2), textcoords="offset points", color="#059669", weight="bold", fontsize=9)

    # 时间轴格式化
    ax_sub.xaxis.set_major_locator(mdates.YearLocator())
    ax_sub.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax_sub.xaxis.set_minor_locator(mdates.MonthLocator(bymonth=[7]))

    fig.subplots_adjust(top=0.92, bottom=0.08, left=0.08, right=0.95, hspace=0.1)

    if output_path is None:
        output_path = CHARTS_DIR / "00_512890_vs_沪深300_全周期走势对比.png"
    plt.savefig(output_path, dpi=250, bbox_inches="tight")
    plt.close(fig)
    print(f"已生成基准篇对比图: {output_path}")
    return output_path


def plot_duel_vs_512890(
    code: str,
    name: str,
    output_path: Path | None = None,
    color_duel: str = "#2563EB",
) -> Path:
    """生成对战篇 1v1 对决双子图 (参赛 ETF vs 512890)。"""
    configure_style()

    s_duel = load_nav_series(code)
    s_512890 = load_nav_series("512890")

    common_idx = s_duel.index.intersection(s_512890.index)
    if len(common_idx) < 50:
        raise ValueError(f"{code} 与 512890 的共同数据点不足 50 个")

    df = pd.DataFrame({"duel": s_duel.loc[common_idx], "512890": s_512890.loc[common_idx]}).sort_index()

    # 归一化为 100
    df["norm_duel"] = df["duel"] / df["duel"].iloc[0] * 100.0
    df["norm_512890"] = df["512890"] / df["512890"].iloc[0] * 100.0
    df["excess"] = df["norm_duel"] - df["norm_512890"]

    start_date = df.index[0].strftime("%Y-%m-%d")
    end_date = df.index[-1].strftime("%Y-%m-%d")
    years = (df.index[-1] - df.index[0]).days / 365.25

    ret_duel = (df["norm_duel"].iloc[-1] / 100.0 - 1.0) * 100
    ret_512890 = (df["norm_512890"].iloc[-1] / 100.0 - 1.0) * 100
    cagr_duel = ((df["norm_duel"].iloc[-1] / 100.0) ** (1 / years) - 1.0) * 100
    cagr_512890 = ((df["norm_512890"].iloc[-1] / 100.0) ** (1 / years) - 1.0) * 100

    peak_duel = df["norm_duel"].cummax()
    max_dd_duel = ((df["norm_duel"] - peak_duel) / peak_duel).min() * 100

    peak_512890 = df["norm_512890"].cummax()
    max_dd_512890 = ((df["norm_512890"] - peak_512890) / peak_512890).min() * 100

    fig, (ax_main, ax_sub) = plt.subplots(
        2, 1, figsize=(11, 7.5), sharex=True, gridspec_kw={"height_ratios": [3, 1.2], "hspace": 0.08}
    )

    c_bench = "#6B7280"  # 512890 作为基准标尺，用稳健中灰

    # ── 主图 ──
    ax_main.plot(df.index, df["norm_duel"], color=color_duel, linewidth=2.2, label=f"{name} ({code}): +{ret_duel:.1f}% (年化 {cagr_duel:.2f}%, 最大回撤 {max_dd_duel:.1f}%)")
    ax_main.plot(df.index, df["norm_512890"], color=c_bench, linewidth=1.8, linestyle="--", label=f"红利低波ETF (512890 基准): +{ret_512890:.1f}% (年化 {cagr_512890:.2f}%, 最大回撤 {max_dd_512890:.1f}%)")
    ax_main.axhline(100, color="#D1D5DB", linestyle=":", linewidth=0.8)

    ax_main.set_title(f"{name} ({code}) vs 华泰柏瑞红利低波 ETF (512890) 实盘对决", fontsize=14, pad=14, weight="bold", color="#111827")
    ax_main.set_ylabel("分红再投累计净值 (起点=100)", fontsize=10, weight="medium")
    ax_main.legend(loc="upper left", frameon=True, facecolor="#FFFFFF", edgecolor="#E5E7EB", fontsize=9.5)
    ax_main.grid(True, linestyle="--", alpha=0.5)

    last_dt = df.index[-1]
    ax_main.annotate(f"{df['norm_duel'].iloc[-1]:.1f}", xy=(last_dt, df["norm_duel"].iloc[-1]), xytext=(8, -2), textcoords="offset points", color=color_duel, weight="bold", fontsize=9.5)
    ax_main.annotate(f"{df['norm_512890'].iloc[-1]:.1f}", xy=(last_dt, df["norm_512890"].iloc[-1]), xytext=(8, -2), textcoords="offset points", color=c_bench, weight="bold", fontsize=9.5)

    # ── 子图 ──
    ax_sub.plot(df.index, df["excess"], color=color_duel, linewidth=1.5, label=f"{name} 相对 512890 累计超额 (百分点)")
    ax_sub.fill_between(df.index, 0, df["excess"], where=(df["excess"] >= 0), color="#10B981", alpha=0.25)
    ax_sub.fill_between(df.index, 0, df["excess"], where=(df["excess"] < 0), color="#EF4444", alpha=0.25)
    ax_sub.axhline(0, color="#6B7280", linestyle="-", linewidth=0.8)

    ax_sub.set_ylabel("超额收益 (pp)", fontsize=9.5, weight="medium")
    ax_sub.set_xlabel(f"共同实盘交易区间 ({start_date} ~ {end_date})", fontsize=9.5, labelpad=8)
    ax_sub.legend(loc="upper left", frameon=True, facecolor="#FFFFFF", edgecolor="#E5E7EB", fontsize=8.5)
    ax_sub.grid(True, linestyle="--", alpha=0.5)

    latest_excess = df["excess"].iloc[-1]
    sign_str = "+" if latest_excess >= 0 else ""
    ax_sub.annotate(f"{sign_str}{latest_excess:.1f}%", xy=(last_dt, latest_excess), xytext=(8, -2), textcoords="offset points", color="#059669" if latest_excess >= 0 else "#DC2626", weight="bold", fontsize=9)

    ax_sub.xaxis.set_major_locator(mdates.YearLocator())
    ax_sub.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax_sub.xaxis.set_minor_locator(mdates.MonthLocator(bymonth=[7]))

    fig.subplots_adjust(top=0.92, bottom=0.08, left=0.08, right=0.95, hspace=0.1)

    if output_path is None:
        output_path = CHARTS_DIR / f"{code}_vs_512890_对决走势.png"
    plt.savefig(output_path, dpi=250, bbox_inches="tight")
    plt.close(fig)
    print(f"已生成对战图: {output_path}")
    return output_path


def plot_funnel_chart(output_path: Path | None = None) -> Path:
    """生成全市场红利 ETF 严选数据漏斗图（阶梯式圆角卡片、对称高协调度设计）。"""
    configure_style()
    output_path = output_path or (CHARTS_DIR / "00_红利ETF严选数据漏斗.png")
    fig, ax = plt.subplots(figsize=(9.2, 4.1), dpi=250)

    stages = [
        {
            "num": "01",
            "name": "全市场海选池",
            "desc": "沪深股票ETF（51/56/58/159开头）",
            "count": "1,596 只",
            "ratio_str": "基准底池 (100%)",
            "bar_pct": 100.0,
            "color": "#64748B",
            "tag": "海选大底池",
            "tag_bg": "#F1F5F9",
            "tag_color": "#475569",
        },
        {
            "num": "02",
            "name": "红利主题池",
            "desc": "初筛：仅保留名称含“红利/股息/高股息”",
            "count": "84 只",
            "ratio_str": "留存 5.3% ｜ 剔除 94.7% 赛道杂音",
            "bar_pct": 55.0,
            "color": "#2563EB",
            "tag": "剔除 95% 杂音",
            "tag_bg": "#EFF6FF",
            "tag_color": "#1D4ED8",
        },
        {
            "num": "03",
            "name": "5年实盘老将",
            "desc": "硬核门槛：牛熊实盘运作满5年(2021.10前)",
            "count": "12 只",
            "ratio_str": "留存 0.8% ｜ 一票否决 85.7% 蹭热点新兵",
            "bar_pct": 28.0,
            "color": "#D97706",
            "tag": "一票否决 85.7%",
            "tag_bg": "#FEF3C7",
            "tag_color": "#B45309",
        },
        {
            "num": "04",
            "name": "健康核心主力",
            "desc": "流动性底线：最新场内资产规模 ≥ 2 亿元",
            "count": "10 只",
            "ratio_str": "留存 0.6% ｜ 锁定正赛 10 只对决主角",
            "bar_pct": 16.0,
            "color": "#DC2626",
            "tag": "正赛巅峰擂台",
            "tag_bg": "#FEE2E2",
            "tag_color": "#B91C1C",
        },
    ]

    y_centers = [3.10, 2.20, 1.30, 0.40]
    card_h = 0.72
    card_w = 95.0
    card_x = 2.5

    # 顶部标题栏（与卡片主体水平严格居中）
    fig.text(0.5, 0.945, "全市场红利 ETF 严选数据漏斗", fontsize=13, fontweight="bold", color="#0F172A", ha="center")
    fig.text(0.5, 0.89, "四层硬核实盘过滤法则：从 1,596 只全市场底池，层层严选出 10 只健康核心主力", fontsize=8.6, color="#64748B", ha="center")

    for i, s in enumerate(stages):
        yc = y_centers[i]
        is_winner = (i == 3)

        # 1. 单行底卡（圆角卡片）
        bg_color = "#FEF2F2" if is_winner else "#F8FAFC"
        border_color = "#FECACA" if is_winner else "#E2E8F0"
        border_w = 1.0 if is_winner else 0.6
        rect = patches.FancyBboxPatch(
            (card_x, yc - card_h / 2),
            card_w,
            card_h,
            boxstyle="round,pad=0.06,rounding_size=0.16",
            facecolor=bg_color,
            edgecolor=border_color,
            linewidth=border_w,
            zorder=1,
        )
        ax.add_patch(rect)

        # 2. 序号圆标 (x: 4.2)
        badge_color = "#DC2626" if is_winner else "#64748B"
        badge = patches.FancyBboxPatch(
            (4.2, yc - 0.20),
            2.6,
            0.40,
            boxstyle="round,pad=0.03,rounding_size=0.12",
            facecolor=badge_color,
            edgecolor="none",
            zorder=2,
        )
        ax.add_patch(badge)
        ax.text(5.5, yc, s["num"], fontsize=8.5, fontweight="bold", color="#FFFFFF", ha="center", va="center", zorder=3)

        # 3. 名称与规则 (x: 8.0 ~ 36.0)
        title_color = "#DC2626" if is_winner else "#0F172A"
        ax.text(8.0, yc + 0.12, s["name"], fontsize=10.2, fontweight="bold", color=title_color, va="center", zorder=3)
        ax.text(8.0, yc - 0.14, s["desc"], fontsize=7.8, color="#64748B", va="center", zorder=3)

        # 4. 中间进度条与转化提示 (x: 38.0 ~ 74.0)
        bar_left = 38.0
        bar_total_w = 34.0
        bar_act_w = max(bar_total_w * (s["bar_pct"] / 100.0), 1.6)
        bar_y = yc + 0.10
        bar_h = 0.16

        # 底槽
        track = patches.FancyBboxPatch(
            (bar_left, bar_y - bar_h / 2),
            bar_total_w,
            bar_h,
            boxstyle="round,pad=0.02,rounding_size=0.06",
            facecolor="#E2E8F0" if not is_winner else "#FCA5A5",
            edgecolor="none",
            zorder=2,
            alpha=0.6,
        )
        ax.add_patch(track)

        # 彩色条
        bar_patch = patches.FancyBboxPatch(
            (bar_left, bar_y - bar_h / 2),
            bar_act_w,
            bar_h,
            boxstyle="round,pad=0.02,rounding_size=0.06",
            facecolor=s["color"],
            edgecolor="none",
            zorder=3,
        )
        ax.add_patch(bar_patch)

        # 条形下方说明
        ax.text(bar_left, yc - 0.14, s["ratio_str"], fontsize=7.6, color="#475569" if not is_winner else "#B91C1C", va="center", zorder=3)

        # 5. 右侧核心指标与标签 (x: 75.0 ~ 95.0)
        # 上层：大号粗体数量 (右对齐在 94.5)
        ax.text(94.5, yc + 0.12, s["count"], fontsize=11.5, fontweight="bold", color=s["color"], ha="right", va="center", zorder=3)

        # 下层：状态徽章 (右对齐在 94.5)
        tag_w = 14.0
        tag_h = 0.28
        tag_rect = patches.FancyBboxPatch(
            (94.5 - tag_w, yc - 0.14 - tag_h / 2),
            tag_w,
            tag_h,
            boxstyle="round,pad=0.03,rounding_size=0.08",
            facecolor=s["tag_bg"],
            edgecolor="none",
            zorder=2,
        )
        ax.add_patch(tag_rect)
        ax.text(94.5 - tag_w / 2, yc - 0.14, s["tag"], fontsize=7.5, fontweight="bold", color=s["tag_color"], ha="center", va="center", zorder=3)

    # 4 层之间的漏斗向心连接
    for i in range(3):
        arrow_y = (y_centers[i] + y_centers[i + 1]) / 2
        ax.text(50.0, arrow_y, "▼ 严选过滤", fontsize=7.0, color="#94A3B8", ha="center", va="center", zorder=4)

    ax.set_xlim(0, 100)
    ax.set_ylim(-0.15, 3.65)
    ax.axis("off")

    plt.subplots_adjust(left=0.02, right=0.98, top=0.87, bottom=0.03)
    plt.savefig(output_path, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    print(f"已生成漏斗图: {output_path}")
    return output_path


def plot_radar_board_single(
    scores: list[float],
    max_scores: list[float],
    title: str,
    label: str,
    output_path: Path,
    color: str = "#DC2626",
) -> Path:
    """生成宽屏五维战力看板（左侧雷达 + 右侧细条得分）。"""
    configure_style()
    labels = ['全周期收益\n(25分)', '极限风控\n(25分)', '持有稳定性\n(20分)', '底层编制\n(15分)', '实操运营\n(15分)']
    short_labels = ['一、全周期收益能力', '二、极限风控抗摔性', '三、持有稳定性胜率', '四、底层编制与防坑', '五、实操与运营品质']
    pct = [s / m * 100 for s, m in zip(scores, max_scores)]
    num_vars = len(labels)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    pct_cycle = pct + pct[:1]
    angles_cycle = angles + angles[:1]

    fig = plt.figure(figsize=(9.8, 4.8), dpi=250)
    gs = fig.add_gridspec(1, 2, width_ratios=[1.05, 1.35], wspace=0.30, top=0.74, bottom=0.08, left=0.06, right=0.95)

    # 左侧：紧凑雷达图
    ax_radar = fig.add_subplot(gs[0, 0], polar=True)
    ax_radar.set_theta_offset(np.pi / 2)
    ax_radar.set_theta_direction(-1)
    ax_radar.set_xticks(angles)
    ax_radar.set_xticklabels(labels, fontsize=8.5, weight='semibold', color='#374151')
    ax_radar.set_ylim(0, 100)
    ax_radar.set_yticks([25, 50, 75, 100])
    ax_radar.set_yticklabels(['25%', '50%', '75%', '100%'], color='#9CA3AF', fontsize=7.5)

    ax_radar.plot(angles_cycle, pct_cycle, color=color, linewidth=2.0, linestyle='solid')
    ax_radar.fill(angles_cycle, pct_cycle, color=color, alpha=0.22)
    ax_radar.set_title(f"战力轮廓: {label}", size=10.5, color='#1F2937', weight='bold', pad=12)

    # 右侧：细条进度条与分值拆解看板
    ax_bars = fig.add_subplot(gs[0, 1])
    y_pos = np.arange(len(scores))[::-1]
    total_score = sum(scores)
    total_max = sum(max_scores)

    for i, (score, m, p, s_lbl) in enumerate(zip(scores, max_scores, pct, short_labels)):
        y = y_pos[i]
        # 背景灰槽
        ax_bars.barh(y, 100, height=0.42, color="#F3F4F6", edgecolor="none", zorder=1)
        # 实际得分条
        ax_bars.barh(y, p, height=0.42, color=color, edgecolor="none", zorder=2, alpha=0.88)

        # 指标名称
        ax_bars.text(0, y + 0.32, s_lbl, fontsize=8.5, fontweight='bold', color='#1F2937', va='center')
        # 分数文本
        ax_bars.text(102, y, f"{score:.1f} / {m:.0f}分 ({p:.0f}%)", fontsize=8.5, fontweight='semibold', color='#374151', va='center')

    ax_bars.set_xlim(0, 138)
    ax_bars.set_ylim(-0.5, len(scores) - 0.2)
    ax_bars.axis('off')
    ax_bars.set_title(f"维度明细 ｜ 综合总分: {total_score:.1f} / {total_max:.0f}分", size=10.5, color='#111827', weight='bold', pad=32)

    plt.suptitle(title, size=13.5, color='#111827', weight='bold', y=0.95)
    plt.savefig(output_path, bbox_inches='tight')
    plt.close(fig)
    print(f"已生成宽屏单标的雷达看板: {output_path}")
    return output_path


def plot_radar_board_duel(
    scores_duel: list[float],
    scores_bench: list[float],
    max_scores: list[float],
    title: str,
    label_duel: str,
    label_bench: str,
    output_path: Path,
    color_duel: str = "#2563EB",
    color_bench: str = "#6B7280",
) -> Path:
    """生成宽屏双雄对决战力看板（左侧双雷达 + 右侧对比柱线）。"""
    configure_style()
    labels = ['全周期收益\n(25分)', '极限风控\n(25分)', '持有稳定性\n(20分)', '底层编制\n(15分)', '实操运营\n(15分)']
    short_labels = ['一、全周期收益能力', '二、极限风控抗摔性', '三、持有稳定性胜率', '四、底层编制与防坑', '五、实操与运营品质']
    pct_duel = [s / m * 100 for s, m in zip(scores_duel, max_scores)]
    pct_bench = [s / m * 100 for s, m in zip(scores_bench, max_scores)]
    num_vars = len(labels)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    pct_duel_cycle = pct_duel + pct_duel[:1]
    pct_bench_cycle = pct_bench + pct_bench[:1]
    angles_cycle = angles + angles[:1]

    fig = plt.figure(figsize=(9.8, 4.8), dpi=250)
    gs = fig.add_gridspec(1, 2, width_ratios=[1.08, 1.38], wspace=0.30, top=0.74, bottom=0.08, left=0.06, right=0.95)

    # 左侧：双雄雷达对比图
    ax_radar = fig.add_subplot(gs[0, 0], polar=True)
    ax_radar.set_theta_offset(np.pi / 2)
    ax_radar.set_theta_direction(-1)
    ax_radar.set_xticks(angles)
    ax_radar.set_xticklabels(labels, fontsize=8.5, weight='semibold', color='#374151')
    ax_radar.set_ylim(0, 100)
    ax_radar.set_yticks([25, 50, 75, 100])
    ax_radar.set_yticklabels(['25%', '50%', '75%', '100%'], color='#9CA3AF', fontsize=7.5)

    ax_radar.plot(angles_cycle, pct_bench_cycle, color=color_bench, linewidth=1.6, linestyle='--', label=label_bench)
    ax_radar.fill(angles_cycle, pct_bench_cycle, color='#9CA3AF', alpha=0.12)
    ax_radar.plot(angles_cycle, pct_duel_cycle, color=color_duel, linewidth=2.0, linestyle='solid', label=label_duel)
    ax_radar.fill(angles_cycle, pct_duel_cycle, color=color_duel, alpha=0.22)
    ax_radar.legend(loc='lower center', bbox_to_anchor=(0.5, -0.22), ncol=2, frameon=True, fontsize=8)

    # 右侧：双雄细条对比看板
    ax_bars = fig.add_subplot(gs[0, 1])
    y_pos = np.arange(len(scores_duel))[::-1]
    total_duel = sum(scores_duel)
    total_bench = sum(scores_bench)

    for i, (sd, sb, m, pd, pb, s_lbl) in enumerate(zip(scores_duel, scores_bench, max_scores, pct_duel, pct_bench, short_labels)):
        y = y_pos[i]
        # 背景底槽
        ax_bars.barh(y + 0.11, 100, height=0.22, color="#F3F4F6", edgecolor="none", zorder=1)
        ax_bars.barh(y - 0.13, 100, height=0.22, color="#F3F4F6", edgecolor="none", zorder=1)

        # 挑战者条形 (上)
        ax_bars.barh(y + 0.11, pd, height=0.22, color=color_duel, edgecolor="none", zorder=2, alpha=0.90)
        # 基准条形 (下)
        ax_bars.barh(y - 0.13, pb, height=0.22, color=color_bench, edgecolor="none", zorder=2, alpha=0.75)

        # 维度标题
        diff = sd - sb
        diff_str = f"+{diff:.1f}" if diff > 0 else (f"{diff:.1f}" if diff < 0 else "持平")

        ax_bars.text(0, y + 0.33, f"{s_lbl} [差值: {diff_str}]", fontsize=8, fontweight='bold', color='#1F2937', va='center')
        ax_bars.text(102, y + 0.11, f"{label_duel}: {sd:.1f}分", fontsize=7.8, fontweight='semibold', color=color_duel, va='center')
        ax_bars.text(102, y - 0.13, f"{label_bench}: {sb:.1f}分", fontsize=7.8, fontweight='normal', color=color_bench, va='center')

    ax_bars.set_xlim(0, 148)
    ax_bars.set_ylim(-0.55, len(scores_duel) - 0.15)
    ax_bars.axis('off')
    ax_bars.set_title(f"维度对决 ｜ {label_duel} {total_duel:.1f}分 vs {label_bench} {total_bench:.1f}分", size=10.5, color='#111827', weight='bold', pad=32)

    plt.suptitle(title, size=13.5, color='#111827', weight='bold', y=0.95)
    plt.savefig(output_path, bbox_inches='tight')
    plt.close(fig)
    print(f"已生成宽屏双雄雷达对决看板: {output_path}")
    return output_path


def plot_radar_single(
    scores: list[float],
    max_scores: list[float],
    title: str,
    label: str,
    output_path: Path,
    color: str = "#C0392B",
) -> Path:
    """生成单只 ETF 的五维雷达图。"""
    configure_style()
    labels = ['全周期收益\n(满分25)', '极限风控\n(满分25)', '持有稳定性\n(满分20)', '底层编制\n(满分15)', '实操运营\n(满分15)']
    pct = [s / m * 100 for s, m in zip(scores, max_scores)]
    num_vars = len(labels)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    pct += pct[:1]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=10, weight='semibold', color='#1F2937')
    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(['20%', '40%', '60%', '80%', '100%'], color='#9CA3AF', fontsize=8)

    ax.plot(angles, pct, color=color, linewidth=2, linestyle='solid', label=label)
    ax.fill(angles, pct, color=color, alpha=0.25)
    plt.title(title, size=13, color='#111827', weight='bold', pad=20)
    plt.legend(loc='upper right', bbox_to_anchor=(1.2, 1.1), frameon=True)
    plt.savefig(output_path, dpi=250, bbox_inches='tight')
    plt.close(fig)
    print(f"已生成单标的雷达图: {output_path}")
    return output_path


def plot_radar_duel(
    scores_duel: list[float],
    scores_bench: list[float],
    max_scores: list[float],
    title: str,
    label_duel: str,
    label_bench: str,
    output_path: Path,
    color_duel: str = "#2563EB",
    color_bench: str = "#6B7280",
) -> Path:
    """生成两只 ETF 对决的五维雷达图。"""
    configure_style()
    labels = ['全周期收益\n(满分25)', '极限风控\n(满分25)', '持有稳定性\n(满分20)', '底层编制\n(满分15)', '实操运营\n(满分15)']
    pct_duel = [s / m * 100 for s, m in zip(scores_duel, max_scores)]
    pct_bench = [s / m * 100 for s, m in zip(scores_bench, max_scores)]
    num_vars = len(labels)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    pct_duel += pct_duel[:1]
    pct_bench += pct_bench[:1]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=10, weight='semibold', color='#1F2937')
    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(['20%', '40%', '60%', '80%', '100%'], color='#9CA3AF', fontsize=8)

    ax.plot(angles, pct_bench, color=color_bench, linewidth=1.8, linestyle='--', label=label_bench)
    ax.fill(angles, pct_bench, color='#9CA3AF', alpha=0.15)
    ax.plot(angles, pct_duel, color=color_duel, linewidth=2.2, linestyle='solid', label=label_duel)
    ax.fill(angles, pct_duel, color=color_duel, alpha=0.25)

    plt.title(title, size=13, color='#111827', weight='bold', pad=20)
    plt.legend(loc='upper right', bbox_to_anchor=(1.25, 1.12), frameon=True)
    plt.savefig(output_path, dpi=250, bbox_inches='tight')
    plt.close(fig)
    print(f"已生成对决雷达图: {output_path}")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="生成五周年实盘对决图表")
    parser.add_argument("--bench", action="store_true", help="生成基准篇 512890 vs 沪深300 对比图")
    parser.add_argument("--funnel", action="store_true", help="生成红利 ETF 严选数据漏斗图")
    parser.add_argument("--radar", action="store_true", help="生成雷达与看板图")
    parser.add_argument("--code", type=str, help="生成指定基金 vs 512890 对战图")
    parser.add_argument("--name", type=str, default="", help="指定基金简称")
    parser.add_argument("--all", action="store_true", help="批量生成专栏所有对战图与看板图")
    args = parser.parse_args()

    if args.funnel:
        plot_funnel_chart()

    if args.radar:
        plot_radar_board_single(
            [18.0, 23.0, 18.0, 12.0, 14.0],
            [25, 25, 20, 15, 15],
            "红利低波 ETF（512890）五维量化战力看板",
            "华泰柏瑞 512890",
            CHARTS_DIR / "00_512890_五维战力雷达看板.png",
        )
        plot_radar_board_duel(
            [17.0, 24.5, 17.5, 13.0, 12.5],
            [18.0, 23.0, 18.0, 12.0, 14.0],
            [25, 25, 20, 15, 15],
            "第 1 战：景顺红利低波 100 vs 华泰红利低波 五维量化对决看板",
            "景顺 100",
            "华泰 50",
            CHARTS_DIR / "01_515100_五维战力雷达对决看板.png",
        )
        plot_radar_board_duel(
            [13.5, 24.5, 16.0, 13.0, 12.5],
            [18.0, 23.0, 18.0, 12.0, 14.0],
            [25, 25, 20, 15, 15],
            "第 2 战：嘉实 300红利低波 vs 华泰红利低波 五维量化对决看板",
            "嘉实 300",
            "华泰 50",
            CHARTS_DIR / "02_515300_五维战力雷达对决看板.png",
        )

    if args.bench or (not args.code and not args.all and not args.funnel and not args.radar):
        plot_benchmark_vs_hs300()

    if args.code:
        plot_duel_vs_512890(args.code, args.name or args.code)

    if args.all:
        plot_benchmark_vs_hs300()
        plot_funnel_chart()
        plot_radar_board_single(
            [18.0, 23.0, 18.0, 12.0, 14.0],
            [25, 25, 20, 15, 15],
            "红利低波 ETF（512890）五维量化战力看板",
            "华泰柏瑞 512890",
            CHARTS_DIR / "00_512890_五维战力雷达看板.png",
        )
        plot_radar_board_duel(
            [17.0, 24.5, 17.5, 13.0, 12.5],
            [18.0, 23.0, 18.0, 12.0, 14.0],
            [25, 25, 20, 15, 15],
            "第 1 战：景顺红利低波 100 vs 华泰红利低波 五维量化对决看板",
            "景顺 100",
            "华泰 50",
            CHARTS_DIR / "01_515100_五维战力雷达对决看板.png",
        )
        plot_radar_board_duel(
            [13.5, 24.5, 16.0, 13.0, 12.5],
            [18.0, 23.0, 18.0, 12.0, 14.0],
            [25, 25, 20, 15, 15],
            "第 2 战：嘉实 300红利低波 vs 华泰红利低波 五维量化对决看板",
            "嘉实 300",
            "华泰 50",
            CHARTS_DIR / "02_515300_五维战力雷达对决看板.png",
        )
        battles = [
            ("515100", "景顺长城红利低波100ETF", CHARTS_DIR / "01_515100_vs_512890_对决走势.png"),
            ("515300", "嘉实沪深300红利低波ETF", CHARTS_DIR / "02_515300_vs_512890_对决走势.png"),
            ("515450", "南方标普大盘红利低波50ETF", CHARTS_DIR / "03_515450_vs_512890_对决走势.png"),
            ("501029", "华宝标普A股红利机会(LOF)", CHARTS_DIR / "04_501029_vs_512890_对决走势.png"),
            ("159758", "华夏中证红利质量ETF", CHARTS_DIR / "05_159758_vs_512890_对决走势.png"),
            ("510880", "华泰柏瑞上证红利ETF", CHARTS_DIR / "06_510880_vs_512890_对决走势.png"),
            ("515180", "易方达中证红利ETF", CHARTS_DIR / "07_515180_vs_512890_对决走势.png"),
            ("159905", "工银深证红利ETF", CHARTS_DIR / "08_159905_vs_512890_对决走势.png"),
            ("513690", "博时恒生港股通高股息ETF", CHARTS_DIR / "09_513690_vs_512890_对决走势.png"),
            ("007751", "景顺长城沪港深红利成长低波A", CHARTS_DIR / "特邀_007751_vs_512890_对决走势.png"),
        ]
        for c, n, out in battles:
            try:
                plot_duel_vs_512890(c, n, output_path=out)
            except Exception as e:
                print(f"生成 {c} {n} 失败: {e}")


if __name__ == "__main__":
    main()
