#!/usr/bin/env python3
from pathlib import Path
import json, math, re
import pandas as pd
import numpy as np
import akshare as ak
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / 'data'
CHARTS = BASE / 'charts'
DATA.mkdir(exist_ok=True); CHARTS.mkdir(exist_ok=True)
CODE='300573'
NAME='兴齐眼药'

FONT_CANDIDATES = [
    '/System/Library/Fonts/Hiragino Sans GB.ttc',
    '/System/Library/Fonts/STHeiti Medium.ttc',
    '/System/Library/Fonts/Supplemental/Arial Unicode.ttf',
    '/System/Library/Fonts/PingFang.ttc',
]
FONT_PROP=None
for p in FONT_CANDIDATES:
    if Path(p).exists():
        FONT_PROP=fm.FontProperties(fname=p)
        plt.rcParams['font.family']=FONT_PROP.get_name()
        break
plt.rcParams['axes.unicode_minus']=False

def cn_to_yi(x):
    if x is None or x is False or (isinstance(x,float) and math.isnan(x)): return np.nan
    if isinstance(x,(int,float,np.integer,np.floating)): return float(x)/1e8
    s=str(x).strip().replace(',','')
    if s in ('','False','--','None','nan'): return np.nan
    neg=s.startswith('-')
    if neg: s=s[1:]
    mult=1
    if s.endswith('万'):
        mult=1e4; s=s[:-1]
    elif s.endswith('亿'):
        mult=1e8; s=s[:-1]
    try:
        val=float(s)*mult/1e8
        return -val if neg else val
    except: return np.nan

def pct(x):
    if x is None or x is False: return np.nan
    if isinstance(x,(int,float,np.integer,np.floating)): return float(x)
    s=str(x).strip().replace('%','')
    if s in ('','False','--','None','nan'): return np.nan
    try: return float(s)
    except: return np.nan

# annual financial statements from THS via akshare
benefit=ak.stock_financial_benefit_ths(symbol=CODE, indicator='按年度')
debt=ak.stock_financial_debt_ths(symbol=CODE, indicator='按年度')
cash=ak.stock_financial_cash_ths(symbol=CODE, indicator='按年度')
abstract=ak.stock_financial_abstract(symbol=CODE)
for name,df in [('benefit',benefit),('debt',debt),('cash',cash),('abstract',abstract)]:
    df.to_csv(DATA/f'{CODE}_{name}_raw.csv', index=False, encoding='utf-8-sig')

years=list(range(2020,2026))
rows=[]
for y in years:
    ys=str(y)
    b=benefit[benefit['报告期'].astype(str)==ys].iloc[0]
    d=debt[debt['报告期'].astype(str)==ys].iloc[0]
    c=cash[cash['报告期'].astype(str)==ys].iloc[0]
    revenue=cn_to_yi(b['*营业总收入'])
    net=cn_to_yi(b['*归属于母公司所有者的净利润'])
    deduct=cn_to_yi(b['*扣除非经常性损益后的净利润'])
    cost=cn_to_yi(b['其中：营业成本'])
    sales=cn_to_yi(b['销售费用']); admin=cn_to_yi(b['管理费用']); rd=cn_to_yi(b['研发费用'])
    total_assets=cn_to_yi(d['资产合计']); equity=cn_to_yi(d['归属于母公司所有者权益合计'])
    debt_total=cn_to_yi(d['负债合计'])
    money=cn_to_yi(d['货币资金']); other_current=cn_to_yi(d['其他流动资产'])
    trading=cn_to_yi(d['交易性金融资产']) if '交易性金融资产' in d else np.nan
    st_borrow=cn_to_yi(d['短期借款'])
    one_year=cn_to_yi(d['一年内到期的非流动负债']) if '一年内到期的非流动负债' in d else np.nan
    long_borrow=cn_to_yi(d['长期借款']) if '长期借款' in d else np.nan
    bonds=cn_to_yi(d['应付债券']) if '应付债券' in d else np.nan
    lease=cn_to_yi(d['租赁负债']) if '租赁负债' in d else np.nan
    ar=cn_to_yi(d['应收账款']) if '应收账款' in d else np.nan
    notes=cn_to_yi(d['其中：应收票据']) if '其中：应收票据' in d else np.nan
    fin_rec=cn_to_yi(d['应收款项融资']) if '应收款项融资' in d else np.nan
    inventory=cn_to_yi(d['存货']); contract=cn_to_yi(d['合同负债']) if '合同负债' in d else np.nan
    cfo=cn_to_yi(c['*经营活动产生的现金流量净额'])
    capex=cn_to_yi(c['购建固定资产、无形资产和其他长期资产支付的现金'])
    dividend=cn_to_yi(c['分配股利、利润或偿付利息支付的现金']) if '分配股利、利润或偿付利息支付的现金' in c else np.nan
    rows.append(dict(year=y,revenue_yi=revenue,net_profit_yi=net,non_gaap_yi=deduct,cost_yi=cost,
                     gross_margin=(revenue-cost)/revenue*100 if revenue else np.nan,
                     net_margin=net/revenue*100 if revenue else np.nan,
                     sales_expense_yi=sales,admin_expense_yi=admin,rd_expense_yi=rd,rd_ratio=rd/revenue*100 if revenue else np.nan,
                     total_assets_yi=total_assets,equity_yi=equity,debt_yi=debt_total,asset_liability_ratio=debt_total/total_assets*100 if total_assets else np.nan,
                     asset_turnover=revenue/total_assets if total_assets else np.nan,equity_multiplier=total_assets/equity if equity else np.nan,
                     roe_simple=net/equity*100 if equity else np.nan,
                     money_yi=money,trading_assets_yi=trading,other_current_assets_yi=other_current,short_borrow_yi=st_borrow,
                     one_year_noncurrent_liab_yi=one_year,long_borrow_yi=long_borrow,bonds_yi=bonds,lease_liab_yi=lease,
                     ar_yi=ar,notes_receivable_yi=notes,finance_receivable_yi=fin_rec,inventory_yi=inventory,contract_liab_yi=contract,
                     cfo_yi=cfo,capex_yi=capex,fcf_yi=cfo-capex,dividend_cash_yi=dividend,
                     cfo_net_ratio=cfo/net*100 if net else np.nan,fcf_net_ratio=(cfo-capex)/net*100 if net else np.nan,capex_cfo_ratio=capex/cfo*100 if cfo else np.nan))
annual=pd.DataFrame(rows)
annual.to_csv(DATA/f'{CODE}_annual_financial_summary.csv',index=False,encoding='utf-8-sig')

# quarterly from previous chart data
qpath=CHARTS/f'{CODE}_季度数据.csv'
quarterly=pd.read_csv(qpath)
latest_q=quarterly.iloc[-1].to_dict()
q3y=quarterly.iloc[-13] if len(quarterly)>=13 else None

# valuation history
val=ak.stock_value_em(symbol=CODE)
val.to_csv(DATA/f'{CODE}_valuation_history.csv',index=False,encoding='utf-8-sig')
val['数据日期']=pd.to_datetime(val['数据日期'])
latest=val.sort_values('数据日期').iloc[-1]
pe_series=val[(val['PE(TTM)']>0)&(val['PE(TTM)']<500)].sort_values('数据日期')
last_date=latest['数据日期']
pe10=pe_series[pe_series['数据日期']>=last_date-pd.Timedelta(days=3650)]
pe_current=float(latest['PE(TTM)'])
pe_percentile=float((pe10['PE(TTM)']<=pe_current).mean()*100)
close=float(latest['当日收盘价']); mcap=float(latest['总市值'])/1e8; shares=float(latest['总股本'])

# cash position 2025: annual report note says other current assets are VAT/prepaid tax, no term deposit; trading assets blank.
a2025=annual[annual.year==2025].iloc[0]
long_debt=sum([0 if pd.isna(v) else float(v) for v in [a2025.get('one_year_noncurrent_liab_yi',0), a2025.get('long_borrow_yi',0), a2025.get('bonds_yi',0), a2025.get('lease_liab_yi',0)]])
trading_assets = 0 if pd.isna(a2025.trading_assets_yi) else float(a2025.trading_assets_yi)
cash_position=float(a2025.money_yi) + trading_assets - long_debt
per_share_cash=cash_position*1e8/shares
latest_non_gaap_ttm=float(latest_q['non_gaap_ttm_yi'])
ex_cash_mcap=mcap-cash_position
ex_cash_pe=ex_cash_mcap/latest_non_gaap_ttm

# dividends
try:
    div=ak.stock_history_dividend_detail(symbol=CODE, indicator='分红')
    div.to_csv(DATA/f'{CODE}_dividend_history.csv',index=False,encoding='utf-8-sig')
    # fiscal 2025: 2025 interim 10派7, 2026 annual implementation 10派10; per share = 1.7 yuan (with capitalization caveat)
except Exception:
    div=pd.DataFrame()

# peers current valuation: prefer all-A spot; if network fails, fall back to each stock_value_em latest
peers={'300015':'爱尔眼科','301267':'华厦眼科','301239':'普瑞眼科','301103':'何氏眼科','300595':'欧普康视','688050':'爱博医疗','300573':'兴齐眼药'}
peer_rows=[]
try:
    spot=ak.stock_zh_a_spot_em()
    for code,name in peers.items():
        r=spot[spot['代码'].astype(str)==code]
        if len(r):
            rr=r.iloc[0]
            peer_rows.append({'代码':code,'公司':name,'最新价':rr.get('最新价'), '总市值_亿':float(rr.get('总市值'))/1e8 if pd.notna(rr.get('总市值')) else np.nan,
                              '市盈率动态':rr.get('市盈率-动态'), '市净率':rr.get('市净率')})
except Exception as e:
    print('stock_zh_a_spot_em failed, fallback:', repr(e))
    for code,name in peers.items():
        try:
            v=ak.stock_value_em(symbol=code).sort_values('数据日期').iloc[-1]
            peer_rows.append({'代码':code,'公司':name,'最新价':v.get('当日收盘价'), '总市值_亿':float(v.get('总市值'))/1e8 if pd.notna(v.get('总市值')) else np.nan,
                              '市盈率动态':v.get('PE(TTM)'), '市净率':v.get('市净率')})
        except Exception as ee:
            peer_rows.append({'代码':code,'公司':name,'最新价':np.nan,'总市值_亿':np.nan,'市盈率动态':np.nan,'市净率':np.nan})
peer_df=pd.DataFrame(peer_rows)
peer_df.to_csv(DATA/f'{CODE}_peer_valuation.csv',index=False,encoding='utf-8-sig')

summary={
 'latest_trade_date': str(last_date.date()), 'close': close, 'market_cap_yi': mcap, 'shares': shares,
 'pe_ttm': pe_current, 'pe_percentile_available_since': str(pe10['数据日期'].min().date()), 'pe_percentile': pe_percentile,
 'latest_quarter': latest_q.get('quarter'), 'latest_non_gaap_ttm_yi': latest_non_gaap_ttm,
 'cash_position_yi': cash_position, 'per_share_cash': per_share_cash, 'ex_cash_mcap_yi': ex_cash_mcap, 'ex_cash_pe': ex_cash_pe,
 'long_debt_yi': long_debt, 'data_note':'现金头寸按2025年报：货币资金 + 交易性金融资产(0) - 一年内到期租赁负债 - 租赁负债；其他流动资产为待抵扣进项税/预缴所得税，不计入。'
}
(DATA/f'{CODE}_valuation_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')

# product structure hard-coded from 2025 annual report table page 22
product=pd.DataFrame([
 {'产品':'滴眼剂','收入_亿':19.502430176,'占比':78.87,'同比':42.76,'毛利率':85.12},
 {'产品':'凝胶剂/眼膏剂','收入_亿':3.6655368602,'占比':14.82,'同比':1.02,'毛利率':84.52},
 {'产品':'溶液剂','收入_亿':0.7001793176,'占比':2.83,'同比':13.17,'毛利率':np.nan},
 {'产品':'医疗服务','收入_亿':0.6609520478,'占比':2.67,'同比':-50.26,'毛利率':np.nan},
 {'产品':'其他','收入_亿':0.1994239663,'占比':0.81,'同比':1.33,'毛利率':np.nan},
])
product.to_csv(DATA/f'{CODE}_product_structure_2025.csv',index=False,encoding='utf-8-sig')

# charts
def save(fig,name):
    fig.tight_layout(); fig.savefig(CHARTS/name,bbox_inches='tight',facecolor='white',dpi=160); plt.close(fig)

fig,ax1=plt.subplots(figsize=(12,6))
ax2=ax1.twinx(); x=np.arange(len(annual)); labels=annual.year.astype(str)
ax1.bar(x-0.18,annual.revenue_yi,width=0.36,color='#90CAF9',label='营业收入')
ax1.bar(x+0.18,annual.non_gaap_yi,width=0.36,color='#EF9A9A',label='扣非净利润')
ax2.plot(x,annual.gross_margin,'o-',color='#2E7D32',label='毛利率')
ax2.plot(x,annual.net_margin,'s-',color='#F57C00',label='净利率')
ax1.set_xticks(x); ax1.set_xticklabels(labels,fontproperties=FONT_PROP)
ax1.set_ylabel('亿元',fontproperties=FONT_PROP); ax2.set_ylabel('%',fontproperties=FONT_PROP)
ax1.set_title('兴齐眼药：收入、扣非净利润与利润率',fontproperties=FONT_PROP,fontsize=15,fontweight='bold')
lines1,labels1=ax1.get_legend_handles_labels(); lines2,labels2=ax2.get_legend_handles_labels(); ax1.legend(lines1+lines2,labels1+labels2,prop=FONT_PROP,loc='upper left')
ax1.grid(alpha=.2)
save(fig,f'{CODE}_收入利润与利润率.png')

fig,ax=plt.subplots(figsize=(12,6)); x=np.arange(len(annual)); w=.25
ax.bar(x-w,annual.net_profit_yi,width=w,color='#90CAF9',label='归母净利润')
ax.bar(x,annual.cfo_yi,width=w,color='#A5D6A7',label='经营现金流')
ax.bar(x+w,annual.fcf_yi,width=w,color='#FFCC80',label='自由现金流')
ax.set_xticks(x); ax.set_xticklabels(labels,fontproperties=FONT_PROP); ax.set_ylabel('亿元',fontproperties=FONT_PROP)
ax.set_title('兴齐眼药：净利润、经营现金流与自由现金流',fontproperties=FONT_PROP,fontsize=15,fontweight='bold')
ax.legend(prop=FONT_PROP); ax.grid(axis='y',alpha=.2)
save(fig,f'{CODE}_现金流质量.png')

fig,(ax1,ax2)=plt.subplots(2,1,figsize=(13,9),gridspec_kw={'height_ratios':[1.15,1]})
x=np.arange(len(annual)); w=.22
ax1.bar(x-w,annual.ar_yi,width=w,color='#64B5F6',label='应收账款')
ax1.bar(x,annual.inventory_yi,width=w,color='#FFB74D',label='存货')
ax1.bar(x+w,annual.contract_liab_yi,width=w,color='#81C784',label='合同负债')
ax1.set_xticks(x); ax1.set_xticklabels(labels,fontproperties=FONT_PROP); ax1.set_ylabel('亿元',fontproperties=FONT_PROP)
ax1.set_title('应收、存货与合同负债',fontproperties=FONT_PROP,fontsize=13,fontweight='bold')
ax1.legend(prop=FONT_PROP,loc='upper left'); ax1.grid(axis='y',alpha=.2)

rev_growth=annual.revenue_yi.pct_change()*100
inv_growth=annual.inventory_yi.pct_change()*100
inv_rev_ratio=annual.inventory_yi/annual.revenue_yi*100
l1,=ax2.plot(x,rev_growth,'o-',color='#1565C0',linewidth=2.4,label='营收同比')
l2,=ax2.plot(x,inv_growth,'s-',color='#EF6C00',linewidth=2.4,label='存货同比')
ax2b=ax2.twinx()
l3,=ax2b.plot(x,inv_rev_ratio,'^-',color='#2E7D32',linewidth=2.2,label='存货/营收')
ax2.axhline(0,color='#999',lw=1,alpha=.5)
ax2.set_xticks(x); ax2.set_xticklabels(labels,fontproperties=FONT_PROP)
ax2.set_ylabel('同比增速(%)',fontproperties=FONT_PROP); ax2b.set_ylabel('存货/营收(%)',fontproperties=FONT_PROP)
ax2.set_title('存货增长与营收增长对比',fontproperties=FONT_PROP,fontsize=13,fontweight='bold')
ax2.legend([l1,l2,l3],[l1.get_label(),l2.get_label(),l3.get_label()],prop=FONT_PROP,loc='upper right')
ax2.grid(axis='y',alpha=.2)
fig.suptitle('兴齐眼药：营运质量',fontproperties=FONT_PROP,fontsize=15,fontweight='bold')
save(fig,f'{CODE}_营运质量.png')

fig,(ax1,ax2)=plt.subplots(1,2,figsize=(14,6),gridspec_kw={'width_ratios':[1.2,1]})
p=product.sort_values('收入_亿')
colors=['#B0BEC5' if v<10 else '#1976D2' for v in p['占比']]
ax1.barh(p['产品'],p['收入_亿'],color=colors)
for i,(_,r) in enumerate(p.iterrows()): ax1.text(r['收入_亿']+0.1,i,f"{r['收入_亿']:.2f}亿 / {r['占比']:.1f}%",va='center',fontproperties=FONT_PROP,fontsize=9)
ax1.set_title('2025年收入结构',fontproperties=FONT_PROP,fontweight='bold')
ax1.set_xlabel('亿元',fontproperties=FONT_PROP)
p2=product.sort_values('同比')
ax2.axvline(0,color='#999',lw=1); ax2.plot(p2['同比'],p2['产品'],'o-',color='#D32F2F')
for i,(_,r) in enumerate(p2.iterrows()): ax2.text(r['同比']+(1 if r['同比']>=0 else -1),i,f"{r['同比']:.1f}%",va='center',ha='left' if r['同比']>=0 else 'right',fontproperties=FONT_PROP,fontsize=9)
ax2.set_title('2025年同比增速',fontproperties=FONT_PROP,fontweight='bold')
ax2.set_xlabel('%',fontproperties=FONT_PROP)
fig.suptitle('兴齐眼药：产品结构与增长来源',fontproperties=FONT_PROP,fontsize=15,fontweight='bold')
save(fig,f'{CODE}_产品结构与增长来源.png')

print(json.dumps(summary,ensure_ascii=False,indent=2))
print('\nannual tail')
print(annual.tail(6).round(3).to_string(index=False))
print('\npeers')
print(peer_df.to_string(index=False))