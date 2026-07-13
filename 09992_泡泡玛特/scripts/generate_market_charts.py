#!/usr/bin/env python3
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.font_manager import FontProperties
import yfinance as yf

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / 'data'
OUT = BASE / 'charts'
OUT.mkdir(exist_ok=True)
FONT_PATHS = ['/System/Library/Fonts/PingFang.ttc','/System/Library/Fonts/Hiragino Sans GB.ttc','/System/Library/Fonts/STHeiti Medium.ttc']
FONT = FontProperties(fname=next((p for p in FONT_PATHS if Path(p).exists()), FONT_PATHS[-1]))
plt.rcParams['axes.unicode_minus'] = False
BLUE='#2563EB'; ORANGE='#F97316'; RED='#DC2626'; GREEN='#16A34A'; GRAY='#64748B'

def style(ax):
    ax.grid(axis='y', alpha=.2)
    ax.spines['top'].set_visible(False)
    for lab in ax.get_xticklabels()+ax.get_yticklabels(): lab.set_fontproperties(FONT)

def save(fig,name):
    p=OUT/name
    fig.savefig(p,dpi=180,bbox_inches='tight',facecolor='white')
    plt.close(fig)
    print(p)

# 1) 半年度股价与归母TTM利润主图
h=pd.read_csv(DATA/'halfyear_stock_profit.csv')
x=np.arange(len(h))
fig,ax1=plt.subplots(figsize=(16,8),dpi=180)
ax2=ax1.twinx()
l1,=ax1.plot(x,h['期末股价_港元'],marker='o',lw=2.6,color=BLUE,label='期末股价（港元）')
l2,=ax2.plot(x,h['归母TTM_亿元'],marker='s',lw=2.6,color=ORANGE,label='归母净利润TTM（亿元）')
ax2.fill_between(x,h['归母TTM_亿元'],alpha=.10,color=ORANGE)
ax1.set_xticks(x); ax1.set_xticklabels(h['期间'],rotation=25,ha='right',fontproperties=FONT)
ax1.set_ylabel('股价（港元）',fontproperties=FONT); ax2.set_ylabel('归母净利润TTM（亿元人民币）',fontproperties=FONT)
ax1.set_title('泡泡玛特：股价与归母净利润TTM趋势',fontproperties=FONT,fontsize=18,weight='bold',pad=20)
ax1.text(.5,1.01,'港股仅披露半年报/年报；最新点为2026-07-10股价与2025A利润TTM',transform=ax1.transAxes,ha='center',fontproperties=FONT,color='#555',fontsize=10)
style(ax1); ax2.spines['top'].set_visible(False)
for lab in ax2.get_yticklabels(): lab.set_fontproperties(FONT)
ax1.legend([l1,l2],[l1.get_label(),l2.get_label()],prop=FONT,loc='upper left',frameon=False)
for i in [len(h)-3,len(h)-2,len(h)-1]:
    ax1.annotate(f"{h.loc[i,'期末股价_港元']:.1f}",xy=(i,h.loc[i,'期末股价_港元']),xytext=(0,10),textcoords='offset points',ha='center',fontproperties=FONT,color=BLUE,fontsize=9)
    ax2.annotate(f"{h.loc[i,'归母TTM_亿元']:.1f}",xy=(i,h.loc[i,'归母TTM_亿元']),xytext=(0,-16),textcoords='offset points',ha='center',fontproperties=FONT,color=ORANGE,fontsize=9)
fig.tight_layout(); save(fig,'09992_股价vs归母净利润TTM_双Y轴.png')

# 2) 归一化辅助图（只看方向，不判断估值）
base=0
fig,ax=plt.subplots(figsize=(15,7),dpi=180)
price=h['期末股价_港元']/h.loc[base,'期末股价_港元']*100
profit=h['归母TTM_亿元']/h.loc[base,'归母TTM_亿元']*100
ax.plot(x,price,marker='o',lw=2.4,color=BLUE,label='股价（基期=100）')
ax.plot(x,profit,marker='s',lw=2.4,color=ORANGE,label='归母利润TTM（基期=100）')
ax.set_xticks(x); ax.set_xticklabels(h['期间'],rotation=25,ha='right',fontproperties=FONT)
ax.set_ylabel('指数（2021H1=100）',fontproperties=FONT)
ax.set_title('泡泡玛特：股价与归母利润TTM归一化趋势',fontproperties=FONT,fontsize=18,weight='bold',pad=20)
ax.text(.5,1.01,'归一化图仅看方向与增幅，不能判断估值高低',transform=ax.transAxes,ha='center',fontproperties=FONT,color='#555',fontsize=10)
style(ax); ax.legend(prop=FONT,frameon=False)
fig.tight_layout(); save(fig,'09992_股价vs归母净利润TTM_归一化.png')

# 3) 上市以来点时近似PE
px=yf.download('9992.HK',start='2020-12-11',end='2026-07-11',auto_adjust=False,progress=False)
fx=yf.download('CNYHKD=X',start='2020-12-11',end='2026-07-11',auto_adjust=False,progress=False)
if isinstance(px.columns,pd.MultiIndex): px.columns=px.columns.get_level_values(0)
if isinstance(fx.columns,pd.MultiIndex): fx.columns=fx.columns.get_level_values(0)
df=px[['Close']].rename(columns={'Close':'股价_港元'}).join(fx[['Close']].rename(columns={'Close':'CNYHKD'}),how='left')
df['CNYHKD']=df['CNYHKD'].ffill().bfill()
steps=[('2020-12-11',0.39),('2021-04-01',0.44),('2021-08-31',0.5776),('2022-04-01',0.62),('2022-08-31',0.6014),('2023-04-01',0.35),('2023-08-31',0.4628),('2024-04-01',0.81),('2024-08-31',1.1503),('2025-04-01',2.36),('2025-08-31',5.1068),('2026-04-01',9.61)]
df['EPS_TTM_人民币']=np.nan
for d,e in steps: df.loc[df.index>=pd.Timestamp(d),'EPS_TTM_人民币']=e
df['PE_TTM_近似']=df['股价_港元']/(df['EPS_TTM_人民币']*df['CNYHKD'])
df.to_csv(DATA/'historical_pe_daily.csv',encoding='utf-8-sig')
pe=df['PE_TTM_近似'].dropna(); q10,q25,q50,q75,q90=pe.quantile([.1,.25,.5,.75,.9]); current=pe.iloc[-1]; pct=(pe<=current).mean()*100
fig,ax=plt.subplots(figsize=(16,8),dpi=180)
ax.axhspan(0,q10,color='#DCFCE7',alpha=.9,label='0%-10%分位')
ax.axhspan(q10,q25,color='#FEF9C3',alpha=.75,label='10%-25%分位')
ax.axhspan(q25,q75,color='#E2E8F0',alpha=.55,label='25%-75%分位')
ax.plot(pe.index,pe.values,color=BLUE,lw=1.5,label='点时近似PE')
ax.scatter([pe.index[-1]],[current],color=RED,s=55,zorder=5)
ax.annotate(f'当前 {current:.1f}倍\n历史分位 {pct:.1f}%',xy=(pe.index[-1],current),xytext=(-90,35),textcoords='offset points',fontproperties=FONT,color=RED,arrowprops=dict(arrowstyle='->',color=RED))
ax.axhline(q10,color=GREEN,lw=1,ls='--'); ax.axhline(q50,color=GRAY,lw=1,ls='--')
ax.text(pe.index[20],q10+2,f'10%分位 {q10:.1f}倍',fontproperties=FONT,color=GREEN,fontsize=9)
ax.text(pe.index[20],q50+2,f'中位数 {q50:.1f}倍',fontproperties=FONT,color=GRAY,fontsize=9)
ax.set_ylim(0,min(max(q90*1.25,80),180)); ax.set_ylabel('PE（倍）',fontproperties=FONT)
ax.set_title('泡泡玛特：上市以来点时近似PE',fontproperties=FONT,fontsize=18,weight='bold',pad=20)
ax.text(.5,1.01,'未复权收盘价 ÷ 点时可得EPS TTM；业绩切换日采用统一近似，供历史分位参考',transform=ax.transAxes,ha='center',fontproperties=FONT,color='#555',fontsize=10)
style(ax); ax.legend(prop=FONT,frameon=False,loc='upper right')
fig.tight_layout(); save(fig,'09992_上市以来PE历史分位图.png')
print({'current_pe':round(current,2),'percentile':round(pct,2),'q10':round(q10,2),'q25':round(q25,2),'median':round(q50,2),'q75':round(q75,2),'q90':round(q90,2)})
