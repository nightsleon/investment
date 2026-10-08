#!/usr/bin/env python3
"""指数行情回溯指标计算脚本模板。

用法:
    python calculate_metrics.py --data-dir ./data --start 20160810 --end 20260810

输入 CSV 格式（中证官网 JSON 导出）:
    交易日期,收盘点位
    2016-08-10,3456.7890
    ...

输出:
    - 收益风险汇总.csv
    - 稳定性指标.csv
    - 年度收益.csv
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class SeriesConfig:
    name: str
    filename: str
    date_col: str = "交易日期"
    value_col: str = "收盘点位"
    source_type: str = "官网全收益指数"
    launch_date: str | None = None  # 正式发布日期，用于标注回溯


def load_series(config: SeriesConfig, data_dir: Path, start: pd.Timestamp, end: pd.Timestamp) -> pd.Series:
    frame = pd.read_csv(data_dir / config.filename)
    frame[config.date_col] = pd.to_datetime(frame[config.date_col].astype(str), format="mixed")
    frame = frame.sort_values(config.date_col).drop_duplicates(config.date_col, keep="last")
    series = frame.set_index(config.date_col)[config.value_col].astype(float)
    series = series.loc[start:end]
    if series.index[0] != start or series.index[-1] != end:
        raise RuntimeError(f"{config.name} 区间异常：{series.index[0]} ~ {series.index[-1]}")
    if not series.index.is_monotonic_increasing or series.isna().any() or (series <= 0).any():
        raise RuntimeError(f"{config.name} 序列质量异常")
    return series


def annualized_return(start_value: float, end_value: float, start: pd.Timestamp, end: pd.Timestamp) -> float:
    return (end_value / start_value) ** (365.2425 / (end - start).days) - 1


def max_drawdown(series: pd.Series) -> tuple[float, pd.Timestamp, pd.Timestamp, str | None]:
    running_max = series.cummax()
    drawdown = series / running_max - 1
    trough = cast(pd.Timestamp, drawdown.idxmin())
    peak = cast(pd.Timestamp, series.loc[:trough].idxmax())
    recovered = series.loc[trough:][series.loc[trough:] >= series.loc[peak]]
    recovery = recovered.index[0].date().isoformat() if len(recovered) else None
    return float(drawdown.loc[trough]), peak, trough, recovery


def pct(value: float) -> str:
    return f"{value:.4%}"


def calc_one(config: SeriesConfig, data_dir: Path, start: pd.Timestamp, end: pd.Timestamp) -> dict:
    series = load_series(config, data_dir, start, end)
    daily_returns = series.pct_change().dropna()
    monthly = series.resample("ME").last()
    monthly_returns = monthly.pct_change().dropna()
    start_date = cast(pd.Timestamp, series.index[0])
    end_date = cast(pd.Timestamp, series.index[-1])
    cagr = annualized_return(series.iloc[0], series.iloc[-1], start_date, end_date)
    daily_vol = daily_returns.std(ddof=1) * np.sqrt(252)
    monthly_vol = monthly_returns.std(ddof=1) * np.sqrt(12)
    max_dd, peak, trough, recovery = max_drawdown(series)

    # 年度收益
    year_end = series.resample("YE").last()
    annual = year_end.pct_change()
    start_year = start_date.year + 1
    end_year = end_date.year - 1
    complete = annual[(annual.index.year >= start_year) & (annual.index.year <= end_year)]

    # 滚动收益
    rolling3 = ((monthly / monthly.shift(36)) ** (1 / 3) - 1).dropna()
    rolling5 = ((monthly / monthly.shift(60)) ** (1 / 5) - 1).dropna()

    # 回溯占比
    backtest_ratio = ""
    if config.launch_date:
        launch = pd.Timestamp(config.launch_date)
        if launch > start_date:
            backtest_days = (launch - start_date).days
            total_days = (end_date - start_date).days
            backtest_ratio = f"{backtest_days / total_days:.1%}"

    return {
        "指数": config.name,
        "数据口径": config.source_type,
        "回溯占比": backtest_ratio,
        "交易日数": len(series),
        "期初日期": start_date.date().isoformat(),
        "期末日期": end_date.date().isoformat(),
        "累计收益": pct(series.iloc[-1] / series.iloc[0] - 1),
        "精确年化收益": pct(cagr),
        "日频年化波动": pct(daily_vol),
        "月频年化波动": pct(monthly_vol),
        "最大回撤": pct(max_dd),
        "回撤高点日期": peak.date().isoformat(),
        "回撤低点日期": trough.date().isoformat(),
        "修复日期": recovery or "区间末尚未修复",
        "收益/月频波动": f"{cagr / monthly_vol:.4f}",
        "完整年度正收益": f"{int((complete > 0).sum())}/{len(complete)}",
        "最差年度": pct(float(complete.min())) if len(complete) else "N/A",
        "最差年度年份": int(complete.idxmin().year) if len(complete) else "N/A",
        "滚动3年样本数": len(rolling3),
        "滚动3年正收益占比": pct(float((rolling3 > 0).mean())) if len(rolling3) else "N/A",
        "滚动3年年化中位数": pct(float(rolling3.median())) if len(rolling3) else "N/A",
        "滚动3年年化最低值": pct(float(rolling3.min())) if len(rolling3) else "N/A",
        "滚动5年样本数": len(rolling5),
        "滚动5年正收益占比": pct(float((rolling5 > 0).mean())) if len(rolling5) else "N/A",
        "滚动5年年化中位数": pct(float(rolling5.median())) if len(rolling5) else "N/A",
        "滚动5年年化最低值": pct(float(rolling5.min())) if len(rolling5) else "N/A",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="指数行情回溯指标计算")
    parser.add_argument("--data-dir", required=True, help="CSV 数据目录")
    parser.add_argument("--start", required=True, help="开始日期 YYYYMMDD")
    parser.add_argument("--end", required=True, help="结束日期 YYYYMMDD")
    parser.add_argument("--output-dir", default=".", help="输出目录")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    start = pd.Timestamp(args.start)
    end = pd.Timestamp(args.end)

    # ========== 在这里配置要分析的指数 ==========
    series_list: list[SeriesConfig] = [
        # 示例：
        # SeriesConfig("中证红利", "000922_中证红利_全收益.csv"),
        # SeriesConfig("中证红利低波动", "H30269_中证红利低波动_全收益.csv"),
    ]
    # ============================================

    if not series_list:
        print("请在脚本中配置 series_list。")
        return

    rows = []
    annual_data: dict[int, dict[str, float]] = {}
    for config in series_list:
        row = calc_one(config, data_dir, start, end)
        rows.append(row)

        # 收集年度收益
        series = load_series(config, data_dir, start, end)
        year_end = series.resample("YE").last()
        annual = year_end.pct_change()
        start_year = start.year + 1
        end_year = end.year - 1
        complete = annual[(annual.index.year >= start_year) & (annual.index.year <= end_year)]
        for ts, val in complete.items():
            year = int(ts.year)
            if year not in annual_data:
                annual_data[year] = {}
            annual_data[year][config.name] = float(val)

    summary_df = pd.DataFrame(rows)
    summary_df.to_csv(output_dir / "收益风险汇总.csv", index=False, encoding="utf-8-sig")

    annual_df = pd.DataFrame.from_dict(annual_data, orient="index")
    annual_df.index.name = "年度"
    annual_df.to_csv(output_dir / "年度收益.csv", encoding="utf-8-sig", float_format="%.6f")

    print(summary_df[["指数", "精确年化收益", "月频年化波动", "最大回撤", "收益/月频波动"]].to_string(index=False))
    print()
    print(annual_df.to_string())


if __name__ == "__main__":
    main()
