#!/usr/bin/env python3
"""农夫山泉 股价vs利润TTM 图表生成器 — 港股版本 v2"""

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from datetime import datetime
import os

from pathlib import Path
BASE_DIR = Path(__file__).resolve().parents[1]
os.chdir(BASE_DIR)

print("=" * 70)
print("农夫山泉 股价 vs 利润TTM 图表生成 v3")
print("=" * 70)

# ===== 加载股价数据 =====
price = pd.read_csv('data/price_daily.csv')
price['trade_date'] = pd.to_datetime(price['trade_date'])

# 追加最新 2026-09-16 交易日收盘价 39.38 HKD
latest_date = pd.to_datetime('2026-09-16')
if price['trade_date'].iloc[-1] < latest_date:
    new_p = pd.DataFrame([{
        'trade_date': latest_date,
        'adj_close': 39.38,
        'close': 39.38
    }])
    price = pd.concat([price, new_p], ignore_index=True)
    price.to_csv('data/price_daily.csv', index=False)

print("股价数据: {} 个交易日 ({} ~ {})".format(
    len(price), 
    price['trade_date'].iloc[0].strftime('%Y-%m-%d'),
    price['trade_date'].iloc[-1].strftime('%Y-%m-%d')
))

# ===== 构建利润数据（仅含已公布的报告） =====
# 港股只有半年报(H1)和年报(FY)
# TTM计算：年末=年报本身；年中=上年年报+本年H1-上年H1
profit_records = [
    # (日期, 净利润亿元, 类型)
    ('2019-12-31', 49.54, 'FY'),   # FY2019年报
    ('2020-06-30', 28.60, 'H1'),   # 2020H1
    ('2020-12-31', 52.77, 'FY'),   # FY2020年报
    ('2021-06-30', 40.33, 'H1'),   # 2021H1
    ('2021-12-31', 71.62, 'FY'),   # FY2021年报
    ('2022-06-30', 46.19, 'H1'),   # 2022H1
    ('2022-12-31', 84.99, 'FY'),   # FY2022年报
    ('2023-06-30', 52.59, 'H1'),   # 2023H1
    ('2023-12-31', 120.79, 'FY'),  # FY2023年报
    ('2024-06-30', 62.40, 'H1'),   # 2024H1
    ('2024-12-31', 121.23, 'FY'),  # FY2024年报
    ('2025-06-30', 76.22, 'H1'),   # 2025H1
    ('2025-12-31', 158.68, 'FY'),  # FY2025年报
    ('2026-06-30', 88.87, 'H1'),   # 2026H1 (本次分析主体)
]

profit = pd.DataFrame(profit_records, columns=['date', 'net_profit', 'type'])
profit['date'] = pd.to_datetime(profit['date'])

# ===== 计算TTM =====
ttm_list = []
for i in range(len(profit)):
    row = profit.iloc[i]
    if row['type'] == 'FY':
        # 年末TTM = 年报全年利润
        ttm_list.append(row['net_profit'])
    elif row['type'] == 'H1':
        # 年中TTM = 上年年报 + 本年H1 - 上年H1
        prev_year = row['date'].year - 1
        prev_fy = profit[(profit['date'].dt.year == prev_year) & (profit['type'] == 'FY')]
        prev_h1 = profit[(profit['date'].dt.year == prev_year) & (profit['type'] == 'H1')]
        
        if not prev_fy.empty and not prev_h1.empty:
            ttm = prev_fy.iloc[0]['net_profit'] + row['net_profit'] - prev_h1.iloc[0]['net_profit']
            ttm_list.append(ttm)
        else:
            ttm_list.append(None)

profit['ttm'] = ttm_list
profit = profit.dropna(subset=['ttm'])
print("\n利润TTM序列 ({} 个数据点):".format(len(profit)))
for _, row in profit.iterrows():
    print("  {} ({}): 净利={:.2f}亿  TTM={:.2f}亿".format(
        row['date'].strftime('%Y-%m-%d'), row['type'], row['net_profit'], row['ttm']))

# ===== 对齐股价和利润 =====
merged = []
for _, row in profit.iterrows():
    report_date = row['date']
    sub = price[price['trade_date'] <= report_date]
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

# 添加最新现价点 (2026-09-16)，实现 G4 门禁：图末点价格 = 正文现价
last_price = price.iloc[-1]
merged.append({
    'date': last_price['trade_date'],
    'label': '2026-09\n(现价)',
    'type': 'Latest',
    'close': last_price['close'],
    'adj_close': last_price['adj_close'],
    'net_profit': 88.87,
    'ttm': 171.33,
})

merged_df = pd.DataFrame(merged)
merged_df.to_csv('data/price_vs_profit.csv', index=False)
print("\n对齐后 {} 个数据点".format(len(merged_df)))

# ===== 统计指标 =====
base_idx = 0
corr = merged_df['adj_close'].corr(merged_df['ttm'])
price_mult = merged_df['adj_close'].iloc[-1] / merged_df['adj_close'].iloc[base_idx]
ttm_mult = merged_df['ttm'].iloc[-1] / merged_df['ttm'].iloc[base_idx]

# ===== 中文字体配置 =====
font_candidates = [
    '/System/Library/Fonts/PingFang.ttc',
    '/System/Library/Fonts/Hiragino Sans GB.ttc',
    '/System/Library/Fonts/STHeiti Medium.ttc',
    '/System/Library/Fonts/Supplemental/Songti.ttc',
]
font_prop = None
font_prop_title = None
font_prop_small = None
font_prop_info = None

for fp in font_candidates:
    if os.path.exists(fp):
        try:
            font_prop = fm.FontProperties(fname=fp, size=12)
            font_prop_title = fm.FontProperties(fname=fp, size=15, weight='bold')
            font_prop_small = fm.FontProperties(fname=fp, size=10)
            font_prop_info = fm.FontProperties(fname=fp, size=11)
            print("使用中文字体: {}".format(fp))
            break
        except Exception:
            continue

if font_prop is None:
    plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
    font_prop = fm.FontProperties()
    font_prop_title = fm.FontProperties(size=15)
    font_prop_small = fm.FontProperties(size=10)
    font_prop_info = fm.FontProperties(size=11)

plt.rcParams['axes.unicode_minus'] = False

# ===== 图1：归一化对比 =====
fig, ax = plt.subplots(figsize=(15, 8), dpi=180, facecolor='white')
ax.set_facecolor('white')

base_close = merged_df['adj_close'].iloc[base_idx]
base_ttm = merged_df['ttm'].iloc[base_idx]
norm_close = merged_df['adj_close'] / base_close
norm_ttm = merged_df['ttm'] / base_ttm

x = range(len(merged_df))
ax.plot(x, norm_close, 'o-', color='#1E88E5', linewidth=2.5, markersize=7, 
        label='股价前复权（基期 2020-12 = 1.0）')
ax.plot(x, norm_ttm, 's-', color='#E53935', linewidth=2.5, markersize=7, 
        label='归母净利润TTM（基期 2020-12 = 1.0）')
ax.fill_between(x, norm_close, norm_ttm, alpha=0.08, color='#E53935')

# 标注末点具体数值
last_x = len(merged_df) - 1
ax.annotate(f"现价 39.38 HKD\n({price_mult:.2f}x)", 
            xy=(last_x, norm_close.iloc[-1]), 
            xytext=(-45, -35), textcoords='offset points',
            color='#1E88E5', fontproperties=font_prop_small,
            arrowprops=dict(arrowstyle='->', color='#1E88E5'))
ax.annotate(f"TTM 171.33 亿\n({ttm_mult:.2f}x)", 
            xy=(last_x, norm_ttm.iloc[-1]), 
            xytext=(-50, 20), textcoords='offset points',
            color='#E53935', fontproperties=font_prop_small,
            arrowprops=dict(arrowstyle='->', color='#E53935'))

# 信息框
info_text = (
    f"走势特征：典型估值压缩（背离）\n"
    f"相关系数: {corr:.3f}\n"
    f"股价变动: {price_mult:.2f}x (下跌 {(1-price_mult)*100:.1f}%)\n"
    f"利润变动: {ttm_mult:.2f}x (增长 {(ttm_mult-1)*100:.1f}%)\n"
    f"末点股价: 39.38 HKD (2026-09-16)"
)
ax.text(0.03, 0.82, info_text, transform=ax.transAxes, fontsize=11, va='top',
        bbox=dict(boxstyle='round,pad=0.6', facecolor='#F8FAFC', edgecolor='#CBD5E1', alpha=0.9),
        fontproperties=font_prop_info)

ax.set_title('农夫山泉（09633.HK）股价 vs 归母净利润TTM 归一化走势对比', 
             fontsize=16, fontweight='bold', fontproperties=font_prop_title, pad=15)
ax.set_ylabel('归一化数值（2020-12 = 1.0）', fontsize=12, fontproperties=font_prop)
ax.legend(fontsize=11, loc='upper left', frameon=True, facecolor='white', framealpha=0.9, prop=font_prop)
ax.set_xticks(x)
ax.set_xticklabels(merged_df['label'], rotation=30, ha='right', fontsize=10, 
                   fontproperties=font_prop_small)
ax.grid(True, linestyle='--', alpha=0.3, color='#94A3B8')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
plt.tight_layout()

chart_path_std = 'charts/09633_归一化_股价vs利润TTM.png'
chart_path_compat = 'charts/9633_normalized_price_vs_profit_TTM.png'
plt.savefig(chart_path_std, bbox_inches='tight', dpi=180, facecolor='white')
plt.savefig(chart_path_compat, bbox_inches='tight', dpi=180, facecolor='white')
plt.close()
print(f"Generated: {chart_path_std}")
print(f"Generated: {chart_path_compat}")

# ===== 图2：双Y轴 =====
fig, ax1 = plt.subplots(figsize=(16, 8), dpi=180, facecolor='white')
ax2 = ax1.twinx()
ax1.set_facecolor('white')

line1, = ax1.plot(x, merged_df['adj_close'], 'o-', color='#1E88E5', linewidth=2.5, markersize=7, 
                  label='股价（前复权，港币 HKD）')
line2, = ax2.plot(x, merged_df['ttm'], 's-', color='#E53935', linewidth=2.5, markersize=7, 
                  label='归母净利润TTM（亿元人民币 RMB）')
ax2.fill_between(x, merged_df['ttm'], alpha=0.08, color='#E53935')

ax1.set_title('农夫山泉（09633.HK）股价与归母净利润TTM双轴趋势', fontsize=16, fontweight='bold', fontproperties=font_prop_title, pad=15)
ax1.set_ylabel('股价（港币 HKD）', color='#1E88E5', fontsize=12, fontproperties=font_prop)
ax2.set_ylabel('归母净利润TTM（亿元人民币 RMB）', color='#E53935', fontsize=12, fontproperties=font_prop)
ax1.legend([line1, line2], [line1.get_label(), line2.get_label()], fontsize=11, loc='upper left', prop=font_prop, frameon=True, facecolor='white')
ax1.tick_params(axis='y', labelcolor='#1E88E5')
ax2.tick_params(axis='y', labelcolor='#E53935')
ax1.set_xticks(x)
ax1.set_xticklabels(merged_df['label'], rotation=30, ha='right', fontsize=10, fontproperties=font_prop_small)
ax1.grid(True, linestyle='--', alpha=0.3, color='#94A3B8')
ax1.spines['top'].set_visible(False)
ax2.spines['top'].set_visible(False)
plt.tight_layout()

chart_dual_std = 'charts/09633_股价vs利润TTM_双Y轴.png'
chart_dual_compat = 'charts/9633_price_vs_profit_TTM_dual_axis.png'
plt.savefig(chart_dual_std, bbox_inches='tight', dpi=180, facecolor='white')
plt.savefig(chart_dual_compat, bbox_inches='tight', dpi=180, facecolor='white')
plt.close()
print(f"Generated: {chart_dual_std}")
print(f"Generated: {chart_dual_compat}")

print("\nStats:")
print("  Correlation: {:.3f}".format(corr))
print("  Price multiplier: {:.2f}x".format(price_mult))
print("  Profit multiplier: {:.2f}x".format(ttm_mult))
print("Done!")
