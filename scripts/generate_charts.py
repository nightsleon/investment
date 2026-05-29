#!/usr/bin/env python3
"""福耀玻璃(600660) 季度股价vs利润对比图 — 双折线版本"""

import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
import json
import urllib.request
import numpy as np
from pathlib import Path

OUT_DIR = Path(__file__).parent
CODE = "600660"
YF_CODE = "600660.SS"

# ============ 1) 获取东方财富财务数据（累计值） ============
def fetch_financials():
    all_data = []
    for page in range(1, 10):
        url = (
            f"https://datacenter.eastmoney.com/securities/api/data/v1/get?"
            f"reportName=RPT_DMSK_FN_INCOME"
            f"&columns=SECUCODE,REPORT_DATE,PARENT_NETPROFIT,DEDUCT_PARENT_NETPROFIT"
            f'&filter=(SECUCODE=%22{CODE}.SH%22)'
            f"&pageSize=50&pageNumber={page}"
            f"&sortColumns=REPORT_DATE&sortTypes=-1&source=HSF10&client=PC"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        if not data.get("success") or not data["result"]["data"]:
            break
        all_data.extend(data["result"]["data"])
    df = pd.DataFrame(all_data)
    df["date"] = pd.to_datetime(df["REPORT_DATE"])
    df = df.sort_values("date").reset_index(drop=True)
    df["net_profit_cum"] = df["PARENT_NETPROFIT"] / 1e8
    df["non_gaap_cum"] = df["DEDUCT_PARENT_NETPROFIT"] / 1e8
    return df

# ============ 2) 累计转单季度 ============
def cum_to_quarterly(df):
    df = df.copy()
    df["quarter"] = df["date"].dt.quarter
    df["net_profit"] = np.nan
    df["non_gaap"] = np.nan
    for i in range(len(df)):
        q = df.iloc[i]["quarter"]
        if q == 1:
            df.loc[df.index[i], "net_profit"] = df.iloc[i]["net_profit_cum"]
            df.loc[df.index[i], "non_gaap"] = df.iloc[i]["non_gaap_cum"]
        else:
            if q == 2:
                prev_mask = (df["date"].dt.year == df.iloc[i]["date"].year) & (df["quarter"] == 1)
            elif q == 3:
                prev_mask = (df["date"].dt.year == df.iloc[i]["date"].year) & (df["quarter"] == 2)
            elif q == 4:
                prev_mask = (df["date"].dt.year == df.iloc[i]["date"].year) & (df["quarter"] == 3)
            prev_rows = df[prev_mask]
            if not prev_rows.empty:
                prev = prev_rows.iloc[-1]
                df.loc[df.index[i], "net_profit"] = df.iloc[i]["net_profit_cum"] - prev["net_profit_cum"]
                df.loc[df.index[i], "non_gaap"] = df.iloc[i]["non_gaap_cum"] - prev["non_gaap_cum"]
    return df.dropna(subset=["net_profit", "non_gaap"])

# ============ 3) 计算TTM ============
def calc_ttm(df):
    df = df.copy()
    df["net_profit_ttm"] = df["net_profit"].rolling(4, min_periods=4).sum()
    df["non_gaap_ttm"] = df["non_gaap"].rolling(4, min_periods=4).sum()
    return df

# ============ 4) 获取股价 ============
def fetch_price():
    raw = yf.download(YF_CODE, start="2015-01-01", end="2026-06-01", auto_adjust=False, progress=False)
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    price = raw.reset_index()[["Date", "Adj Close", "Close"]].rename(
        columns={"Date": "trade_date", "Adj Close": "adj_close", "Close": "close"}
    )
    price["trade_date"] = pd.to_datetime(price["trade_date"]).dt.tz_localize(None)
    return price

# ============ 5) 对齐季度末股价 ============
def match_price(fin, price):
    matched = []
    for _, row in fin.dropna(subset=["non_gaap_ttm"]).iterrows():
        q = row["date"]
        sub = price[price["trade_date"] <= q]
        if sub.empty:
            continue
        last = sub.iloc[-1]
        matched.append({
            "date": q,
            "quarter": f"{q.year}Q{int(row['quarter'])}",
            "adj_close": last["adj_close"],
            "close": last["close"],
            "net_profit_yi": row["net_profit"],
            "non_gaap_yi": row["non_gaap"],
            "net_profit_ttm_yi": row["net_profit_ttm"],
            "non_gaap_ttm_yi": row["non_gaap_ttm"],
        })
    return pd.DataFrame(matched)

# ============ 6) 绘图（全部双折线） ============
def plot_charts(merged):
    plt.rcParams['font.sans-serif'] = ['PingFang SC', 'Heiti SC', 'Arial Unicode MS', 'SimHei']
    plt.rcParams['axes.unicode_minus'] = False

    # --- 图1：归一化对比（双折线） ---
    fig, ax = plt.subplots(figsize=(16, 8), dpi=150)
    base_close = merged["adj_close"].iloc[0]
    base_ttm = merged["non_gaap_ttm_yi"].iloc[0]
    norm_close = merged["adj_close"] / base_close
    norm_ttm = merged["non_gaap_ttm_yi"] / base_ttm
    
    ax.plot(merged["quarter"], norm_close, "o-", color="#1E88E5", linewidth=2.5, markersize=6, label="归一化股价(前复权)")
    ax.plot(merged["quarter"], norm_ttm, "s-", color="#E53935", linewidth=2.5, markersize=6, label="归一化扣非TTM利润")
    ax.fill_between(range(len(merged)), norm_close, norm_ttm, alpha=0.08, color="gray")
    ax.set_title(f"福耀玻璃(600660) 归一化对比：股价 vs 扣非TTM利润", fontsize=15, fontweight="bold")
    ax.set_ylabel("归一化值（基期=1）", fontsize=12)
    ax.legend(fontsize=12, loc="upper left")
    ticks = list(range(0, len(merged), max(1, len(merged)//12)))
    ax.set_xticks(ticks)
    ax.set_xticklabels([merged["quarter"].iloc[i] for i in ticks], rotation=45, ha="right", fontsize=10)
    ax.grid(True, alpha=0.3)
    
    corr = merged["adj_close"].corr(merged["non_gaap_ttm_yi"])
    price_mult = merged["adj_close"].iloc[-1] / merged["adj_close"].iloc[0]
    ttm_mult = merged["non_gaap_ttm_yi"].iloc[-1] / merged["non_gaap_ttm_yi"].iloc[0]
    ax.text(0.02, 0.95, f"相关系数: {corr:.3f}\n股价涨幅: {price_mult:.1f}x\n利润涨幅: {ttm_mult:.1f}x",
            transform=ax.transAxes, fontsize=11, va="top", bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8))
    plt.tight_layout()
    fig.savefig(OUT_DIR / f"{CODE}_归一化_股价vs扣非TTM.png", bbox_inches="tight")
    plt.close()

    # --- 图2：双折线（股价 + 扣非TTM） ---
    fig, ax1 = plt.subplots(figsize=(18, 9), dpi=150)
    ax2 = ax1.twinx()
    
    x = range(len(merged))
    line1, = ax1.plot(x, merged["adj_close"], "o-", color="#1E88E5", linewidth=2.5, markersize=5, label="股价(前复权)")
    line2, = ax2.plot(x, merged["non_gaap_ttm_yi"], "s-", color="#E53935", linewidth=2.5, markersize=5, label="扣非TTM利润(亿)")
    ax2.fill_between(x, merged["non_gaap_ttm_yi"], alpha=0.08, color="#E53935")
    
    ax1.set_ylabel("股价（元）", color="#1E88E5", fontsize=13, fontweight="bold")
    ax2.set_ylabel("扣非TTM净利润（亿元）", color="#E53935", fontsize=13, fontweight="bold")
    ax1.set_title(f"福耀玻璃(600660) 股价 vs 扣非净利润TTM", fontsize=15, fontweight="bold")
    
    ticks = list(range(0, len(merged), max(1, len(merged)//12)))
    ax1.set_xticks(ticks)
    ax1.set_xticklabels([merged["quarter"].iloc[i] for i in ticks], rotation=45, ha="right", fontsize=10)
    ax1.tick_params(axis='y', labelcolor="#1E88E5", labelsize=11)
    ax2.tick_params(axis='y', labelcolor="#E53935", labelsize=11)
    
    ax1.legend([line1, line2], [line1.get_label(), line2.get_label()], fontsize=12, loc="upper left")
    ax1.grid(True, alpha=0.3)
    
    plt.tight_layout()
    fig.savefig(OUT_DIR / f"{CODE}_股价vs扣非净利润TTM_双Y轴.png", bbox_inches="tight")
    plt.close()

    # --- 图3：双折线（股价 + 单季度扣非） ---
    fig, ax1 = plt.subplots(figsize=(18, 9), dpi=150)
    ax2 = ax1.twinx()
    
    x = range(len(merged))
    line1, = ax1.plot(x, merged["adj_close"], "o-", color="#1E88E5", linewidth=2.5, markersize=5, label="股价(前复权)")
    line2, = ax2.plot(x, merged["non_gaap_yi"], "^-", color="#FF9800", linewidth=2.5, markersize=6, label="单季度扣非利润(亿)")
    ax2.fill_between(x, merged["non_gaap_yi"], alpha=0.08, color="#FF9800")
    
    ax1.set_ylabel("股价（元）", color="#1E88E5", fontsize=13, fontweight="bold")
    ax2.set_ylabel("单季度扣非净利润（亿元）", color="#FF9800", fontsize=13, fontweight="bold")
    ax1.set_title(f"福耀玻璃(600660) 股价 vs 单季度扣非净利润", fontsize=15, fontweight="bold")
    
    ax1.set_xticks(ticks)
    ax1.set_xticklabels([merged["quarter"].iloc[i] for i in ticks], rotation=45, ha="right", fontsize=10)
    ax1.tick_params(axis='y', labelcolor="#1E88E5", labelsize=11)
    ax2.tick_params(axis='y', labelcolor="#FF9800", labelsize=11)
    
    ax1.legend([line1, line2], [line1.get_label(), line2.get_label()], fontsize=12, loc="upper left")
    ax1.grid(True, alpha=0.3)
    
    plt.tight_layout()
    fig.savefig(OUT_DIR / f"{CODE}_股价vs扣非净利润_单季度.png", bbox_inches="tight")
    plt.close()
    
    return corr, price_mult, ttm_mult

# ============ Main ============
if __name__ == "__main__":
    print("1. 获取财务数据...")
    fin_raw = fetch_financials()
    print(f"   {len(fin_raw)} 条记录")
    
    print("2. 累计转单季度...")
    fin = cum_to_quarterly(fin_raw)
    print(f"   {len(fin)} 条单季度数据")
    
    print("3. 计算TTM...")
    fin = calc_ttm(fin)
    
    print("4. 获取股价...")
    price = fetch_price()
    print(f"   {len(price)} 个交易日")
    
    print("5. 对齐...")
    merged = match_price(fin, price)
    print(f"   {len(merged)} 个季度")
    
    csv_path = OUT_DIR / f"{CODE}_季度数据.csv"
    merged.to_csv(csv_path, index=False, encoding="utf-8-sig")
    
    print("6. 生成双折线图...")
    corr, price_mult, ttm_mult = plot_charts(merged)
    print(f"   相关系数={corr:.3f}  股价涨幅={price_mult:.1f}x  利润涨幅={ttm_mult:.1f}x")
    print("   完成!")
