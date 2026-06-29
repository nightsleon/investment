from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import font_manager

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / 'data'
CHARTS = BASE / 'charts'
CHARTS.mkdir(exist_ok=True)

# Font setup for macOS Chinese
FONT_PROP = None
for fp in ['/System/Library/Fonts/Hiragino Sans GB.ttc','/System/Library/Fonts/STHeiti Medium.ttc','/System/Library/Fonts/Supplemental/Arial Unicode.ttf']:
    if Path(fp).exists():
        font_manager.fontManager.addfont(fp)
        FONT_PROP = font_manager.FontProperties(fname=fp)
        plt.rcParams['font.sans-serif'] = [FONT_PROP.get_name()]
        break
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['axes.facecolor'] = 'white'

BLUE = '#4C78A8'
ORANGE = '#F58518'
GREEN = '#54A24B'
RED = '#E45756'
GRAY = '#9AA0A6'
TEAL = '#72B7B2'
PURPLE = '#B279A2'
YELLOW = '#EECA3B'

def set_title(ax, title, subtitle=None):
    ax.set_title(title if not subtitle else f'{title}\n{subtitle}', loc='left', fontsize=15, fontproperties=FONT_PROP, pad=14)

def style(ax):
    ax.grid(axis='y', alpha=.22, linestyle='-')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    for label in ax.get_xticklabels()+ax.get_yticklabels():
        label.set_fontproperties(FONT_PROP)

def save(fig, name):
    fig.tight_layout()
    fig.savefig(CHARTS/name, dpi=180, bbox_inches='tight')
    plt.close(fig)
    print(CHARTS/name)

annual = pd.read_csv(DATA/'annual_financials_2020_2025.csv')
quarter = pd.read_csv(DATA/'quarterly_profit_ttm.csv', parse_dates=['date'])
prod = pd.read_csv(DATA/'product_structure_2025.csv')
cash = pd.read_csv(DATA/'cash_position_2025_pdf_verified.csv')

# 4.2 利润增长来源与持续性：年度扣非 + 同比
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12.5, 8), gridspec_kw={'height_ratios':[2.2,1]}, sharex=True)
years = annual['年份'].astype(int)
profits = annual['扣非净利(亿)']
yoy = profits.pct_change()*100
bars = ax1.bar(years, profits, color=[ORANGE if y in [2021,2022] else BLUE for y in years], width=.55)
set_title(ax1, '4.2 扣非利润高点已过，当前仍在低位修复', '2022年周期高点不可线性外推；2025-2026Q1 TTM仍约45亿')
ax1.set_ylabel('扣非净利润（亿元）', fontproperties=FONT_PROP)
style(ax1)
for b, v in zip(bars, profits):
    ax1.text(b.get_x()+b.get_width()/2, b.get_height()+3, f'{v:.1f}', ha='center', fontsize=9, fontproperties=FONT_PROP)
colors = [GREEN if (not np.isnan(v) and v>=0) else RED for v in yoy]
ax2.bar(years, yoy, color=colors, width=.55)
ax2.axhline(0, color='#333', lw=.8)
ax2.set_ylabel('扣非同比', fontproperties=FONT_PROP)
style(ax2)
for x, v in zip(years, yoy):
    if np.isnan(v):
        continue
    ax2.text(x, v + (8 if v>=0 else -13), f'{v:.0f}%', ha='center', fontsize=9, fontproperties=FONT_PROP)
save(fig, '600089_4.2_扣非利润趋势与同比增速图.png')

# 4.3 现金流质量：净利润/OCF/FCF + 覆盖率
fig, (ax1, ax2) = plt.subplots(2,1,figsize=(12.5,8.2), gridspec_kw={'height_ratios':[2.2,1]}, sharex=True)
x = np.arange(len(annual)); w=.25
net = annual['归母净利(亿)']; ocf = annual['经营现金流(亿)']; fcf = annual['自由现金流(亿)']
ax1.bar(x-w, net, width=w, color=BLUE, label='归母净利')
ax1.bar(x, ocf, width=w, color=GREEN, label='经营现金流')
ax1.bar(x+w, fcf, width=w, color=[RED if v<0 else ORANGE for v in fcf], label='自由现金流')
set_title(ax1, '4.3 经营现金流能覆盖利润，但自由现金流被资本开支吞噬', '2024-2025自由现金流连续为负，2025年缺口扩大到-127.5亿')
ax1.set_ylabel('亿元', fontproperties=FONT_PROP)
ax1.legend(prop=FONT_PROP, ncol=3, frameon=False)
style(ax1)
for xi, v in zip(x+w, fcf):
    ax1.text(xi, v + (6 if v>=0 else -12), f'{v:.1f}', ha='center', fontsize=8.5, fontproperties=FONT_PROP)
ocf_cov = ocf / net
fcf_cov = fcf / net
ax2.plot(x, ocf_cov, marker='o', lw=2.2, color=GREEN, label='经营现金流/净利')
ax2.plot(x, fcf_cov, marker='s', lw=2.2, color=RED, label='自由现金流/净利')
ax2.axhline(1, color='#777', lw=.9, ls='--')
ax2.axhline(0, color='#333', lw=.8)
ax2.set_ylabel('覆盖倍数', fontproperties=FONT_PROP)
ax2.set_xticks(x); ax2.set_xticklabels(annual['年份'].astype(int), fontproperties=FONT_PROP)
ax2.legend(prop=FONT_PROP, ncol=2, frameon=False)
style(ax2)
save(fig, '600089_4.3_净利润经营现金流自由现金流对比图.png')

# 4.4 现金头寸：现金类资产 vs 长期债务 waterfall-like
fig, ax = plt.subplots(figsize=(12.5,6.8))
items = ['可用货币资金','交易性金融资产','一年内到期大额存单','其他流动资产大额存单','长期债务合计','可用现金头寸']
vals = [256.8754-58.7050, 2.7126, 2.1860, 7.0242, -462.8002, -252.7071]
colors = [GREEN, GREEN, GREEN, GREEN, RED, '#444444']
ax.bar(items, vals, color=colors, width=.62)
ax.axhline(0, color='#333', lw=.9)
set_title(ax, '4.4 可用现金头寸为负，资产负债表不提供安全边际', '扣除受限货币资金后，可用现金头寸约-252.7亿')
ax.set_ylabel('亿元', fontproperties=FONT_PROP)
style(ax)
for i, v in enumerate(vals):
    ax.text(i, v + (8 if v>=0 else -18), f'{v:.1f}', ha='center', fontsize=10, fontproperties=FONT_PROP)
plt.xticks(rotation=18, ha='right')
save(fig, '600089_4.4_现金头寸与长期债务对比图.png')

# 4.5 营运质量：应收/存货/合同负债 + 资产负债率
fig, (ax1, ax2) = plt.subplots(2,1,figsize=(12.5,8), gridspec_kw={'height_ratios':[2.2,1]}, sharex=True)
x = np.arange(len(annual)); w=.25
ax1.bar(x-w, annual['应收账款(亿)'], width=w, color=BLUE, label='应收账款')
ax1.bar(x, annual['存货(亿)'], width=w, color=ORANGE, label='存货')
ax1.bar(x+w, annual['合同负债(亿)'], width=w, color=TEAL, label='合同负债')
set_title(ax1, '4.5 营收横盘时，应收和存货继续上升', '2025年应收195亿、存货214亿，营运占款压力增加')
ax1.set_ylabel('亿元', fontproperties=FONT_PROP)
ax1.legend(prop=FONT_PROP, ncol=3, frameon=False)
style(ax1)
ax2.plot(x, annual['资产负债率%'], marker='o', lw=2.2, color=PURPLE, label='资产负债率')
ax2.set_ylabel('资产负债率%', fontproperties=FONT_PROP)
ax2.set_xticks(x); ax2.set_xticklabels(annual['年份'].astype(int), fontproperties=FONT_PROP)
ax2.set_ylim(48, 60)
ax2.legend(prop=FONT_PROP, frameon=False)
style(ax2)
save(fig, '600089_4.5_应收存货合同负债变化图.png')

# 4.6 产品结构：收入占比 + 毛利率
prod_plot = prod.sort_values('收入(亿)', ascending=True)
fig, ax1 = plt.subplots(figsize=(12.5,8))
y = np.arange(len(prod_plot))
colors = [ORANGE if '新能源' in n else (GREEN if '发电' in n or '黄金' in n else BLUE) for n in prod_plot['ITEM_NAME']]
ax1.barh(y, prod_plot['收入(亿)'], color=colors, alpha=.9)
ax1.set_yticks(y); ax1.set_yticklabels(prod_plot['ITEM_NAME'], fontproperties=FONT_PROP)
ax1.set_xlabel('收入（亿元）', fontproperties=FONT_PROP)
set_title(ax1, '4.6 收入第一大来源是电气设备，但利润结构受多周期业务影响', '新能源产品及工程收入占比13.9%，但毛利率仅0.6%')
style(ax1)
for yi, rev, ratio, margin in zip(y, prod_plot['收入(亿)'], prod_plot['占比%'], prod_plot['毛利率%']):
    ax1.text(rev+5, yi, f'{rev:.1f}亿 / {ratio:.1f}% / 毛利{margin:.1f}%', va='center', fontsize=9, fontproperties=FONT_PROP)
save(fig, '600089_4.6_2025年收入结构图.png')
