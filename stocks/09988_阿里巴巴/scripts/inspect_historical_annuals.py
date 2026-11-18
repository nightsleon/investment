#!/usr/bin/env python3
"""Inspect historical annual financials for Alibaba from Eastmoney and Official Filings."""
import urllib.request
import urllib.parse
import json
import pandas as pd
import numpy as np

def fetch_all(report_name):
    rows = []
    page = 1
    while True:
        url = f'https://datacenter.eastmoney.com/securities/api/data/v1/get?reportName={report_name}&columns=SECUCODE,REPORT_DATE,STD_ITEM_NAME,AMOUNT&filter=(SECUCODE=%2209988.HK%22)&pageIndex={page}&pageSize=500&source=F10&client=PC'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read())
        if not data.get('result') or not data['result'].get('data'):
            break
        for r in data['result']['data']:
            rows.append({
                'date': r.get('REPORT_DATE')[:10],
                'item': r.get('STD_ITEM_NAME'),
                'amount': float(r.get('AMOUNT')) if r.get('AMOUNT') is not None else None
            })
        if len(data['result']['data']) < 500 or page >= 10:
            break
        page += 1
    df = pd.DataFrame(rows).drop_duplicates(['date', 'item'])
    return df.pivot(index='date', columns='item', values='amount')

inc = fetch_all('RPT_HKF10_FN_INCOME_PC')
bal = fetch_all('RPT_HKF10_FN_BALANCE_PC')
cf = fetch_all('RPT_HKF10_FN_CASHFLOW_PC')

annual_dates = [d for d in inc.index if d.endswith('03-31')]
print("=== Income Statement Annuals (RMB 100M) ===")
inc_cols = [c for c in ['营业额', '毛利', '研发费用', '销售费用', '管理费用', '经营溢利', '除税前溢利', '股东应占溢利', '除税后溢利'] if c in inc.columns]
print((inc.loc[annual_dates, inc_cols] / 1e8).to_string())

print("\n=== Cash Flow Statement Annuals (RMB 100M) ===")
cf_cols = [c for c in ['经营业务现金净额', '购建固定资产', '购建无形资产及其他资产', '回购股份', '已付股息(融资)', '期末现金'] if c in cf.columns]
print((cf.loc[[d for d in annual_dates if d in cf.index], cf_cols] / 1e8).to_string())

print("\n=== Balance Sheet Statement Annuals (RMB 100M) ===")
bal_cols = [c for c in ['总资产', '总负债', '股东权益', '总权益', '现金及等价物', '短期投资', '短期贷款', '长期贷款', '商誉', '保留溢利(累计亏损)'] if c in bal.columns]
print((bal.loc[[d for d in annual_dates if d in bal.index], bal_cols] / 1e8).to_string())

