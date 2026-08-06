#!/usr/bin/env python3
"""统一复算A股红利指数长期风险收益与稳定性指标。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import cast

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
PERF = BASE / "sources" / "performance-data"
START = pd.Timestamp("2016-06-30")
END = pd.Timestamp("2026-07-31")


@dataclass(frozen=True)
class SeriesConfig:
    name: str
    filename: str
    date_col: str = "交易日期"
    value_col: str = "收盘点位"
    source_type: str = "官网全收益指数"


SERIES = (
    SeriesConfig("标普中国A股大盘红利低波50", "SPDJI_标普中国A股大盘红利低波50_CNY_TR_2016-06-30_2026-07-31.csv"),
    SeriesConfig("标普中国A股红利机会", "SPDJI_标普中国A股红利机会_CNY_TR_2016-06-30_2026-07-31.csv"),
    SeriesConfig("中证红利低波动", "H30269_中证红利低波动_全收益_2016-06-30_2026-07-31.csv"),
    SeriesConfig("中证红利", "000922_中证红利_全收益_2016-06-30_2026-07-31.csv"),
    SeriesConfig("中证红利低波动100", "930955_中证红利低波动100_全收益_2016-06-30_2026-07-31.csv"),
    SeriesConfig("中证全指红利质量", "932315_中证全指红利质量_全收益_2016-06-30_2026-07-31.csv"),
    SeriesConfig("中证红利质量", "931468_中证红利质量_全收益_2016-06-30_2026-07-31.csv"),
    SeriesConfig("上证红利", "000015_上证红利_全收益_2016-06-30_2026-07-31.csv"),
    SeriesConfig("中证沪港深红利成长低波动", "931157_沪港深红利成长低波动_全收益_2016-06-30_2026-07-31.csv"),
    SeriesConfig(
        "深证红利（159905复权净值代理）",
        "399324_深证红利_159905复权净值代理_2016-06-30_2026-07-31.csv",
        value_col="复权单位净值",
        source_type="跟踪ETF复权净值代理（已扣费，非官方全收益指数）",
    ),
)


def load_series(config: SeriesConfig) -> pd.Series:
    frame = pd.read_csv(PERF / config.filename)
    frame[config.date_col] = pd.to_datetime(frame[config.date_col].astype(str), format="mixed")
    frame = frame.sort_values(config.date_col).drop_duplicates(config.date_col, keep="last")
    series = frame.set_index(config.date_col)[config.value_col].astype(float)
    series = series.loc[START:END]
    if series.index[0] != START or series.index[-1] != END:
        raise RuntimeError(f"{config.name}区间异常：{series.index[0]}—{series.index[-1]}")
    if not series.index.is_monotonic_increasing or series.isna().any() or (series <= 0).any():
        raise RuntimeError(f"{config.name}序列质量异常")
    return series


def annualized_return(start_value: float, end_value: float, start: pd.Timestamp, end: pd.Timestamp) -> float:
    return (end_value / start_value) ** (365.2425 / (end - start).days) - 1


def max_drawdown(series: pd.Series) -> tuple[float, pd.Timestamp, pd.Timestamp, str]:
    running_max = series.cummax()
    drawdown = series / running_max - 1
    trough = cast(pd.Timestamp, drawdown.idxmin())
    peak = cast(pd.Timestamp, series.loc[:trough].idxmax())
    recovered = series.loc[trough:][series.loc[trough:] >= series.loc[peak]]
    recovery = recovered.index[0].date().isoformat() if len(recovered) else "区间末尚未修复"
    return float(drawdown.loc[trough]), peak, trough, recovery


def pct(value: float) -> str:
    return f"{value:.8%}"


def main() -> None:
    summary_rows = []
    stability_rows = []
    annual_rows: dict[int, dict[str, float]] = {year: {} for year in range(2017, 2026)}

    for config in SERIES:
        series = load_series(config)
        daily_returns = series.pct_change().dropna()
        monthly = series.resample("ME").last()
        monthly_returns = monthly.pct_change().dropna()
        start_date = cast(pd.Timestamp, series.index[0])
        end_date = cast(pd.Timestamp, series.index[-1])
        cagr = annualized_return(series.iloc[0], series.iloc[-1], start_date, end_date)
        daily_vol = daily_returns.std(ddof=1) * np.sqrt(252)
        monthly_vol = monthly_returns.std(ddof=1) * np.sqrt(12)
        max_dd, peak, trough, recovery = max_drawdown(series)

        year_end = series.resample("YE").last()
        annual = year_end.pct_change()
        complete = annual[(annual.index.year >= 2017) & (annual.index.year <= 2025)]
        if len(complete) != 9:
            raise RuntimeError(f"{config.name}完整年度数量异常：{len(complete)}")
        for timestamp, value in complete.items():
            annual_rows[timestamp.year][config.name] = float(value)

        rolling3 = (monthly / monthly.shift(36)) ** (1 / 3) - 1
        rolling5 = (monthly / monthly.shift(60)) ** (1 / 5) - 1
        rolling3 = rolling3.dropna()
        rolling5 = rolling5.dropna()

        summary_rows.append(
            {
                "指数": config.name,
                "数据口径": config.source_type,
                "交易日数": len(series),
                "期初日期": start_date.date().isoformat(),
                "期初点位": f"{series.iloc[0]:.8f}",
                "期末日期": end_date.date().isoformat(),
                "期末点位": f"{series.iloc[-1]:.8f}",
                "累计收益": pct(series.iloc[-1] / series.iloc[0] - 1),
                "精确年化收益": pct(cagr),
                "日频年化波动": pct(daily_vol),
                "月频年化波动": pct(monthly_vol),
                "最大回撤": pct(max_dd),
                "回撤高点日期": peak.date().isoformat(),
                "回撤低点日期": trough.date().isoformat(),
                "修复日期": recovery,
                "收益/月频波动": f"{cagr / monthly_vol:.4f}",
            }
        )
        stability_rows.append(
            {
                "指数": config.name,
                "数据口径": config.source_type,
                "完整年度正收益": f"{int((complete > 0).sum())}/9",
                "最差年度": pct(float(complete.min())),
                "最差年度年份": int(complete.idxmin().year),
                "滚动3年样本数": len(rolling3),
                "滚动3年正收益占比": pct(float((rolling3 > 0).mean())),
                "滚动3年年化中位数": pct(float(rolling3.median())),
                "滚动3年年化最低值": pct(float(rolling3.min())),
                "滚动5年样本数": len(rolling5),
                "滚动5年正收益占比": pct(float((rolling5 > 0).mean())),
                "滚动5年年化中位数": pct(float(rolling5.median())),
                "滚动5年年化最低值": pct(float(rolling5.min())),
            }
        )

    pd.DataFrame(summary_rows).to_csv(PERF / "复算指标_2016-06-30_2026-07-31.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(stability_rows).to_csv(PERF / "稳定性指标_2016-06-30_2026-07-31.csv", index=False, encoding="utf-8-sig")
    annual_frame = pd.DataFrame.from_dict(annual_rows, orient="index")
    annual_frame.index.name = "年度"
    annual_frame.to_csv(PERF / "年度收益_2017_2025.csv", encoding="utf-8-sig", float_format="%.10f")

    print(pd.DataFrame(summary_rows)[["指数", "精确年化收益", "月频年化波动", "最大回撤", "收益/月频波动"]].to_string(index=False))
    print()
    print(pd.DataFrame(stability_rows)[["指数", "完整年度正收益", "最差年度", "滚动3年正收益占比", "滚动3年年化中位数", "滚动5年正收益占比", "滚动5年年化中位数"]].to_string(index=False))


if __name__ == "__main__":
    main()
