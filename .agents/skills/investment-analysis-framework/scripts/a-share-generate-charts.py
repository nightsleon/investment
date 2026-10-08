#!/usr/bin/env python3
"""
A-Share Stock Price vs Financial Metrics Chart Generator

Usage:
  Single metric:  python3 generate_charts.py --ticker 000333 --xls path/to/financial.xls --output-dir ./output
  Dual metric:    python3 generate_charts.py --ticker 000333 --xls path/to/financial.xls --dual-metric --output-dir ./output

Generates:
1. Dual Y-axis: stock price vs TTM profit
2. Normalized comparison chart
3. (With --dual-metric) Combined chart with both dakfei and net profit TTM
4. CSV with aligned data
"""

import argparse
import pandas as pd
import xlrd
import yfinance as yf
import matplotlib.pyplot as plt
from pathlib import Path


def setup_chinese_font():
    plt.rcParams['font.sans-serif'] = ['PingFang SC', 'Heiti SC', 'Arial Unicode MS', 'SimHei', 'Noto Sans CJK SC']
    plt.rcParams['axes.unicode_minus'] = False


def parse_financial_xls(xls_path, row_index=2):
    """Parse Chinese financial XLS. row_index: 2=net profit, 4=non-recurring profit"""
    book = xlrd.open_workbook(xls_path, ignore_workbook_corruption=True)
    sh = book.sheet_by_index(0)
    headers = sh.row_values(1)
    data = sh.row_values(row_index)
    rows = []
    for d, v in zip(headers[1:], data[1:]):
        if not d:
            continue
        if isinstance(v, str):
            v = v.strip()
            if v in ('--', ''):
                continue
            v = float(v.replace('%', ''))
        else:
            v = float(v)
        rows.append((pd.to_datetime(d), v))
    return pd.DataFrame(rows, columns=['date', 'value']).dropna().sort_values('date').reset_index(drop=True)


def fetch_price(ticker, start='2009-01-01', end='2026-12-31'):
    """Fetch A-share stock price via yfinance. Auto-detect SZ/SS suffix."""
    if '.' not in ticker:
        if ticker.startswith(('6', '9')):
            ticker = f"{ticker}.SS"
        else:
            ticker = f"{ticker}.SZ"
    raw = yf.download(ticker, start=start, end=end, auto_adjust=False, progress=False)
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    price = raw.reset_index()[['Date', 'Adj Close']].rename(
        columns={'Date': 'trade_date', 'Adj Close': 'adj_close'})
    price['trade_date'] = pd.to_datetime(price['trade_date'])
    return price.sort_values('trade_date')


def align_quarterly(fin_df, price_df, min_date='2013-01-01'):
    matched = []
    for _, row in fin_df.iterrows():
        q = row['date']
        sub = price_df[price_df['trade_date'] <= q]
        if sub.empty:
            continue
        last = sub.iloc[-1]
        matched.append((q, float(last['adj_close']), row['value'], pd.to_datetime(last['trade_date'])))
    merged = pd.DataFrame(matched, columns=['date', 'adj_close', 'metric', 'trade_date'])
    merged = merged[merged['trade_date'] >= pd.Timestamp(min_date)].sort_values('date').reset_index(drop=True)
    return merged


def compute_ttm(merged):
    merged['ttm'] = merged['metric'].rolling(window=4, min_periods=4).sum()
    return merged.dropna(subset=['ttm']).reset_index(drop=True)


def plot_dual_axis(merged, title, ylabel_profit, output_path, use_ttm=True):
    setup_chinese_font()
    fig, ax1 = plt.subplots(figsize=(18, 8), dpi=180)
    ax2 = ax1.twinx()
    profit_col = 'ttm' if use_ttm else 'metric'
    profit_yi = merged[profit_col] / 1e8
    ax1.plot(merged['date'], merged['adj_close'], color='#1f77b4', marker='o', linewidth=2.2, markersize=4, label='Stock Price')
    ax2.plot(merged['date'], profit_yi, color='#2ca02c', marker='s', linewidth=2.5, markersize=5, label=ylabel_profit)
    year_ticks = merged.groupby(merged['date'].dt.year)['date'].max().tolist()
    ax1.set_xticks(year_ticks)
    ax1.set_xticklabels([f"{d.year}" for d in year_ticks], rotation=0, ha='center')
    ax1.set_title(title, fontsize=16, pad=14)
    ax1.set_ylabel('Stock Price (CNY)', color='#1f77b4')
    ax2.set_ylabel(ylabel_profit, color='#2ca02c')
    ax1.grid(True, axis='y', linestyle='--', alpha=0.25)
    lines = ax1.get_lines() + ax2.get_lines()
    ax1.legend(lines, [l.get_label() for l in lines], loc='upper left', frameon=False, fontsize=11)
    plt.tight_layout()
    fig.savefig(output_path, bbox_inches='tight')
    plt.close(fig)


def plot_normalized(merged, title, label_profit, output_path, use_ttm=True):
    setup_chinese_font()
    profit_col = 'ttm' if use_ttm else 'metric'
    norm_close = merged['adj_close'] / merged['adj_close'].iloc[0]
    norm_profit = merged[profit_col] / merged[profit_col].iloc[0]
    fig, ax = plt.subplots(figsize=(18, 8), dpi=180)
    ax.plot(merged['date'], norm_close, color='#1f77b4', marker='o', linewidth=2.2, markersize=4, label='Price (normalized)')
    ax.plot(merged['date'], norm_profit, color='#d62728', marker='s', linewidth=2.5, markersize=5, label=f'{label_profit} (normalized)')
    ax.axhline(1, color='gray', linestyle='--', linewidth=0.8, alpha=0.5)
    year_ticks = merged.groupby(merged['date'].dt.year)['date'].max().tolist()
    ax.set_xticks(year_ticks)
    ax.set_xticklabels([f"{d.year}" for d in year_ticks], rotation=0, ha='center')
    ax.set_title(title, fontsize=16, pad=14)
    ax.set_ylabel('Normalized Index (base=1)')
    ax.legend(loc='upper left', frameon=False, fontsize=11)
    ax.grid(True, axis='y', linestyle='--', alpha=0.25)
    plt.tight_layout()
    fig.savefig(output_path, bbox_inches='tight')
    plt.close(fig)


def plot_dual_metric(merged_n, merged_d, title, output_path):
    setup_chinese_font()
    fig, ax1 = plt.subplots(figsize=(18, 9), dpi=180)
    ax2 = ax1.twinx()
    ax1.plot(merged_n['date'], merged_n['adj_close'], color='#1f77b4', marker='o', linewidth=2.2, markersize=4, label='Stock Price')
    ax2.plot(merged_d['date'], merged_d['ttm'] / 1e8, color='#d62728', marker='s', linewidth=2.5, markersize=5, label='Non-recurring Profit TTM')
    ax2.plot(merged_n['date'], merged_n['ttm'] / 1e8, color='#2ca02c', marker='^', linewidth=2.0, markersize=4, alpha=0.7, label='Net Profit TTM')
    ax2.fill_between(merged_d['date'], merged_d['ttm'] / 1e8, merged_n['ttm'] / 1e8, alpha=0.1, color='gray')
    year_ticks = merged_n.groupby(merged_n['date'].dt.year)['date'].max().tolist()
    ax1.set_xticks(year_ticks)
    ax1.set_xticklabels([f"{d.year}" for d in year_ticks], rotation=0, ha='center')
    ax1.set_title(title, fontsize=16, pad=14)
    ax1.set_ylabel('Stock Price (CNY)', color='#1f77b4')
    ax2.set_ylabel('Profit TTM (100M CNY)')
    ax1.grid(True, axis='y', linestyle='--', alpha=0.25)
    lines = ax1.get_lines() + ax2.get_lines()
    ax1.legend(lines, [l.get_label() for l in lines], loc='upper left', frameon=False, fontsize=11)
    plt.tight_layout()
    fig.savefig(output_path, bbox_inches='tight')
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description='A-Share Stock vs Financial Metrics Chart Generator')
    parser.add_argument('--ticker', required=True, help='Stock code, e.g. 000333')
    parser.add_argument('--xls', required=True, help='Path to financial statement XLS')
    parser.add_argument('--metric-row', type=int, default=2, help='Row index in XLS (2=net profit, 4=non-recurring)')
    parser.add_argument('--metric-name', default='Net Profit', help='Metric display name')
    parser.add_argument('--output-dir', default='.', help='Output directory')
    parser.add_argument('--min-date', default='2013-01-01', help='Minimum date for analysis')
    parser.add_argument('--dual-metric', action='store_true', help='Generate combined chart with both metrics')
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    prefix = args.ticker.replace('.', '_')

    print(f"Fetching {args.ticker} price data...")
    price = fetch_price(args.ticker)

    print(f"Parsing financial XLS (row {args.metric_row}: {args.metric_name})...")
    fin = parse_financial_xls(args.xls, row_index=args.metric_row)

    print("Aligning and computing TTM...")
    merged = align_quarterly(fin, price, min_date=args.min_date)
    merged = compute_ttm(merged)

    csv_path = out_dir / f"{prefix}_price_vs_{args.metric_name}_TTM.csv"
    merged.to_csv(csv_path, index=False, encoding='utf-8-sig')

    dual_path = out_dir / f"{prefix}_price_vs_{args.metric_name}_TTM.png"
    norm_path = out_dir / f"{prefix}_normalized_{args.metric_name}_TTM.png"
    plot_dual_axis(merged, f'{args.ticker}: Price vs {args.metric_name} TTM', f'{args.metric_name} TTM', dual_path)
    plot_normalized(merged, f'{args.ticker}: Normalized (Price vs {args.metric_name} TTM)', f'{args.metric_name} TTM', norm_path)

    corr = merged['adj_close'].corr(merged['ttm'])
    price_mult = merged['adj_close'].iloc[-1] / merged['adj_close'].iloc[0]
    ttm_mult = merged['ttm'].iloc[-1] / merged['ttm'].iloc[0]

    print(f"\n=== Results ===")
    print(f"CSV: {csv_path}")
    print(f"Dual chart: {dual_path}")
    print(f"Normalized chart: {norm_path}")
    print(f"Period: {merged['date'].iloc[0].strftime('%Y-%m')} to {merged['date'].iloc[-1].strftime('%Y-%m')}")
    print(f"Price: {merged['adj_close'].iloc[0]:.2f} to {merged['adj_close'].iloc[-1]:.2f} ({price_mult:.1f}x)")
    print(f"TTM {args.metric_name}: {merged['ttm'].iloc[0]/1e8:.1f} to {merged['ttm'].iloc[-1]/1e8:.1f} 100M ({ttm_mult:.1f}x)")
    print(f"Correlation: {corr:.4f}")
    print(f"R-squared: {corr**2:.4f}")

    if args.dual_metric:
        print("\nDual-metric mode: generating combined chart...")
        fin_n = parse_financial_xls(args.xls, row_index=2)
        fin_d = parse_financial_xls(args.xls, row_index=4)
        merged_n = compute_ttm(align_quarterly(fin_n, price, min_date=args.min_date))
        merged_d = compute_ttm(align_quarterly(fin_d, price, min_date=args.min_date))
        combined_path = out_dir / f"{prefix}_price_vs_dual_TTM.png"
        plot_dual_metric(merged_n, merged_d, f'{args.ticker}: Price vs Non-recurring/Net Profit TTM', combined_path)
        corr_d = merged_d['adj_close'].corr(merged_d['ttm'])
        print(f"Combined chart: {combined_path}")
        print(f"Correlation (non-recurring): {corr_d:.4f}  R-squared: {corr_d**2:.4f}")


if __name__ == '__main__':
    main()
