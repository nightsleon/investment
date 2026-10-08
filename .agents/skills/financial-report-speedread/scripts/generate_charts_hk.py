#!/usr/bin/env python3
"""港股半年度股价 vs 利润TTM 对比图生成器（通用固化脚本）

用法:
    python generate_charts_hk.py 09633 农夫山泉
    python generate_charts_hk.py 09992 泡泡玛特
    python generate_charts_hk.py 09633 农夫山泉 --latest-h1 88.87 --latest-price 39.38 --out-dir ./charts

特性:
    1. 自动从东方财富 F10 接口获取所有历史年报(FY)与中报(H1)股东应占溢利
    2. 支持通过 --latest-h1 或 --latest-fy 补充未入库的最新报告期净利润
    3. 自动从 yfinance 获取日频股价，支持 --latest-price 锁定最新实测价（对齐 G4 门禁）
    4. 规范计算 TTM 利润：年末TTM=FY，年中TTM=上年FY+本年H1-上年H1
    5. 输出标准白底无遮挡的归一化图、双Y轴图及对齐数据 CSV
"""

import sys
import os
import argparse
import json
import urllib.request
import urllib.parse
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import yfinance as yf


def setup_chinese_font():
    font_candidates = [
        '/System/Library/Fonts/PingFang.ttc',
        '/System/Library/Fonts/Hiragino Sans GB.ttc',
        '/System/Library/Fonts/STHeiti Medium.ttc',
        '/System/Library/Fonts/Supplemental/Songti.ttc',
    ]
    font_prop = None
    for fp in font_candidates:
        if os.path.exists(fp):
            try:
                font_prop = fm.FontProperties(fname=fp, size=12)
                fm.FontProperties(fname=fp, size=15, weight='bold')
                return fp
            except Exception:
                continue
    plt.rcParams['font.sans-serif'] = ['PingFang SC', 'Hiragino Sans GB', 'Heiti SC', 'Arial Unicode MS', 'SimHei']
    plt.rcParams['axes.unicode_minus'] = False
    return None


def fetch_hk_financials(clean_code: str):
    """从东财 F10 获取所有历史 H1 与 FY 股东应占溢利"""
    # 1. 报告期列表
    summary_url = (
        "https://datacenter.eastmoney.com/securities/api/data/v1/get?"
        "reportName=RPT_CUSTOM_HKSK_APPFN_CASHFLOW_SUMMARY"
        "&columns=SECUCODE,SECURITY_NAME_ABBR,REPORT_DATE,REPORT_TYPE"
        f'&filter=(SECUCODE=%22{clean_code}.HK%22)&source=F10&client=PC'
    )
    req = urllib.request.Request(summary_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=12) as resp:
        sdata = json.loads(resp.read())

    if not sdata.get('result') or not sdata['result'].get('data'):
        raise ValueError(f"未查询到股票代码 {clean_code}.HK 的财务报告列表")

    report_list = sdata['result']['data'][0].get('REPORT_LIST', [])
    if not report_list:
        raise ValueError(f"股票代码 {clean_code}.HK 报告列表为空")

    stock_name_abbr = report_list[0].get('SECURITY_NAME_ABBR', clean_code)
    valid_dates = [
        r['REPORT_DATE'][:10]
        for r in report_list
        if r.get('REPORT_TYPE') in ['年报', '中报']
    ]

    # 2. 批量查询利润表
    dates_str = "','".join(valid_dates)
    filter_str = f'(SECUCODE="{clean_code}.HK")(REPORT_DATE in (\'{dates_str}\'))'
    inc_url = (
        "https://datacenter.eastmoney.com/securities/api/data/v1/get?"
        "reportName=RPT_HKF10_FN_INCOME_PC"
        "&columns=SECUCODE,REPORT_DATE,STD_ITEM_NAME,AMOUNT"
        f"&filter={urllib.parse.quote(filter_str)}&pageSize=500&source=F10&client=PC"
    )

    req2 = urllib.request.Request(inc_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req2, timeout=12) as resp:
        idata = json.loads(resp.read())

    profit_map = {}
    if idata.get('result') and idata['result'].get('data'):
        for row in idata['result']['data']:
            item_name = row.get('STD_ITEM_NAME', '')
            if item_name in ['股东应占溢利', '母公司拥有人应占溢利', '除税后溢利']:
                dt = row.get('REPORT_DATE', '')[:10]
                amount = row.get('AMOUNT')
                if dt and dt not in profit_map and amount is not None:
                    profit_map[dt] = float(amount) / 1e8  # 换算为亿元

    records = []
    for dt in sorted(profit_map.keys()):
        t = 'FY' if dt.endswith('12-31') else 'H1'
        records.append((dt, profit_map[dt], t))

    return stock_name_abbr, records


def compute_ttm(records):
    """计算半年度 TTM 净利润"""
    df = pd.DataFrame(records, columns=['date', 'net_profit', 'type'])
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').drop_duplicates('date').reset_index(drop=True)

    ttm_list = []
    for i in range(len(df)):
        row = df.iloc[i]
        if row['type'] == 'FY':
            ttm_list.append(row['net_profit'])
        elif row['type'] == 'H1':
            prev_year = row['date'].year - 1
            prev_fy = df[(df['date'].dt.year == prev_year) & (df['type'] == 'FY')]
            prev_h1 = df[(df['date'].dt.year == prev_year) & (df['type'] == 'H1')]
            if not prev_fy.empty and not prev_h1.empty:
                ttm_list.append(prev_fy.iloc[0]['net_profit'] + row['net_profit'] - prev_h1.iloc[0]['net_profit'])
            else:
                ttm_list.append(None)

    df['ttm'] = ttm_list
    return df.dropna(subset=['ttm']).reset_index(drop=True)


def fetch_price_data(clean_code: str, start_date='2018-01-01'):
    """获取港股日频股价 (yfinance)"""
    yf_symbol = f"{int(clean_code):04d}.HK"
    raw = yf.download(yf_symbol, start=start_date, auto_adjust=False, progress=False)
    if hasattr(raw.columns, 'levels'):
        raw.columns = raw.columns.get_level_values(0)
    price = raw.reset_index()[['Date', 'Adj Close', 'Close']].rename(
        columns={'Date': 'trade_date', 'Adj Close': 'adj_close', 'Close': 'close'}
    )
    price['trade_date'] = pd.to_datetime(price['trade_date']).dt.tz_localize(None)
    return price


def main():
    parser = argparse.ArgumentParser(description="港股股价 vs 利润TTM 图表生成器")
    parser.add_argument("code", help="港股代码，如 09633 或 9633")
    parser.add_argument("name", nargs="?", default=None, help="公司简称，如 农夫山泉")
    parser.add_argument("--latest-h1", type=float, default=None, help="最新未入库中报净利(亿元)，如 88.87")
    parser.add_argument("--latest-h1-date", default=None, help="最新中报日期，默认当年06-30，如 2026-06-30")
    parser.add_argument("--latest-fy", type=float, default=None, help="最新未入库年报净利(亿元)")
    parser.add_argument("--latest-fy-date", default=None, help="最新年报日期，默认上年12-31")
    parser.add_argument("--latest-price", type=float, default=None, help="手动指定最新实测股价(港币)，对齐G4门禁")
    parser.add_argument("--latest-date", default=None, help="手动指定最新股价日期，格式 YYYY-MM-DD")
    parser.add_argument("--out-dir", default="./charts", help="图表输出目录，默认为 ./charts")
    parser.add_argument("--base-date", default="2020-01-01", help="归一化基准最早起始年份，默认2020")
    args = parser.parse_args()

    clean_code = f"{int(args.code):05d}"
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== 开始生成港股 [{clean_code}] 股价与利润趋势图表 ===")
    
    # 1. 抓取财务数据
    fetched_name, records = fetch_hk_financials(clean_code)
    stock_name = args.name or fetched_name
    print(f"公司: {stock_name} ({clean_code}.HK)")
    print(f"已获取官方历史财报点数: {len(records)}")

    # 2. 追加未入库数据
    curr_year = datetime.now().year
    if args.latest_fy is not None:
        fy_date = args.latest_fy_date or f"{curr_year-1}-12-31"
        records.append((fy_date, args.latest_fy, 'FY'))
        print(f"追加年报数据: {fy_date} 净利={args.latest_fy}亿")

    if args.latest_h1 is not None:
        h1_date = args.latest_h1_date or f"{curr_year}-06-30"
        records.append((h1_date, args.latest_h1, 'H1'))
        print(f"追加中报数据: {h1_date} 净利={args.latest_h1}亿")

    # 3. 计算TTM
    profit_df = compute_ttm(records)
    print(f"成功计算 TTM 序列共 {len(profit_df)} 个节点，最新 TTM 为: {profit_df['ttm'].iloc[-1]:.2f} 亿元")

    # 4. 获取股价
    price_df = fetch_price_data(clean_code)
    
    # 若指定最新价格，追加/更新至 price_df
    if args.latest_price is not None:
        today_str = args.latest_date or datetime.now().strftime('%Y-%m-%d')
        today_dt = pd.to_datetime(today_str)
        if price_df['trade_date'].iloc[-1] < today_dt:
            new_row = pd.DataFrame([{'trade_date': today_dt, 'adj_close': args.latest_price, 'close': args.latest_price}])
            price_df = pd.concat([price_df, new_row], ignore_index=True)
        else:
            price_df.loc[price_df.index[-1], 'adj_close'] = args.latest_price
            price_df.loc[price_df.index[-1], 'close'] = args.latest_price

    # 5. 对齐利润与股价
    merged = []
    for _, row in profit_df.iterrows():
        report_date = row['date']
        sub = price_df[price_df['trade_date'] <= report_date]
        if sub.empty:
            continue
        last = sub.iloc[-1]
        merged.append({
            'date': report_date,
            'label': row['date'].strftime('%Y-%m'),
            'type': row['type'],
            'close': last['close'],
            'adj_close': last['adj_close'],
            'net_profit': row['net_profit'],
            'ttm': row['ttm'],
        })

    # 末点对齐当前实测价格（满足 G4 硬门禁）
    latest_p = price_df.iloc[-1]
    last_dt_str = latest_p['trade_date'].strftime('%Y-%m')
    if merged and merged[-1]['date'] < latest_p['trade_date']:
        merged.append({
            'date': latest_p['trade_date'],
            'label': f"{last_dt_str}\n(现价)",
            'type': 'Latest',
            'close': latest_p['close'],
            'adj_close': latest_p['adj_close'],
            'net_profit': profit_df['net_profit'].iloc[-1],
            'ttm': profit_df['ttm'].iloc[-1],
        })

    merged_df = pd.DataFrame(merged)
    csv_path = out_dir / f"{clean_code}_半年度股价与利润对齐.csv"
    merged_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"数据已保存: {csv_path}")

    # 统计计算
    base_idx = 0
    corr = merged_df['adj_close'].corr(merged_df['ttm'])
    price_mult = merged_df['adj_close'].iloc[-1] / merged_df['adj_close'].iloc[base_idx]
    ttm_mult = merged_df['ttm'].iloc[-1] / merged_df['ttm'].iloc[base_idx]

    font_path = setup_chinese_font()
    font_prop = fm.FontProperties(fname=font_path, size=12) if font_path else fm.FontProperties(size=12)
    font_title = fm.FontProperties(fname=font_path, size=15, weight='bold') if font_path else fm.FontProperties(size=15)
    font_small = fm.FontProperties(fname=font_path, size=10) if font_path else fm.FontProperties(size=10)
    font_info = fm.FontProperties(fname=font_path, size=11) if font_path else fm.FontProperties(size=11)

    # 6. 图1：归一化图
    fig, ax = plt.subplots(figsize=(15, 8), dpi=180, facecolor='white')
    ax.set_facecolor('white')
    base_close = merged_df['adj_close'].iloc[base_idx]
    base_ttm = merged_df['ttm'].iloc[base_idx]
    norm_close = merged_df['adj_close'] / base_close
    norm_ttm = merged_df['ttm'] / base_ttm

    x = range(len(merged_df))
    base_label = merged_df['label'].iloc[base_idx].replace('\n', ' ')
    ax.plot(x, norm_close, 'o-', color='#1E88E5', linewidth=2.5, markersize=7, 
            label=f'股价前复权（基期 {base_label} = 1.0）')
    ax.plot(x, norm_ttm, 's-', color='#E53935', linewidth=2.5, markersize=7, 
            label=f'归母净利润TTM（基期 {base_label} = 1.0）')
    ax.fill_between(x, norm_close, norm_ttm, alpha=0.08, color='#E53935')

    last_x = len(merged_df) - 1
    last_price_val = merged_df['adj_close'].iloc[-1]
    last_ttm_val = merged_df['ttm'].iloc[-1]

    ax.annotate(f"现价 {last_price_val:.2f} HKD\n({price_mult:.2f}x)", 
                xy=(last_x, norm_close.iloc[-1]), 
                xytext=(-45, -35), textcoords='offset points',
                color='#1E88E5', fontproperties=font_small,
                arrowprops=dict(arrowstyle='->', color='#1E88E5'))
    ax.annotate(f"TTM {last_ttm_val:.2f} 亿\n({ttm_mult:.2f}x)", 
                xy=(last_x, norm_ttm.iloc[-1]), 
                xytext=(-50, 20), textcoords='offset points',
                color='#E53935', fontproperties=font_small,
                arrowprops=dict(arrowstyle='->', color='#E53935'))

    info_text = (
        f"相关系数: {corr:.3f}\n"
        f"股价变动: {price_mult:.2f}x ({(price_mult-1)*100:+.1f}%)\n"
        f"利润变动: {ttm_mult:.2f}x ({(ttm_mult-1)*100:+.1f}%)\n"
        f"末点股价: {last_price_val:.2f} HKD"
    )
    ax.text(0.03, 0.82, info_text, transform=ax.transAxes, fontsize=11, va='top',
            bbox=dict(boxstyle='round,pad=0.6', facecolor='#F8FAFC', edgecolor='#CBD5E1', alpha=0.9),
            fontproperties=font_info)

    ax.set_title(f'{stock_name}（{clean_code}.HK）股价 vs 归母净利润TTM 归一化走势对比', 
                 fontsize=16, fontweight='bold', fontproperties=font_title, pad=15)
    ax.set_ylabel(f'归一化数值（{base_label} = 1.0）', fontsize=12, fontproperties=font_prop)
    ax.legend(fontsize=11, loc='upper left', frameon=True, facecolor='white', framealpha=0.9, prop=font_prop)
    ax.set_xticks(x)
    ax.set_xticklabels(merged_df['label'], rotation=30, ha='right', fontsize=10, fontproperties=font_small)
    ax.grid(True, linestyle='--', alpha=0.3, color='#94A3B8')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()

    norm_chart_path = out_dir / f"{clean_code}_归一化_股价vs利润TTM.png"
    plt.savefig(norm_chart_path, bbox_inches='tight', dpi=180, facecolor='white')
    plt.close()
    print(f"归一化图已生成: {norm_chart_path}")

    # 7. 图2：双Y轴图
    fig, ax1 = plt.subplots(figsize=(16, 8), dpi=180, facecolor='white')
    ax2 = ax1.twinx()
    ax1.set_facecolor('white')

    l1, = ax1.plot(x, merged_df['adj_close'], 'o-', color='#1E88E5', linewidth=2.5, markersize=7, 
                   label='股价（前复权，港币 HKD）')
    l2, = ax2.plot(x, merged_df['ttm'], 's-', color='#E53935', linewidth=2.5, markersize=7, 
                   label='归母净利润TTM（亿元人民币 RMB）')
    ax2.fill_between(x, merged_df['ttm'], alpha=0.08, color='#E53935')

    ax1.set_title(f'{stock_name}（{clean_code}.HK）股价与归母净利润TTM双轴趋势', fontsize=16, fontweight='bold', fontproperties=font_title, pad=15)
    ax1.set_ylabel('股价（港币 HKD）', color='#1E88E5', fontsize=12, fontproperties=font_prop)
    ax2.set_ylabel('归母净利润TTM（亿元人民币 RMB）', color='#E53935', fontsize=12, fontproperties=font_prop)
    ax1.legend([l1, l2], [l1.get_label(), l2.get_label()], fontsize=11, loc='upper left', prop=font_prop, frameon=True, facecolor='white')
    ax1.tick_params(axis='y', labelcolor='#1E88E5')
    ax2.tick_params(axis='y', labelcolor='#E53935')
    ax1.set_xticks(x)
    ax1.set_xticklabels(merged_df['label'], rotation=30, ha='right', fontsize=10, fontproperties=font_small)
    ax1.grid(True, linestyle='--', alpha=0.3, color='#94A3B8')
    ax1.spines['top'].set_visible(False)
    ax2.spines['top'].set_visible(False)
    plt.tight_layout()

    dual_chart_path = out_dir / f"{clean_code}_股价vs利润TTM_双Y轴.png"
    plt.savefig(dual_chart_path, bbox_inches='tight', dpi=180, facecolor='white')
    plt.close()
    print(f"双Y轴图已生成: {dual_chart_path}")

    print("=== 图表生成与固化完成 ===")


if __name__ == '__main__':
    main()
