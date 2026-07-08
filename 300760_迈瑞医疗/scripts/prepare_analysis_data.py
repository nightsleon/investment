import pandas as pd, numpy as np, json, math
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]; DATA=BASE/'data'
inc=pd.read_csv(DATA/'RPT_DMSK_FN_INCOME.csv', parse_dates=['REPORT_DATE'])
bal=pd.read_csv(DATA/'RPT_DMSK_FN_BALANCE.csv', parse_dates=['REPORT_DATE'])
cf=pd.read_csv(DATA/'RPT_DMSK_FN_CASHFLOW.csv', parse_dates=['REPORT_DATE'])
# keep annual 2020-2025 and latest Q1 if any
def annual(df):
    d=df[df.REPORT_DATE.dt.month.eq(12)].copy().sort_values('REPORT_DATE')
    return d[d.REPORT_DATE.dt.year.between(2020,2025)]
A=annual(inc)[['REPORT_DATE','TOTAL_OPERATE_INCOME','OPERATE_INCOME','PARENT_NETPROFIT','DEDUCT_PARENT_NETPROFIT','OPERATE_COST','SALE_EXPENSE','MANAGE_EXPENSE']]
B=annual(bal)[['REPORT_DATE','TOTAL_ASSETS','TOTAL_LIABILITIES','TOTAL_EQUITY','MONETARYFUNDS','ACCOUNTS_RECE','INVENTORY','ADVANCE_RECEIVABLES','FIXED_ASSET','DEBT_ASSET_RATIO']]
C=annual(cf)[['REPORT_DATE','NETCASH_OPERATE','CONSTRUCT_LONG_ASSET','NETCASH_INVEST','NETCASH_FINANCE','CCE_ADD','SALES_SERVICES']]
df=A.merge(B,on='REPORT_DATE',how='left').merge(C,on='REPORT_DATE',how='left')
df['年份']=df.REPORT_DATE.dt.year
for col in df.columns:
    if col!='REPORT_DATE' and col!='年份': df[col]=pd.to_numeric(df[col],errors='coerce')/1e8
# metrics
df['营收']=df['TOTAL_OPERATE_INCOME']; df['净利润']=df['PARENT_NETPROFIT']; df['扣非净利润']=df['DEDUCT_PARENT_NETPROFIT']
df['毛利率']=(df['TOTAL_OPERATE_INCOME']-df['OPERATE_COST'])/df['TOTAL_OPERATE_INCOME']*100
df['净利率']=df['PARENT_NETPROFIT']/df['TOTAL_OPERATE_INCOME']*100
df['总资产周转率']=df['TOTAL_OPERATE_INCOME']/df['TOTAL_ASSETS'] # year-end simple
# equity multiplier = assets/equity
df['权益乘数']=df['TOTAL_ASSETS']/df['TOTAL_EQUITY']
df['简单ROE']=df['PARENT_NETPROFIT']/df['TOTAL_EQUITY']*100
df['经营现金流']=df['NETCASH_OPERATE']; df['资本开支']=df['CONSTRUCT_LONG_ASSET']; df['自由现金流']=df['NETCASH_OPERATE']-df['CONSTRUCT_LONG_ASSET']
df['资产负债率']=df['TOTAL_LIABILITIES']/df['TOTAL_ASSETS']*100
df['应收账款']=df['ACCOUNTS_RECE']; df['存货']=df['INVENTORY']
# 东方财富摘要字段 ADVANCE_RECEIVABLES 是预收款项，不是合同负债；合同负债用年报合并资产负债表复核值。
contract_liabilities={
    2020:32.93398162,
    2021:24.08192187,
    2022:41.42767341,
    2023:19.73361518,
    2024:21.65767452,
    2025:30.00601014,
}
df['合同负债']=df['年份'].map(contract_liabilities)
# 2025 cash position from PDF detailed: monetary 176.9037 + trading 2.5049 - long borrowing 0.0406 ; do not count other current assets (VAT/prepaid taxes)
# For prior years approximate using API monetary only minus long debt unavailable (tiny); use monetary funds for trend, 2025 exact + trading.
df['现金头寸_近似']=df['MONETARYFUNDS']
df.loc[df['年份'].eq(2025),'现金头寸_近似']=(17690372308+250485746-4062631)/1e8
# save annual core Chinese columns
cols=['年份','营收','净利润','扣非净利润','毛利率','净利率','总资产周转率','权益乘数','简单ROE','经营现金流','资本开支','自由现金流','现金头寸_近似','资产负债率','应收账款','存货','合同负债']
out=df[cols].copy()
out.to_csv(DATA/'annual_core.csv',index=False,encoding='utf-8-sig')
# product 2025 from PDF; previous revenue = current/(1+yoy)
prod=pd.DataFrame([
    ['体外诊断',122.406569,-9.41],
    ['生命信息与支持',98.367237,-19.80],
    ['医学影像',57.167056,-18.02],
    ['新兴业务',53.779611,38.85],
])
prod.columns=['业务','收入_亿元','同比_%']
prod['占比_%']=prod['收入_亿元']/prod['收入_亿元'].sum()*100
prod['上年收入_亿元']=prod['收入_亿元']/(1+prod['同比_%']/100)
prod['收入增量_亿元']=prod['收入_亿元']-prod['上年收入_亿元']
prod.to_csv(DATA/'product_structure_2025.csv',index=False,encoding='utf-8-sig')
# latest q1 and TTM from cumulative API -> quarter conversion
incq=inc.sort_values('REPORT_DATE').copy()
incq=incq[incq.REPORT_DATE.dt.year>=2018]
for col in ['PARENT_NETPROFIT','DEDUCT_PARENT_NETPROFIT','TOTAL_OPERATE_INCOME']:
    incq[col]=pd.to_numeric(incq[col],errors='coerce')/1e8
rows=[]
for y,grp in incq.groupby(incq.REPORT_DATE.dt.year):
    grp=grp.sort_values('REPORT_DATE')
    prev={c:0 for c in ['PARENT_NETPROFIT','DEDUCT_PARENT_NETPROFIT','TOTAL_OPERATE_INCOME']}
    for _,r in grp.iterrows():
        q=r.REPORT_DATE.month//3
        item={'date':r.REPORT_DATE,'year':y,'quarter':q}
        for c in prev:
            val=r[c]
            item[c+'_q']=val-prev[c] if q>1 else val
            prev[c]=val
        rows.append(item)
qdf=pd.DataFrame(rows).sort_values('date')
qdf['non_gaap_ttm_yi']=qdf['DEDUCT_PARENT_NETPROFIT_q'].rolling(4).sum()
qdf['net_profit_ttm_yi']=qdf['PARENT_NETPROFIT_q'].rolling(4).sum()
qdf.to_csv(DATA/'quarterly_financial.csv',index=False,encoding='utf-8-sig')
# valuation stats
pe=pd.read_csv(DATA/'pe_history.csv', parse_dates=['TRADE_DATE'])
pe=pe.dropna(subset=['PE_TTM'])
last=pe.iloc[-1]
cut=last.TRADE_DATE - pd.DateOffset(years=10)
pe10=pe[pe.TRADE_DATE>=cut]
pe_pct=(pe10.PE_TTM<=last.PE_TTM).mean()*100
# 3y CAGR annual 2022->2025
v2022=float(out.loc[out['年份'].eq(2022),'扣非净利润'].iloc[0]); v2025=float(out.loc[out['年份'].eq(2025),'扣非净利润'].iloc[0])
cagr3=(v2025/v2022)**(1/3)-1
valuation={'last_trade_date':str(last.TRADE_DATE.date()),'close':float(last.CLOSE_PRICE),'pe_ttm':float(last.PE_TTM),'pb':float(last.PB_MRQ),'market_cap_yi':float(last.TOTAL_MARKET_CAP)/1e8,'pe_percentile_available_period_pct':pe_pct,'available_start':str(pe10.TRADE_DATE.min().date()),'available_days':len(pe10),'deduct_np_2022_yi':v2022,'deduct_np_2025_yi':v2025,'deduct_np_3y_cagr_pct':cagr3*100,'peg':float(last.PE_TTM)/(cagr3*100) if cagr3>0 else None}
(DATA/'valuation_summary.json').write_text(json.dumps(valuation,ensure_ascii=False,indent=2),encoding='utf-8')
print(out.to_string(index=False))
print(prod.to_string(index=False))
print(json.dumps(valuation,ensure_ascii=False,indent=2))
print('quarters tail')
print(qdf.tail(6).to_string(index=False))
