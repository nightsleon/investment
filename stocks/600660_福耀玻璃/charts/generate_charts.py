#!/usr/bin/env python3
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import yfinance as yf
from python_calamine import CalamineWorkbook

CODE = '600660'
MARKET = 'SH'
NAME = '福耀玻璃'
BASE = Path('/Users/pidan-l/Documents/AI投资/investment/600660_福耀玻璃')
DATA_DIR = BASE / 'data'
OUT_DIR = BASE / 'charts'


def read_simple_xls(path: Path) -> pd.DataFrame:
    rows = CalamineWorkbook.from_path(str(path)).get_sheet_by_index(0).to_python()
    header = rows[0][1:]
    frame = pd.DataFrame({'date': header})
    for row in rows[1:]:
        frame[row[0]] = row[1:]
    frame['date'] = pd.to_datetime(frame['date'])
    frame = frame.sort_values('date').reset_index(drop=True)
    numeric_cols = [c for c in frame.columns if c != 'date']
    for col in numeric_cols:
        frame[col] = pd.to_numeric(frame[col], errors='coerce')
    frame['quarter'] = frame['date'].dt.year.astype(str) + 'Q' + frame['date'].dt.quarter.astype(str)
    frame['net_profit_yi'] = frame['净利润(元)'] / 1e8
    frame['non_gaap_yi'] = frame['扣非净利润(元)'] / 1e8
    frame['revenue_yi'] = frame['营业总收入(元)'] / 1e8
    frame['non_gaap_ttm_yi'] = frame['non_gaap_yi'].rolling(4, min_periods=4).sum()
    frame['net_profit_ttm_yi'] = frame['net_profit_yi'].rolling(4, min_periods=4).sum()
    return frame


def fetch_price() -> pd.DataFrame:
    raw = yf.download('600660.SS', start='2015-01-01', end='2026-06-07', auto_adjust=False, progress=False)
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    price = raw.reset_index()[['Date', 'Adj Close', 'Close']].rename(columns={'Date': 'trade_date', 'Adj Close': 'adj_close', 'Close': 'close'})
    price['trade_date'] = pd.to_datetime(price['trade_date']).dt.tz_localize(None)
    return price


def align_quarter_price(fin: pd.DataFrame, price: pd.DataFrame) -> pd.DataFrame:
    matched = []
    for _, row in fin.dropna(subset=['non_gaap_ttm_yi']).iterrows():
        qdate = row['date']
        sub = price[price['trade_date'] <= qdate]
        if sub.empty:
            continue
        last = sub.iloc[-1]
        matched.append({
            'date': qdate,
            'quarter': row['quarter'],
            'trade_date': last['trade_date'],
            'adj_close': float(last['adj_close']),
            'close': float(last['close']),
            'net_profit_yi': float(row['net_profit_yi']),
            'non_gaap_yi': float(row['non_gaap_yi']),
            'revenue_yi': float(row['revenue_yi']),
            'non_gaap_ttm_yi': float(row['non_gaap_ttm_yi']),
            'net_profit_ttm_yi': float(row['net_profit_ttm_yi']),
        })
    return pd.DataFrame(matched)


def setup_matplotlib():
    plt.rcParams['font.sans-serif'] = ['PingFang SC', 'Heiti SC', 'Arial Unicode MS', 'SimHei']
    plt.rcParams['axes.unicode_minus'] = False


def save_normalized_chart(df: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(16, 8), dpi=160)
    x = np.arange(len(df))
    norm_price = df['adj_close'] / df['adj_close'].iloc[0]
    norm_profit = df['non_gaap_ttm_yi'] / df['non_gaap_ttm_yi'].iloc[0]
    ax.plot(x, norm_price, 'o-', color='#1E88E5', linewidth=2.5, markersize=5, label='归一化股价(前复权)')
    ax.plot(x, norm_profit, 's-', color='#E53935', linewidth=2.5, markersize=5, label='归一化扣非TTM利润')
    ax.fill_between(x, norm_price, norm_profit, alpha=0.08, color='gray')
    ax.set_title(f'{NAME}({CODE}) 归一化对比：股价 vs 扣非TTM利润', fontsize=15, fontweight='bold')
    ax.set_ylabel('归一化值（基期=1）')
    ax.set_xticks(x[::max(1, len(x)//12)])
    ax.set_xticklabels(df['quarter'].iloc[::max(1, len(x)//12)], rotation=45, ha='right')
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3)
    corr = df['adj_close'].corr(df['non_gaap_ttm_yi'])
    price_mult = df['adj_close'].iloc[-1] / df['adj_close'].iloc[0]
    profit_mult = df['non_gaap_ttm_yi'].iloc[-1] / df['non_gaap_ttm_yi'].iloc[0]
    ax.text(0.02, 0.96, f'相关系数: {corr:.3f}\n股价涨幅: {price_mult:.1f}x\n利润涨幅: {profit_mult:.1f}x', transform=ax.transAxes, va='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    plt.tight_layout()
    fig.savefig(OUT_DIR / f'{CODE}_归一化_股价vs扣非TTM.png', bbox_inches='tight')
    plt.close(fig)


def save_dual_axis_ttm_chart(df: pd.DataFrame):
    fig, ax1 = plt.subplots(figsize=(18, 9), dpi=160)
    ax2 = ax1.twinx()
    x = np.arange(len(df))
    tick_step = max(1, len(df) // 12)
    l1, = ax1.plot(x, df['adj_close'], 'o-', color='#1E88E5', linewidth=2.5, markersize=5, label='股价(前复权)')
    l2, = ax2.plot(x, df['non_gaap_ttm_yi'], 's-', color='#E53935', linewidth=2.5, markersize=5, label='扣非TTM利润(亿)')
    ax2.fill_between(x, df['non_gaap_ttm_yi'], color='#E53935', alpha=0.08)
    ax1.set_title(f'{NAME}({CODE}) 股价 vs 扣非净利润TTM', fontsize=15, fontweight='bold')
    ax1.set_ylabel('股价（元）', color='#1E88E5', fontsize=12, fontweight='bold')
    ax2.set_ylabel('扣非TTM净利润（亿元）', color='#E53935', fontsize=12, fontweight='bold')
    ax1.tick_params(axis='y', labelcolor='#1E88E5')
    ax2.tick_params(axis='y', labelcolor='#E53935')
    ax1.set_xticks(x[::tick_step])
    ax1.set_xticklabels(df['quarter'].iloc[::tick_step], rotation=45, ha='right')
    ax1.grid(True, alpha=0.3)
    ax1.legend([l1, l2], [l1.get_label(), l2.get_label()], loc='upper left')
    plt.tight_layout()
    fig.savefig(OUT_DIR / f'{CODE}_股价vs扣非净利润TTM_双Y轴.png', bbox_inches='tight')
    plt.close(fig)


def save_dual_axis_quarter_chart(df: pd.DataFrame):
    fig, ax1 = plt.subplots(figsize=(18, 9), dpi=160)
    ax2 = ax1.twinx()
    x = np.arange(len(df))
    tick_step = max(1, len(df) // 12)
    l1, = ax1.plot(x, df['adj_close'], 'o-', color='#1E88E5', linewidth=2.5, markersize=5, label='股价(前复权)')
    l2, = ax2.plot(x, df['non_gaap_yi'], '^-', color='#FF9800', linewidth=2.5, markersize=6, label='单季度扣非利润(亿)')
    ax2.fill_between(x, df['non_gaap_yi'], color='#FF9800', alpha=0.08)
    ax1.set_title(f'{NAME}({CODE}) 股价 vs 单季度扣非净利润', fontsize=15, fontweight='bold')
    ax1.set_ylabel('股价（元）', color='#1E88E5', fontsize=12, fontweight='bold')
    ax2.set_ylabel('单季度扣非净利润（亿元）', color='#FF9800', fontsize=12, fontweight='bold')
    ax1.tick_params(axis='y', labelcolor='#1E88E5')
    ax2.tick_params(axis='y', labelcolor='#FF9800')
    ax1.set_xticks(x[::tick_step])
    ax1.set_xticklabels(df['quarter'].iloc[::tick_step], rotation=45, ha='right')
    ax1.grid(True, alpha=0.3)
    ax1.legend([l1, l2], [l1.get_label(), l2.get_label()], loc='upper left')
    plt.tight_layout()
    fig.savefig(OUT_DIR / f'{CODE}_股价vs扣非净利润_单季度.png', bbox_inches='tight')
    plt.close(fig)


def main():
    setup_matplotlib()
    fin = read_simple_xls(DATA_DIR / f'{CODE}_main_simple.xls')
    price = fetch_price()
    merged = align_quarter_price(fin, price)
    merged.to_csv(OUT_DIR / f'{CODE}_季度数据.csv', index=False, encoding='utf-8-sig')
    save_normalized_chart(merged)
    save_dual_axis_ttm_chart(merged)
    save_dual_axis_quarter_chart(merged)
    print(str(OUT_DIR / f'{CODE}_归一化_股价vs扣非TTM.png'))
    print(str(OUT_DIR / f'{CODE}_股价vs扣非净利润TTM_双Y轴.png'))
    print(str(OUT_DIR / f'{CODE}_股价vs扣非净利润_单季度.png'))
    print(str(OUT_DIR / f'{CODE}_季度数据.csv'))


if __name__ == '__main__':
    main()
