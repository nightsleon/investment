import pandas as pd, numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import yfinance as yf
from matplotlib.font_manager import FontProperties
BASE=Path(__file__).resolve().parents[1]; DATA=BASE/'data'; CHARTS=BASE/'charts'
font_path='/System/Library/Fonts/Hiragino Sans GB.ttc'
font=FontProperties(fname=font_path)
plt.rcParams['axes.unicode_minus']=False
q=pd.read_csv(DATA/'quarterly_financial.csv', parse_dates=['date'])
q=q.dropna(subset=['non_gaap_ttm_yi'])
start=str(q['date'].min().date())
raw=yf.download('300760.SZ', start=start, end='2026-09-03', auto_adjust=False, progress=False)
if isinstance(raw.columns,pd.MultiIndex): raw.columns=raw.columns.get_level_values(0)
price=raw.reset_index()[['Date','Close','Adj Close']].rename(columns={'Date':'trade_date','Adj Close':'adj_close','Close':'close'})
rows=[]
for _,r in q.iterrows():
    sub=price[price.trade_date<=r.date]
    if sub.empty: continue
    p=sub.iloc[-1]
    rows.append({**r.to_dict(),'trade_date':p.trade_date,'adj_close':float(p.adj_close),'close':float(p.close)})
m=pd.DataFrame(rows)
# 追加最新交易日快照(不覆盖末个报告期, 保留真实季度末价格, 使图上能看出6/30之后走势)
if not m.empty and len(price):
    last=price.iloc[-1]
    tail=m.iloc[-1].to_dict()
    tail.update({'date':pd.Timestamp(last.trade_date),'year':int(last.trade_date.year),
                 'quarter':int((last.trade_date.month-1)//3+1),
                 'trade_date':last.trade_date,'adj_close':float(last.adj_close),'close':float(last.close)})
    m=pd.concat([m,pd.DataFrame([tail])],ignore_index=True)
m.to_csv(DATA/'stock_profit_quarterly_merged.csv',index=False,encoding='utf-8-sig')
# plot 1 dual axis TTM main
fig, ax1=plt.subplots(figsize=(14,7),dpi=180)
ax2=ax1.twinx()
l1=ax1.plot(m.date,m.adj_close,'o-',color='#1f77b4',lw=2.3,ms=4,label='股价(前复权,元)')
l2=ax2.plot(m.date,m.non_gaap_ttm_yi,'s-',color='#ff7f0e',lw=2.3,ms=4,label='扣非净利润TTM(亿元)')
ax2.fill_between(m.date,m.non_gaap_ttm_yi,alpha=.08,color='#ff7f0e')
ax1.set_title('迈瑞医疗：股价 vs 扣非净利润TTM',fontproperties=font,fontsize=16,pad=12)
ax1.set_xlabel('季度',fontproperties=font); ax1.set_ylabel('股价(元)',fontproperties=font); ax2.set_ylabel('扣非TTM(亿元)',fontproperties=font)
ax1.grid(axis='y',alpha=.25); ax1.xaxis.set_major_formatter(mdates.DateFormatter('%YQ'))
lines=l1+l2; labels=[x.get_label() for x in lines]; ax1.legend(lines,labels,prop=font,loc='upper right')
# latest labels
ax1.annotate(f"{m.adj_close.iloc[-1]:.1f}元",(m.date.iloc[-1],m.adj_close.iloc[-1]),xytext=(-45,10),textcoords='offset points',fontproperties=font,color='#1f77b4')
ax2.annotate(f"{m.non_gaap_ttm_yi.iloc[-1]:.3g}亿",(m.date.iloc[-1],m.non_gaap_ttm_yi.iloc[-1]),xytext=(-45,-20),textcoords='offset points',fontproperties=font,color='#ff7f0e')
fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(CHARTS/'300760_股价vs扣非净利润TTM_双Y轴.png',bbox_inches='tight'); plt.close(fig)
# normalized
base=m[m.non_gaap_ttm_yi>0].iloc[0]
mn=m[m.date>=base.date].copy()
mn['price_norm']=mn.adj_close/base.adj_close; mn['profit_norm']=mn.non_gaap_ttm_yi/base.non_gaap_ttm_yi
fig,ax=plt.subplots(figsize=(14,7),dpi=180)
ax.plot(mn.date,mn.price_norm,'o-',lw=2.3,color='#1f77b4',label='股价(基期=1)')
ax.plot(mn.date,mn.profit_norm,'s-',lw=2.3,color='#ff7f0e',label='扣非TTM(基期=1)')
ax.set_title('迈瑞医疗：股价与扣非TTM归一化对比',fontproperties=font,fontsize=16,pad=12)
ax.grid(axis='y',alpha=.25); ax.legend(prop=font); fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(CHARTS/'300760_归一化_股价vs扣非TTM.png',bbox_inches='tight'); plt.close(fig)
# single quarter
fig, ax1=plt.subplots(figsize=(14,7),dpi=180); ax2=ax1.twinx()
l1=ax1.plot(m.date,m.adj_close,'o-',color='#1f77b4',lw=2.1,ms=4,label='股价(前复权,元)')
l2=ax2.plot(m.date,m.DEDUCT_PARENT_NETPROFIT_q,'s-',color='#2ca02c',lw=2.1,ms=4,label='单季度扣非净利润(亿元)')
ax1.set_title('迈瑞医疗：股价 vs 单季度扣非净利润',fontproperties=font,fontsize=16,pad=12)
ax1.grid(axis='y',alpha=.25); lines=l1+l2; ax1.legend(lines,[x.get_label() for x in lines],prop=font,loc='upper right')
fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(CHARTS/'300760_股价vs扣非净利润_单季度.png',bbox_inches='tight'); plt.close(fig)
print(m.tail().to_string(index=False))
