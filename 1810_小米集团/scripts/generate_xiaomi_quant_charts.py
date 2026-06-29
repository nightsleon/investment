#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import matplotlib.dates as mdates
import yfinance as yf

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / 'data'
CHART = BASE / 'charts'
DATA.mkdir(exist_ok=True)
CHART.mkdir(exist_ok=True)

FONT_CANDIDATES = [
    '/System/Library/Fonts/Hiragino Sans GB.ttc',
    '/System/Library/Fonts/STHeiti Medium.ttc',
    '/System/Library/Fonts/PingFang.ttc',
    '/System/Library/Fonts/Supplemental/Arial Unicode.ttf',
]
for fp in FONT_CANDIDATES:
    if Path(fp).exists():
        FONT = FontProperties(fname=fp)
        break
else:
    FONT = FontProperties()
plt.rcParams['axes.unicode_minus'] = False

BLUE='#2563EB'; ORANGE='#F97316'; GREEN='#16A34A'; RED='#DC2626'; PURPLE='#7C3AED'; GRAY='#64748B'

def style(ax):
    ax.grid(axis='y', alpha=0.22)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    for label in ax.get_xticklabels()+ax.get_yticklabels():
        label.set_fontproperties(FONT)

def title(ax, text, sub=None):
    ax.set_title(text, fontproperties=FONT, fontsize=17, weight='bold', pad=16)
    if sub:
        ax.text(0.5, 1.01, sub, transform=ax.transAxes, ha='center', va='bottom', fontproperties=FONT, fontsize=10, color='#555')

def save(fig, name):
    out = CHART / name
    fig.savefig(out, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(out)

annual = pd.read_csv(DATA/'xiaomi_annual_core.csv', index_col=0)
annual = annual.loc['2019-12-31':'2025-12-31'].copy()

# 现金头寸口径校正：港股 IFRS 的“按公允价值计入损益之短期投资”属于彼得林奇口径下的有价证券。
# 旧版 annual_core.csv 的“短期投资”只含摊余成本短投，漏算了 FVPL 短投。
balance_raw_path = DATA / 'balance_annual_raw.csv'
if balance_raw_path.exists():
    balance_raw = pd.read_csv(balance_raw_path, index_col='date')
    for dt in annual.index:
        if dt in balance_raw.index:
            row = balance_raw.loc[dt]
            fvpl_short = 0 if pd.isna(row.get('指定以公允价值记账之金融资产(流动)', np.nan)) else row['指定以公允价值记账之金融资产(流动)'] / 1e8
            amortized_short = 0 if pd.isna(row.get('短期投资', np.nan)) else row['短期投资'] / 1e8
            annual.loc[dt, '短期投资'] = fvpl_short + amortized_short
            annual.loc[dt, '现金头寸_近似'] = (
                annual.loc[dt, '现金及等价物'] + annual.loc[dt, '短期存款'] +
                annual.loc[dt, '中长期存款'] + annual.loc[dt, '短期投资'] - annual.loc[dt, '长期贷款']
            )
    annual.to_csv(DATA / 'xiaomi_annual_core.csv')

years = [x[:4] for x in annual.index]
x = np.arange(len(years))

# 4.1 ROE + normalized DuPont factors
fig = plt.figure(figsize=(15, 8), dpi=180)
gs = fig.add_gridspec(2, 1, height_ratios=[1.15, 1], hspace=0.34)
ax0 = fig.add_subplot(gs[0])
ax0.bar(x, annual['简单ROE'] * 100, width=0.46, color='#93C5FD')
ax0.axhline(0, color='#999', lw=0.8)
ax0.set_xticks(x); ax0.set_xticklabels(years, fontproperties=FONT)
ax0.set_ylabel('ROE %', fontproperties=FONT)
style(ax0); title(ax0, '小米集团：ROE从2022低谷修复，2025回到15.6%', '杜邦三因子按2019=100归一化：净利率修复最明显，资产周转率仍低于早期')
for i, v in enumerate(annual['简单ROE'] * 100):
    ax0.text(i, v + (0.6 if v >= 0 else -0.6), f'{v:.1f}%', ha='center', va='bottom' if v >= 0 else 'top', fontproperties=FONT, fontsize=9)

ax1 = fig.add_subplot(gs[1])
metrics = [
    ('净利率', '净利率', '%', RED, 100),
    ('总资产周转率', '总资产周转率', '次', GREEN, 1),
    ('权益乘数', '权益乘数', '倍', PURPLE, 1),
]
for label, col, unit, color, mult in metrics:
    raw = annual[col].astype(float) * mult
    norm = raw / raw.iloc[0] * 100
    ax1.plot(x, norm, marker='o', color=color, lw=2.4, label=f'{label}（2019=100）')
    last_norm = norm.iloc[-1]
    last_raw = raw.iloc[-1]
    actual = f'{last_raw:.1f}{unit}' if unit != '%' else f'{last_raw:.1f}%'
    y_offset = {'净利率': 0, '总资产周转率': -10, '权益乘数': 10}[label]
    ax1.annotate(
        f'{label} {actual}',
        xy=(x[-1], last_norm), xytext=(12, y_offset), textcoords='offset points',
        fontproperties=FONT, color=color, va='center', fontsize=10
    )
ax1.axhline(100, color='#999', lw=0.9, ls='--', alpha=0.8)
ax1.set_xticks(x); ax1.set_xticklabels(years, fontproperties=FONT)
ax1.set_ylabel('归一化（2019=100）', fontproperties=FONT)
ax1.set_xlim(x[0] - 0.35, x[-1] + 0.85)
style(ax1)
ax1.legend(prop=FONT, loc='upper left', ncol=3, frameon=False)
fig.tight_layout()
save(fig, '1810_4.1_ROE与杜邦三因子趋势图.png')

# 4.2 profit trend
q_path = DATA / '1810_小米集团_季度股价利润数据.csv'
q = pd.read_csv(q_path) if q_path.exists() else None
latest_ttm = float(q.loc[q['quarter_label'] == '2026Q1', 'profit_ttm_yi'].iloc[-1]) if q is not None and (q['quarter_label'] == '2026Q1').any() else np.nan
profit_labels = years + ['2026Q1\nTTM']
profit_values = list(annual['股东应占溢利'].astype(float).values) + [latest_ttm]
profit_x = np.arange(len(profit_labels))
fig, ax1 = plt.subplots(figsize=(15, 7.5), dpi=180)
ax2 = ax1.twinx()
bar_colors = ['#FDBA74'] * len(years) + ['#FCA5A5']
bars = ax1.bar(profit_x, profit_values, width=0.46, color=bar_colors, label='股东应占溢利/TTM（亿元）')
ax1.axhline(0, color='#999', lw=0.8)
ax1.set_xticks(profit_x); ax1.set_xticklabels(profit_labels, fontproperties=FONT)
ax1.set_ylabel('亿元', fontproperties=FONT)
style(ax1)

profit_yoy = list((annual['股东应占溢利'].astype(float).pct_change() * 100).values)
if q is not None and np.isfinite(latest_ttm) and (q['quarter_label'] == '2025Q1').any():
    ttm_2025q1 = float(q.loc[q['quarter_label'] == '2025Q1', 'profit_ttm_yi'].iloc[-1])
    profit_yoy.append((latest_ttm / ttm_2025q1 - 1) * 100)
else:
    profit_yoy.append(np.nan)
yoy_line, = ax2.plot(profit_x, profit_yoy, marker='o', color=BLUE, lw=2.2, label='利润同比/TTM同比')
ax2.axhline(0, color='#999', lw=0.8, ls='--', alpha=0.7)
ax2.set_ylabel('同比 %', fontproperties=FONT)
ax2.spines['top'].set_visible(False)
for label in ax2.get_yticklabels():
    label.set_fontproperties(FONT)

title(ax1, '小米集团：股东应占溢利趋势', '2019-2025为年度股东应占溢利；2026Q1为最近四季度TTM')
for i, v in enumerate(profit_values):
    if np.isfinite(v):
        color = '#8A3A00' if i < len(years) else RED
        ax1.text(i, v + 10, f'{v:.0f}', ha='center', fontproperties=FONT, fontsize=9, color=color)
for i, v in enumerate(profit_yoy):
    if np.isfinite(v) and i > 0:
        ax2.text(i, v + (18 if v >= 0 else -18), f'{v:.0f}%', ha='center', va='bottom' if v >= 0 else 'top', fontproperties=FONT, fontsize=8, color=BLUE)
if np.isfinite(latest_ttm):
    ax1.annotate(
        '2026Q1 TTM',
        xy=(profit_x[-1], latest_ttm), xytext=(0, -28), textcoords='offset points',
        ha='center', va='top', fontproperties=FONT, fontsize=9, color=RED
    )
ax1.legend([bars, yoy_line], ['股东应占溢利/TTM（亿元）', '利润同比/TTM同比'], loc='upper left', prop=FONT, frameon=False)
fig.tight_layout(); save(fig, '1810_4.2_扣非利润趋势与同比增速图.png')

# 4.3 product structure 2025
product = pd.DataFrame([
    ['智能手机', 1864, -2.8, 10.9],
    ['IoT与生活消费品', 1232, 18.3, 23.1],
    ['互联网服务', 362, 6.2, 76.0],
    ['智能电动汽车及AI等创新业务', 1061, 223.8, 20.1],
    ['其他相关业务', 54, 30.5, np.nan],
], columns=['业务','收入_亿元','同比_%','毛利率_%'])
product['收入占比_%'] = product['收入_亿元'] / 4572.87 * 100
product['2024收入_亿元_反推'] = product['收入_亿元'] / (1 + product['同比_%'] / 100)
product['收入增量_亿元'] = product['收入_亿元'] - product['2024收入_亿元_反推']
product.to_csv(DATA/'xiaomi_2025_product_structure.csv', index=False, encoding='utf-8-sig')
fig, axes = plt.subplots(1,2,figsize=(16,7), dpi=180, gridspec_kw={'width_ratios':[1.35,1]})
colors_map = {
    '智能手机': '#93C5FD',
    'IoT与生活消费品': '#FDBA74',
    '智能电动汽车及AI等创新业务': '#FDE68A',
    '互联网服务': '#A7F3D0',
    '其他相关业务': '#CBD5E1',
}
prod = product.sort_values('收入_亿元', ascending=True)
axes[0].barh(prod['业务'], prod['收入_亿元'], height=0.52, color=[colors_map[b] for b in prod['业务']])
style(axes[0]); axes[0].set_xlabel('收入（亿元）', fontproperties=FONT)
for y, val, pct, gm in zip(prod['业务'], prod['收入_亿元'], prod['收入占比_%'], prod['毛利率_%']):
    gm_text = '毛利率-' if pd.isna(gm) else f'毛利率{gm:.1f}%'
    axes[0].text(val + 22, y, f'{val:.0f}亿 / {pct:.1f}% / {gm_text}', va='center', fontproperties=FONT, fontsize=9)

inc = product.sort_values('收入增量_亿元', ascending=True)
inc_colors = [GREEN if v >= 0 else RED for v in inc['收入增量_亿元']]
axes[1].barh(inc['业务'], inc['收入增量_亿元'], height=0.52, color=inc_colors)
axes[1].axvline(0, color='#999', lw=0.8)
style(axes[1]); axes[1].set_xlabel('收入增量（亿元，按同比反推）', fontproperties=FONT)
for y, inc_val, yoy in zip(inc['业务'], inc['收入增量_亿元'], inc['同比_%']):
    # 负增量标签放在柱体右侧，避免和左侧品类标签/零轴重叠
    ha = 'left'
    dx = 12
    axes[1].annotate(f'{inc_val:+.0f}亿 / {yoy:+.1f}%', xy=(inc_val, y), xytext=(dx, 0), textcoords='offset points',
                     va='center', ha=ha, fontproperties=FONT, fontsize=9, color=GREEN if inc_val >= 0 else RED)
axes[1].set_xlim(min(-120, inc['收入增量_亿元'].min() * 1.8), inc['收入增量_亿元'].max() * 1.15)
title(axes[0], '小米集团：2025年产品收入结构', '左图为收入/占比/毛利率；右图为按同比反推的收入增量贡献')
axes[1].set_title('2025收入增量贡献', fontproperties=FONT, fontsize=12, pad=10)
fig.tight_layout(); save(fig, '1810_4.3_收入结构与产品增速图.png')

# 4.4 cashflow
fig, axes = plt.subplots(2,1,figsize=(15,10), dpi=180, sharex=True, gridspec_kw={'height_ratios':[1.5,1]})
w=0.25
axes[0].bar(x-w, annual['股东应占溢利'], width=w, color='#FDBA74', label='股东应占溢利')
axes[0].bar(x, annual['经营现金流'], width=w, color='#93C5FD', label='经营现金流')
axes[0].bar(x+w, annual['自由现金流'], width=w, color='#86EFAC', label='自由现金流')
axes[0].axhline(0,color='#999',lw=0.8); style(axes[0]); axes[0].set_ylabel('亿元', fontproperties=FONT)
axes[0].legend(prop=FONT, loc='upper left')
title(axes[0], '小米集团：现金流与利润对比', '上图为利润、经营现金流和自由现金流；下图为现金流覆盖率')
opf = annual['经营现金流']/annual['股东应占溢利']*100
fcf = annual['自由现金流']/annual['股东应占溢利']*100
for series, color, label, marker in [(opf, BLUE, '经营现金流/利润', 'o'), (fcf, RED, '自由现金流/利润', 's')]:
    clipped = series.clip(lower=-100, upper=250)
    axes[1].plot(x, clipped, marker=marker, color=color, lw=2.2, label=label)
axes[1].axhline(100,color='#999',lw=0.8,ls='--')
axes[1].set_ylim(-120, 270)
axes[1].set_xticks(x); axes[1].set_xticklabels(years, fontproperties=FONT)
axes[1].set_ylabel('%', fontproperties=FONT); style(axes[1]); axes[1].legend(prop=FONT, loc='upper right')
for idx, year in enumerate(years):
    if year == '2022':
        axes[1].annotate('2022极值\n已截断', xy=(idx, -100), xytext=(0, 16), textcoords='offset points',
                         ha='center', va='bottom', fontproperties=FONT, fontsize=8, color=GRAY)
last_i = len(years) - 1
axes[1].annotate(f'{opf.iloc[-1]:.0f}%', xy=(last_i, opf.iloc[-1]), xytext=(10, 0), textcoords='offset points',
                 va='center', fontproperties=FONT, fontsize=9, color=BLUE)
axes[1].annotate(f'{fcf.iloc[-1]:.0f}%', xy=(last_i, fcf.iloc[-1]), xytext=(10, -10), textcoords='offset points',
                 va='center', fontproperties=FONT, fontsize=9, color=RED)
fig.tight_layout(); save(fig, '1810_4.4_净利润经营现金流自由现金流对比图.png')

# 4.5 cash position
recent = annual.loc['2021-12-31':'2025-12-31'].copy(); yrs=[i[:4] for i in recent.index]; xx=np.arange(len(yrs))
fig, ax1 = plt.subplots(figsize=(15,7.5), dpi=180)
ax2 = ax1.twinx()
bars = ax1.bar(xx, recent['现金头寸_近似'], width=0.46, color='#93C5FD', label='现金头寸近似（亿元）')
line, = ax2.plot(xx, recent['资产负债率']*100, marker='o', color=RED, lw=2.2, label='资产负债率')
ax1.axhline(0,color='#999',lw=0.8)
ax1.set_xticks(xx); ax1.set_xticklabels(yrs, fontproperties=FONT)
ax1.set_ylabel('现金头寸（亿元）', fontproperties=FONT)
ax2.set_ylabel('资产负债率 %', fontproperties=FONT)
# 资产负债率实际只在约47%-53%之间小幅波动，右轴从0开始避免视觉夸大变化。
ax2.set_ylim(0, 60)
style(ax1); ax2.spines['top'].set_visible(False)
for label in ax2.get_yticklabels():
    label.set_fontproperties(FONT)
title(ax1, '小米集团：现金头寸与资产负债率', '现金头寸明细见表格；图中仅展示现金安全垫与资产负债率变化')
for i, v in enumerate(recent['现金头寸_近似']):
    ax1.text(i, v + 35, f'{v:.0f}亿', ha='center', fontproperties=FONT, fontsize=9, color=BLUE)
for i, v in enumerate(recent['资产负债率']*100):
    ax2.annotate(f'{v:.1f}%', xy=(i, v), xytext=(0, 10), textcoords='offset points',
                 ha='center', va='bottom', fontproperties=FONT, fontsize=9, color=RED)
ax1.legend([bars, line], ['现金头寸近似（亿元）', '资产负债率'], loc='upper left', prop=FONT, frameon=False)
fig.tight_layout(); save(fig, '1810_4.5_现金头寸拆解与资产负债安全垫图.png')

# 4.6 operating quality
recent = annual.loc['2021-12-31':'2025-12-31'].copy(); yrs=[i[:4] for i in recent.index]; xx=np.arange(len(yrs))
fig, axes = plt.subplots(2,1,figsize=(15,10), dpi=180, sharex=True, gridspec_kw={'height_ratios':[1.4,1]})
w=0.25
axes[0].bar(xx-w, recent['应收账款'], width=w, color='#BFDBFE', label='应收账款')
axes[0].bar(xx, recent['存货'], width=w, color='#FDE68A', label='存货')
axes[0].bar(xx+w, recent['合同负债'], width=w, color='#BBF7D0', label='合同负债/预收')
style(axes[0]); axes[0].set_ylabel('亿元', fontproperties=FONT); axes[0].legend(prop=FONT, loc='upper left')
title(axes[0], '小米集团：存货随汽车扩张上升，但合同负债也同步抬升', '观察重点不是存货单点上升，而是存货、订单/合同负债、交付和折扣是否匹配')
rev_yoy = recent['营收'].pct_change()*100
inv_yoy = recent['存货'].pct_change()*100
inv_rev = recent['存货']/recent['营收']*100
axes[1].bar(xx-0.15, rev_yoy, width=0.3, color='#93C5FD', label='营收同比')
axes[1].bar(xx+0.15, inv_yoy, width=0.3, color='#FDBA74', label='存货同比')
axes[1].plot(xx, inv_rev, marker='o', color=RED, label='存货/营收')
axes[1].axhline(0,color='#999',lw=0.8); axes[1].set_xticks(xx); axes[1].set_xticklabels(yrs, fontproperties=FONT)
axes[1].set_ylabel('%', fontproperties=FONT); style(axes[1]); axes[1].legend(prop=FONT, loc='upper left')
fig.tight_layout(); save(fig, '1810_4.6_应收存货合同负债变化图.png')

# price-profit charts with current point
q = pd.read_csv(DATA/'1810_小米集团_季度股价利润数据.csv', parse_dates=['date','trade_date'])
# yfinance latest quote and fx
h = yf.Ticker('1810.HK').history(period='10d')
latest = h.iloc[-1]
latest_date = pd.Timestamp(latest.name).tz_localize(None)
fx = float(yf.Ticker('HKDCNY=X').history(period='5d')['Close'].iloc[-1])
fast = yf.Ticker('1810.HK').fast_info
shares = int(fast.get('shares') or 25739565494)
price = float(latest['Close'])
market_hkd = price * shares
market_cny_yi = market_hkd * fx / 1e8
ttm = float(q.iloc[-1]['profit_ttm_yi'])
pe = market_cny_yi / ttm
cash = float(annual.loc['2025-12-31','现金头寸_近似'])
ex_cash_pe = (market_cny_yi - cash) / ttm
quote = {
    'date': str(latest_date.date()), 'price_hkd': price, 'shares': shares, 'market_cap_hkd_yi': market_hkd/1e8,
    'hkd_cny': fx, 'market_cap_cny_yi': market_cny_yi, 'profit_ttm_yi': ttm, 'pe': pe,
    'cash_position_yi': cash, 'ex_cash_pe': ex_cash_pe
}
(DATA/'quote_yfinance.json').write_text(json.dumps(quote, ensure_ascii=False, indent=2))
# append current row as observation, not quarter result
cur = q.iloc[-1].copy()
cur['date'] = latest_date
cur['quarter_label'] = '2026-06-29'
cur['trade_date'] = latest_date
cur['close_hkd'] = price
cur['adj_close_hkd'] = price
plotq = pd.concat([q, pd.DataFrame([cur])], ignore_index=True)
# dual
fig, ax1 = plt.subplots(figsize=(16,8.5), dpi=180); ax2=ax1.twinx()
ax1.plot(plotq['date'], plotq['adj_close_hkd'], marker='o', lw=2.4, ms=4, color=BLUE, label='股价（港元）')
ax2.plot(plotq['date'], plotq['profit_ttm_yi'], marker='s', lw=2.4, ms=4, color=RED, label='股东应占溢利TTM（亿元）')
ax2.fill_between(plotq['date'], plotq['profit_ttm_yi'], alpha=0.08, color=RED)
ax1.xaxis.set_major_locator(mdates.YearLocator()); ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
style(ax1); ax2.spines['top'].set_visible(False)
for label in ax2.get_yticklabels(): label.set_fontproperties(FONT)
ax1.set_ylabel('股价（港元）', fontproperties=FONT, color=BLUE); ax2.set_ylabel('股东应占溢利TTM（亿元）', fontproperties=FONT, color=RED)
title(ax1, '小米集团：股价已从2025高位回撤，利润TTM也从高位回落', '双轴图只看趋势和斜率，不比较绝对高低；最新点为2026-06-29股价+2026Q1 TTM利润')
lines=ax1.get_lines()+ax2.get_lines(); ax1.legend(lines, [l.get_label() for l in lines], loc='upper left', prop=FONT)
last=plotq.iloc[-1]
ax1.annotate(f"{price:.2f}港元", xy=(last['date'], price), xytext=(8,8), textcoords='offset points', color=BLUE, fontproperties=FONT, bbox=dict(fc='white',ec=BLUE,boxstyle='round,pad=0.2'))
ax2.annotate(f"TTM {ttm:.1f}亿", xy=(last['date'], ttm), xytext=(8,-12), textcoords='offset points', color=RED, fontproperties=FONT, bbox=dict(fc='white',ec=RED,boxstyle='round,pad=0.2'))
fig.tight_layout(); save(fig, '1810_小米集团_股价vs股东应占溢利TTM_双Y轴.png')
# norm
m=plotq[plotq['profit_ttm_yi']>0].copy(); m['price_norm']=m['adj_close_hkd']/m['adj_close_hkd'].iloc[0]; m['profit_norm']=m['profit_ttm_yi']/m['profit_ttm_yi'].iloc[0]
fig, ax=plt.subplots(figsize=(16,8), dpi=180)
ax.plot(m['date'], m['price_norm'], marker='o', color=BLUE, lw=2.4, label='股价/基期')
ax.plot(m['date'], m['profit_norm'], marker='s', color=RED, lw=2.4, label='利润TTM/基期')
ax.xaxis.set_major_locator(mdates.YearLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
style(ax); ax.legend(prop=FONT, loc='upper left'); ax.set_ylabel('基期=1', fontproperties=FONT)
title(ax, '小米集团：归一化后看，2025股价明显跑赢利润，2026已回撤', '辅助图只看走势同步性，不单独判断高估/低估')
fig.tight_layout(); save(fig, '1810_小米集团_股价vs股东应占溢利TTM_归一化.png')
# single quarter
fig, ax1=plt.subplots(figsize=(16,8), dpi=180); ax2=ax1.twinx()
ax1.plot(q['date'], q['adj_close_hkd'], marker='o', color=BLUE, lw=2.2, label='季度末股价（港元）')
ax2.bar(q['date'], q['profit_q_yi'], width=55, color='#FDBA74', label='单季度股东应占溢利（亿元）')
ax2.axhline(0,color='#999',lw=0.8)
ax1.xaxis.set_major_locator(mdates.YearLocator()); ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
style(ax1); ax2.spines['top'].set_visible(False)
for label in ax2.get_yticklabels(): label.set_fontproperties(FONT)
ax1.set_ylabel('股价（港元）', fontproperties=FONT, color=BLUE); ax2.set_ylabel('单季度利润（亿元）', fontproperties=FONT, color=ORANGE)
title(ax1, '小米集团：2026Q1单季利润回落，需要验证是季节性还是趋势', '单季度利润由累计值差分得到，用于解释TTM变化')
lines=ax1.get_lines()+[ax2.patches[0]]; ax1.legend(lines, ['季度末股价（港元）','单季度股东应占溢利（亿元）'], prop=FONT, loc='upper left')
fig.tight_layout(); save(fig, '1810_小米集团_股价vs股东应占溢利_单季度.png')
print('QUOTE_JSON', DATA/'quote_yfinance.json')
