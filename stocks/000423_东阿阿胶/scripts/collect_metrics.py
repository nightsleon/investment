#!/usr/bin/env python3
from pathlib import Path
from python_calamine import CalamineWorkbook
import pandas as pd, numpy as np, urllib.request, urllib.parse, json
from datetime import datetime, timedelta

BASE=Path(__file__).resolve().parents[1]
OUT=BASE/'data'; OUT.mkdir(exist_ok=True)
CODE='000423'; MARKET='SZ'; SECU=f'{CODE}.{MARKET}'

def em(report, columns='ALL', filter=None, sort='REPORT_DATE', pages=5, source='HSF10'):
    all=[]
    for page in range(1,pages+1):
        params={'reportName':report,'columns':columns,'filter':filter or f'(SECUCODE="{SECU}")','pageSize':'100','pageNumber':str(page),'sortColumns':sort,'sortTypes':'-1','source':source,'client':'PC'}
        url='https://datacenter.eastmoney.com/securities/api/data/v1/get?'+urllib.parse.urlencode(params)
        req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Referer':'https://emweb.securities.eastmoney.com/'})
        data=json.loads(urllib.request.urlopen(req,timeout=20).read())
        rows=(data.get('result') or {}).get('data') or []
        if not rows: break
        all.extend(rows)
    return pd.DataFrame(all)

def read_xls(path):
    rows=CalamineWorkbook.from_path(str(path)).get_sheet_by_index(0).to_python()
    cols=rows[0][1:]
    data={r[0]:r[1:] for r in rows[1:]}
    df=pd.DataFrame(data,index=cols)
    return df

year=read_xls(OUT/'000423_main_year.xls')
simple=read_xls(OUT/'000423_main_simple.xls')
# clean annual selected
ann=pd.DataFrame(index=[int(x) for x in year.index[:10]])
for src,dst in [('营业总收入(元)','营收'),('净利润(元)','净利润'),('扣非净利润(元)','扣非净利润'),('基本每股收益(元)','EPS'),('每股经营现金流(元)','每股经营现金流')]:
    ann[dst]=pd.to_numeric(list(year[src])[:10], errors='coerce')
for src,dst in [('销售净利率','净利率'),('销售毛利率','毛利率'),('净资产收益率','ROE加权'),('资产负债率','资产负债率')]:
    ann[dst]=[float(str(x).replace('%','')) if pd.notna(x) and str(x)!='--' else np.nan for x in list(year[src])[:10]]
ann=ann.sort_index()
for c in ['营收','净利润','扣非净利润']:
    ann[c]=ann[c]/1e8
# cashflow and balance
cf=em('RPT_DMSK_FN_CASHFLOW', columns='SECUCODE,REPORT_DATE,NETCASH_OPERATE,CONSTRUCT_LONG_ASSET', pages=3)
bs=em('RPT_DMSK_FN_BALANCE', columns='SECUCODE,REPORT_DATE,TOTAL_ASSETS,TOTAL_LIABILITIES,TOTAL_EQUITY,MONETARYFUNDS,ACCOUNTS_RECE,INVENTORY,ADVANCE_RECEIVABLES,SHORT_LOAN', pages=3)
inc=em('RPT_DMSK_FN_INCOME', columns='SECUCODE,REPORT_DATE,TOTAL_OPERATE_INCOME,PARENT_NETPROFIT,DEDUCT_PARENT_NETPROFIT', pages=3)
for df in [cf,bs,inc]: df['date']=pd.to_datetime(df['REPORT_DATE'])
annual_cf=cf[cf.date.dt.month.eq(12)].copy(); annual_cf['year']=annual_cf.date.dt.year
annual_bs=bs[bs.date.dt.month.eq(12)].copy(); annual_bs['year']=annual_bs.date.dt.year
# Build cash table 2020-2025
cash=[]
for y in range(2020,2026):
    rcf=annual_cf[annual_cf.year==y]
    if rcf.empty: continue
    net=float(rcf.iloc[0].get('NETCASH_OPERATE') or 0)/1e8
    capex=float(rcf.iloc[0].get('CONSTRUCT_LONG_ASSET') or 0)/1e8
    npv=float(ann.loc[y,'净利润']) if y in ann.index else np.nan
    cash.append({'年份':y,'经营现金流':net,'资本开支':capex,'自由现金流':net-capex,'净利润':npv,'经营现金流/净利润':net/npv if npv else np.nan,'自由现金流/净利润':(net-capex)/npv if npv else np.nan})
cash=pd.DataFrame(cash)
# DuPont 2020-2025 using annual avg assets/equity
rows=[]
for y in range(2020,2026):
    b0=annual_bs[annual_bs.year==y-1]; b1=annual_bs[annual_bs.year==y]
    if b0.empty or b1.empty or y not in ann.index: continue
    avg_assets=(float(b0.iloc[0].TOTAL_ASSETS)+float(b1.iloc[0].TOTAL_ASSETS))/2/1e8
    avg_equity=(float(b0.iloc[0].TOTAL_EQUITY)+float(b1.iloc[0].TOTAL_EQUITY))/2/1e8
    rev=float(ann.loc[y,'营收']); net=float(ann.loc[y,'净利润'])
    rows.append({'年份':y,'净利率%':net/rev*100,'总资产周转率':rev/avg_assets,'权益乘数':avg_assets/avg_equity,'ROE估算%':net/avg_equity*100,'ROE加权%':ann.loc[y,'ROE加权']})
dup=pd.DataFrame(rows)
# valuation latest and PE percentile
val=em('RPT_VALUEANALYSIS_DET', columns='SECUCODE,TRADE_DATE,TOTAL_MARKET_CAP,CLOSE_PRICE,TOTAL_SHARES,PE_TTM,PB_MRQ,PS_TTM,PCF_OCF_TTM', sort='TRADE_DATE', pages=30, source='HSF10')
val['TRADE_DATE']=pd.to_datetime(val['TRADE_DATE'])
latest=val.sort_values('TRADE_DATE').iloc[-1].to_dict()
cut=pd.Timestamp(datetime.now().date()-timedelta(days=365*10+3))
pe_hist=pd.to_numeric(val[val.TRADE_DATE>=cut]['PE_TTM'], errors='coerce').dropna()
cur_pe=float(latest['PE_TTM'])
pe_pct=(pe_hist<cur_pe).mean()*100
# latest Q TTM from simple
sd=simple.copy(); sd.index=pd.to_datetime(sd.index); sd=sd.sort_index()
non=pd.to_numeric(sd['扣非净利润(元)'],errors='coerce')/1e8
npq=pd.to_numeric(sd['净利润(元)'],errors='coerce')/1e8
revq=pd.to_numeric(sd['营业总收入(元)'],errors='coerce')/1e8
ttm=pd.DataFrame({'扣非':non,'净利':npq,'营收':revq})
ttm['扣非TTM']=ttm['扣非'].rolling(4).sum(); ttm['净利TTM']=ttm['净利'].rolling(4).sum(); ttm['营收TTM']=ttm['营收'].rolling(4).sum()
# peers latest
peers=['600436.SH','600085.SH','000538.SZ','000999.SZ','600332.SH','600535.SH']
peer_rows=[]
for sec in peers:
    try:
        d=em('RPT_VALUEANALYSIS_DET', columns='SECUCODE,SECURITY_NAME_ABBR,TRADE_DATE,TOTAL_MARKET_CAP,CLOSE_PRICE,PE_TTM,PB_MRQ', filter=f'(SECUCODE="{sec}")', sort='TRADE_DATE', pages=1).iloc[0]
        peer_rows.append({'代码':sec,'名称':d.SECURITY_NAME_ABBR,'日期':str(d.TRADE_DATE)[:10],'股价':d.CLOSE_PRICE,'市值亿元':float(d.TOTAL_MARKET_CAP)/1e8,'PE_TTM':d.PE_TTM,'PB':d.PB_MRQ})
    except Exception as e: peer_rows.append({'代码':sec,'error':str(e)})
peers_df=pd.DataFrame(peer_rows)
# save
ann.round(4).to_csv(OUT/'000423_annual_metrics.csv',encoding='utf-8-sig')
cash.round(4).to_csv(OUT/'000423_cashflow_metrics.csv',index=False,encoding='utf-8-sig')
dup.round(4).to_csv(OUT/'000423_dupont.csv',index=False,encoding='utf-8-sig')
ttm.round(4).to_csv(OUT/'000423_quarter_ttm_from_ths.csv',encoding='utf-8-sig')
peers_df.round(4).to_csv(OUT/'000423_peers_valuation.csv',index=False,encoding='utf-8-sig')
summary={
 'latest_trade_date':str(latest['TRADE_DATE'].date()),'close':float(latest['CLOSE_PRICE']),'market_cap_yi':float(latest['TOTAL_MARKET_CAP'])/1e8,
 'total_shares_yi':float(latest['TOTAL_SHARES'])/1e8,'pe_ttm':cur_pe,'pb':float(latest['PB_MRQ']),'ps_ttm':float(latest['PS_TTM']),'pcf_ocf_ttm':float(latest['PCF_OCF_TTM']),'pe_percentile_10y':pe_pct,
 'latest_quarter':str(ttm.index[-1].date()),'deduct_ttm_yi':float(ttm.iloc[-1]['扣非TTM']),'net_ttm_yi':float(ttm.iloc[-1]['净利TTM']),'rev_ttm_yi':float(ttm.iloc[-1]['营收TTM']),
 'cash_position_2025_yi':(5267456076.17+3815103071.18+109185753.42-20788859.52-38631469.59)/1e8,
 'cash_position_per_share':(5267456076.17+3815103071.18+109185753.42-20788859.52-38631469.59)/643976824,
 'ex_cash_market_cap_yi':float(latest['TOTAL_MARKET_CAP'])/1e8 - (5267456076.17+3815103071.18+109185753.42-20788859.52-38631469.59)/1e8,
 'ex_cash_pe':(float(latest['TOTAL_MARKET_CAP'])/1e8 - (5267456076.17+3815103071.18+109185753.42-20788859.52-38631469.59)/1e8)/float(ttm.iloc[-1]['扣非TTM']),
 'dividend_per_share_2025_annual_final':14.354904/10,
 'dividend_yield_2025_annual_final_on_latest_close':(14.354904/10)/float(latest['CLOSE_PRICE'])*100,
 'dividend_per_share_2025_interim':12.700919/10,
 'dividend_yield_2025_interim_on_latest_close':(12.700919/10)/float(latest['CLOSE_PRICE'])*100,
 'dividend_per_share_2025_full_year':(14.354904+12.700919)/10,
 'dividend_yield_2025_full_year_on_latest_close':((14.354904+12.700919)/10)/float(latest['CLOSE_PRICE'])*100,
 'dividend_cash_2025_full_year_yi':((14.354904+12.700919)/10)*float(latest['TOTAL_SHARES'])/1e8,
 'dividend_payout_2025_full_year_to_net_profit':(((14.354904+12.700919)/10)*float(latest['TOTAL_SHARES'])/1e8)/float(ann.loc[2025,'净利润']),
 'deduct_np_3y_cagr_2022_2025':(float(ann.loc[2025,'扣非净利润'])/float(ann.loc[2022,'扣非净利润']))**(1/3)-1,
 'deduct_np_5y_cagr_2020_2025':(float(ann.loc[2025,'扣非净利润'])/abs(float(ann.loc[2020,'扣非净利润'])))**(1/5)-1 if ann.loc[2020,'扣非净利润']>0 else None
}
(OUT/'000423_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
print('\nANNUAL\n',ann.tail(6).round(3).to_string())
print('\nCASH\n',cash.round(3).to_string(index=False))
print('\nDUPONT\n',dup.round(3).to_string(index=False))
print('\nPEERS\n',peers_df.round(3).to_string(index=False))
