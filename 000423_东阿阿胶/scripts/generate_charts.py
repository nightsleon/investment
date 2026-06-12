#!/usr/bin/env python3
from pathlib import Path
from python_calamine import CalamineWorkbook
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import yfinance as yf

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / 'data' / '000423_main_simple.xls'
CHARTS = BASE / 'charts'
CHARTS.mkdir(exist_ok=True)
CODE='000423'
YF_CODE='000423.SZ'
NAME='东阿阿胶'

def read_simple():
    rows = CalamineWorkbook.from_path(str(DATA)).get_sheet_by_index(0).to_python()
    dates = pd.to_datetime(rows[0][1:])
    def row(name):
        for r in rows:
            if r[0] == name:
                return r[1:]
        raise KeyError(name)
    df = pd.DataFrame({
        'date': dates,
        'net_profit_yuan': row('净利润(元)'),
        'non_gaap_yuan': row('扣非净利润(元)'),
        'revenue_yuan': row('营业总收入(元)'),
        'eps': row('基本每股收益(元)'),
    }).sort_values('date')
    for c in ['net_profit_yuan','non_gaap_yuan','revenue_yuan','eps']:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    df['net_profit_yi'] = df['net_profit_yuan']/1e8
    df['non_gaap_yi'] = df['non_gaap_yuan']/1e8
    df['revenue_yi'] = df['revenue_yuan']/1e8
    df['net_profit_ttm_yi'] = df['net_profit_yi'].rolling(4, min_periods=4).sum()
    df['non_gaap_ttm_yi'] = df['non_gaap_yi'].rolling(4, min_periods=4).sum()
    df['eps_ttm'] = df['eps'].rolling(4, min_periods=4).sum()
    return df.dropna(subset=['non_gaap_ttm_yi']).reset_index(drop=True)

def get_price(start='2010-01-01'):
    raw = yf.download(YF_CODE, start=start, auto_adjust=False, progress=False)
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    px = raw.reset_index()[['Date','Adj Close','Close']].rename(columns={'Date':'trade_date','Adj Close':'adj_close','Close':'close'})
    px['trade_date'] = pd.to_datetime(px['trade_date']).dt.tz_localize(None)
    return px.dropna()

def match_price(fin, px):
    out=[]
    for _, r in fin.iterrows():
        sub = px[px['trade_date'] <= r['date']]
        if sub.empty: continue
        p = sub.iloc[-1]
        rec = r.to_dict(); rec.update({'trade_date':p['trade_date'], 'adj_close':p['adj_close'], 'close':p['close']})
        out.append(rec)
    return pd.DataFrame(out)

def setup_font():
    plt.rcParams['font.sans-serif'] = ['PingFang SC','Heiti SC','Arial Unicode MS','SimHei','DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False

def save_norm(df):
    fig, ax = plt.subplots(figsize=(15,7), dpi=160)
    d = df.copy()
    d['price_norm'] = d['adj_close']/d['adj_close'].iloc[0]
    d['ttm_norm'] = d['non_gaap_ttm_yi']/d['non_gaap_ttm_yi'].iloc[0]
    ax.plot(d['date'], d['price_norm'], 'o-', lw=2.4, color='#1976D2', label='股价(前复权) 归一化')
    ax.plot(d['date'], d['ttm_norm'], 's-', lw=2.4, color='#E64A19', label='扣非TTM利润 归一化')
    ax.set_title(f'{NAME}：股价 vs 扣非TTM利润（归一化，仅看趋势同步性）', fontsize=16)
    ax.grid(alpha=.25); ax.legend(); fig.autofmt_xdate(); fig.tight_layout()
    fig.savefig(CHARTS/f'{CODE}_归一化_股价vs扣非TTM.png'); plt.close(fig)

def save_ttm(df):
    fig, ax1 = plt.subplots(figsize=(16,8), dpi=160)
    ax2 = ax1.twinx()
    l1, = ax1.plot(df['date'], df['adj_close'], 'o-', lw=2.4, color='#1976D2', label='股价(前复权，元)')
    l2, = ax2.plot(df['date'], df['non_gaap_ttm_yi'], 's-', lw=2.4, color='#E64A19', label='扣非净利润TTM(亿元)')
    ax2.fill_between(df['date'], df['non_gaap_ttm_yi'], alpha=.08, color='#E64A19')
    ax1.set_ylabel('股价(元)'); ax2.set_ylabel('扣非TTM(亿元)')
    ax1.set_title(f'{NAME}：股价 vs 扣非净利润TTM（双Y轴主图）', fontsize=16)
    ax1.grid(alpha=.25); ax1.legend(handles=[l1,l2], loc='upper left'); fig.autofmt_xdate(); fig.tight_layout()
    fig.savefig(CHARTS/f'{CODE}_股价vs扣非净利润TTM_双Y轴.png'); plt.close(fig)

def save_quarter(df):
    fig, ax1 = plt.subplots(figsize=(16,8), dpi=160)
    ax2 = ax1.twinx()
    l1, = ax1.plot(df['date'], df['adj_close'], 'o-', lw=2.2, color='#1976D2', label='股价(前复权，元)')
    l2, = ax2.plot(df['date'], df['non_gaap_yi'], 's-', lw=2.2, color='#388E3C', label='单季度扣非净利润(亿元)')
    ax2.fill_between(df['date'], df['non_gaap_yi'], alpha=.08, color='#388E3C')
    ax1.set_ylabel('股价(元)'); ax2.set_ylabel('单季扣非(亿元)')
    ax1.set_title(f'{NAME}：股价 vs 单季度扣非净利润（季节性辅助图）', fontsize=16)
    ax1.grid(alpha=.25); ax1.legend(handles=[l1,l2], loc='upper left'); fig.autofmt_xdate(); fig.tight_layout()
    fig.savefig(CHARTS/f'{CODE}_股价vs扣非净利润_单季度.png'); plt.close(fig)

if __name__ == '__main__':
    setup_font()
    fin = read_simple()
    px = get_price(str(fin['date'].min().date()))
    merged = match_price(fin, px)
    merged.to_csv(CHARTS/f'{CODE}_季度数据.csv', index=False, encoding='utf-8-sig')
    save_norm(merged); save_ttm(merged); save_quarter(merged)
    print(merged[['date','trade_date','adj_close','close','non_gaap_yi','non_gaap_ttm_yi']].tail(8).to_string(index=False))
    print('saved to', CHARTS)
