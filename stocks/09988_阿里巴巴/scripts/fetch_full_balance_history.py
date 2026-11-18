#!/usr/bin/env python3
"""Fetch full balance history for Alibaba 09988.HK from Eastmoney."""
import urllib.request
import urllib.parse
import json
import pandas as pd

items = [
    "总资产", "总负债", "股东权益", "总权益", "保留溢利(累计亏损)", 
    "现金及等价物", "短期投资", "短期贷款", "长期贷款", "可转换票据及债券", 
    "商誉", "应付帐款", "物业厂房及设备", "无形资产", "受限制存款及现金"
]

results = {}
for it in items:
    f_str = f'(SECUCODE="09988.HK")(STD_ITEM_NAME="{it}")'
    url = f'https://datacenter.eastmoney.com/securities/api/data/v1/get?reportName=RPT_HKF10_FN_BALANCE_PC&columns=SECUCODE,REPORT_DATE,STD_ITEM_NAME,AMOUNT&filter={urllib.parse.quote(f_str)}&pageSize=100&source=F10&client=PC'
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

df_bal = pd.DataFrame(results)
annual_dates = [f"{y}-03-31" for y in range(2020, 2027)] + ["2026-06-30"]
df_annual = df_bal.loc[[d for d in annual_dates if d in df_bal.index]]
print((df_annual / 1e8).to_string())
df_bal.to_csv("stocks/09988_阿里巴巴/data/balance_history_all.csv", encoding="utf-8-sig")
