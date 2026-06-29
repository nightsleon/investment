#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.font_manager import FontProperties

BASE=Path(__file__).resolve().parents[1]
DATA=BASE/'data'; CHART=BASE/'charts'; CHART.mkdir(exist_ok=True)

def font():
    for p in ['/System/Library/Fonts/Hiragino Sans GB.ttc','/System/Library/Fonts/STHeiti Medium.ttc','/System/Library/Fonts/Supplemental/Arial Unicode.ttf']:
        if Path(p).exists(): return FontProperties(fname=p)
    return FontProperties()
FONT=font(); plt.rcParams['axes.unicode_minus']=False

def set_font(ax):
    for label in ax.get_xticklabels()+ax.get_yticklabels(): label.set_fontproperties(FONT)
    ax.spines['top'].set_visible(False); ax.grid(axis='y', alpha=0.22)

# 单季度利润图
q=pd.read_csv(DATA/'1810_小米集团_季度股价利润数据.csv', parse_dates=['date','trade_date'])
fig, ax1=plt.subplots(figsize=(16,8), dpi=180)
ax2=ax1.twinx(); c1='#2563EB'; c2='#F97316'
ax1.plot(q['date'], q['adj_close_hkd'], marker='o', lw=2.2, ms=4, color=c1, label='股价（港元）')
ax2.plot(q['date'], q['profit_q_yi'], marker='s', lw=2.2, ms=4, color=c2, label='单季度股东应占溢利（亿元）')
ax2.axhline(0, color='#888', lw=0.8)
ax1.xaxis.set_major_locator(mdates.YearLocator()); ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
set_font(ax1); set_font(ax2)
ax1.set_ylabel('股价（港元）', fontproperties=FONT, color=c1); ax2.set_ylabel('单季度股东应占溢利（亿元）', fontproperties=FONT, color=c2)
ax1.tick_params(axis='y', labelcolor=c1); ax2.tick_params(axis='y', labelcolor=c2)
ax1.set_title('小米集团-W：股价与单季度利润', fontproperties=FONT, fontsize=20, weight='bold', pad=16)
ax1.text(0.5,1.01,'单季度利润由年初累计值差分得到；用于观察季节性和最新季度变化', transform=ax1.transAxes, ha='center', fontproperties=FONT, fontsize=11, color='#555')
lines=ax1.get_lines()+ax2.get_lines(); ax1.legend(lines,[l.get_label() for l in lines], loc='upper left', prop=FONT, frameon=True)
fig.tight_layout(rect=(0,0.03,1,0.95))
out=CHART/'1810_小米集团_股价vs股东应占溢利_单季度.png'; fig.savefig(out,bbox_inches='tight',facecolor='white'); plt.close(fig)
print(out)

# 年度基本面图：营收/利润/毛利率/净利率
annual=pd.read_csv(DATA/'xiaomi_annual_core.csv', index_col=0)
annual=annual.loc['2019-12-31':]
years=[x[:4] for x in annual.index]
fig, ax1=plt.subplots(figsize=(15,8), dpi=180); ax2=ax1.twinx()
w=0.35; x=range(len(years))
b1=ax1.bar([i-w/2 for i in x], annual['营收'], width=w, color='#93C5FD', label='营收（亿元）')
b2=ax1.bar([i+w/2 for i in x], annual['股东应占溢利'], width=w, color='#FDBA74', label='股东应占溢利（亿元）')
l1,=ax2.plot(x, annual['毛利率']*100, marker='o', lw=2.2, color='#16A34A', label='毛利率')
l2,=ax2.plot(x, annual['净利率']*100, marker='s', lw=2.2, color='#DC2626', label='净利率')
ax1.set_xticks(list(x)); ax1.set_xticklabels(years, fontproperties=FONT)
set_font(ax1); set_font(ax2)
ax1.set_ylabel('亿元', fontproperties=FONT); ax2.set_ylabel('%', fontproperties=FONT)
ax1.set_title('小米集团-W：2022低谷后收入与利润修复，毛利率台阶上移', fontproperties=FONT, fontsize=19, weight='bold', pad=16)
handles=[b1,b2,l1,l2]; labels=[h.get_label() for h in handles]; ax1.legend(handles,labels,loc='upper left',prop=FONT)
for i,v in enumerate(annual['股东应占溢利']):
    ax1.text(i+w/2, v+max(annual['股东应占溢利'])*0.015, f'{v:.0f}', ha='center', va='bottom', fontproperties=FONT, fontsize=9, color='#8A3A00')
fig.tight_layout(rect=(0,0.03,1,0.95))
out2=CHART/'1810_小米集团_年度营收利润率.png'; fig.savefig(out2,bbox_inches='tight',facecolor='white'); plt.close(fig); print(out2)

# 营运和现金流图
fig, axes=plt.subplots(2,1,figsize=(15,10), dpi=180, sharex=True)
ax=axes[0]
ax.bar([i-0.25 for i in x], annual['应收账款'], width=0.25, color='#BFDBFE', label='应收账款')
ax.bar(x, annual['存货'], width=0.25, color='#FDE68A', label='存货')
ax.bar([i+0.25 for i in x], annual['合同负债'], width=0.25, color='#BBF7D0', label='合同负债/预收')
set_font(ax); ax.set_ylabel('亿元', fontproperties=FONT); ax.legend(prop=FONT, loc='upper left')
ax.set_title('营运质量：EV拉动存货上升，合同负债/预收同步抬升', fontproperties=FONT, fontsize=17, weight='bold')
ax=axes[1]
ax.plot(x, annual['经营现金流'], marker='o', lw=2.2, color='#2563EB', label='经营现金流')
ax.plot(x, annual['自由现金流'], marker='s', lw=2.2, color='#DC2626', label='自由现金流')
ax.axhline(0,color='#888',lw=0.8)
set_font(ax); ax.set_ylabel('亿元', fontproperties=FONT); ax.legend(prop=FONT, loc='upper left')
ax.set_xticks(list(x)); ax.set_xticklabels(years, fontproperties=FONT)
fig.tight_layout()
out3=CHART/'1810_小米集团_营运质量现金流.png'; fig.savefig(out3,bbox_inches='tight',facecolor='white'); plt.close(fig); print(out3)
