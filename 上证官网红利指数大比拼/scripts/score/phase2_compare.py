#!/usr/bin/env python3
"""二期：基于ETF/基金实际净值的对比分析。

- 计算每只基金的四维度得分（收益40%、风险30%、效率15%、稳定性15%）
- 计算跟踪偏离度（基金净值 vs 对应指数全收益）
- 以华泰柏瑞红利低波ETF（512890）为基准
- 生成排名报告 + 跟踪偏离图 + 行情对比图
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

matplotlib.rcParams["font.sans-serif"] = ["Arial Unicode MS", "PingFang SC", "Heiti SC"]
matplotlib.rcParams["axes.unicode_minus"] = False

BASE = Path(__file__).resolve().parents[2]
NAV_DIR = BASE / "sources" / "fund-nav-correct"  # 正确口径：手工复算的分红再投净值
INDEX_CSV_DIR = BASE / "sources" / "performance-data-30index"
OUTPUT_DIR = BASE / "02_二期深度对比"
CHART_DIR = OUTPUT_DIR / "charts"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CHART_DIR.mkdir(parents=True, exist_ok=True)

BENCHMARK_CODE = "512890"  # 华泰柏瑞红利低波ETF
BENCHMARK_NAME = "华泰柏瑞红利低波ETF"

# 统一评价区间
FIVE_YEAR_START = pd.Timestamp("2021-08-02")
FIVE_YEAR_END = pd.Timestamp("2026-08-10")
TWO_YEAR_START = pd.Timestamp("2024-08-10")
TWO_YEAR_END = pd.Timestamp("2026-08-10")

WEIGHTS = {
    "return": 0.40,
    "risk": 0.30,
    "efficiency": 0.15,
    "stability": 0.15,
}


def simplify_name(name: str) -> str:
    """精简基金名称，去掉冗长后缀。"""
    name = name.replace("交易型开放式指数证券投资基金", "ETF")
    name = name.replace("中证", "")
    name = name.replace("沪深", "")
    name = name.replace("证券投资基金", "")
    name = name.replace("指数型发起式", "")
    name = name.replace("指数型", "")
    name = name.replace("(QDII)", "")
    name = name.replace("投资", "")
    return name[:16]


# ========== 指标计算 ==========

def annualized_return(start_val: float, end_val: float, start_date: pd.Timestamp, end_date: pd.Timestamp) -> float:
    days = (end_date - start_date).days
    if days <= 0 or start_val <= 0 or end_val <= 0:
        return float("nan")
    return (end_val / start_val) ** (365.2425 / days) - 1


def max_drawdown(series: pd.Series) -> float:
    """最大回撤（负的）"""
    peak = series.expanding(min_periods=1).max()
    dd = series / peak - 1
    return float(dd.min())


def calculate_metrics(nav_series: pd.Series) -> dict:
    """从净值序列计算四维度指标。"""
    s = nav_series.dropna().sort_index()
    if len(s) < 30:
        return {"sufficient": False}

    start_date = s.index[0]
    end_date = s.index[-1]
    start_val = s.iloc[0]
    end_val = s.iloc[-1]

    # 收益
    cagr = annualized_return(start_val, end_val, start_date, end_date)
    total_return = end_val / start_val - 1

    # 风险：最大回撤
    mdd = max_drawdown(s)

    # 月频波动率
    monthly = s.resample("M").last()
    monthly_ret = monthly.pct_change().dropna()
    monthly_vol = float(monthly_ret.std() * math.sqrt(12)) if len(monthly_ret) > 5 else float("nan")

    # 风险收益效率
    efficiency = cagr / monthly_vol if monthly_vol and not np.isnan(monthly_vol) else float("nan")

    # 稳定性：年度胜率 + 滚动3年中位数
    # 年度收益（完整自然年）
    annual = s.resample("Y").last()
    annual_ret = annual.pct_change().dropna()
    # 只算完整年份（起始年和结束年如果只有部分数据不算）
    complete_years = []
    for year in annual_ret.index.year:
        year_data = s[str(year)]
        if len(year_data) > 200:  # 一年交易240天左右，>200天算完整
            year_ret = year_data.iloc[-1] / year_data.iloc[0] - 1
            complete_years.append(year_ret)

    if len(complete_years) >= 2:
        win_rate = f"{int(sum(1 for r in complete_years if r > 0))}/{len(complete_years)}"
    else:
        win_rate = "N/A"

    # 滚动3年年化收益
    rolling3 = ((monthly / monthly.shift(36)) ** (1 / 3) - 1).dropna() if len(monthly) > 36 else pd.Series(dtype=float)
    rolling3_median = float(rolling3.median()) if len(rolling3) > 0 else float("nan")

    return {
        "sufficient": True,
        "start_date": str(start_date.date()),
        "end_date": str(end_date.date()),
        "data_points": len(s),
        "cagr": cagr,
        "total_return": total_return,
        "max_drawdown": mdd,
        "monthly_vol": monthly_vol,
        "return_over_vol": efficiency,
        "annual_win_rate": win_rate,
        "rolling3_median": rolling3_median,
        "complete_years": len(complete_years),
    }


# ========== 跟踪偏离度 ==========

def load_index_nav(index_code: str) -> pd.Series:
    """加载指数全收益CSV。"""
    # 找匹配的文件
    for f in INDEX_CSV_DIR.glob(f"{index_code}_*_全收益.csv"):
        df = pd.read_csv(f, encoding="utf-8-sig")
        # 找日期列和价格列
        date_col = None
        price_col = None
        for col in df.columns:
            col_lower = col.lower()
            if "date" in col_lower or "日期" in col:
                date_col = col
            if "close" in col_lower or "收盘" in col or "value" in col_lower:
                price_col = col
        if date_col and price_col:
            df[date_col] = pd.to_datetime(df[date_col])
            s = df.set_index(date_col)[price_col]
            return s.sort_index()
    return pd.Series(dtype=float)


def tracking_error(fund_nav: pd.Series, index_nav: pd.Series) -> dict:
    """计算基金相对跟踪指数的偏离度。"""
    # 对齐日期
    common = fund_nav.index.intersection(index_nav.index)
    if len(common) < 30:
        return {"sufficient": False}

    f = fund_nav.loc[common].sort_index()
    idx = index_nav.loc[common].sort_index()

    # 归一化到同一起点
    f_norm = f / f.iloc[0]
    idx_norm = idx / idx.iloc[0]

    # 累计偏离 = 基金累计收益 - 指数累计收益
    diff = (f_norm - 1) - (idx_norm - 1)

    # 年化跟踪误差（日收益差的标准差 * sqrt(252)）
    f_ret = f.pct_change().dropna()
    idx_ret = idx.pct_change().dropna()
    common_ret = f_ret.index.intersection(idx_ret.index)
    if len(common_ret) > 20:
        diff_ret = f_ret.loc[common_ret] - idx_ret.loc[common_ret]
        te_annual = float(diff_ret.std() * math.sqrt(252))
    else:
        te_annual = float("nan")

    # 总偏离（期末累计收益差）
    total_f = f_norm.iloc[-1] - 1
    total_idx = idx_norm.iloc[-1] - 1
    total_diff = total_f - total_idx

    # 偏离序列
    diff_series = diff

    return {
        "sufficient": True,
        "data_points": len(common),
        "tracking_error_annual": te_annual,
        "total_excess_return": total_diff,
        "fund_total_return": total_f,
        "index_total_return": total_idx,
        "diff_series": diff_series,
        "fund_norm": f_norm,
        "index_norm": idx_norm,
    }


# ========== 评分 ==========

def score_funds(metrics_list: list[dict], use_stability: bool = True) -> list[dict]:
    """相对排名制评分，返回带得分的列表。
    use_stability=False时只用三个维度（收益/风险/效率），权重分别为50/30/20。
    """
    df = pd.DataFrame(metrics_list)
    df = df[df["sufficient"]].copy()
    if len(df) == 0:
        return []

    df["score_return"] = df["cagr"].rank(pct=True) * 100
    df["score_risk"] = df["max_drawdown"].rank(pct=True) * 100
    df["score_efficiency"] = df["return_over_vol"].rank(pct=True) * 100

    if use_stability:
        def parse_win_rate(wr: str) -> float:
            if wr == "N/A" or not wr:
                return float("nan")
            parts = wr.split("/")
            if len(parts) == 2:
                try:
                    return int(parts[0]) / int(parts[1])
                except:
                    return float("nan")
            return float("nan")

        df["win_rate_num"] = df["annual_win_rate"].apply(parse_win_rate)
        df["score_stability"] = (
            df["win_rate_num"].rank(pct=True) * 50
            + df["rolling3_median"].rank(pct=True) * 50
        )
        df["total_score"] = (
            df["score_return"] * WEIGHTS["return"]
            + df["score_risk"] * WEIGHTS["risk"]
            + df["score_efficiency"] * WEIGHTS["efficiency"]
            + df["score_stability"] * WEIGHTS["stability"]
        )
    else:
        # 三维度：收益50%、风险30%、效率20%
        df["total_score"] = (
            df["score_return"] * 0.50
            + df["score_risk"] * 0.30
            + df["score_efficiency"] * 0.20
        )

    df = df.sort_values("total_score", ascending=False).reset_index(drop=True)
    df["rank"] = range(1, len(df) + 1)

    return df.to_dict("records")


# ========== 图表 ==========

def chart_colors(n: int) -> list[str]:
    """生成n种不同颜色。"""
    cmap = plt.cm.tab20
    return [cmap(i % 20) for i in range(n)]


def generate_tracking_chart(fund_code: str, fund_name: str, te_data: dict) -> str:
    """生成跟踪偏离度折线图，返回文件路径。"""
    if not te_data.get("sufficient"):
        return ""

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    diff = te_data["diff_series"] * 100  # 转百分比

    ax.plot(diff.index, diff.values, color="#2563eb", linewidth=1.0, label="累计偏离")
    ax.axhline(y=0, color="#999", linestyle="--", linewidth=0.8)

    ax.set_title(f"{fund_name}（{fund_code}）跟踪偏离度", fontsize=13, pad=12)
    ax.set_ylabel("累计偏离（%）", fontsize=11)
    ax.legend(loc="upper left", fontsize=10)
    ax.grid(True, alpha=0.3)

    # 标注期末偏离
    final_diff = diff.iloc[-1]
    ax.annotate(f"期末：{final_diff:+.2f}%",
                xy=(diff.index[-1], final_diff),
                xytext=(-10, 15), textcoords="offset points",
                fontsize=9,
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#ccc", alpha=0.9))

    plt.tight_layout()
    fname = f"跟踪偏离_{fund_code}.png"
    fpath = CHART_DIR / fname
    fig.savefig(fpath, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return str(fpath)


def generate_vs_benchmark_chart(fund_code: str, fund_name: str, fund_nav: pd.Series,
                                 bench_code: str, bench_name: str, bench_nav: pd.Series) -> str:
    """生成基金与基准的行情对比图，返回文件路径。"""
    common = fund_nav.index.intersection(bench_nav.index)
    if len(common) < 30:
        return ""

    f = fund_nav.loc[common].sort_index()
    b = bench_nav.loc[common].sort_index()

    f_norm = f / f.iloc[0] * 100
    b_norm = b / b.iloc[0] * 100

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    ax.plot(b_norm.index, b_norm.values, color="#999", linewidth=0.8, linestyle="--",
            label=f"{bench_name}（{bench_code}）基准 +{(b_norm.iloc[-1]-100):.2f}%")
    ax.plot(f_norm.index, f_norm.values, color="#dc2626", linewidth=1.0,
            label=f"{fund_name}（{fund_code}） +{(f_norm.iloc[-1]-100):.2f}%")

    ax.set_title(f"{fund_name} vs {bench_name}（归一化=100）", fontsize=13, pad=12)
    ax.set_ylabel("归一化净值", fontsize=11)
    ax.legend(loc="upper left", fontsize=10)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fname = f"对比基准_{fund_code}.png"
    fpath = CHART_DIR / fname
    fig.savefig(fpath, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return str(fpath)


def generate_group_chart(scored: list[dict], fund_navs: dict[str, pd.Series],
                        start_date: pd.Timestamp, end_date: pd.Timestamp, group_name: str) -> str:
    """组内所有基金归一化对比的总图。"""
    if not scored:
        return ""

    fig, ax = plt.subplots(figsize=(12, 7.5))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    # 找共同日期
    all_dates = None
    for s in scored:
        code = s["fund_code"]
        if code in fund_navs:
            nav = fund_navs[code].loc[start_date:end_date]
            all_dates = nav.index if all_dates is None else all_dates.intersection(nav.index)

    if all_dates is None or len(all_dates) < 30:
        return ""

    # 按收益从低到高画（低的在下层）
    navs_to_plot = []
    for s in scored:
        code = s["fund_code"]
        if code not in fund_navs:
            continue
        nav = fund_navs[code].loc[all_dates]
        norm = nav / nav.iloc[0] * 100
        ret = norm.iloc[-1] - 100
        navs_to_plot.append((s, norm, ret))

    # 画图顺序：收益低的先画（在下层），颜色从后往前取
    navs_to_plot.sort(key=lambda x: x[2])
    colors = chart_colors(len(navs_to_plot))

    # 收集图例项（按收益从高到低排）
    legend_items = []
    for i, (s, norm, ret) in enumerate(navs_to_plot):
        code = s["fund_code"]
        short = s.get("short_name", code)
        is_bench = code == BENCHMARK_CODE
        if is_bench:
            line, = ax.plot(norm.index, norm.values, color="#999", linewidth=1.8, linestyle="--", zorder=10)
            legend_items.append((999, line, f"{short}（基准） +{ret:.2f}%"))
        else:
            line, = ax.plot(norm.index, norm.values, color=colors[i], linewidth=0.9)
            legend_items.append((ret, line, f"{short} +{ret:.2f}%"))

    # 图例按收益从高到低排序（基准始终在最上面）
    legend_items.sort(key=lambda x: -x[0])
    legend_handles = [item[1] for item in legend_items]
    legend_labels = [item[2] for item in legend_items]

    ax.legend(legend_handles, legend_labels, loc="upper left", fontsize=9, ncol=2, framealpha=0.9)
    ax.set_title(f"红利类基金对比 - {group_name}（归一化=100）", fontsize=14, pad=12)
    ax.set_ylabel("归一化净值", fontsize=11)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fname = f"组内对比_{group_name}.png"
    fpath = CHART_DIR / fname
    fig.savefig(fpath, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return str(fpath)


def generate_all_in_one_chart(scored: list[dict], fund_navs: dict[str, pd.Series]) -> str:
    if not scored:
        return ""

    fig, ax = plt.subplots(figsize=(12, 7.5))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    # 找出共同日期区间
    all_dates = None
    for s in scored:
        code = s["fund_code"]
        if code in fund_navs:
            dates = fund_navs[code].index
            all_dates = dates if all_dates is None else all_dates.intersection(dates)

    if all_dates is None or len(all_dates) < 30:
        return ""

    # 按收益排序画（收益低的先画在下层）
    sorted_by_return = sorted(scored, key=lambda x: x.get("total_return", 0))
    colors = chart_colors(len(sorted_by_return))

    bench_data = None
    for i, s in enumerate(sorted_by_return):
        code = s["fund_code"]
        if code not in fund_navs:
            continue
        nav = fund_navs[code].loc[all_dates]
        norm = nav / nav.iloc[0] * 100
        ret = norm.iloc[-1] - 100

        if code == BENCHMARK_CODE:
            bench_data = norm
            ax.plot(norm.index, norm.values, color="#999", linewidth=1.5, linestyle="--",
                    label=f"{s['short_name']} 基准 +{ret:.2f}%", zorder=10)
        else:
            short = s.get("short_name", s["fund_name"][:8])
            ax.plot(norm.index, norm.values, color=colors[i], linewidth=0.8,
                    label=f"{short} +{ret:.2f}%")

    ax.set_title("红利类基金5年累计收益对比（归一化=100）", fontsize=14, pad=12)
    ax.set_ylabel("归一化净值", fontsize=11)
    ax.legend(loc="upper left", fontsize=8, ncol=2, framealpha=0.9)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fpath = CHART_DIR / "全部基金5年对比.png"
    fig.savefig(fpath, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return str(fpath)


# ========== 主流程 ==========

def load_fund_nav(fund_code: str) -> pd.Series:
    """加载基金分红再投净值CSV（正确口径）。"""
    for f in NAV_DIR.glob(f"{fund_code}_*_净值.csv"):
        df = pd.read_csv(f, parse_dates=["date"], index_col="date", encoding="utf-8-sig")
        if "reinvested_nav" in df.columns:
            s = df["reinvested_nav"].astype(float)
        else:
            s = df.iloc[:, 0]
        return s.sort_index()
    return pd.Series(dtype=float)


def main() -> None:
    # 1. 加载基金清单（从一期ETF可投资性数据中读取）
    # 先假设净值数据目录下有的就是候选
    fund_list = []
    for f in NAV_DIR.glob("*_净值.csv"):
        code = f.stem.replace("_净值", "")
        # 如果有汇总JSON，用那个
        pass

    # 直接从汇总文件读
    summary_path = NAV_DIR / "_汇总_基金净值.json"
    print(f"summary_path: {summary_path}")
    print(f"exists: {summary_path.exists()}")
    if summary_path.exists():
        with open(summary_path, encoding="utf-8") as f:
            summary = json.load(f)
        fund_list = summary
    else:
        # 扫描目录
        for f in NAV_DIR.glob("*_净值.csv"):
            code = f.stem.split("_")[0]
            fund_list.append({"fund_code": code, "fund_name": code})

    print(f"加载基金: {len(fund_list)}只")

    # 2. 加载每只基金的净值，计算指标
    fund_navs = {}
    all_metrics = []
    for fund in fund_list:
        code = fund["fund_code"]
        name = fund.get("fund_name", code)
        nav = load_fund_nav(code)
        if len(nav) < 30:
            print(f"  {code} {name}: 数据不足，跳过")
            continue
        fund_navs[code] = nav

        m = calculate_metrics(nav)
        m["fund_code"] = code
        m["fund_name"] = name
        m["short_name"] = name.replace("交易型开放式指数证券投资基金", "ETF")[:12]
        all_metrics.append(m)

    print(f"有效基金: {len(all_metrics)}只")

    if not all_metrics:
        print("没有有效基金数据，退出")
        return

    # 2.5 分组：5年组（≥1200天）、2年组（480-1200天）、观察池（<480天）
    group_5y = [m for m in all_metrics if m.get("data_points", 0) >= 1200]
    group_2y = [m for m in all_metrics if 480 <= m.get("data_points", 0) < 1200]
    obs_pool = [m for m in all_metrics if m.get("data_points", 0) < 480]

    print(f"\n5年组（≥5年）: {len(group_5y)}只")
    print(f"2年组（2-5年）: {len(group_2y)}只")
    print(f"观察池（<2年）: {len(obs_pool)}只")

    # 加载基准净值
    bench_nav = fund_navs.get(BENCHMARK_CODE, pd.Series(dtype=float))
    if len(bench_nav) == 0:
        print("基准基金数据缺失，退出")
        return

    # 基金代码 -> 指数代码
    index_map = {}
    for fund in fund_list:
        if "index_code" in fund:
            index_map[fund["fund_code"]] = fund["index_code"]

    all_results = {}
    te_results = {}

    for group_name, group_data in [("5年组", group_5y), ("2年组", group_2y)]:
        if not group_data:
            continue

        # 统一区间：5年组用5年区间，2年组用2年区间
        if group_name == "5年组":
            common_start, common_end = FIVE_YEAR_START, FIVE_YEAR_END
        else:
            common_start, common_end = TWO_YEAR_START, TWO_YEAR_END

        print(f"\n=== {group_name} ===")
        print(f"  统一区间: {common_start.date()} ~ {common_end.date()}")

        # 截取统一区间重新计算指标，数据不够的跳过
        group_metrics = []
        for m in group_data:
            code = m["fund_code"]
            nav = fund_navs.get(code)
            if nav is None or len(nav) == 0:
                continue
            nav_clip = nav.loc[common_start:common_end]
            if len(nav_clip) < 100:
                print(f"  {code} {m['fund_name']}: 区间数据不足({len(nav_clip)}天)，跳过")
                continue
            new_m = calculate_metrics(nav_clip)
            new_m["fund_code"] = code
            new_m["fund_name"] = m["fund_name"]
            new_m["short_name"] = simplify_name(m["fund_name"])
            new_m["index_code"] = index_map.get(code, "")
            group_metrics.append(new_m)

        # 基准在共同区间的指标
        bench_clip = bench_nav.loc[common_start:common_end]
        bench_m = calculate_metrics(bench_clip)
        bench_m["fund_code"] = BENCHMARK_CODE
        bench_m["fund_name"] = BENCHMARK_NAME
        bench_m["short_name"] = "华泰柏瑞红利低波"
        bench_m["index_code"] = index_map.get(BENCHMARK_CODE, "H30269")

        # 基准也加入评分（用来确定百分位锚点）
        # 先检查基准是否已在列表中
        has_bench = any(m["fund_code"] == BENCHMARK_CODE for m in group_metrics)
        all_for_scoring = group_metrics if has_bench else group_metrics + [bench_m]
        use_stab = group_name == "5年组"
        scored = score_funds(all_for_scoring, use_stability=use_stab)

        # 找基准得分
        bench_score = None
        for s in scored:
            if s["fund_code"] == BENCHMARK_CODE:
                bench_score = s
                break

        # 分档
        if bench_score:
            bench_total = bench_score["total_score"]
            for s in scored:
                diff = s["total_score"] - bench_total
                if s["fund_code"] == BENCHMARK_CODE:
                    s["tier"] = "基准"
                elif diff >= 3:
                    s["tier"] = "第一梯队（显著更优）"
                elif diff >= -3:
                    s["tier"] = "第二梯队（接近基准）"
                else:
                    s["tier"] = "第三梯队（落后较多）"
                s["score_vs_benchmark"] = diff

        print(f"  排名（基准得分: {bench_score['total_score']:.1f}）:")
        for s in scored:
            marker = "★" if s["fund_code"] == BENCHMARK_CODE else " "
            print(f"    {marker} {s.get('rank', 0):>2}. {s['short_name']:<14} {s['total_score']:.1f}  CAGR:{s['cagr']:.2%}  MDD:{s['max_drawdown']:.2%}  {s.get('tier','')}")

        # 跟踪误差 + 图表
        for s in scored:
            code = s["fund_code"]
            idx_code = s.get("index_code", "")
            if idx_code and code in fund_navs:
                idx_nav = load_index_nav(idx_code)
                if len(idx_nav) >= 30:
                    # 截取相同区间
                    common_idx = fund_navs[code].index.intersection(idx_nav.index)
                    common_idx = common_idx[(common_idx >= common_start) & (common_idx <= common_end)]
                    if len(common_idx) > 30:
                        te = tracking_error(fund_navs[code].loc[common_idx], idx_nav.loc[common_idx])
                        te_results[code] = te
                        generate_tracking_chart(code, s["short_name"], te)

            # 与基准对比图
            if code != BENCHMARK_CODE and len(bench_clip) > 30 and code in fund_navs:
                f_nav = fund_navs[code].loc[common_start:common_end]
                generate_vs_benchmark_chart(
                    code, s["short_name"], f_nav,
                    BENCHMARK_CODE, bench_m["short_name"], bench_clip
                )

        # 组内总图
        generate_group_chart(scored, fund_navs, common_start, common_end, group_name)

        all_results[group_name] = scored

    # 保存
    output_all = {}
    for gname, scored in all_results.items():
        group_data = []
        for s in scored:
            code = s["fund_code"]
            te = te_results.get(code, {})
            row = {
                "rank": s.get("rank", 0),
                "fund_code": code,
                "fund_name": s["fund_name"],
                "short_name": s.get("short_name", ""),
                "tier": s.get("tier", ""),
                "total_score": round(s["total_score"], 2),
                "score_vs_benchmark": round(s.get("score_vs_benchmark", float("nan")), 2) if s.get("score_vs_benchmark") is not None else None,
                "cagr_pct": round(s["cagr"] * 100, 2) if not np.isnan(s.get("cagr", float("nan"))) else None,
                "total_return_pct": round(s["total_return"] * 100, 2) if s.get("total_return") is not None else None,
                "max_drawdown_pct": round(s["max_drawdown"] * 100, 2) if s.get("max_drawdown") is not None else None,
                "monthly_vol_pct": round(s.get("monthly_vol", float("nan")) * 100, 2) if s.get("monthly_vol") else None,
                "return_over_vol": round(s["return_over_vol"], 4) if s.get("return_over_vol") else None,
                "annual_win_rate": s.get("annual_win_rate", "N/A"),
                "rolling3_median_pct": round(s["rolling3_median"] * 100, 2) if s.get("rolling3_median") is not None and not np.isnan(s.get("rolling3_median", float("nan"))) else None,
                "tracking_error_annual_pct": round(te.get("tracking_error_annual", float("nan")) * 100, 2) if te.get("tracking_error_annual") else None,
                "excess_return_pct": round(te.get("total_excess_return", float("nan")) * 100, 2) if "total_excess_return" in te else None,
                "data_points": s.get("data_points", 0),
            }
            group_data.append(row)
        output_all[gname] = group_data

    # 观察池
    obs_data = []
    for m in obs_pool:
        code = m["fund_code"]
        obs_data.append({
            "fund_code": code,
            "fund_name": m["fund_name"],
            "short_name": simplify_name(m["fund_name"]),
            "data_points": m.get("data_points", 0),
            "cagr_pct": round(m["cagr"] * 100, 2) if m.get("sufficient") and not np.isnan(m.get("cagr", float("nan"))) else None,
            "total_return_pct": round(m["total_return"] * 100, 2) if m.get("sufficient") else None,
            "max_drawdown_pct": round(m["max_drawdown"] * 100, 2) if m.get("sufficient") else None,
        })
    output_all["观察池"] = obs_data

    with open(OUTPUT_DIR / "基金对比_指标及排名.json", "w", encoding="utf-8") as f:
        json.dump(output_all, f, ensure_ascii=False, indent=2)

    print(f"\n✓ 数据已保存: {OUTPUT_DIR / '基金对比_指标及排名.json'}")
    print(f"✓ 图表目录: {CHART_DIR}")


if __name__ == "__main__":
    main()
