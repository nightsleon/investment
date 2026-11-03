import os, json, re, time
from pathlib import Path
import requests
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / 'data'
REPORTS = BASE / '年报'
CHARTS = BASE / 'charts'
SCRIPTS = BASE / 'scripts'
for p in [DATA, REPORTS, CHARTS, SCRIPTS]:
    p.mkdir(parents=True, exist_ok=True)

CODE = '300750'
SECU = '300750.SZ'
COMPANY = '宁德时代'
HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)', 'Referer': 'http://www.cninfo.com.cn/'}

def get_json(url, params=None, method='get', data=None, timeout=30):
    if method == 'post':
        r = requests.post(url, headers=HEADERS, params=params, data=data, timeout=timeout)
    else:
        r = requests.get(url, headers=HEADERS, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()

def em_report(report, pageSize=200):
    url = 'https://datacenter.eastmoney.com/securities/api/data/v1/get'
    params = {'reportName': report, 'columns': 'ALL', 'filter': f'(SECUCODE="{SECU}")', 'pageSize': pageSize, 'sortColumns': 'REPORT_DATE', 'sortTypes': '-1', 'source': 'HSF10', 'client': 'PC'}
    j = get_json(url, params=params)
    return pd.DataFrame((j.get('result') or {}).get('data') or [])

# 1 quote
try:
    q = get_json('https://push2.eastmoney.com/api/qt/stock/get', params={'secid': '0.300750', 'fields': 'f43,f44,f45,f46,f47,f48,f57,f58,f60,f116,f117,f162,f167,f168,f170,f171,f173,f187'})
    quote = q.get('data') or {}
except Exception as e:
    quote = {'error': str(e)}
(DATA / 'quote_eastmoney.json').write_text(json.dumps(quote, ensure_ascii=False, indent=2), encoding='utf-8')

# 2 financial APIs
for rpt in ['RPT_DMSK_FN_INCOME', 'RPT_DMSK_FN_BALANCE', 'RPT_DMSK_FN_CASHFLOW']:
    try:
        df = em_report(rpt)
        df.to_csv(DATA / f'{rpt}.csv', index=False, encoding='utf-8-sig')
    except Exception as e:
        print('EM fail', rpt, e)

# 3 value analysis PE history
try:
    url = 'https://datacenter.eastmoney.com/securities/api/data/v1/get'
    params = {'reportName': 'RPT_VALUEANALYSIS_DET', 'columns': 'ALL', 'filter': f'(SECUCODE="{SECU}")', 'pageSize': 5000, 'sortColumns': 'TRADE_DATE', 'sortTypes': '1', 'source': 'HSF10', 'client': 'PC'}
    j = get_json(url, params=params)
    pd.DataFrame((j.get('result') or {}).get('data') or []).to_csv(DATA / 'pe_history.csv', index=False, encoding='utf-8-sig')
except Exception as e:
    print('PE hist fail', e)
