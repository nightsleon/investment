import os, re, json, time, math
from pathlib import Path
from datetime import datetime
import requests
import pandas as pd

BASE=Path(__file__).resolve().parents[1]
DATA=BASE/'data'; REPORTS=BASE/'年报'; CHARTS=BASE/'charts'; SCRIPTS=BASE/'scripts'
for p in [DATA,REPORTS,CHARTS,SCRIPTS]: p.mkdir(parents=True, exist_ok=True)
CODE='300760'; SECU='300760.SZ'; COMPANY='迈瑞医疗'
HEADERS={'User-Agent':'Mozilla/5.0','Referer':'http://www.cninfo.com.cn/'}

def get_json(url, params=None, method='get', data=None, timeout=30):
    if method=='post':
        r=requests.post(url,headers=HEADERS,params=params,data=data,timeout=timeout)
    else:
        r=requests.get(url,headers=HEADERS,params=params,timeout=timeout)
    r.raise_for_status()
    return r.json()

def em_report(report, pageSize=200):
    url='https://datacenter.eastmoney.com/securities/api/data/v1/get'
    params={'reportName':report,'columns':'ALL','filter':f'(SECUCODE="{SECU}")','pageSize':pageSize,'sortColumns':'REPORT_DATE','sortTypes':'-1','source':'HSF10','client':'PC'}
    j=get_json(url,params=params)
    return pd.DataFrame((j.get('result') or {}).get('data') or [])

# 1 quote
try:
    q=get_json('https://push2.eastmoney.com/api/qt/stock/get', params={'secid':'0.300760','fields':'f43,f44,f45,f46,f47,f48,f57,f58,f60,f116,f117,f162,f167,f168,f170,f171,f173,f187'})
    quote=q.get('data') or {}
except Exception as e:
    quote={'error':str(e)}
(DATA/'quote_eastmoney.json').write_text(json.dumps(quote,ensure_ascii=False,indent=2),encoding='utf-8')

# 2 financial APIs
for rpt in ['RPT_DMSK_FN_INCOME','RPT_DMSK_FN_BALANCE','RPT_DMSK_FN_CASHFLOW']:
    try:
        df=em_report(rpt)
        df.to_csv(DATA/f'{rpt}.csv',index=False,encoding='utf-8-sig')
    except Exception as e:
        print('EM fail',rpt,e)

# 3 value analysis PE history
try:
    url='https://datacenter.eastmoney.com/securities/api/data/v1/get'
    params={'reportName':'RPT_VALUEANALYSIS_DET','columns':'ALL','filter':f'(SECUCODE="{SECU}")','pageSize':5000,'sortColumns':'TRADE_DATE','sortTypes':'1','source':'HSF10','client':'PC'}
    j=get_json(url,params=params)
    pd.DataFrame((j.get('result') or {}).get('data') or []).to_csv(DATA/'pe_history.csv',index=False,encoding='utf-8-sig')
except Exception as e:
    print('PE hist fail',e)

# 4 cninfo reports 2020-2026
try:
    top=requests.post('http://www.cninfo.com.cn/new/information/topSearch/query',headers=HEADERS,data={'keyWord':COMPANY,'maxSecNum':10},timeout=20).json()
    org=None
    for item in top:
        if item.get('code')==CODE:
            org=item.get('orgId'); break
    (DATA/'cninfo_topsearch.json').write_text(json.dumps(top,ensure_ascii=False,indent=2),encoding='utf-8')
    stock=f'{CODE},{org}' if org else CODE
    data={'pageNum':1,'pageSize':50,'column':'szse','tabName':'fulltext','plate':'sz','stock':stock,'searchkey':'','secid':'','category':'category_ndbg_szsh','trade':'','seDate':'2020-01-01~2026-07-07','sortName':'','sortType':'','isHLtitle':'true'}
    j=requests.post('http://www.cninfo.com.cn/new/hisAnnouncement/query',headers={**HEADERS,'Referer':'http://www.cninfo.com.cn/new/commonUrl/pageOfSearch?url=disclosure/list/search'},data=data,timeout=30).json()
    anns=j.get('announcements') or []
    manifest=[]
    for a in anns:
        title=re.sub('<.*?>','',a.get('announcementTitle',''))
        if ('年度报告' in title or '第一季度报告' in title) and '摘要' not in title and '英文' not in title:
            url='http://static.cninfo.com.cn/'+a['adjunctUrl']
            m=re.search(r'(20\d{2})',title) or re.search(r'/(20\d{2})-',a['adjunctUrl'])
            year=m.group(1) if m else str(a.get('announcementTime',''))[:4]
            typ='Q1' if '第一季度' in title else '年度报告'
            fname=f'{year}_{COMPANY}_{typ}.pdf'
            path=REPORTS/fname
            if not path.exists() or path.stat().st_size<100000:
                rr=requests.get(url,headers=HEADERS,timeout=60)
                rr.raise_for_status(); path.write_bytes(rr.content); time.sleep(0.2)
            manifest.append({'year':year,'type':typ,'title':title,'url':url,'file':str(path.relative_to(BASE)),'bytes':path.stat().st_size})
    (REPORTS/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
except Exception as e:
    print('cninfo fail',e)

# 5 akshare data optional
try:
    import akshare as ak
    try:
        spot=ak.stock_zh_a_spot_em()
        spot[spot['代码'].astype(str).eq(CODE)].to_csv(DATA/'ak_spot.csv',index=False,encoding='utf-8-sig')
    except Exception as e: print('ak spot fail',e)
    for name, func in [('financial_indicator', lambda: ak.stock_financial_analysis_indicator(symbol=CODE)),
                       ('main_business', lambda: ak.stock_zygc_ym(symbol=CODE))]:
        try:
            df=func(); df.to_csv(DATA/f'ak_{name}.csv',index=False,encoding='utf-8-sig')
        except Exception as e: print('ak',name,'fail',e)
except Exception as e:
    print('ak import fail',e)
print('done', BASE)
