#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
import warnings, json, math
warnings.filterwarnings('ignore')
import pandas as pd
import numpy as np
import akshare as ak
import yfinance as yf

BASE=Path(__file__).resolve().parents[1]
DATA=BASE/'data'; DATA.mkdir(parents=True, exist_ok=True)
CODE='01810'; YF='1810.HK'

def to_yi(x):
    return pd.to_numeric(x, errors='coerce')/1e8

def pivot_report(symbol):
    df=ak.stock_financial_hk_report_em(stock=CODE, symbol=symbol, indicator='年度')
    df['date']=pd.to_datetime(df['REPORT_DATE']).dt.date.astype(str)
    piv=df.pivot_table(index='date', columns='STD_ITEM_NAME', values='AMOUNT', aggfunc='last').sort_index()
    return piv

def report_period(symbol):
    df=ak.stock_financial_hk_report_em(stock=CODE, symbol=symbol, indicator='报告期')
    df['date']=pd.to_datetime(df['REPORT_DATE']).dt.date.astype(str)
    piv=df.pivot_table(index='date', columns='STD_ITEM_NAME', values='AMOUNT', aggfunc='last').sort_index()
    return piv

# 年度利润表/资产负债表/现金流量表
inc=pivot_report('利润表')
bal=pivot_report('资产负债表')
cf=pivot_report('现金流量表')
for name,df in [('income_annual_raw',inc),('balance_annual_raw',bal),('cashflow_annual_raw',cf)]:
    df.to_csv(DATA/f'{name}.csv', encoding='utf-8-sig')

# 分析指标
ind=ak.stock_financial_hk_analysis_indicator_em(symbol=CODE)
ind['date']=pd.to_datetime(ind['REPORT_DATE']).dt.date.astype(str)
ind=ind.sort_values('date')
ind.to_csv(DATA/'analysis_indicator_raw.csv', index=False, encoding='utf-8-sig')

# 年度核心表：选 2019-2025
idx=[d for d in inc.index if d>='2019-12-31']
annual=pd.DataFrame(index=idx)
annual['营收']=to_yi(inc.reindex(idx).get('营业额'))
annual['毛利']=to_yi(inc.reindex(idx).get('毛利'))
annual['股东应占溢利']=to_yi(inc.reindex(idx).get('股东应占溢利'))
annual['经营溢利']=to_yi(inc.reindex(idx).get('经营溢利'))
annual['经营现金流']=to_yi(cf.reindex(idx).get('经营活动产生的现金流量净额'))
# capex field names inspect
for col in ['购买固定资产、无形资产及其他长期资产支付的现金','购建固定资产、无形资产和其他长期资产支付的现金','资本开支','购买物业、厂房及设备付款']:
    if col in cf.columns:
        annual['资本开支']=abs(to_yi(cf.reindex(idx).get(col))); break
if '资本开支' not in annual.columns:
    # print likely investment/capex fields separately
    annual['资本开支']=np.nan
annual['自由现金流']=annual['经营现金流']-annual['资本开支']
annual['总资产']=to_yi(bal.reindex(idx).get('总资产'))
annual['权益总额']=to_yi(bal.reindex(idx).get('总权益')) if '总权益' in bal.columns else to_yi(bal.reindex(idx).get('股东权益'))
annual['经营现金流']=to_yi(cf.reindex(idx).get('经营业务现金净额'))
annual['资本开支']=abs(to_yi(cf.reindex(idx).get('购建固定资产')))
annual['自由现金流']=annual['经营现金流']-annual['资本开支']
annual['现金及等价物']=to_yi(bal.reindex(idx).get('现金及等价物'))
annual['短期存款']=to_yi(bal.reindex(idx).get('短期存款'))
annual['中长期存款']=to_yi(bal.reindex(idx).get('中长期存款'))
annual['短期投资']=to_yi(bal.reindex(idx).get('短期投资'))
annual['长期投资']=to_yi(bal.reindex(idx).get('长期投资'))
annual['长期贷款']=to_yi(bal.reindex(idx).get('长期贷款'))
annual['非流动负债合计']=to_yi(bal.reindex(idx).get('非流动负债合计'))
annual['现金头寸_近似']=annual[['现金及等价物','短期存款','中长期存款','短期投资']].sum(axis=1)-annual['长期贷款'].fillna(0)
for col in ['应收帐款','应收账款','应收贸易款项']:
    if col in bal.columns:
        annual['应收账款']=to_yi(bal.reindex(idx).get(col)); break
for col in ['存货','库存']:
    if col in bal.columns:
        annual['存货']=to_yi(bal.reindex(idx).get(col)); break
for col in ['预收款项','合约负债','合同负债']:
    if col in bal.columns:
        annual['合同负债']=to_yi(bal.reindex(idx).get(col)); break
annual['毛利率']=annual['毛利']/annual['营收']
annual['净利率']=annual['股东应占溢利']/annual['营收']
annual['总资产周转率']=annual['营收']/annual['总资产']
annual['权益乘数']=annual['总资产']/annual['权益总额']
annual['简单ROE']=annual['股东应占溢利']/annual['权益总额']
annual['资产负债率']=1-annual['权益总额']/annual['总资产']
annual.to_csv(DATA/'xiaomi_annual_core.csv', encoding='utf-8-sig')

# 季度/报告期核心数据，使用已生成CSV
q_path=DATA/'1810_小米集团_季度股价利润数据.csv'
if q_path.exists():
    q=pd.read_csv(q_path)
else:
    q=pd.DataFrame()

# 行情：yfinance latest
hist=yf.download(YF, period='5d', auto_adjust=False, progress=False)
if isinstance(hist.columns, pd.MultiIndex): hist.columns=hist.columns.get_level_values(0)
last=hist.dropna().iloc[-1]
last_date=hist.dropna().index[-1].date().isoformat()
info=yf.Ticker(YF).fast_info
quote={
    'last_date': last_date,
    'close_hkd': float(last['Close']),
    'market_cap_hkd': float(getattr(info,'market_cap', np.nan)) if hasattr(info,'market_cap') else np.nan,
    'shares': float(getattr(info,'shares', np.nan)) if hasattr(info,'shares') else np.nan,
}
(DATA/'quote_yfinance.json').write_text(json.dumps(quote, ensure_ascii=False, indent=2), encoding='utf-8')

# 东方财富行情 spot/valuation尝试
extra={}
try:
    spot=ak.stock_hk_spot_em()
    row=spot[(spot.astype(str).apply(lambda s: s.str.contains('01810|小米', regex=True)).any(axis=1))]
    row.to_csv(DATA/'spot_em_xiaomi.csv', index=False, encoding='utf-8-sig')
except Exception as e:
    extra['spot_error']=repr(e)
try:
    val=ak.stock_hk_valuation_baidu(symbol='01810', indicator='总览')
    val.to_csv(DATA/'valuation_baidu_xiaomi.csv', index=False, encoding='utf-8-sig')
except Exception as e:
    extra['valuation_error']=repr(e)

# 估值历史 yfinance approximate PE = market cap / latest TTM profit (HKD/RMB mismatch not used for final)
# 关键列名探查
with open(DATA/'field_names.txt','w',encoding='utf-8') as f:
    for label,df in [('income',inc),('balance',bal),('cashflow',cf)]:
        f.write('\n## '+label+'\n')
        f.write('\n'.join(map(str,df.columns.tolist())))
        f.write('\n')

# 摘要输出
print('annual_core')
print(annual.tail(7).round(2).to_string())
print('\nquote', quote)
print('\nfields saved', DATA/'field_names.txt')
print('files in data generated')
