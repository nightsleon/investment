#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成小米集团-W(1810.HK)股价 vs 利润TTM对比图。

港股/A股差异处理：
1) 股票代码用 Yahoo Finance 的 1810.HK，不是 A 股 .SS/.SZ；价格单位为港元。
2) 港股财报字段用东方财富港股财务接口；这里取“股东应占溢利”（累计值），再转为单季值。
3) 小米虽为港股，但披露季度业绩；因此按季度TTM计算，不按普通港股半年报TTM。
4) 东方财富接口字段 CURRENCY 标为 HKD，但小米公告通常以人民币列报；图中利润轴标为“亿元（财报列报币种，按接口原值）”，避免与港元股价混为同一币种。
"""
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

import akshare as ak
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.font_manager import FontProperties

BASE = Path(__file__).resolve().parents[1]
DATA_DIR = BASE / 'data'
CHART_DIR = BASE / 'charts'
DATA_DIR.mkdir(parents=True, exist_ok=True)
CHART_DIR.mkdir(parents=True, exist_ok=True)

CODE_HK = '01810'
YF_CODE = '1810.HK'
NAME = '小米集团-W'


def get_font():
    candidates = [
        '/System/Library/Fonts/Hiragino Sans GB.ttc',
        '/System/Library/Fonts/STHeiti Medium.ttc',
        '/System/Library/Fonts/PingFang.ttc',
        '/System/Library/Fonts/Supplemental/Arial Unicode.ttf',
    ]
    for p in candidates:
        if Path(p).exists():
            return FontProperties(fname=p)
    return FontProperties()

FONT = get_font()
plt.rcParams['axes.unicode_minus'] = False


def fetch_financials():
    df = ak.stock_financial_hk_report_em(stock=CODE_HK, symbol='利润表', indicator='报告期')
    profit = df[df['STD_ITEM_NAME'].eq('股东应占溢利')].copy()
    if profit.empty:
        raise RuntimeError('未找到“股东应占溢利”字段')
    profit['date'] = pd.to_datetime(profit['REPORT_DATE']).dt.tz_localize(None)
    profit['year'] = profit['date'].dt.year
    profit['quarter'] = profit['date'].dt.quarter
    profit['profit_cum_yi'] = pd.to_numeric(profit['AMOUNT'], errors='coerce') / 1e8
    profit = profit[['date','year','quarter','profit_cum_yi']].sort_values('date').dropna()

    # 东方财富港股利润表为年初至报告期累计值：Q1=单季；Q2/Q3/Q4=本期累计-上一期累计。
    single = []
    last_by_year = {}
    for _, row in profit.iterrows():
        y, q, cum = int(row['year']), int(row['quarter']), float(row['profit_cum_yi'])
        if q == 1 or y not in last_by_year:
            val = cum
        else:
            val = cum - last_by_year[y]
        last_by_year[y] = cum
        single.append(val)
    profit['profit_q_yi'] = single
    profit['profit_ttm_yi'] = profit['profit_q_yi'].rolling(4).sum()
    # 上市前数据不用于股价对比
    profit = profit[profit['date'] >= pd.Timestamp('2018-09-30')].copy()
    return profit


def fetch_prices(start, end):
    raw = yf.download(YF_CODE, start=start, end=end, auto_adjust=False, progress=False)
    if raw.empty:
        raise RuntimeError('yfinance 未返回股价数据')
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    raw = raw.reset_index()
    raw['Date'] = pd.to_datetime(raw['Date']).dt.tz_localize(None)
    cols = ['Date','Close']
    if 'Adj Close' in raw.columns:
        cols.append('Adj Close')
    price = raw[cols].rename(columns={'Date':'trade_date','Close':'close_hkd','Adj Close':'adj_close_hkd'})
    if 'adj_close_hkd' not in price.columns:
        price['adj_close_hkd'] = price['close_hkd']
    return price


def align(fin, price):
    rows = []
    for _, r in fin.dropna(subset=['profit_ttm_yi']).iterrows():
        sub = price[price['trade_date'] <= r['date']]
        if sub.empty:
            continue
        p = sub.iloc[-1]
        rows.append({
            'date': r['date'],
            'quarter_label': f"{int(r['year'])}Q{int(r['quarter'])}",
            'trade_date': p['trade_date'],
            'close_hkd': float(p['close_hkd']),
            'adj_close_hkd': float(p['adj_close_hkd']),
            'profit_q_yi': float(r['profit_q_yi']),
            'profit_ttm_yi': float(r['profit_ttm_yi']),
            'profit_cum_yi': float(r['profit_cum_yi']),
        })
    return pd.DataFrame(rows)


def annotate_last(ax, x, y, text, color, xytext=(8,0)):
    ax.annotate(text, xy=(x, y), xytext=xytext, textcoords='offset points',
                color=color, fontsize=11, fontproperties=FONT, va='center',
                bbox=dict(boxstyle='round,pad=0.25', fc='white', ec=color, alpha=0.9))


def style_date_axis(ax):
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax.grid(True, axis='y', alpha=0.22)
    ax.spines['top'].set_visible(False)


def plot_dual(merged):
    fig, ax1 = plt.subplots(figsize=(16, 8.5), dpi=180)
    ax2 = ax1.twinx()
    c1, c2 = '#2563EB', '#DC2626'
    l1, = ax1.plot(merged['date'], merged['adj_close_hkd'], marker='o', lw=2.6, ms=4.5, color=c1, label='股价：前复权收盘价（港元）')
    l2, = ax2.plot(merged['date'], merged['profit_ttm_yi'], marker='s', lw=2.6, ms=4.5, color=c2, label='股东应占溢利TTM（亿元）')
    ax2.fill_between(merged['date'], merged['profit_ttm_yi'], alpha=0.08, color=c2)

    ax1.set_ylabel('股价（港元，1810.HK 前复权）', fontproperties=FONT, fontsize=12, color=c1)
    ax2.set_ylabel('股东应占溢利TTM（亿元，财报列报币种）', fontproperties=FONT, fontsize=12, color=c2)
    ax1.tick_params(axis='y', labelcolor=c1)
    ax2.tick_params(axis='y', labelcolor=c2)
    style_date_axis(ax1)

    ax1.set_title('小米集团-W：股价与利润TTM趋势对比', fontproperties=FONT, fontsize=20, weight='bold', pad=18)
    subtitle = '港股口径：1810.HK 股价为港元；利润取东方财富港股财报“股东应占溢利”累计值转单季后滚动4季TTM'
    ax1.text(0.5, 1.01, subtitle, transform=ax1.transAxes, ha='center', va='bottom', fontproperties=FONT, fontsize=11, color='#555')
    ax1.legend(handles=[l1, l2], loc='upper left', prop=FONT, frameon=True, framealpha=0.95)

    last = merged.iloc[-1]
    annotate_last(ax1, last['date'], last['adj_close_hkd'], f"{last['quarter_label']} 股价 {last['adj_close_hkd']:.2f}港元", c1, (10, 8))
    annotate_last(ax2, last['date'], last['profit_ttm_yi'], f"TTM {last['profit_ttm_yi']:.1f}亿", c2, (10, -12))

    note = '注意：双轴图只看趋势/斜率是否同步，不比较两条线的绝对高低；港元股价与利润列报币种不可直接相除。'
    fig.text(0.08, 0.035, note, fontproperties=FONT, fontsize=10, color='#666')
    fig.tight_layout(rect=(0, 0.06, 1, 0.95))
    out = CHART_DIR / '1810_小米集团_股价vs股东应占溢利TTM_双Y轴.png'
    fig.savefig(out, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return out


def plot_norm(merged):
    # 归一化不能以负数/零利润TTM为基期，否则后续正常正利润会被画成负数。
    # 小米2018Q3的GAAP股东应占溢利TTM为负，主要受上市前可转换可赎回优先股公允价值变动等非经营项影响；
    # 因此归一化图从第一个正TTM点开始。
    m = merged[merged['profit_ttm_yi'] > 0].copy()
    if m.empty:
        raise RuntimeError('没有正利润TTM，无法生成归一化图')
    m['price_norm'] = m['adj_close_hkd'] / m['adj_close_hkd'].iloc[0]
    m['profit_norm'] = m['profit_ttm_yi'] / m['profit_ttm_yi'].iloc[0]
    fig, ax = plt.subplots(figsize=(16, 8), dpi=180)
    c1, c2 = '#2563EB', '#DC2626'
    ax.plot(m['date'], m['price_norm'], marker='o', lw=2.6, ms=4.5, color=c1, label='股价 / 基期')
    ax.plot(m['date'], m['profit_norm'], marker='s', lw=2.6, ms=4.5, color=c2, label='利润TTM / 基期')
    style_date_axis(ax)
    ax.set_ylabel('基期=1', fontproperties=FONT, fontsize=12)
    ax.set_title('小米集团-W：股价与利润TTM归一化趋势', fontproperties=FONT, fontsize=20, weight='bold', pad=16)
    ax.text(0.5, 1.01, '辅助图：只看走势同步性，不用于判断高估/低估', transform=ax.transAxes,
            ha='center', va='bottom', fontproperties=FONT, fontsize=11, color='#555')
    ax.legend(loc='upper left', prop=FONT, frameon=True)
    last = m.iloc[-1]
    annotate_last(ax, last['date'], last['price_norm'], f"股价 {last['price_norm']:.2f}x", c1, (10, 8))
    annotate_last(ax, last['date'], last['profit_norm'], f"利润 {last['profit_norm']:.2f}x", c2, (10, -12))
    fig.tight_layout(rect=(0, 0.03, 1, 0.95))
    out = CHART_DIR / '1810_小米集团_股价vs股东应占溢利TTM_归一化.png'
    fig.savefig(out, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return out


def main():
    fin = fetch_financials()
    price = fetch_prices('2018-07-01', (pd.Timestamp.today() + pd.Timedelta(days=1)).strftime('%Y-%m-%d'))
    merged = align(fin, price)
    if len(merged) < 6:
        raise RuntimeError(f'对齐后数据点过少：{len(merged)}')

    csv_path = DATA_DIR / '1810_小米集团_季度股价利润数据.csv'
    merged.to_csv(csv_path, index=False, encoding='utf-8-sig')
    out1 = plot_dual(merged)
    out2 = plot_norm(merged)

    corr = merged['adj_close_hkd'].corr(merged['profit_ttm_yi'])
    norm_base = merged[merged['profit_ttm_yi'] > 0].iloc[0]
    norm_tail = merged.iloc[-1]
    price_mult = norm_tail['adj_close_hkd'] / norm_base['adj_close_hkd']
    profit_mult = norm_tail['profit_ttm_yi'] / norm_base['profit_ttm_yi']
    print(f'DATA_POINTS={len(merged)}')
    print(f'PERIOD={merged.iloc[0]["quarter_label"]}~{merged.iloc[-1]["quarter_label"]}')
    print(f'NORM_BASE={norm_base["quarter_label"]}, price={norm_base["adj_close_hkd"]:.2f} HKD, profit_ttm={norm_base["profit_ttm_yi"]:.2f} yi')
    print(f'LATEST={merged.iloc[-1]["quarter_label"]}, trade_date={merged.iloc[-1]["trade_date"].date()}, price={merged.iloc[-1]["adj_close_hkd"]:.2f} HKD, profit_ttm={merged.iloc[-1]["profit_ttm_yi"]:.2f} yi')
    print(f'PRICE_MULT_FROM_POSITIVE_BASE={price_mult:.2f}')
    print(f'PROFIT_TTM_MULT_FROM_POSITIVE_BASE={profit_mult:.2f}')
    print(f'CORR={corr:.3f}')
    print(f'CSV={csv_path}')
    print(f'CHART_DUAL={out1}')
    print(f'CHART_NORM={out2}')

if __name__ == '__main__':
    main()
