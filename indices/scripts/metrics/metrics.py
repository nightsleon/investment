#!/usr/bin/env python3
"""指数与基金量化评估公共算法库 (Common Quantitative Metrics Library).

提供全市场红利ETF与指数评估的核心指标计算：
- 分红再投财富指数构建 (Reinvested NAV Wealth Index)
- 复合年化收益率 (CAGR)
- 历史最大回撤及区间 (Max Drawdown, Peak, Trough)
- 年化下行标准差 (Annualized Downside Deviation, 纯亏损波动率)
- 卡玛比率 (Calmar Ratio = CAGR / |Max DD|)
- 分年度收益率与胜率 (Calendar Year Returns & Annual Win Rate)
- 基金1对1公共区间对决对比表生成 (Head-to-Head Comparison Matrix)
"""
from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

SOURCES_DIR = Path(__file__).resolve().parents[2] / "sources"
FUND_NAV_DIR = SOURCES_DIR / "fund-nav-correct"


@dataclass
class PerformanceSummary:
    code: str
    name: str
    start_date: str
    end_date: str
    total_days: int
    trading_days: int
    total_return_pct: float
    cagr_pct: float
    max_drawdown_pct: float
    max_drawdown_peak: str
    max_drawdown_trough: str
    downside_vol_pct: float
    calmar_ratio: float
    annual_returns: Dict[int, float]


def load_fund_reinvested_nav(csv_path: Path) -> Dict[date, float]:
    """从 fund-nav-correct CSV 文件中加载 (日期 -> 分红再投净值) 映射表。"""
    nav_map: Dict[date, float] = {}
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            d_str = row.get("date") or row.get("FSRQ")
            if not d_str:
                continue
            d = datetime.strptime(d_str.strip(), "%Y-%m-%d").date()
            val_str = row.get("reinvested_nav") or row.get("nav_reinvested") or row.get("DWJZ")
            if val_str:
                try:
                    nav_map[d] = float(val_str)
                except ValueError:
                    continue
    return dict(sorted(nav_map.items()))


def calculate_cagr(start_val: float, end_val: float, calendar_days: int) -> float:
    """计算复合年化增长率 (CAGR, 单位: 百分比)."""
    if calendar_days <= 0 or start_val <= 0:
        return 0.0
    years = calendar_days / 365.25
    if years <= 0:
        return 0.0
    return ((end_val / start_val) ** (1.0 / years) - 1.0) * 100.0


def calculate_max_drawdown(nav_series: List[Tuple[date, float]]) -> Tuple[float, date, date]:
    """计算时间序列的最大回撤 (百分比, 负数) 以及高点日期和低点日期。

    返回: (max_dd_pct, peak_date, trough_date)
    """
    if not nav_series:
        return 0.0, date.min, date.min

    peak = nav_series[0][1]
    peak_date = nav_series[0][0]
    max_dd = 0.0
    best_peak_date = peak_date
    trough_date = peak_date

    current_peak_date = peak_date
    for d, val in nav_series:
        if val > peak:
            peak = val
            current_peak_date = d
        else:
            dd = (val - peak) / peak
            if dd < max_dd:
                max_dd = dd
                best_peak_date = current_peak_date
                trough_date = d

    return max_dd * 100.0, best_peak_date, trough_date


def calculate_downside_deviation(
    nav_series: List[Tuple[date, float]],
    target: float = 0.0,
    annualization_factor: float = 242.0,
) -> float:
    """计算年化下行标准差 (单位: 百分比).

    仅统计日收益率低于目标 (默认 0.0) 的离差平方，衡量真实下行风险，不惩罚上涨。
    公式: sqrt( sum(min(r_t - target, 0)^2) / N ) * sqrt(242) * 100
    """
    if len(nav_series) < 2:
        return 0.0

    negative_diff_sq_sum = 0.0
    n = len(nav_series) - 1

    for i in range(1, len(nav_series)):
        prev = nav_series[i - 1][1]
        curr = nav_series[i][1]
        if prev <= 0:
            continue
        r = (curr - prev) / prev
        diff = r - target
        if diff < 0:
            negative_diff_sq_sum += diff * diff

    daily_downside_std = math.sqrt(negative_diff_sq_sum / n)
    return daily_downside_std * math.sqrt(annualization_factor) * 100.0


def calculate_calmar_ratio(cagr_pct: float, max_drawdown_pct: float) -> float:
    """计算卡玛比率 (Calmar Ratio = CAGR / |Max DD|)."""
    abs_dd = abs(max_drawdown_pct)
    if abs_dd < 1e-6:
        return 0.0
    return round(cagr_pct / abs_dd, 2)


def calculate_calendar_year_returns(nav_series: List[Tuple[date, float]]) -> Dict[int, float]:
    """计算自然年度收益率 (单位: 百分比)."""
    if not nav_series:
        return {}

    years: Dict[int, List[Tuple[date, float]]] = {}
    for d, val in nav_series:
        years.setdefault(d.year, []).append((d, val))

    sorted_years = sorted(years.keys())
    annual_rets: Dict[int, float] = {}

    for i, yr in enumerate(sorted_years):
        yr_data = years[yr]
        if i == 0:
            start_val = yr_data[0][1]
        else:
            prev_yr = sorted_years[i - 1]
            start_val = years[prev_yr][-1][1]
        end_val = yr_data[-1][1]
        ret = ((end_val - start_val) / start_val) * 100.0
        annual_rets[yr] = round(ret, 2)

    return annual_rets


def evaluate_series(
    code: str,
    name: str,
    nav_series: List[Tuple[date, float]],
) -> PerformanceSummary:
    """评估单只基金或指数全时间序列的完整表现。"""
    if not nav_series:
        raise ValueError(f"序列为空: {code} {name}")

    start_date = nav_series[0][0]
    end_date = nav_series[-1][0]
    start_val = nav_series[0][1]
    end_val = nav_series[-1][1]
    calendar_days = (end_date - start_date).days

    total_return_pct = ((end_val - start_val) / start_val) * 100.0
    cagr_pct = calculate_cagr(start_val, end_val, calendar_days)
    max_dd_pct, peak_d, trough_d = calculate_max_drawdown(nav_series)
    downside_vol_pct = calculate_downside_deviation(nav_series)
    calmar = calculate_calmar_ratio(cagr_pct, max_dd_pct)
    annual_rets = calculate_calendar_year_returns(nav_series)

    return PerformanceSummary(
        code=code,
        name=name,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        total_days=calendar_days,
        trading_days=len(nav_series),
        total_return_pct=round(total_return_pct, 2),
        cagr_pct=round(cagr_pct, 2),
        max_drawdown_pct=round(max_dd_pct, 2),
        max_drawdown_peak=peak_d.isoformat(),
        max_drawdown_trough=trough_d.isoformat(),
        downside_vol_pct=round(downside_vol_pct, 2),
        calmar_ratio=calmar,
        annual_returns=annual_rets,
    )


def compare_funds_common_period(
    nav_a: Dict[date, float],
    nav_b: Dict[date, float],
    info_a: Tuple[str, str],  # (code, name)
    info_b: Tuple[str, str],  # (code, name)
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Tuple[PerformanceSummary, PerformanceSummary]:
    """对齐两只基金的公共交易日区间，并计算双方标准化指标。"""
    common_dates = sorted(set(nav_a.keys()) & set(nav_b.keys()))
    if start_date:
        common_dates = [d for d in common_dates if d >= start_date]
    if end_date:
        common_dates = [d for d in common_dates if d <= end_date]

    if not common_dates:
        raise ValueError("无重叠交易日期")

    series_a = [(d, nav_a[d]) for d in common_dates]
    series_b = [(d, nav_b[d]) for d in common_dates]

    summary_a = evaluate_series(info_a[0], info_a[1], series_a)
    summary_b = evaluate_series(info_b[0], info_b[1], series_b)

    return summary_a, summary_b


def find_fund_file(code: str) -> Optional[Path]:
    matches = list(FUND_NAV_DIR.glob(f"{code}*.csv"))
    return matches[0] if matches else None


def format_comparison_table(s_a: PerformanceSummary, s_b: PerformanceSummary) -> str:
    lines = []
    lines.append("┌──────────────────────────┬─────────────────────────────┬─────────────────────────────┬─────────────────┐")
    lines.append(f"│ 核心指标 (公共区间)      │ {s_a.name[:10]:<12} ({s_a.code}) │ {s_b.name[:10]:<12} ({s_b.code}) │ 差异对比        │")
    lines.append("├──────────────────────────┼─────────────────────────────┼─────────────────────────────┼─────────────────┤")
    lines.append(f"│ 公共交易周期             │ {s_a.start_date} ~ {s_a.end_date}   │ {s_b.start_date} ~ {s_b.end_date}   │ {s_a.trading_days} 交易日     │")
    diff_ret = s_b.total_return_pct - s_a.total_return_pct
    lines.append(f"│ 累计复权回报 (分红再投)  │ +{s_a.total_return_pct:.2f}%{' ': <16} │ +{s_b.total_return_pct:.2f}%{' ': <16} │ {diff_ret:+.2f}%         │")
    diff_cagr = s_b.cagr_pct - s_a.cagr_pct
    lines.append(f"│ 年化复合增长率 (CAGR)    │ +{s_a.cagr_pct:.2f}%{' ': <17} │ +{s_b.cagr_pct:.2f}%{' ': <17} │ {diff_cagr:+.2f}%         │")
    diff_dd = s_b.max_drawdown_pct - s_a.max_drawdown_pct
    lines.append(f"│ 历史最大回撤             │ {s_a.max_drawdown_pct:.2f}%{' ': <18} │ {s_b.max_drawdown_pct:.2f}%{' ': <18} │ {diff_dd:+.2f}% (浅/深)   │")
    diff_vol = s_b.downside_vol_pct - s_a.downside_vol_pct
    lines.append(f"│ 年化下行标准差 (纯跌波)  │ {s_a.downside_vol_pct:.2f}%{' ': <18} │ {s_b.downside_vol_pct:.2f}%{' ': <18} │ {diff_vol:+.2f}%         │")
    lines.append(f"│ 卡玛比率 (CAGR/|回撤|)   │ {s_a.calmar_ratio:<24} │ {s_b.calmar_ratio:<24} │ {s_b.calmar_ratio - s_a.calmar_ratio:+.2f}           │")
    lines.append("└──────────────────────────┴─────────────────────────────┴─────────────────────────────┴─────────────────┘")

    lines.append("\n年度收益率对比:")
    all_years = sorted(set(s_a.annual_returns.keys()) & set(s_b.annual_returns.keys()))
    lines.append("年份\t" + f"{s_a.code}\t" + f"{s_b.code}\t" + "胜负")
    for yr in all_years:
        ra = s_a.annual_returns[yr]
        rb = s_b.annual_returns[yr]
        winner = f"{s_a.code} 胜" if ra > rb else (f"{s_b.code} 胜" if rb > ra else "平")
        lines.append(f"{yr}\t{ra:+.2f}%\t{rb:+.2f}%\t{winner} ({abs(rb-ra):.2f}%)")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3:
        c_a = sys.argv[1]
        c_b = sys.argv[2]
        f_a = find_fund_file(c_a)
        f_b = find_fund_file(c_b)
        if not f_a or not f_b:
            print(f"找不到基金文件: {c_a}={f_a}, {c_b}={f_b}")
            sys.exit(1)
        nav_a = load_fund_reinvested_nav(f_a)
        nav_b = load_fund_reinvested_nav(f_b)
        n_a = f_a.stem.split("_")[1] if "_" in f_a.stem else c_a
        n_b = f_b.stem.split("_")[1] if "_" in f_b.stem else c_b
        s_a, s_b = compare_funds_common_period(nav_a, nav_b, (c_a, n_a), (c_b, n_b))
        print(format_comparison_table(s_a, s_b))
    else:
        file_512890 = find_fund_file("512890")
        if file_512890:
            navs = load_fund_reinvested_nav(file_512890)
            summary = evaluate_series("512890", "红利低波ETF", list(navs.items()))
            print(f"自测成功: {summary.name} ({summary.code})")
            print(f"  区间: {summary.start_date} ~ {summary.end_date} ({summary.trading_days} 交易日)")
            print(f"  累计回报: +{summary.total_return_pct}%")
            print(f"  CAGR: +{summary.cagr_pct}%")
            print(f"  最大回撤: {summary.max_drawdown_pct}% (高点: {summary.max_drawdown_peak}, 低点: {summary.max_drawdown_trough})")
            print(f"  下行标准差: {summary.downside_vol_pct}%")
            print(f"  卡玛比率: {summary.calmar_ratio}")
            print(f"  年度收益: {summary.annual_returns}")
