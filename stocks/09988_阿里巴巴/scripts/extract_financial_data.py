#!/usr/bin/env python3
"""Extract and align Alibaba 09988.HK financial data from Eastmoney and Official Filings."""
import urllib.request
import urllib.parse
import json
import pandas as pd
import numpy as np

def fetch_eastmoney(report_name, filter_str):
    url = f'https://datacenter.eastmoney.com/securities/api/data/v1/get?reportName={report_name}&columns=SECUCODE,REPORT_DATE,STD_ITEM_NAME,AMOUNT&filter={urllib.parse.quote(filter_str)}&pageSize=500&source=F10&client=PC'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=12) as resp:
        return json.loads(resp.read())

# Fetch income, balance, cashflow
income_data = fetch_eastmoney('RPT_HKF10_FN_INCOME_PC', '(SECUCODE="09988.HK")')
balance_data = fetch_eastmoney('RPT_HKF10_FN_BALANCE_PC', '(SECUCODE="09988.HK")')
cashflow_data = fetch_eastmoney('RPT_HKF10_FN_CASHFLOW_PC', '(SECUCODE="09988.HK")')

def to_pivot(res_json):
    if not res_json.get('result') or not res_json['result'].get('data'):
        return pd.DataFrame()
    rows = []
    for r in res_json['result']['data']:
        rows.append({
            'date': r.get('REPORT_DATE')[:10],
            'item': r.get('STD_ITEM_NAME'),
            'amount': float(r.get('AMOUNT')) if r.get('AMOUNT') is not None else np.nan
        })
    df = pd.DataFrame(rows).drop_duplicates(['date', 'item'])
    return df.pivot(index='date', columns='item', values='amount')

p_inc = to_pivot(income_data)
p_bal = to_pivot(balance_data)
p_cf = to_pivot(cashflow_data)

print("Income dates:", list(p_inc.index))
print("Income columns:", list(p_inc.columns)[:15])
print("\nBalance dates:", list(p_bal.index))
print("Balance columns:", list(p_bal.columns)[:15])
print("\nCashflow dates:", list(p_cf.index))
print("Cashflow columns:", list(p_cf.columns)[:15])

# Let's inspect annual dates (03-31 for Alibaba!)
annual_dates = [d for d in p_inc.index if d.endswith('03-31')]
print("\nAnnual dates (FY ending March 31):", annual_dates)

