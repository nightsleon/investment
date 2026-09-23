#!/usr/bin/env python3
"""二期v2：计算30只基金指标、评分、生成图表和报告数据。"""
from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

matplotlib.rcParams["font.sans-serif"] = ["Arial Unicode MS", "PingFang SC", "Heiti SC"]
matplotlib.rcParams["axes.unicode_minus"] = False

BASE = Path(__file__).resolve().parents[2]
NAV_DIR = BASE / "sources" / "fund-nav-correct"
INDEX_DIR = BASE / "sources" / "performance-data-30index"
OUTPUT_DIR = BASE / "02_二期深度对比"
CHART_DIR = OUTPUT_DIR / "charts"
CHART_DIR.mkdir(parents=True, exist_ok=True)

BENCHMARK = "512890"

FUNDS = [
    # 5年组
    {"code": "512890", "short": "华泰柏瑞红利低波", "index_code": "H30269", "group": "5年组", "aum": 324.14, "type": "ETF"},
    {"code": "510880", "short": "华泰柏瑞上证红利", "index_code": "000015", "group": "5年组", "aum": 213.18, "type": "ETF"},
    {"code": "515180", "short": "易方达中证红利", "index_code": "000922", "group": "5年组", "aum": 179.08, "type": "ETF"},
    {"code": "515300", "short": "嘉实300红利低波", "index_code": "930740", "group": "5年组", "aum": 45.20, "type": "ETF"},
    {"code": "007751", "short": "景顺长城红利成长低波", "index_code": "931157", "group": "5年组", "aum": 34.51, "type": "指数基金"},
    {"code": "008928", "short": "宏利消费红利", "index_code": "H30094", "group": "5年组", "aum": 7.99, "type": "指数基金"},
    {"code": "512530", "short": "建信300红利", "index_code": "000821", "group": "5年组", "aum": 1.60, "type": "ETF"},
    {"code": "501307", "short": "银河沪港深高股息LOF", "index_code": "930917", "group": "5年组", "aum": 0.65, "type": "LOF"},
    {"code": "007178", "short": "浙商预期高股息增强", "index_code": "CESFHY", "group": "5年组", "aum": 0.62, "type": "指数增强"},
    {"code": "007671", "short": "建信红利潜力", "index_code": "H30089", "group": "5年组", "aum": 0.42, "type": "指数基金"},
    {"code": "3070HK", "short": "平安香港高息股ETF", "index_code": "H11140", "group": "5年组", "aum": 10.87, "type": "ETF(港股)"},
    # 3年组
    {"code": "012708", "short": "东方红红利低波", "index_code": "931446", "group": "3年组", "aum": 65.11, "type": "指数基金"},
    {"code": "513530", "short": "华泰柏瑞港股通高股息", "index_code": "930914", "group": "3年组", "aum": 42.71, "type": "ETF(QDII)"},
    {"code": "159691", "short": "工银港股通高息精选", "index_code": "930839", "group": "3年组", "aum": 44.55, "type": "ETF"},
    {"code": "561580", "short": "华泰柏瑞央企红利", "index_code": "000825", "group": "3年组", "aum": 26.98, "type": "ETF"},
    {"code": "560700", "short": "广发央企股东回报", "index_code": "932039", "group": "3年组", "aum": 5.38, "type": "ETF"},
    {"code": "159758", "short": "华夏红利质量", "index_code": "931468", "group": "3年组", "aum": 15.06, "type": "ETF"},
    # 观察池
    {"code": "561060", "short": "华安国企红利", "index_code": "000824", "group": "观察池", "aum": 0.63, "type": "ETF"},
    {"code": "513910", "short": "华夏港股通央企红利", "index_code": "931233", "group": "观察池", "aum": 32.47, "type": "ETF"},
    {"code": "510720", "short": "国泰上证国企红利", "index_code": "000151", "group": "观察池", "aum": 21.76, "type": "ETF"},
    {"code": "159307", "short": "博时红利低波100", "index_code": "930955", "group": "观察池", "aum": 71.99, "type": "ETF"},
    {"code": "020456", "short": "平安上证红利低波", "index_code": "H50040", "group": "观察池", "aum": 0.84, "type": "指数基金"},
    {"code": "563180", "short": "银华高股息策略", "index_code": "H30366", "group": "观察池", "aum": 1.26, "type": "ETF"},
    {"code": "520990", "short": "景顺国新港股通央企红利", "index_code": "931722", "group": "观察池", "aum": 34.01, "type": "ETF"},
    {"code": "021561", "short": "天弘央企红利50", "index_code": "931231", "group": "观察池", "aum": 3.50, "type": "指数基金"},
    {"code": "159336", "short": "融通诚通央企红利", "index_code": "931132", "group": "观察池", "aum": 4.24, "type": "ETF"},
    {"code": "159209", "short": "招商中证全指红利质量", "index_code": "932315", "group": "观察池", "aum": 25.07, "type": "ETF"},
    {"code": "159207", "short": "广发智选高股息", "index_code": "932305", "group": "观察池", "aum": 22.87, "type": "ETF"},
    {"code": "563700", "short": "易方达红利价值", "index_code": "H30270", "group": "观察池", "aum": 4.16, "type": "ETF"},
    {"code": "560570", "short": "国联安A500红利低波", "index_code": "932422", "group": "观察池", "aum": 12.30, "type": "ETF"},
]


def load_nav(code: str) -> pd.Series:
    for f in NAV_DIR.glob(f"{code}_*_净值.csv"):
        df = pd.read_csv(f, parse_dates=["date"], index_col="date", encoding="utf-8-sig")
        if "reinvested_nav" in df.columns:
            return df["reinvested_nav"].astype(float).sort_index()
    return pd.Series(dtype=float)


def load_index_nav(index_code: str) -> pd.Series:
    for f in INDEX_DIR.glob(f"{index_code}_*_全收益.csv"):
        df = pd.read_csv(f, encoding="utf-8-sig")
        date_col = None
        price_col = None
        for col in df.columns:
            cl = col.lower()
            if "date" in cl or "日期" in col:
                date_col = col
            if "close" in cl or "收盘" in col or "value" in cl:
                price_col = col
        if date_col and price_col:
            df[date_col] = pd.to_datetime(df[date_col])
            return df.set_index(date_col)[price_col].astype(float).sort_index()
    return pd.Series(dtype=float)


def calc_metrics(nav: pd.Series) -> dict:
    s = nav.dropna().sort_index()
    if len(s) < 30:
        return {"sufficient": False}
    start_date, end_date = s.index[0], s.index[-1]
    start_val, end_val = s.iloc[0], s.iloc[-1]
    days = (end_date - start_date).days
    years = days / 365.25
    cagr = (end_val / start_val) ** (365.25 / days) - 1 if days > 0 else 0
    total_return = end_val / start_val - 1
    # Max drawdown
    peak = s.expanding(min_periods=1).max()
    mdd = float((s / peak - 1).min())
    # Monthly vol
    monthly = s.resample("ME").last()
    monthly_ret = monthly.pct_change().dropna()
    monthly_vol = float(monthly_ret.std() * math.sqrt(12)) if len(monthly_ret) > 5 else float("nan")
    efficiency = cagr / monthly_vol if monthly_vol and not np.isnan(monthly_vol) and monthly_vol > 0 else float("nan")
    # Annual win rate
    complete_years = []
    for year in range(start_date.year, end_date.year + 1):
        ydata = s[s.index.year == year]
        if len(ydata) > 200:
            complete_years.append(ydata.iloc[-1] / ydata.iloc[0] - 1)
    win_rate = f"{sum(1 for r in complete_years if r > 0)}/{len(complete_years)}" if len(complete_years) >= 1 else "N/A"
    # Rolling 3Y median
    rolling3 = ((monthly / monthly.shift(36)) ** (1/3) - 1).dropna() if len(monthly) > 36 else pd.Series(dtype=float)
    rolling3_median = float(rolling3.median()) if len(rolling3) > 0 else float("nan")

    return {
        "sufficient": True,
        "data_points": len(s),
        "start_date": str(start_date.date()),
        "end_date": str(end_date.date()),
        "cagr": cagr, "total_return": total_return,
        "max_drawdown": mdd, "monthly_vol": monthly_vol,
        "return_over_vol": efficiency,
        "annual_win_rate": win_rate,
        "rolling3_median": rolling3_median,
        "complete_years": len(complete_years),
    }


def calc_tracking_error(fund_nav: pd.Series, index_nav: pd.Series) -> dict:
    common = fund_nav.index.intersection(index_nav.index)
    if len(common) < 30:
        return {"sufficient": False}
    f = fund_nav.loc[common].sort_index()
    idx = index_nav.loc[common].sort_index()
    f_norm = f / f.iloc[0]
    idx_norm = idx / idx.iloc[0]
    f_ret = f.pct_change().dropna()
    idx_ret = idx.pct_change().dropna()
    cr = f_ret.index.intersection(idx_ret.index)
    if len(cr) > 20:
        diff_ret = f_ret.loc[cr] - idx_ret.loc[cr]
        te_annual = float(diff_ret.std() * math.sqrt(252))
    else:
        te_annual = float("nan")
    total_diff = (f_norm.iloc[-1] - 1) - (idx_norm.iloc[-1] - 1)
    return {
        "sufficient": True,
        "data_points": len(common),
        "tracking_error_annual": te_annual,
        "total_excess_return": float(total_diff),
    }


def score_group(metrics_list: list[dict], use_stability: bool = True) -> list[dict]:
    df = pd.DataFrame(metrics_list)
    df = df[df["sufficient"]].copy()
    if len(df) == 0:
        return []
    df["score_return"] = df["cagr"].rank(pct=True) * 100
    df["score_risk"] = df["max_drawdown"].rank(pct=True) * 100
    df["score_efficiency"] = df["return_over_vol"].rank(pct=True) * 100
    if use_stability:
        def parse_wr(wr):
            if wr == "N/A" or not wr:
                return np.nan
            parts = wr.split("/")
            try:
                return int(parts[0]) / int(parts[1])
            except:
                return np.nan
        df["wr_num"] = df["annual_win_rate"].apply(parse_wr)
        df["score_stability"] = (
            df["wr_num"].rank(pct=True) * 50
            + df["rolling3_median"].rank(pct=True) * 50
        )
        df["total_score"] = (
            df["score_return"] * 0.40 + df["score_risk"] * 0.30
            + df["score_efficiency"] * 0.15 + df["score_stability"] * 0.15
        )
    else:
        df["total_score"] = (
            df["score_return"] * 0.50 + df["score_risk"] * 0.30
            + df["score_efficiency"] * 0.20
        )
    df = df.sort_values("total_score", ascending=False).reset_index(drop=True)
    df["rank"] = range(1, len(df) + 1)
    return df.to_dict("records")


def tier(score, bench_score):
    if score >= bench_score + 3:
        return "第一梯队"
    elif score >= bench_score - 3:
        return "第二梯队"
    else:
        return "第三梯队"


# ========== Charts ==========

def chart_colors(n):
    cmap = plt.cm.tab20
    return [cmap(i % 20) for i in range(n)]


def group_chart(scored, navs, group_name, common_dates):
    fig, ax = plt.subplots(figsize=(12, 7.5))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    plot_items = []
    for s in scored:
        code = s["code"]
        if code not in navs:
            continue
        nav = navs[code].loc[common_dates]
        norm = nav / nav.iloc[0] * 100
        ret = norm.iloc[-1] - 100
        plot_items.append((s, norm, ret))
    plot_items.sort(key=lambda x: x[2])
    colors = chart_colors(len(plot_items))
    legend_items = []
    for i, (s, norm, ret) in enumerate(plot_items):
        code = s["code"]
        is_bench = code == BENCHMARK
        if is_bench:
            line, = ax.plot(norm.index, norm.values, color="#999", linewidth=1.8, linestyle="--", zorder=10)
            legend_items.append((999, line, f"★{s['short']} +{ret:.1f}%"))
        else:
            line, = ax.plot(norm.index, norm.values, color=colors[i], linewidth=0.8)
            legend_items.append((ret, line, f"{s['short']} +{ret:.1f}%"))
    legend_items.sort(key=lambda x: -x[0])
    ax.legend([h for _, h, _ in legend_items], [l for _, _, l in legend_items],
              loc="upper left", fontsize=8, ncol=2, framealpha=0.9)
    ax.set_title(f"红利类基金对比 - {group_name}（归一化=100）", fontsize=14, pad=12)
    ax.set_ylabel("归一化净值", fontsize=11)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    fpath = CHART_DIR / f"组内对比_{group_name}.png"
    fig.savefig(fpath, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return fpath


def vs_bench_chart(fund_code, fund_short, fund_nav, bench_nav, common_dates):
    f = fund_nav.loc[common_dates]
    b = bench_nav.loc[common_dates]
    f_norm = f / f.iloc[0] * 100
    b_norm = b / b.iloc[0] * 100
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor("white"); ax.set_facecolor("white")
    ax.plot(b_norm.index, b_norm.values, color="#999", linewidth=0.8, linestyle="--",
            label=f"华泰柏瑞红利低波（基准） +{b_norm.iloc[-1]-100:.2f}%")
    ax.plot(f_norm.index, f_norm.values, color="#dc2626", linewidth=1.0,
            label=f"{fund_short} +{f_norm.iloc[-1]-100:.2f}%")
    ax.set_title(f"{fund_short} vs 基准（归一化=100）", fontsize=13, pad=12)
    ax.legend(loc="upper left", fontsize=10)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    fpath = CHART_DIR / f"对比基准_{fund_code}.png"
    fig.savefig(fpath, dpi=150, bbox_inches="tight")
    plt.close(fig)


def tracking_chart(fund_code, fund_short, fund_nav, index_nav):
    common = fund_nav.index.intersection(index_nav.index)
    if len(common) < 30:
        return
    f = fund_nav.loc[common].sort_index()
    idx = index_nav.loc[common].sort_index()
    f_norm = f / f.iloc[0]
    idx_norm = idx / idx.iloc[0]
    diff = (f_norm - idx_norm) * 100
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor("white"); ax.set_facecolor("white")
    ax.plot(diff.index, diff.values, color="#2563eb", linewidth=1.0)
    ax.axhline(y=0, color="#999", linestyle="--", linewidth=0.8)
    ax.set_title(f"{fund_short}（{fund_code}）跟踪偏离度", fontsize=13, pad=12)
    ax.set_ylabel("累计偏离（%）", fontsize=11)
    ax.grid(True, alpha=0.3)
    final = diff.iloc[-1]
    ax.annotate(f"期末：{final:+.2f}%", xy=(diff.index[-1], final),
                xytext=(-10, 15), textcoords="offset points", fontsize=9,
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#ccc", alpha=0.9))
    plt.tight_layout()
    fpath = CHART_DIR / f"跟踪偏离_{fund_code}.png"
    fig.savefig(fpath, dpi=150, bbox_inches="tight")
    plt.close(fig)


# ========== Main ==========

def main():
    # Load all NAVs
    navs = {}
    index_navs = {}
    for fund in FUNDS:
        navs[fund["code"]] = load_nav(fund["code"])
        if fund["index_code"] not in index_navs:
            index_navs[fund["index_code"]] = load_index_nav(fund["index_code"])

    results = {"5年组": [], "3年组": [], "观察池": []}

    for group_name in ["5年组", "3年组"]:
        g_funds = [f for f in FUNDS if f["group"] == group_name]
        # Find common dates
        common_dates = None
        for f in g_funds:
            nav = navs[f["code"]]
            if len(nav) > 0:
                common_dates = nav.index if common_dates is None else common_dates.intersection(nav.index)
        common_dates = common_dates.sort_values()
        # Trim to >= 2020 to avoid very old data for 5yr group
        print(f"\n{group_name}: 共同区间 {common_dates[0].date()} ~ {common_dates[-1].date()}, {len(common_dates)}个交易日")

        use_stability = group_name == "5年组"
        metrics_list = []
        for f in g_funds:
            nav = navs[f["code"]].loc[common_dates]
            m = calc_metrics(nav)
            if not m["sufficient"]:
                continue
            # Tracking error
            te = calc_tracking_error(navs[f["code"]], index_navs.get(f["index_code"], pd.Series(dtype=float)))
            m.update({
                "code": f["code"], "short": f["short"],
                "index_code": f["index_code"], "aum": f["aum"], "type": f["type"],
                "te_annual": te.get("tracking_error_annual", float("nan")),
                "te_excess": te.get("total_excess_return", float("nan")),
            })
            metrics_list.append(m)

        # 3年组：把基准512890截取到同区间参与评分
        if group_name == "3年组":
            bench_nav_slice = navs[BENCHMARK].loc[common_dates[0]:common_dates[-1]]
            bm = calc_metrics(bench_nav_slice)
            if bm["sufficient"]:
                bte = calc_tracking_error(navs[BENCHMARK], index_navs["H30269"])
                bm.update({
                    "code": BENCHMARK, "short": "华泰柏瑞红利低波★基准",
                    "index_code": "H30269", "aum": 324.14, "type": "ETF",
                    "te_annual": bte.get("tracking_error_annual", float("nan")),
                    "te_excess": bte.get("total_excess_return", float("nan")),
                    "is_benchmark": True,
                })
                metrics_list.append(bm)

        scored = score_group(metrics_list, use_stability=use_stability)
        bench_score = next((s["total_score"] for s in scored if s["code"] == BENCHMARK), 0)

        for s in scored:
            if s["code"] == BENCHMARK:
                s["tier"] = "基准"
            else:
                s["tier"] = tier(s["total_score"], bench_score)
            results[group_name].append(s)

        # Generate group chart
        group_chart(scored, navs, group_name, common_dates)

        # Individual charts for non-observation funds
        for s in scored:
            code = s["code"]
            if code == BENCHMARK:
                continue
            vs_bench_chart(code, s["short"], navs[code], navs[BENCHMARK], common_dates)
            if not np.isnan(s.get("te_annual", float("nan"))):
                tracking_chart(code, s["short"], navs[code], index_navs.get(s["index_code"], pd.Series(dtype=float)))

    # Observation pool: each fund own data, no scoring
    for f in [x for x in FUNDS if x["group"] == "观察池"]:
        nav = navs[f["code"]]
        m = calc_metrics(nav)
        if m["sufficient"]:
            te = calc_tracking_error(nav, index_navs.get(f["index_code"], pd.Series(dtype=float)))
            m.update({
                "code": f["code"], "short": f["short"],
                "aum": f["aum"], "type": f["type"],
                "te_annual": te.get("tracking_error_annual", float("nan")),
            })
            results["观察池"].append(m)

    # Save JSON
    out_json = OUTPUT_DIR / "基金对比_指标及排名_v2.json"
    with open(out_json, "w", encoding="utf-8") as fp:
        json.dump(results, fp, ensure_ascii=False, indent=2, default=str)
    print(f"\n✓ 结果保存: {out_json}")

    # Print summary tables
    for g in ["5年组", "3年组"]:
        print(f"\n{'='*100}")
        print(f"{g}")
        print(f"{'='*100}")
        print(f"{'排名':>3} {'基金':<22} {'总分':>6} {'总收益':>8} {'CAGR':>7} {'最大回撤':>8} {'收益/波动':>8} {'跟踪误差':>7} {'规模':>7} {'梯队'}")
        for s in results[g]:
            print(f"{s['rank']:>3} {s['short']:<22} {s['total_score']:>6.1f} "
                  f"{s['total_return']*100:>7.2f}% {s['cagr']*100:>6.2f}% "
                  f"{s['max_drawdown']*100:>7.2f}% {s['return_over_vol']:>8.2f} "
                  f"{s.get('te_annual',0)*100:>6.2f}% {s['aum']:>7.2f} {s['tier']}")

    print(f"\n观察池: {len(results['观察池'])}只")
    for m in results["观察池"]:
        print(f"  {m['short']:<22} {m['data_points']:>5}天  CAGR={m['cagr']*100:>6.2f}%  MDD={m['max_drawdown']*100:>7.2f}%  AUM={m['aum']}")


if __name__ == "__main__":
    main()
