#!/usr/bin/env python3
"""抓取农夫山泉主要港股可比公司的最新行情快照。"""
from pathlib import Path
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
import pandas as pd
import yfinance as yf

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "data" / "peer_snapshot.csv"
PEERS = {
    "9633.HK": "农夫山泉",
    "2460.HK": "华润饮料",
    "0322.HK": "康师傅控股",
    "0220.HK": "统一企业中国",
}
rows = []
now_hk = datetime.now(ZoneInfo("Asia/Hong_Kong"))
latest_complete_date = now_hk.date() if now_hk.time() >= time(16, 10) else now_hk.date() - timedelta(days=1)
for ticker, name in PEERS.items():
    obj = yf.Ticker(ticker)
    hist = obj.history(period="10d", auto_adjust=False).dropna(subset=["Close"])
    hist = hist.loc[hist.index.date <= latest_complete_date]
    if hist.empty:
        raise RuntimeError(f"{ticker} 无行情")
    info = obj.info
    last = hist.iloc[-1]
    reference_price = float(info["regularMarketPrice"])
    implied_total_shares = float(info["marketCap"]) / reference_price
    close_price = float(last["Close"])
    trailing_eps = float(info["trailingEps"])
    rows.append({
        "公司": name,
        "代码": ticker,
        "交易日": hist.index[-1].date().isoformat(),
        "股价_HKD": close_price,
        "市值_亿港元": close_price * implied_total_shares / 1e8,
        "PE_TTM": close_price / trailing_eps,
        "股息率_%": float(info.get("dividendYield", 0)) * reference_price / close_price,
        "来源": f"Yahoo Finance（{ticker}，通过yfinance读取）",
    })
pd.DataFrame(rows).to_csv(OUT, index=False, encoding="utf-8-sig", float_format="%.4f")
print(pd.DataFrame(rows).to_string(index=False))
