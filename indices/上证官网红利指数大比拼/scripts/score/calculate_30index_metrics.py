#!/usr/bin/env python3
"""解析30只红利指数Excel，转CSV归档，计算全部回溯指标。"""
from __future__ import annotations

import json
import os
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

BASE = Path(__file__).resolve().parents[2]
EXCEL_DIR = BASE / "sources" / "excel-30index"
CSV_DIR = BASE / "sources" / "performance-data-30index"
CSV_DIR.mkdir(parents=True, exist_ok=True)

# 三档回溯区间的终点统一取最近交易日
END_DATE = pd.Timestamp("2026-08-07")

# 10年/5年/3年的起点
START_10Y = pd.Timestamp("2016-08-08")
START_5Y = pd.Timestamp("2021-08-09")
START_3Y = pd.Timestamp("2023-08-08")


def load_basic_info() -> list[dict]:
    with open(EXCEL_DIR / "basic_info.json", encoding="utf-8") as f:
        return json.load(f)


def parse_excel_to_csv(xlsx_path: Path, price_code: str, name: str) -> pd.Series | None:
    """解析Excel，保存CSV，返回收盘价序列。"""
    df = pd.read_excel(xlsx_path, sheet_name=0)
    date_col = [c for c in df.columns if c.startswith("日期")][0]
    close_col = [c for c in df.columns if c.startswith("收盘")][0]

    df[date_col] = pd.to_datetime(df[date_col].astype(str), format="%Y%m%d")
    df = df.sort_values(date_col).drop_duplicates(date_col, keep="last")
    series = df.set_index(date_col)[close_col].astype(float)
    series = series[series > 0]

    csv_path = CSV_DIR / f"{price_code}_{name}_全收益.csv"
    df[[date_col, close_col]].to_csv(csv_path, index=False, encoding="utf-8-sig")

    return series


def annualized_return(start_value: float, end_value: float, start: pd.Timestamp, end: pd.Timestamp) -> float:
    if start_value <= 0 or end_value <= 0:
        return float("nan")
    days = (end - start).days
    if days <= 0:
        return float("nan")
    return (end_value / start_value) ** (365.2425 / days) - 1


def max_drawdown(series: pd.Series) -> tuple[float, pd.Timestamp | None, pd.Timestamp | None, str | None]:
    if len(series) == 0:
        return float("nan"), None, None, None
    running_max = series.cummax()
    drawdown = series / running_max - 1
    trough_idx = drawdown.idxmin()
    trough = trough_idx
    peak = series.loc[:trough].idxmax()
    recovered = series.loc[trough:][series.loc[trough:] >= series.loc[peak]]
    recovery = recovered.index[0].date().isoformat() if len(recovered) else None
    return float(drawdown.loc[trough]), peak, trough, recovery


def calc_metrics(series: pd.Series, start: pd.Timestamp, end: pd.Timestamp, launch_date: str | None) -> dict:
    """计算指定区间的全部指标。"""
    s = series.loc[start:end]
    if len(s) < 60:  # 至少需要约3个月的交易日
        return {"sufficient_data": False, "record_count": len(s)}

    start_date = s.index[0]
    end_date = s.index[-1]
    cagr = annualized_return(s.iloc[0], s.iloc[-1], start_date, end_date)

    daily_returns = s.pct_change().dropna()
    monthly = s.resample("ME").last()
    monthly_returns = monthly.pct_change().dropna()

    daily_vol = daily_returns.std(ddof=1) * np.sqrt(252)
    monthly_vol = monthly_returns.std(ddof=1) * np.sqrt(12) if len(monthly_returns) > 0 else float("nan")

    max_dd, peak, trough, recovery = max_drawdown(s)

    # 年度收益
    year_end = s.resample("YE").last()
    annual = year_end.pct_change()
    start_year = start_date.year + 1
    end_year = end_date.year - 1
    complete = annual[(annual.index.year >= start_year) & (annual.index.year <= end_year)]

    # 滚动收益
    rolling3 = ((monthly / monthly.shift(36)) ** (1 / 3) - 1).dropna() if len(monthly) > 36 else pd.Series(dtype=float)
    rolling5 = ((monthly / monthly.shift(60)) ** (1 / 5) - 1).dropna() if len(monthly) > 60 else pd.Series(dtype=float)

    # 回溯占比
    backtest_ratio = ""
    if launch_date:
        launch = pd.Timestamp(launch_date)
        if launch > start_date:
            bt_days = (launch - start_date).days
            total_days = (end_date - start_date).days
            backtest_ratio = f"{bt_days / total_days:.1%}"

    # 发布前后CAGR落差
    pre_post_gap = ""
    if launch_date:
        launch = pd.Timestamp(launch_date)
        if launch > start_date and launch < end_date:
            pre = s.loc[start_date:launch]
            post = s.loc[launch:end_date]
            if len(pre) > 60 and len(post) > 60:
                pre_cagr = annualized_return(pre.iloc[0], pre.iloc[-1], pre.index[0], pre.index[-1])
                post_cagr = annualized_return(post.iloc[0], post.iloc[-1], post.index[0], post.index[-1])
                gap = (pre_cagr - post_cagr) * 100
                pre_post_gap = f"{gap:+.2f}pp"
            elif len(pre) > 60 and len(post) <= 60:
                pre_post_gap = "发布后数据不足"

    return {
        "sufficient_data": True,
        "record_count": len(s),
        "start_date": start_date.date().isoformat(),
        "end_date": end_date.date().isoformat(),
        "cumulative_return": s.iloc[-1] / s.iloc[0] - 1,
        "cagr": cagr,
        "daily_vol": daily_vol,
        "monthly_vol": monthly_vol,
        "max_drawdown": max_dd,
        "peak_date": peak.date().isoformat() if peak else None,
        "trough_date": trough.date().isoformat() if trough else None,
        "recovery_date": recovery,
        "return_over_vol": cagr / monthly_vol if monthly_vol and not np.isnan(monthly_vol) else float("nan"),
        "annual_win_rate": f"{int((complete > 0).sum())}/{len(complete)}" if len(complete) > 0 else "N/A",
        "worst_year": float(complete.min()) if len(complete) > 0 else float("nan"),
        "worst_year_year": int(complete.idxmin().year) if len(complete) > 0 else None,
        "rolling3_median": float(rolling3.median()) if len(rolling3) > 0 else float("nan"),
        "rolling3_positive_pct": float((rolling3 > 0).mean()) if len(rolling3) > 0 else float("nan"),
        "rolling3_min": float(rolling3.min()) if len(rolling3) > 0 else float("nan"),
        "rolling3_count": len(rolling3),
        "rolling5_median": float(rolling5.median()) if len(rolling5) > 0 else float("nan"),
        "rolling5_positive_pct": float((rolling5 > 0).mean()) if len(rolling5) > 0 else float("nan"),
        "rolling5_min": float(rolling5.min()) if len(rolling5) > 0 else float("nan"),
        "rolling5_count": len(rolling5),
        "backtest_ratio": backtest_ratio,
        "pre_post_gap": pre_post_gap,
        "complete_years": len(complete),
        "annual_data": {int(ts.year): float(v) for ts, v in complete.items()} if len(complete) > 0 else {},
    }


def main() -> None:
    basic_info = load_basic_info()

    all_metrics = []
    all_annual: dict[int, dict[str, float]] = {}

    for info in basic_info:
        price_code = info["price_code"]
        name = info["name"]
        tr_code = info["tr_code"]
        market = info.get("market", "")
        launch_date = info.get("publishDate")

        xlsx_path = EXCEL_DIR / f"{price_code}_{name}.xlsx"
        if not xlsx_path.exists():
            print(f"✗ {price_code} {name}: Excel不存在")
            continue

        series = parse_excel_to_csv(xlsx_path, price_code, name)
        if series is None or len(series) == 0:
            print(f"✗ {price_code} {name}: 解析失败")
            continue

        # 计算三档区间
        m10 = calc_metrics(series, START_10Y, END_DATE, launch_date)
        m5 = calc_metrics(series, START_5Y, END_DATE, launch_date)
        m3 = calc_metrics(series, START_3Y, END_DATE, launch_date)

        # 收集年度收益（用10年区间的）
        if m10.get("sufficient_data") and m10.get("annual_data"):
            for year, val in m10["annual_data"].items():
                if year not in all_annual:
                    all_annual[year] = {}
                all_annual[year][name] = val

        all_metrics.append({
            "price_code": price_code,
            "name": name,
            "tr_code": tr_code,
            "market": market,
            "launch_date": launch_date,
            "basic_date": info.get("basicDate"),
            "currency": info.get("currencyCn"),
            "total_records": len(series),
            "data_start": series.index[0].date().isoformat(),
            "data_end": series.index[-1].date().isoformat(),
            "metrics_10y": m10,
            "metrics_5y": m5,
            "metrics_3y": m3,
        })

        status10 = "✓" if m10.get("sufficient_data") else "✗"
        status5 = "✓" if m5.get("sufficient_data") else "✓"
        status3 = "✓" if m3.get("sufficient_data") else "✓"
        print(f"{status10}{status5}{status3} {price_code} {name}: 总{len(series)}条, 数据{series.index[0].date()}~{series.index[-1].date()}")

    # 保存完整指标JSON
    metrics_path = CSV_DIR / "全部指标.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(all_metrics, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n完整指标: {metrics_path}")

    # 保存年度收益
    annual_df = pd.DataFrame.from_dict(all_annual, orient="index")
    annual_df.index.name = "年度"
    annual_df.sort_index(inplace=True)
    annual_path = CSV_DIR / "年度收益.csv"
    annual_df.to_csv(annual_path, encoding="utf-8-sig", float_format="%.6f")
    print(f"年度收益: {annual_path}")

    # 打印汇总表
    print("\n" + "=" * 120)
    print(f"{'指数':<22} {'市场':<6} {'10Y CAGR':>10} {'10Y MDD':>10} {'5Y CAGR':>10} {'5Y MDD':>10} {'3Y CAGR':>10} {'回溯占比':>8} {'前后落差':>10}")
    print("-" * 120)
    for m in sorted(all_metrics, key=lambda x: (x["market"], -((x["metrics_10y"].get("cagr") or -1)))):
        m10 = m["metrics_10y"]
        m5 = m["metrics_5y"]
        m3 = m["metrics_3y"]
        cagr10 = f"{m10['cagr']:.2%}" if m10.get("sufficient_data") and not np.isnan(m10.get("cagr", float("nan"))) else "N/A"
        mdd10 = f"{m10['max_drawdown']:.2%}" if m10.get("sufficient_data") and not np.isnan(m10.get("max_drawdown", float("nan"))) else "N/A"
        cagr5 = f"{m5['cagr']:.2%}" if m5.get("sufficient_data") and not np.isnan(m5.get("cagr", float("nan"))) else "N/A"
        mdd5 = f"{m5['max_drawdown']:.2%}" if m5.get("sufficient_data") and not np.isnan(m5.get("max_drawdown", float("nan"))) else "N/A"
        cagr3 = f"{m3['cagr']:.2%}" if m3.get("sufficient_data") and not np.isnan(m3.get("cagr", float("nan"))) else "N/A"
        bt = m10.get("backtest_ratio", "") if m10.get("sufficient_data") else ""
        gap = m10.get("pre_post_gap", "") if m10.get("sufficient_data") else ""
        print(f"{m['name']:<22} {m['market']:<6} {cagr10:>10} {mdd10:>10} {cagr5:>10} {mdd5:>10} {cagr3:>10} {bt:>8} {gap:>10}")


if __name__ == "__main__":
    main()
