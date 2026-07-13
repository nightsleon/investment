#!/usr/bin/env python3
import requests, pandas as pd
from pathlib import Path
from python_calamine import CalamineWorkbook
BASE=Path(__file__).resolve().parents[1]
API='https://datacenter.eastmoney.com/securities/api/data/v1/get'

def fetch(report,size=200):
    p={'reportName':report,'columns':'ALL','filter':'(SECUCODE="000333.SZ")','pageSize':size,'sortColumns':'REPORT_DATE','sortTypes':'-1','source':'HSF10','client':'PC'}
    return requests.get(API,params=p,timeout=30).json()['result']['data']

def year_xls():
    rows=CalamineWorkbook.from_path(str(BASE/'data/000333_main_year.xls')).get_sheet_by_index(0).to_python()
    years=[int(x) for x in rows[0][1:] if x]
    return {str(r[0]):dict(zip(years,r[1:1+len(years)])) for r in rows[1:]}

def pct(x): return float(str(x).strip('%')) if x not in (None,'--','') else None
x=year_xls()
bal=fetch('RPT_DMSK_FN_BALANCE'); cf=fetch('RPT_DMSK_FN_CASHFLOW')
def annual(rows):
    out={}
    for r in rows:
        d=pd.to_datetime(r['REPORT_DATE'])
        if d.month==12 and d.day==31 and d.year not in out: out[d.year]=r
    return out
b,c=annual(bal),annual(cf)
rows=[]
for y in range(2020,2026):
    assets=b[y]['TOTAL_ASSETS']/1e8; equity=b[y]['TOTAL_EQUITY']/1e8
    prev_assets=b.get(y-1,{}).get('TOTAL_ASSETS',b[y]['TOTAL_ASSETS'])/1e8
    prev_equity=b.get(y-1,{}).get('TOTAL_EQUITY',b[y]['TOTAL_EQUITY'])/1e8
    revenue=x['营业总收入(元)'][y]/1e8; np=x['净利润(元)'][y]/1e8
    cfo=c[y]['NETCASH_OPERATE']/1e8; capex=c[y]['CONSTRUCT_LONG_ASSET']/1e8
    rows.append({'年份':y,'营收':revenue,'净利润':np,'扣非净利润':x['扣非净利润(元)'][y]/1e8,
      '净资产收益率':pct(x['净资产收益率'][y]),'销售净利率':pct(x['销售净利率'][y]),
      '总资产周转率':revenue/((assets+prev_assets)/2),'权益乘数':((assets+prev_assets)/2)/((equity+prev_equity)/2),
      '经营现金流':cfo,'资本开支':capex,'自由现金流':cfo-capex,
      '资产负债率':pct(x['资产负债率'][y]),'应收账款':b[y]['ACCOUNTS_RECE']/1e8,'存货':b[y]['INVENTORY']/1e8,
      # 合同负债来自各年度年报合并资产负债表；2020 年起执行新收入准则。
      '合同负债': {2020:184.00922,2021:239.16595,2022:279.60038,2023:417.65475,2024:492.54717,2025:469.93060}[y],
      # 现金头寸=货币资金+交易性金融资产-长期借款-应付债券-租赁负债；
      # 定期存款已包含在货币资金中，不重复加计；短期借款不扣。
      '现金头寸_近似': {2020:666.23,2021:564.87,2022:31.98,2023:320.60,2024:1317.63,2025:682.03}[y]})
pd.DataFrame(rows).to_csv(BASE/'data/annual_core.csv',index=False)
product=pd.DataFrame([
 ['智能家居',2999.27,11.28,29.90],['楼宇科技',357.91,25.72,30.58],['机器人与自动化',310.11,8.05,21.31],
 ['工业技术',272.32,10.24,17.50],['其他创新业务',287.19,26.94,11.26],['其他',337.72,1.96,15.53]],columns=['业务','收入_亿元','同比_%','毛利率_%'])
product.to_csv(BASE/'data/product_structure.csv',index=False)
# valuation history uses TRADE_DATE rather than REPORT_DATE
p={'reportName':'RPT_VALUEANALYSIS_DET','columns':'ALL','filter':'(SECUCODE="000333.SZ")','pageSize':5000,'sortColumns':'TRADE_DATE','sortTypes':'1','source':'HSF10','client':'PC'}
v=requests.get(API,params=p,timeout=30).json()['result']['data']
pd.DataFrame(v).to_csv(BASE/'data/valuation_history.csv',index=False)
print(BASE/'data/annual_core.csv'); print(BASE/'data/product_structure.csv'); print(BASE/'data/valuation_history.csv')
