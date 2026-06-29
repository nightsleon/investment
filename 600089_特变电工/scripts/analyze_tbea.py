import requests, json, math, os
from pathlib import Path
import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
from matplotlib import font_manager

BASE=Path(__file__).resolve().parents[1]
DATA=BASE/'data'; CHARTS=BASE/'charts'; REPORTS=BASE/'reports'
for p in [DATA,CHARTS,REPORTS]: p.mkdir(parents=True, exist_ok=True)
CODE='600089'; SECU='600089.SH'; YF='600089.SS'; NAME='特变电工'

session=requests.Session(); session.headers.update({'User-Agent':'Mozilla/5.0','Referer':'https://emweb.securities.eastmoney.com/'})
def em(report, filt=f'(SECUCODE="{SECU}")', page=200, sort='REPORT_DATE', st='-1', source='HSF10'):
    url='https://datacenter.eastmoney.com/securities/api/data/v1/get'
    params={'reportName':report,'columns':'ALL','filter':filt,'pageSize':page,'source':source,'client':'PC'}
    if sort:
        params.update({'sortColumns':sort,'sortTypes':st})
    r=session.get(url,params=params,timeout=25); r.raise_for_status(); j=r.json()
    if not j.get('success'):
        raise RuntimeError(f'{report} failed: {j}')
    return (j.get('result') or {}).get('data') or []

def em_web(report, filt, page=100, sort='REPORT_DATE', st='-1'):
    url='https://datacenter-web.eastmoney.com/api/data/v1/get'
    params={'reportName':report,'columns':'ALL','filter':filt,'pageSize':page,'sortColumns':sort,'sortTypes':st,'source':'WEB','client':'WEB'}
    r=session.get(url,params=params,timeout=25); r.raise_for_status(); j=r.json()
    if not j.get('success'):
        return []
    return (j.get('result') or {}).get('data') or []

def yi(x):
    return None if x is None or (isinstance(x,float) and math.isnan(x)) else x/1e8

def pct(x):
    return None if x is None or (isinstance(x,float) and math.isnan(x)) else x

# Fetch
basic=em('RPT_F10_ORG_BASICINFO', page=1, sort=None)[0]
main=em('RPT_F10_FINANCE_MAINFINADATA', page=80)
income=em('RPT_DMSK_FN_INCOME', page=80)
bal=em('RPT_F10_FINANCE_GBALANCE', page=80)
cash=em('RPT_F10_FINANCE_GCASHFLOW', page=80)
products=em('RPT_F10_FN_MAINOP', filt=f'(SECUCODE="{SECU}")(REPORT_DATE=\'2025-12-31\')', page=100, sort='MAINOP_TYPE,RANK', st='1,1')
bonus=em_web('RPT_SHAREBONUS_DET', f'(SECURITY_CODE="{CODE}")', page=30)

# Normalize dfs
main_df=pd.DataFrame(main); main_df['date']=pd.to_datetime(main_df['REPORT_DATE']); main_df=main_df.sort_values('date')
income_df=pd.DataFrame(income); income_df['date']=pd.to_datetime(income_df['REPORT_DATE']); income_df=income_df.sort_values('date')
bal_df=pd.DataFrame(bal); bal_df['date']=pd.to_datetime(bal_df['REPORT_DATE']); bal_df=bal_df.sort_values('date')
cash_df=pd.DataFrame(cash); cash_df['date']=pd.to_datetime(cash_df['REPORT_DATE']); cash_df=cash_df.sort_values('date')

# annual table 2020-2025
annual=main_df[main_df['date'].dt.month.eq(12)].copy().tail(6)
rows=[]
for _,r in annual.iterrows():
    y=r['date'].year
    c=cash_df[cash_df['date'].eq(r['date'])]
    b=bal_df[bal_df['date'].eq(r['date'])]
    ocf=c.iloc[0]['NETCASH_OPERATE'] if not c.empty else np.nan
    capex=c.iloc[0]['CONSTRUCT_LONG_ASSET'] if not c.empty else np.nan
    fcf=ocf-capex if pd.notna(ocf) and pd.notna(capex) else np.nan
    rows.append({
        '年份':y,'营收(亿)':yi(r['TOTALOPERATEREVE']),'归母净利(亿)':yi(r['PARENTNETPROFIT']),'扣非净利(亿)':yi(r['KCFJCXSYJLR']),
        '毛利率%':r.get('XSMLL'),'净利率%':r.get('XSJLL'),'ROE%':r.get('ROEJQ'),'资产负债率%':r.get('ZCFZL'),
        '总资产周转率':r.get('TOAZZL'),'权益乘数':r.get('QYCS'),
        '经营现金流(亿)':yi(ocf),'资本开支(亿)':yi(capex),'自由现金流(亿)':yi(fcf),
        '应收账款(亿)': yi(b.iloc[0]['ACCOUNTS_RECE']) if not b.empty else None,
        '存货(亿)': yi(b.iloc[0]['INVENTORY']) if not b.empty else None,
        '合同负债(亿)': yi(b.iloc[0]['CONTRACT_LIAB']) if not b.empty else None,
        '货币资金(亿)': yi(b.iloc[0]['MONETARYFUNDS']) if not b.empty else None,
    })
annual_out=pd.DataFrame(rows)
annual_out.to_csv(DATA/'annual_financials_2020_2025.csv',index=False,encoding='utf-8-sig')

# quarterly single-quarter from cumulative income/main
q=main_df.copy()
q['year']=q['date'].dt.year; q['qtr']=q['date'].dt.quarter
for col in ['TOTALOPERATEREVE','PARENTNETPROFIT','KCFJCXSYJLR','EPSJB']:
    q[col+'_single']=q.groupby('year')[col].diff()
    q.loc[q['qtr'].eq(1), col+'_single']=q.loc[q['qtr'].eq(1), col]
q['deduct_ttm']=q['KCFJCXSYJLR_single'].rolling(4).sum()
q['net_ttm']=q['PARENTNETPROFIT_single'].rolling(4).sum()
q_out=q[['date','REPORT_DATE_NAME','TOTALOPERATEREVE_single','PARENTNETPROFIT_single','KCFJCXSYJLR_single','deduct_ttm','net_ttm']].copy()
for col in ['TOTALOPERATEREVE_single','PARENTNETPROFIT_single','KCFJCXSYJLR_single','deduct_ttm','net_ttm']:
    q_out[col]=q_out[col]/1e8
q_out.to_csv(DATA/'quarterly_profit_ttm.csv',index=False,encoding='utf-8-sig')

# yfinance price data
hist=yf.download(YF,start='2016-01-01',progress=False,auto_adjust=False)
if isinstance(hist.columns,pd.MultiIndex): hist.columns=hist.columns.get_level_values(0)
hist=hist.reset_index(); hist['Date']=pd.to_datetime(hist['Date']).dt.tz_localize(None)
latest=hist.dropna(subset=['Close']).iloc[-1]
last_price=float(latest['Close']); last_date=latest['Date'].strftime('%Y-%m-%d')
shares=5052792571
marketcap=last_price*shares/1e8
# match quarter end price
matched=[]
for _,r in q.dropna(subset=['deduct_ttm']).iterrows():
    sub=hist[hist['Date']<=r['date']]
    if sub.empty: continue
    p=sub.iloc[-1]
    pe=(float(p['Close'])*shares)/(r['deduct_ttm']) if r['deduct_ttm'] and r['deduct_ttm']>0 else np.nan
    matched.append({'date':r['date'],'quarter':r['REPORT_DATE_NAME'],'close':float(p['Close']),'adj_close':float(p['Adj Close']),'deduct_ttm_yi':r['deduct_ttm']/1e8,'net_ttm_yi':r['net_ttm']/1e8,'pe_quarter':pe})
match=pd.DataFrame(matched)
match.to_csv(DATA/'price_profit_matched.csv',index=False,encoding='utf-8-sig')

# Latest valuation
latest_q=q.iloc[-1]
latest_deduct_ttm=latest_q['deduct_ttm']/1e8
latest_net_ttm=latest_q['net_ttm']/1e8
pe_ttm=marketcap/latest_deduct_ttm
pe_series=match[match['date']>=pd.Timestamp('2016-01-01')]['pe_quarter'].dropna()
pe_pct=float((pe_series<=pe_ttm).mean()*100) if len(pe_series)>0 else np.nan

# Cash position: conservative using 2025 annual audited API fields, notes not fetched
b2025=bal_df[bal_df['date'].dt.strftime('%Y-%m-%d').eq('2025-12-31')].iloc[0]
def nz(v):
    return 0 if v is None or pd.isna(v) else v
cash_pos=nz(b2025.get('MONETARYFUNDS'))+nz(b2025.get('FVTPL_FINASSET'))+nz(b2025.get('APPOINT_FVTPL_FINASSET'))+nz(b2025.get('TRADE_FINASSET_NOTFVTPL'))+nz(b2025.get('CREDITOR_INVEST'))
long_debt=nz(b2025.get('LONG_LOAN'))+nz(b2025.get('NONCURRENT_LIAB_1YEAR'))+nz(b2025.get('BOND_PAYABLE'))+nz(b2025.get('LEASE_LIAB'))
net_cash=(cash_pos-long_debt)/1e8
cash_components={
 '货币资金(亿)':yi(b2025.get('MONETARYFUNDS')), '交易性/债权投资等可见金融资产(亿)':yi(nz(b2025.get('FVTPL_FINASSET'))+nz(b2025.get('APPOINT_FVTPL_FINASSET'))+nz(b2025.get('TRADE_FINASSET_NOTFVTPL'))+nz(b2025.get('CREDITOR_INVEST'))),
 '长期借款(亿)':yi(b2025.get('LONG_LOAN')), '一年内到期非流动负债(亿)':yi(b2025.get('NONCURRENT_LIAB_1YEAR')), '应付债券(亿)':yi(b2025.get('BOND_PAYABLE')), '租赁负债(亿)':yi(b2025.get('LEASE_LIAB')), '保守现金头寸(亿)':net_cash
}

# Products 2025 by product type MAINOP_TYPE=2
prod=pd.DataFrame(products)
prod2=prod[prod['MAINOP_TYPE'].astype(str).eq('2')].copy()
prod2['收入(亿)']=prod2['MAIN_BUSINESS_INCOME']/1e8
prod2['占比%']=prod2['MBI_RATIO']*100
prod2['毛利率%']=prod2['GROSS_RPOFIT_RATIO']*100
prod2[['ITEM_NAME','收入(亿)','占比%','毛利率%']].to_csv(DATA/'product_structure_2025.csv',index=False,encoding='utf-8-sig')

# Dividends
bonus_df=pd.DataFrame(bonus)
if not bonus_df.empty:
    bonus_df['REPORT_DATE']=pd.to_datetime(bonus_df['REPORT_DATE'])
    bonus_out=bonus_df[['REPORT_DATE','PRETAX_BONUS_RMB','IMPL_PLAN_PROFILE','ASSIGN_PROGRESS','BASIC_EPS']].head(8)
    bonus_out.to_csv(DATA/'dividends.csv',index=False,encoding='utf-8-sig')

# Peers current from yf
peers={'中国西电':'601179.SS','思源电气':'002028.SZ','平高电气':'600312.SS','正泰电器':'601877.SS','通威股份':'600438.SS','大全能源':'688303.SS'}
peer_rows=[]
for n,t in peers.items():
    try:
        tk=yf.Ticker(t); fi=tk.fast_info; h=tk.history(period='5d')
        price=float(h['Close'].dropna().iloc[-1]) if not h.empty else np.nan
        mc=float(fi.get('marketCap') or np.nan)/1e8
        peer_rows.append({'公司':n,'代码':t,'最新价':price,'市值(亿)':mc})
    except Exception as e:
        peer_rows.append({'公司':n,'代码':t,'最新价':np.nan,'市值(亿)':np.nan})
pd.DataFrame(peer_rows).to_csv(DATA/'peer_market_caps.csv',index=False,encoding='utf-8-sig')

# Charts font
font_path=None
for fp in ['/System/Library/Fonts/Hiragino Sans GB.ttc','/System/Library/Fonts/STHeiti Medium.ttc','/System/Library/Fonts/Supplemental/Arial Unicode.ttf']:
    if Path(fp).exists(): font_path=fp; break
if font_path:
    font_manager.fontManager.addfont(font_path); fp=font_manager.FontProperties(fname=font_path); plt.rcParams['font.sans-serif']=[fp.get_name()]
plt.rcParams['axes.unicode_minus']=False

# Chart 1 normalized
m=match[match['deduct_ttm_yi']>0].copy()
base=m.iloc[0]
fig,ax=plt.subplots(figsize=(14,7),dpi=160)
ax.plot(m['date'],m['adj_close']/base['adj_close'],marker='o',lw=2.2,label='股价(前复权)')
ax.plot(m['date'],m['deduct_ttm_yi']/base['deduct_ttm_yi'],marker='s',lw=2.2,label='扣非TTM')
ax.set_title('特变电工：股价 vs 扣非TTM归一化（只看趋势，不看高低）')
ax.grid(alpha=.25); ax.legend(); fig.autofmt_xdate(); fig.tight_layout()
fig.savefig(CHARTS/'600089_归一化_股价vs扣非TTM.png'); plt.close(fig)

# Chart 2 dual axis
fig,ax1=plt.subplots(figsize=(14,7),dpi=160); ax2=ax1.twinx()
l1=ax1.plot(m['date'],m['adj_close'],marker='o',lw=2.2,color='#1f77b4',label='股价(前复权)')
l2=ax2.plot(m['date'],m['deduct_ttm_yi'],marker='s',lw=2.2,color='#d95f02',label='扣非TTM(亿)')
ax1.set_ylabel('股价(元)'); ax2.set_ylabel('扣非TTM(亿元)')
ax1.set_title('特变电工：股价 vs 扣非净利润TTM（双Y轴）')
ax1.grid(alpha=.25); lines=l1+l2; ax1.legend(lines,[l.get_label() for l in lines],loc='upper left'); fig.autofmt_xdate(); fig.tight_layout()
fig.savefig(CHARTS/'600089_股价vs扣非净利润TTM_双Y轴.png'); plt.close(fig)

# Chart 3 single q
fig,ax1=plt.subplots(figsize=(14,7),dpi=160); ax2=ax1.twinx()
l1=ax1.plot(match['date'],match['adj_close'],marker='o',lw=2.0,color='#1f77b4',label='股价(前复权)')
l2=ax2.plot(q_out['date'],q_out['KCFJCXSYJLR_single'],marker='s',lw=2.0,color='#2ca02c',label='单季度扣非(亿)')
ax1.set_ylabel('股价(元)'); ax2.set_ylabel('单季度扣非净利润(亿元)')
ax1.set_title('特变电工：股价 vs 单季度扣非净利润')
ax1.grid(alpha=.25); lines=l1+l2; ax1.legend(lines,[l.get_label() for l in lines],loc='upper left'); fig.autofmt_xdate(); fig.tight_layout()
fig.savefig(CHARTS/'600089_股价vs扣非净利润_单季度.png'); plt.close(fig)

# Chart 4 annual fundamentals
fig,axs=plt.subplots(2,1,figsize=(13,9),dpi=160,sharex=True)
a=annual_out
axs[0].bar(a['年份']-0.15,a['营收(亿)'],width=.3,label='营收(亿)',color='#8ecae6')
axs[0].bar(a['年份']+0.15,a['扣非净利(亿)'],width=.3,label='扣非净利(亿)',color='#fb8500')
axs[0].set_title('营收基本横盘，利润随硅料/煤炭周期大幅波动')
axs[0].legend(); axs[0].grid(axis='y',alpha=.25)
axs[1].plot(a['年份'],a['ROE%'],marker='o',label='ROE%')
axs[1].plot(a['年份'],a['净利率%'],marker='s',label='净利率%')
axs[1].plot(a['年份'],a['资产负债率%'],marker='^',label='资产负债率%')
axs[1].legend(); axs[1].grid(alpha=.25)
fig.tight_layout(); fig.savefig(CHARTS/'600089_年度基本面.png'); plt.close(fig)

summary={
 'latest_date':last_date,'latest_price':last_price,'shares':shares,'marketcap_yi':marketcap,
 'latest_deduct_ttm_yi':latest_deduct_ttm,'latest_net_ttm_yi':latest_net_ttm,'pe_ttm':pe_ttm,'pe_quarter_percentile_approx':pe_pct,
 'cash_components':cash_components,'cash_position_yi':net_cash,
 'deduct_3y_cagr_2023_2026ttm': (latest_deduct_ttm/(annual_out[annual_out['年份'].eq(2023)]['扣非净利(亿)'].iloc[0]))**(1/3)-1,
 'deduct_5y_cagr_2020_2025': (annual_out[annual_out['年份'].eq(2025)]['扣非净利(亿)'].iloc[0]/annual_out[annual_out['年份'].eq(2020)]['扣非净利(亿)'].iloc[0])**(1/5)-1,
 'q1_2026_rev_yoy': main_df.iloc[-1]['TOTALOPERATEREVETZ'], 'q1_2026_deduct_yoy': main_df.iloc[-1]['KCFJCXSYJLRTZ'], 'q1_2026_parent_yoy': main_df.iloc[-1]['PARENTNETPROFITTZ'],
 'data_source':'东方财富财务API + yfinance行情；现金头寸为API字段保守估算，未逐项查PDF附注定期存款。'
}
(DATA/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
print('created', BASE)
