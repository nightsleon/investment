"""
Quarterly stock analysis: align financial data with stock prices, calculate TTM, output CSV.
Usage: python quarterly_analysis.py <stock_code> <exchange>
Example: python quarterly_analysis.py 002847 SZ
"""
import sys
import os
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from pathlib import Path
import json
import urllib.request

def get_financial_data(code, exchange):
    """Fetch financial data from 东方财富 API."""
    secucode = f"{code}.{exchange}"
    url = (
        f"https://datacenter.eastmoney.com/securities/api/data/v1/get?"
        f"reportName=RPT_DMSK_FN_INCOME"
        f"&columns=SECUCODE,REPORT_DATE,PARENT_NETPROFIT,DEDUCT_PARENT_NETPROFIT"
        f"&filter=(SECUCODE=%22{secucode}%22)"
        f"&pageSize=50&sortColumns=REPORT_DATE&sortTypes=-1&source=HSF10&client=PC"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())

    rows = []
    for item in data["result"]["data"]:
        rows.append({
            "date": pd.to_datetime(item["REPORT_DATE"].split(" ")[0]),
            "net_profit": item["PARENT_NETPROFIT"],
            "non_gaap": item["DEDUCT_PARENT_NETPROFIT"],
        })
    return pd.DataFrame(rows).sort_values("date").reset_index(drop=True)


def get_stock_price(code, exchange):
    """Fetch stock price from Yahoo Finance."""
    ticker = f"{code}.{exchange}"
    raw = yf.download(ticker, start="2015-01-01", end="2026-12-31", auto_adjust=False, progress=False)
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    price = raw.reset_index()[["Date", "Adj Close", "Close"]].rename(
        columns={"Date": "trade_date", "Adj Close": "adj_close", "Close": "close"}
    )
    return price.sort_values("trade_date").reset_index(drop=True)


def align_data(fin, price):
    """Align financial data with stock prices by quarter end."""
    fin["net_profit_ttm"] = fin["net_profit"].rolling(4).sum()
    fin["non_gaap_ttm"] = fin["non_gaap"].rolling(4).sum()

    matched = []
    for _, row in fin.iterrows():
        q = row["date"]
        sub = price[price["trade_date"] <= q]
        if sub.empty:
            continue
        last = sub.iloc[-1]
        matched.append({
            "quarter": f"{q.year}Q{(q.month-1)//3+1}",
            "date": q.strftime("%Y-%m-%d"),
            "trade_date": last["trade_date"].strftime("%Y-%m-%d"),
            "adj_close": round(float(last["adj_close"]), 2),
            "close": round(float(last["close"]), 2),
            "net_profit_yi": round(row["net_profit"] / 1e8, 2),
            "non_gaap_yi": round(row["non_gaap"] / 1e8, 2),
            "net_profit_ttm_yi": round(row["net_profit_ttm"] / 1e8, 2) if pd.notna(row["net_profit_ttm"]) else "",
            "non_gaap_ttm_yi": round(row["non_gaap_ttm"] / 1e8, 2) if pd.notna(row["non_gaap_ttm"]) else "",
        })
    out = pd.DataFrame(matched)
    return out[out["adj_close"] > 0].reset_index(drop=True)


def main():
    code = sys.argv[1] if len(sys.argv) > 1 else "002847"
    exchange = sys.argv[2] if len(sys.argv) > 2 else "SZ"

    print(f"Fetching financial data for {code}.{exchange}...")
    fin = get_financial_data(code, exchange)
    print(f"  Financial data: {len(fin)} quarters")

    print(f"Fetching stock price...")
    price = get_stock_price(code, exchange)
    print(f"  Price data: {len(price)} days")

    print("Aligning data...")
    out = align_data(fin, price)

    os.makedirs(code, exist_ok=True)
    outpath = f"{code}/{code}_季度数据.csv"
    out.to_csv(outpath, index=False, encoding="utf-8-sig")
    print(f"Output: {outpath} ({len(out)} quarters)")
    print(f"\n{out.tail(5).to_string(index=False)}")


if __name__ == "__main__":
    main()
