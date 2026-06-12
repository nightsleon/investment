#!/usr/bin/env python3
from pathlib import Path
import json
import urllib.request
import urllib.parse
import warnings
from matplotlib import font_manager as fm
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / 'data'
CHARTS = BASE / 'charts'
CHARTS.mkdir(exist_ok=True)
CODE = '000423'
SECU = '000423.SZ'
NAME = '东阿阿胶'

warnings.filterwarnings('ignore', message='Glyph .* missing from font')

FONT_CANDIDATES = [
    '/System/Library/Fonts/Hiragino Sans GB.ttc',
    '/System/Library/Fonts/STHeiti Medium.ttc',
    '/System/Library/Fonts/Supplemental/Arial Unicode.ttf',
]
FONT_PROP = None
for _font in FONT_CANDIDATES:
    if Path(_font).exists():
        fm.fontManager.addfont(_font)
        FONT_PROP = fm.FontProperties(fname=_font)
        plt.rcParams['font.family'] = FONT_PROP.get_name()
        break
plt.rcParams['axes.unicode_minus'] = False
plt.style.use('seaborn-v0_8-whitegrid')

BLUE = '#2563EB'
ORANGE = '#F97316'
GREEN = '#10B981'
RED = '#EF4444'
PURPLE = '#8B5CF6'
GRAY = '#6B7280'
LIGHT_BLUE = '#DBEAFE'
LIGHT_ORANGE = '#FFEDD5'
LIGHT_GREEN = '#D1FAE5'


def em(report, columns='ALL', filter_expr=None, sort='REPORT_DATE', page_size=100, pages=5, source='HSF10'):
    rows = []
    for page in range(1, pages + 1):
        params = {
            'reportName': report,
            'columns': columns,
            'filter': filter_expr or f'(SECUCODE="{SECU}")',
            'pageSize': str(page_size),
            'pageNumber': str(page),
            'sortColumns': sort,
            'sortTypes': '-1',
            'source': source,
            'client': 'PC',
        }
        url = 'https://datacenter.eastmoney.com/securities/api/data/v1/get?' + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://emweb.securities.eastmoney.com/'})
        data = json.loads(urllib.request.urlopen(req, timeout=20).read())
        page_rows = (data.get('result') or {}).get('data') or []
        if not page_rows:
            break
        rows.extend(page_rows)
    return pd.DataFrame(rows)


def annotate_source(ax, text='数据来源：同花顺Excel、东方财富API；图表：Hermes'):
    ax.text(0.995, -0.17, text, transform=ax.transAxes, ha='right', va='top', fontsize=9, color=GRAY,
            fontproperties=FONT_PROP)


def apply_font(*axes):
    for ax in axes:
        if ax is None:
            continue
        for label in ax.get_xticklabels() + ax.get_yticklabels():
            label.set_fontproperties(FONT_PROP)
        ax.title.set_fontproperties(FONT_PROP)
        ax.xaxis.label.set_fontproperties(FONT_PROP)
        ax.yaxis.label.set_fontproperties(FONT_PROP)


def load_annual_metrics():
    df = pd.read_csv(DATA / '000423_annual_metrics.csv', index_col=0)
    df.index = df.index.astype(int)
    return df.loc[2020:2025].copy()


def load_dupont():
    return pd.read_csv(DATA / '000423_dupont.csv')


def load_cashflow():
    return pd.read_csv(DATA / '000423_cashflow_metrics.csv')


def load_quarterly():
    df = pd.read_csv(DATA / '000423_quarter_ttm_from_ths.csv', index_col=0)
    df.index = pd.to_datetime(df.index)
    return df.sort_index()


def fetch_operating_quality():
    cols = 'SECUCODE,REPORT_DATE,ACCOUNTS_RECE,INVENTORY,ADVANCE_RECEIVABLES,TOTAL_LIABILITIES,TOTAL_ASSETS,DEBT_ASSET_RATIO'
    df = em('RPT_DMSK_FN_BALANCE', columns=cols, pages=20)
    if df.empty:
        raise RuntimeError('东方财富资产负债表接口返回空数据')
    df['date'] = pd.to_datetime(df['REPORT_DATE'])
    df = df.sort_values('date')
    selected = pd.to_datetime([
        '2020-12-31', '2021-12-31', '2022-12-31',
        '2023-12-31', '2024-12-31', '2025-12-31', '2026-03-31'
    ])
    df = df[df['date'].isin(selected)].copy()
    if df.empty:
        raise RuntimeError('未取到4.5所需年度/季度数据')
    for col in ['ACCOUNTS_RECE', 'INVENTORY', 'ADVANCE_RECEIVABLES', 'TOTAL_LIABILITIES', 'TOTAL_ASSETS', 'DEBT_ASSET_RATIO']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    df['应收账款'] = df['ACCOUNTS_RECE'] / 1e8
    df['存货'] = df['INVENTORY'] / 1e8
    df['合同负债'] = df['ADVANCE_RECEIVABLES'] / 1e8
    ratio = df['DEBT_ASSET_RATIO'].copy()
    need_calc = ratio.isna()
    ratio.loc[need_calc] = df.loc[need_calc, 'TOTAL_LIABILITIES'] / df.loc[need_calc, 'TOTAL_ASSETS'] * 100
    df['资产负债率'] = ratio
    df['年份'] = df['date'].dt.year
    df['标签'] = df['date'].dt.strftime('%Y-%m')
    return df[['date', '年份', '标签', '应收账款', '存货', '合同负债', '资产负债率']].reset_index(drop=True)


def chart_41():
    dup = load_dupont()
    years = dup['年份'].astype(int).tolist()
    x = np.arange(len(years))

    fig = plt.figure(figsize=(13.5, 8.2), dpi=180)
    fig.patch.set_facecolor('white')
    gs = fig.add_gridspec(2, 3, height_ratios=[2.15, 1.05], hspace=0.18, wspace=0.18)
    ax1 = fig.add_subplot(gs[0, :])
    ax_npm = fig.add_subplot(gs[1, 0])
    ax_turn = fig.add_subplot(gs[1, 1])
    ax_lev = fig.add_subplot(gs[1, 2])

    ax1.set_facecolor('white')
    bars = ax1.bar(x, dup['ROE加权%'], width=0.50, color='#DCEAFE', edgecolor=BLUE, linewidth=1.05, label='加权ROE(%)', zorder=2)
    ax1.set_ylabel('ROE(%)', color=BLUE)
    ax1.set_xticks(x)
    ax1.set_xticklabels(years)
    ax1.tick_params(axis='y', labelcolor=BLUE)
    ax1.tick_params(axis='x', length=0)
    ax1.set_ylim(0, max(dup['ROE加权%']) * 1.22)
    ax1.grid(axis='y', color='#E5E7EB', linewidth=0.8)
    ax1.grid(axis='x', visible=False)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    ax1.spines['left'].set_color('#D1D5DB')
    ax1.spines['bottom'].set_color('#D1D5DB')

    for rect, val in zip(bars, dup['ROE加权%']):
        ax1.text(rect.get_x() + rect.get_width()/2, rect.get_height() + 0.28, f'{val:.1f}',
                 ha='center', va='bottom', fontsize=8.8, color='#4B5563', fontproperties=FONT_PROP)

    fig.suptitle(f'{NAME}：ROE与杜邦三因子趋势图（2020-2025）', fontsize=16, y=0.98, fontproperties=FONT_PROP)
    fig.text(0.5, 0.935, '上图看ROE修复结果，下排分别看净利率、周转率、权益乘数的变化路径',
             ha='center', va='center', fontsize=11.5, color=GRAY, fontproperties=FONT_PROP)
    ax1.legend(loc='upper left', frameon=False, prop=FONT_PROP)

    factor_specs = [
        (ax_npm, '净利率%', ORANGE, '净利率(%)'),
        (ax_turn, '总资产周转率', '#0F766E', '总资产周转率'),
        (ax_lev, '权益乘数', '#7C6EE6', '权益乘数'),
    ]

    for ax, col, color, title in factor_specs:
        ax.set_facecolor('white')
        ax.plot(x, dup[col], color=color, marker='o', markersize=4.8, linewidth=2.0)
        ax.set_title(title, fontsize=11, color=color, pad=8, fontproperties=FONT_PROP)
        ax.set_xticks(x)
        ax.set_xticklabels(years, fontsize=8)
        ax.grid(axis='y', color='#E5E7EB', linewidth=0.7)
        ax.grid(axis='x', visible=False)
        ax.tick_params(axis='x', length=0)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#D1D5DB')
        ax.spines['bottom'].set_color('#D1D5DB')
        ymin = dup[col].min()
        ymax = dup[col].max()
        margin = (ymax - ymin) * 0.22 if ymax > ymin else ymax * 0.1 + 0.1
        ax.set_ylim(ymin - margin * 0.35, ymax + margin)
        ax.text(x[-1], dup[col].iloc[-1] + margin * 0.12, f'{dup[col].iloc[-1]:.2f}',
                color=color, fontsize=8.5, ha='center', va='bottom', fontproperties=FONT_PROP)

    ax_npm.set_ylabel('%', color=GRAY)
    ax_turn.set_ylabel('次', color=GRAY)
    ax_lev.set_ylabel('倍', color=GRAY)

    fig.text(0.99, 0.03, '数据来源：同花顺Excel、东方财富API；图表：Hermes',
             ha='right', va='bottom', fontsize=9, color=GRAY, fontproperties=FONT_PROP)
    apply_font(ax1, ax_npm, ax_turn, ax_lev)
    fig.subplots_adjust(left=0.07, right=0.985, top=0.90, bottom=0.10, hspace=0.22, wspace=0.18)
    out = CHARTS / f'{CODE}_4.1_ROE与杜邦三因子趋势图.png'
    fig.savefig(out, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return out


def chart_42():
    annual = load_annual_metrics().copy()
    annual = annual.loc[2020:2025].copy()
    annual['扣非同比%'] = annual['扣非净利润'].pct_change() * 100
    annual['扣非同比展示%'] = annual['扣非同比%']
    annual.loc[annual['扣非净利润'].shift(1) <= 0, '扣非同比展示%'] = np.nan
    years = annual.index.astype(int).tolist()
    x = np.arange(len(years))
    width = 0.28

    fig, ax1 = plt.subplots(figsize=(14.6, 7.9), dpi=180)
    fig.patch.set_facecolor('white')
    ax1.set_facecolor('white')

    bars_rev = ax1.bar(
        x - width / 2,
        annual['营收'],
        width=width,
        color='#DBEAFE',
        edgecolor=BLUE,
        linewidth=1.05,
        label='营收(亿元)',
        zorder=2,
    )
    bars_profit = ax1.bar(
        x + width / 2,
        annual['扣非净利润'],
        width=width,
        color='#FFEDD5',
        edgecolor=ORANGE,
        linewidth=1.05,
        label='扣非净利润(亿元)',
        zorder=2,
    )

    ax1.set_ylabel('金额（亿元）', color=GRAY)
    ax1.tick_params(axis='y', labelcolor=GRAY)
    ax1.tick_params(axis='x', length=0)
    ax1.set_xticks(x)
    ax1.set_xticklabels(years)
    ax1.set_ylim(min(-1.2, annual['扣非净利润'].min() * 1.8), annual['营收'].max() * 1.22)
    ax1.grid(axis='y', color='#E5E7EB', linewidth=0.8)
    ax1.grid(axis='x', visible=False)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    ax1.spines['left'].set_color('#D1D5DB')
    ax1.spines['bottom'].set_color('#D1D5DB')

    ax2 = ax1.twinx()
    l1, = ax2.plot(x, annual['毛利率'], color='#0F766E', marker='o', markersize=5.2, linewidth=2.2,
                   label='毛利率(%)', zorder=3)
    l2, = ax2.plot(x, annual['净利率'], color='#7C3AED', marker='o', markersize=5.0, linewidth=2.0,
                   label='净利率(%)', zorder=3)
    ax2.set_ylabel('利润率(%)', color=GRAY)
    ax2.tick_params(axis='y', labelcolor=GRAY)
    margin_min = min(annual['净利率'].min(), annual['毛利率'].min())
    margin_max = max(annual['净利率'].max(), annual['毛利率'].max())
    ax2.set_ylim(max(0, margin_min - 6), margin_max + 8)
    ax2.spines['top'].set_visible(False)
    ax2.spines['left'].set_visible(False)
    ax2.spines['right'].set_color('#D1D5DB')

    ax3 = ax1.twinx()
    ax3.spines['right'].set_position(('outward', 52))
    l3, = ax3.plot(x, annual['扣非同比展示%'], color='#DC2626', marker='D', markersize=4.8,
                   linewidth=1.9, linestyle='--', label='扣非同比(%)', zorder=3)
    ax3.set_ylabel('扣非同比(%)', color='#DC2626')
    ax3.tick_params(axis='y', labelcolor='#DC2626')
    valid_yoy = annual['扣非同比展示%'].dropna()
    ax3.set_ylim(0, max(120, valid_yoy.max() * 1.18))
    ax3.spines['top'].set_visible(False)
    ax3.spines['left'].set_visible(False)
    ax3.spines['right'].set_color('#FCA5A5')

    fig.suptitle(f'{NAME}：营收、扣非利润与利润率趋势图（2020-2025）', fontsize=16, y=0.975, fontproperties=FONT_PROP)
    fig.text(0.5, 0.93, '扣非利润增长既来自营收扩张，也来自毛利率和净利率修复；2024-2025 年同比增速明显放缓',
             ha='center', va='center', fontsize=11.2, color=GRAY, fontproperties=FONT_PROP)

    handles1, labels1 = ax1.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    handles3, labels3 = ax3.get_legend_handles_labels()
    ax1.legend(handles1 + handles2 + handles3, labels1 + labels2 + labels3,
               loc='upper center', bbox_to_anchor=(0.5, 1.00), ncol=5,
               frameon=False, prop=FONT_PROP, handlelength=2.0, columnspacing=1.4)

    for rect, val in zip(bars_rev, annual['营收']):
        ax1.text(rect.get_x() + rect.get_width()/2, rect.get_height() + 0.8, f'{val:.1f}',
                 ha='center', va='bottom', fontsize=8.1, color=BLUE, fontproperties=FONT_PROP)

    for rect, val in zip(bars_profit, annual['扣非净利润']):
        if val >= 0:
            y = rect.get_height() + 0.35
            va = 'bottom'
        else:
            y = rect.get_height() - 0.28
            va = 'top'
        ax1.text(rect.get_x() + rect.get_width()/2, y, f'{val:.2f}',
                 ha='center', va=va, fontsize=8.1, color=ORANGE, fontproperties=FONT_PROP)

    for i, val in enumerate(annual['毛利率']):
        dy = 1.5 if years[i] != 2022 else 2.8
        ax2.text(x[i], val + dy, f'{val:.1f}%', ha='center', va='bottom', fontsize=8.0,
                 color='#0F766E', fontproperties=FONT_PROP)

    for i, val in enumerate(annual['净利率']):
        if years[i] in {2022, 2023}:
            dy = -2.2
        elif years[i] == 2024:
            dy = -1.6
        else:
            dy = 1.4
        va = 'top' if dy < 0 else 'bottom'
        ax2.text(x[i], val + dy, f'{val:.1f}%', ha='center', va=va, fontsize=8.0,
                 color='#7C3AED', fontproperties=FONT_PROP)

    for i, val in enumerate(annual['扣非同比展示%']):
        if pd.isna(val):
            continue
        if years[i] == 2022:
            dy = 6.0
        elif years[i] == 2023:
            dy = -5.5
        elif years[i] == 2024:
            dy = 4.2
        else:
            dy = 3.8
        va = 'bottom' if dy > 0 else 'top'
        ax3.text(x[i], val + dy, f'{val:.1f}%', ha='center', va=va, fontsize=7.8,
                 color='#DC2626', fontproperties=FONT_PROP)

    ax3.text(x[1] + 0.15, 4.2, '2021同比受2020负基数影响，折线不展示',
             color='#991B1B', fontsize=7.8, ha='center', va='bottom', fontproperties=FONT_PROP)

    annotate_source(ax1)
    apply_font(ax1, ax2, ax3)
    fig.tight_layout(rect=[0, 0.03, 0.965, 0.91])
    out = CHARTS / f'{CODE}_4.2_扣非利润趋势与同比增速图.png'
    fig.savefig(out, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return out


def chart_43():
    df = load_cashflow().copy()
    years = df['年份'].astype(int).tolist()
    x = np.arange(len(years))
    width = 0.23

    fig = plt.figure(figsize=(14.0, 8.4), dpi=180)
    gs = fig.add_gridspec(2, 1, height_ratios=[3.4, 1.35], hspace=0.08)
    ax = fig.add_subplot(gs[0])
    ax_ratio = fig.add_subplot(gs[1], sharex=ax)
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')
    ax_ratio.set_facecolor('white')

    b1 = ax.bar(x - width, df['净利润'], width=width, color=LIGHT_BLUE, edgecolor=BLUE, linewidth=1.0, label='净利润', zorder=2)
    b2 = ax.bar(x, df['经营现金流'], width=width, color=LIGHT_GREEN, edgecolor=GREEN, linewidth=1.0, label='经营现金流', zorder=2)
    b3 = ax.bar(x + width, df['自由现金流'], width=width, color=LIGHT_ORANGE, edgecolor=ORANGE, linewidth=1.0, label='自由现金流', zorder=2)
    ax.set_xticks(x)
    ax.set_xticklabels(years)
    ax.set_ylabel('金额（亿元）', color=GRAY)
    ax.tick_params(axis='y', labelcolor=GRAY)
    ax.tick_params(axis='x', length=0, labelbottom=False)
    ax.grid(axis='y', color='#E5E7EB', linewidth=0.8)
    ax.grid(axis='x', visible=False)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#D1D5DB')
    ax.spines['bottom'].set_color('#D1D5DB')
    ax.set_ylim(0, max(df['经营现金流'].max(), df['自由现金流'].max()) * 1.18)

    fig.suptitle(f'{NAME}：现金兑现能力强，但 2025 年覆盖倍数略回落', fontsize=16, y=0.975, fontproperties=FONT_PROP)
    fig.text(0.5, 0.93, '上图看净利润、经营现金流、自由现金流绝对值；下图看现金流覆盖净利润的倍数',
             ha='center', va='center', fontsize=11.2, color=GRAY, fontproperties=FONT_PROP)

    handles1, labels1 = ax.get_legend_handles_labels()
    ax.legend(handles1, labels1, loc='upper left', ncol=3, frameon=False, prop=FONT_PROP)

    for bars, color in [(b1, BLUE), (b2, GREEN), (b3, ORANGE)]:
        for i, (rect, val) in enumerate(zip(bars, [r.get_height() for r in bars])):
            if years[i] != 2025:
                continue
            ax.text(rect.get_x() + rect.get_width()/2, val + 0.35, f'{val:.2f}',
                    ha='center', va='bottom', fontsize=8.6, color=color, fontproperties=FONT_PROP)

    df_ratio = df.copy()
    df_ratio.loc[df_ratio['年份'].isin([2020, 2021]), ['经营现金流/净利润', '自由现金流/净利润']] = np.nan
    l1, = ax_ratio.plot(x, df_ratio['经营现金流/净利润'], color=GREEN, marker='o', linewidth=2.0,
                        label='经营现金流/净利润', zorder=3)
    l2, = ax_ratio.plot(x, df_ratio['自由现金流/净利润'], color=ORANGE, marker='o', linewidth=2.0,
                        label='自由现金流/净利润', zorder=3)
    ax_ratio.set_ylabel('覆盖倍数(倍)', color=GRAY)
    ax_ratio.tick_params(axis='y', labelcolor=GRAY)
    ax_ratio.tick_params(axis='x', length=0)
    ax_ratio.set_xticks(x)
    ax_ratio.set_xticklabels(years)
    ax_ratio.grid(axis='y', color='#E5E7EB', linewidth=0.8)
    ax_ratio.grid(axis='x', visible=False)
    ax_ratio.spines['top'].set_visible(False)
    ax_ratio.spines['right'].set_visible(False)
    ax_ratio.spines['left'].set_color('#D1D5DB')
    ax_ratio.spines['bottom'].set_color('#D1D5DB')
    valid_ratio = df_ratio[['经营现金流/净利润', '自由现金流/净利润']].stack()
    ax_ratio.set_ylim(0, valid_ratio.max() * 1.18)
    ax_ratio.legend(loc='upper left', ncol=2, frameon=False, prop=FONT_PROP, bbox_to_anchor=(0.0, 0.98))

    for series, color in [('经营现金流/净利润', GREEN), ('自由现金流/净利润', ORANGE)]:
        for i, val in enumerate(df_ratio[series]):
            if pd.isna(val):
                continue
            dy = 0.10 if series == '经营现金流/净利润' else -0.12
            va = 'bottom' if dy > 0 else 'top'
            ax_ratio.text(x[i], val + dy, f'{val:.2f}x', ha='center', va=va,
                          fontsize=8.1, color=color, fontproperties=FONT_PROP)

    ax_ratio.text(x[1] - 0.15, ax_ratio.get_ylim()[1] * 0.84, '2020-2021 净利润基数过低，覆盖倍数失真，已弱化',
                  color=GRAY, fontsize=8.2, ha='left', va='center', fontproperties=FONT_PROP)

    annotate_source(ax_ratio)
    apply_font(ax, ax_ratio)
    fig.subplots_adjust(left=0.07, right=0.985, top=0.87, bottom=0.09, hspace=0.08)
    out = CHARTS / f'{CODE}_4.3_净利润经营现金流自由现金流对比图.png'
    fig.savefig(out, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return out


def chart_45():
    df = fetch_operating_quality().copy()
    annual = df[(df['date'].dt.month == 12) & (df['年份'].between(2020, 2025))].copy()
    q1 = df[df['date'] == pd.Timestamp('2026-03-31')].copy()
    x = np.arange(len(annual))
    width = 0.22

    fig = plt.figure(figsize=(14.0, 8.2), dpi=180)
    gs = fig.add_gridspec(2, 1, height_ratios=[3.2, 1.15], hspace=0.08)
    ax = fig.add_subplot(gs[0])
    ax_small = fig.add_subplot(gs[1], sharex=ax)
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')
    ax_small.set_facecolor('white')

    b1 = ax.bar(x - width, annual['应收账款'], width=width, color=LIGHT_BLUE, edgecolor=BLUE, linewidth=1.0, label='应收账款', zorder=2)
    b2 = ax.bar(x, annual['存货'], width=width, color=LIGHT_ORANGE, edgecolor=ORANGE, linewidth=1.0, label='存货', zorder=2)
    b3 = ax.bar(x + width, annual['合同负债'].fillna(0), width=width, color=LIGHT_GREEN, edgecolor=GREEN, linewidth=1.0, label='合同负债', zorder=2)
    ax.set_xticks(x)
    ax.set_xticklabels(annual['年份'])
    ax.set_ylabel('金额（亿元）', color=GRAY)
    ax.tick_params(axis='y', labelcolor=GRAY)
    ax.tick_params(axis='x', length=0, labelbottom=False)
    ax.grid(axis='y', color='#E5E7EB', linewidth=0.8)
    ax.grid(axis='x', visible=False)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#D1D5DB')
    ax.spines['bottom'].set_color('#D1D5DB')
    ax.set_ylim(0, annual[['应收账款', '存货', '合同负债']].fillna(0).max().max() * 1.18)

    fig.suptitle(f'{NAME}：2020-2025 存货持续去化，2026Q1 应收抬头需观察', fontsize=16, y=0.975, fontproperties=FONT_PROP)
    fig.text(0.5, 0.93, '上图看 2020-2025 年末应收、存货、合同负债；下图看同期资产负债率，右上角补充 2026Q1 最新观察',
             ha='center', va='center', fontsize=11.2, color=GRAY, fontproperties=FONT_PROP)

    handles1, labels1 = ax.get_legend_handles_labels()
    ax.legend(handles1, labels1, loc='upper left', ncol=3, frameon=False, prop=FONT_PROP)

    latest_idx = len(annual) - 1
    for bars, color in [(b1, BLUE), (b2, ORANGE), (b3, GREEN)]:
        rect = bars[latest_idx]
        val = rect.get_height()
        ax.text(rect.get_x() + rect.get_width()/2, val + 0.12, f'{val:.2f}',
                ha='center', va='bottom', fontsize=8.4, color=color, fontproperties=FONT_PROP)

    l1, = ax_small.plot(x, annual['资产负债率'], color=PURPLE, marker='o', linewidth=2.1, label='资产负债率(%)', zorder=3)
    ax_small.set_ylabel('资产负债率(%)', color=PURPLE)
    ax_small.tick_params(axis='y', labelcolor=PURPLE)
    ax_small.tick_params(axis='x', length=0)
    ax_small.set_xticks(x)
    ax_small.set_xticklabels(annual['年份'])
    ax_small.grid(axis='y', color='#E5E7EB', linewidth=0.8)
    ax_small.grid(axis='x', visible=False)
    ax_small.spines['top'].set_visible(False)
    ax_small.spines['right'].set_visible(False)
    ax_small.spines['left'].set_color('#D1D5DB')
    ax_small.spines['bottom'].set_color('#D1D5DB')
    ymin = annual['资产负债率'].min()
    ymax = annual['资产负债率'].max()
    margin = max((ymax - ymin) * 0.28, 0.6)
    ax_small.set_ylim(ymin - margin * 0.45, ymax + margin)
    ax_small.legend(loc='upper left', frameon=False, prop=FONT_PROP)

    for i, val in enumerate(annual['资产负债率']):
        dy = 0.12 if i != 5 else 0.18
        ax_small.text(x[i], val + dy, f'{val:.1f}%', ha='center', va='bottom', fontsize=8.2,
                      color=PURPLE, fontproperties=FONT_PROP)

    if not q1.empty:
        row = q1.iloc[0]
        note = (
            f"2026Q1：应收 {row['应收账款']:.2f} 亿，存货 {row['存货']:.2f} 亿，"
            f"合同负债 {row['合同负债']:.2f} 亿，资产负债率 {row['资产负债率']:.1f}%"
        )
        ax.text(0.985, 0.93, note, transform=ax.transAxes,
                ha='right', va='top', fontsize=8.4, color=GRAY,
                bbox=dict(boxstyle='round,pad=0.22', facecolor='white', edgecolor='#E5E7EB'),
                fontproperties=FONT_PROP)

    annotate_source(ax_small, '数据来源：东方财富API；图表：Hermes')
    apply_font(ax, ax_small)
    fig.subplots_adjust(left=0.07, right=0.985, top=0.87, bottom=0.09, hspace=0.08)
    out = CHARTS / f'{CODE}_4.5_应收存货合同负债变化图.png'
    fig.savefig(out, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return out


def chart_46():
    df = pd.DataFrame({
        '产品': ['阿胶及系列产品', '其他药品及保健品', '毛驴养殖及驴肉产品', '其他'],
        '收入': [61.98, 3.86, 0.58, 0.58],
        '同比': [11.80, 63.65, -15.53, -81.09],
    })
    total = df['收入'].sum()
    df['占比'] = df['收入'] / total * 100
    df['增长来源'] = df['收入'] * df['同比'] / 100

    main = df.sort_values('占比', ascending=True).copy()
    growth = df.sort_values('同比', ascending=True).copy()

    color_map = {
        '阿胶及系列产品': '#CBD5E1',
        '其他药品及保健品': LIGHT_ORANGE,
        '毛驴养殖及驴肉产品': '#F3F4F6',
        '其他': '#F3F4F6',
    }
    edge_map = {
        '阿胶及系列产品': '#94A3B8',
        '其他药品及保健品': ORANGE,
        '毛驴养殖及驴肉产品': '#D1D5DB',
        '其他': '#D1D5DB',
    }

    fig = plt.figure(figsize=(13.8, 8.2), dpi=180)
    gs = fig.add_gridspec(2, 1, height_ratios=[2.8, 1.3], hspace=0.1)
    ax = fig.add_subplot(gs[0])
    ax_small = fig.add_subplot(gs[1])
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')
    ax_small.set_facecolor('white')

    bars = ax.barh(
        main['产品'],
        main['占比'],
        color=[color_map[p] for p in main['产品']],
        edgecolor=[edge_map[p] for p in main['产品']],
        linewidth=1.2,
        zorder=2,
    )
    ax.set_xlim(0, 100)
    ax.set_xlabel('收入占比（%）', color=GRAY)
    ax.grid(axis='x', color='#E5E7EB', linewidth=0.8)
    ax.grid(axis='y', visible=False)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#D1D5DB')
    ax.spines['bottom'].set_color('#D1D5DB')

    fig.suptitle(f'{NAME}：阿胶主品占比 92.5%，第二曲线增速快但体量仍小', fontsize=16, y=0.975, fontproperties=FONT_PROP)
    fig.text(0.5, 0.93, '上图看 2025 年收入结构占比；下图看各产品同比增速，拆开看“谁贡献基本盘、谁贡献弹性”',
             ha='center', va='center', fontsize=11.2, color=GRAY, fontproperties=FONT_PROP)

    for bar, (_, row) in zip(bars, main.iterrows()):
        label = f"{row['收入']:.2f}亿｜{row['占比']:.1f}%"
        ax.text(bar.get_width() + 0.9, bar.get_y() + bar.get_height()/2, label,
                va='center', ha='left', fontsize=10.4, color=edge_map[row['产品']], fontproperties=FONT_PROP)

    ax.text(0.985, 0.08, '第二曲线：其他药品及保健品同比 +63.6%，但收入占比仅 5.8%',
            transform=ax.transAxes, ha='right', va='bottom', fontsize=8.8, color=GRAY,
            bbox=dict(boxstyle='round,pad=0.22', facecolor='white', edgecolor='#E5E7EB'),
            fontproperties=FONT_PROP)

    y = np.arange(len(growth))
    yoy_colors = [ORANGE if p == '其他药品及保健品' else (BLUE if p == '阿胶及系列产品' else '#9CA3AF') for p in growth['产品']]
    ax_small.axvline(0, color='#D1D5DB', linewidth=1.0)
    ax_small.hlines(y, 0, growth['同比'], color=yoy_colors, linewidth=2.6, zorder=2)
    ax_small.scatter(growth['同比'], y, s=52, color=yoy_colors, zorder=3)
    ax_small.set_yticks(y)
    ax_small.set_yticklabels(growth['产品'])
    ax_small.set_xlabel('同比增速（%）', color=GRAY)
    ax_small.grid(axis='x', color='#E5E7EB', linewidth=0.8)
    ax_small.grid(axis='y', visible=False)
    ax_small.spines['top'].set_visible(False)
    ax_small.spines['right'].set_visible(False)
    ax_small.spines['left'].set_color('#D1D5DB')
    ax_small.spines['bottom'].set_color('#D1D5DB')

    xmin = min(-90, growth['同比'].min() - 10)
    xmax = max(70, growth['同比'].max() + 12)
    ax_small.set_xlim(xmin, xmax)

    for yi, (_, row) in enumerate(growth.iterrows()):
        ha = 'left' if row['同比'] >= 0 else 'right'
        dx = 1.8 if row['同比'] >= 0 else -1.8
        ax_small.text(row['同比'] + dx, yi, f"{row['同比']:+.1f}%", va='center', ha=ha,
                      fontsize=9.3, color=edge_map[row['产品']] if row['产品'] in edge_map else GRAY,
                      fontproperties=FONT_PROP)

    annotate_source(ax_small, '数据来源：2025年年报分产品收入；图表：Hermes')
    apply_font(ax, ax_small)
    fig.subplots_adjust(left=0.16, right=0.96, top=0.88, bottom=0.1, hspace=0.1)
    out = CHARTS / f'{CODE}_4.6_2025年收入结构图.png'
    fig.savefig(out, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return out


def main():
    outputs = [chart_41(), chart_42(), chart_43(), chart_45(), chart_46()]
    for path in outputs:
        print(path)


if __name__ == '__main__':
    main()
