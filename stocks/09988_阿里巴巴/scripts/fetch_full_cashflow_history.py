#!/usr/bin/env python3
"""Fetch full cashflow history for Alibaba 09988.HK from Eastmoney."""
import urllib.request
import urllib.parse
import json
import pandas as pd

items = [
    "经营业务现金净额", "经营产生现金", "购建固定资产", "购建无形资产及其他资产",
    "已付股息(融资)", "回购股份", "偿还借款", "新增借款", "发行债券",
    "期初现金", "期末现金", "现金净额"
]

results = {}
for it in items:
    f_str = f'(SECUCODE="09988.HK")(STD_ITEM_NAME="{it}")'
    url = f'https://datacenter.eastmoney.com/securities/api/data/v1/get?reportName=RPT_HKF10_FN_CASHFLOW_PC&columns=SECUCODE,REPORT_DATE,STD_ITEM_NAME,AMOUNT&filter={urllib.parse.quote(f_str)}&pageSize=100&source=F10&client=PC'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            series = {}
            for r in data.get('result', {}).get('data', []):
                series[r.get('REPORT_DATE')[:10]] = float(r.get('AMOUNT')) if r.get('AMOUNT') is not None else None
            results[it] = series
    except Exception as e:
        print(f"Error fetching {it}: {e}")

df_cf = pd.DataFrame(results)
annual_dates = [f"{y}-03-31" for y in range(2020, 2027)] + ["2026-06-30"]
df_annual = df_cf.loc[[d for d in annual_dates if d in df_cf.index]]
print((df_annual / 1e8).to_string())
df_cf.to_csv("stocks/09988_阿里巴巴/data/cashflow_history_all.csv", encoding="utf-8-sig")
