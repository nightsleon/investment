#!/usr/bin/env python3
"""生成美的集团归一化股价vs扣非TTM利润图 + 季度数据CSV"""
import csv
import os
import urllib.request
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

CODE = '000333'
NAME = '美的集团'
BASE = '/Users/pidan-l/Documents/AI-Investment/investment/000333_美的集团'

plt.rcParams['font.sans-serif'] = ['PingFang SC', 'Heiti SC', 'Arial Unicode MS', 'STHeiti']
plt.rcParams['axes.unicode_minus'] = False

# ===== 第一步：从PE历史数据反推季度利润和价格 =====
# 我们有日频PE和市值数据，可以得到日频净利润 = 市值 / PE
# 但我们需要季度级别的扣非TTM来做归一化图
# 用已知的中报数据 + 历史年报数据来构建季度序列

# 已知数据（归母净利润，单位：亿元）
# 2023全年: 385.4 (从2024年底PE静反推)
# 2024全年: ?
# 2025全年: 439.5 (从PE静反推)
# 2025H1: 260.14
# 2026H1: 264.46

# 更靠谱的方式：用我们已有的季度数据逻辑
# 从PE(TTM)日频数据 + 已知的季度利润点
# 构建2018年以来的季度利润序列

# 简化方案：直接用PE历史数据中的市值和PE反推归母TTM，
# 再按季度末取样，做归一化图

# 读取PE历史数据
pe_path = f'{BASE}/data/pe_history.csv'
pe_data = []
with open(pe_path, 'r', encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        try:
            pe = float(row['PE_TTM'])
            mcap = float(row['TOTAL_MARKET_CAP']) / 1e8
            close = float(row['CLOSE_PRICE'])
            date = row['TRADE_DATE']
            if 5 < pe < 100 and mcap > 0:
                ttm_np = mcap / pe
                pe_data.append({'date': date, 'close': close, 'mcap': mcap, 'pe_ttm': pe, 'ttm_np': ttm_np})
        except:
            pass

pe_data.sort(key=lambda x: x['date'])
print(f"有效PE数据: {len(pe_data)}天")
print(f"范围: {pe_data[0]['date']} ~ {pe_data[-1]['date']}")

# 按季度末取样
import datetime
quarter_data = []
current_q = None
for item in pe_data:
    d = item['date'][:10]  # 去掉时间
    dt = datetime.datetime.strptime(d, '%Y-%m-%d')
    q = f"{dt.year}Q{(dt.month-1)//3+1}"
    if q != current_q:
        if current_q:
            quarter_data.append(last_item)
        current_q = q
    last_item = {'quarter': q, 'date': d, 'close': item['close'], 'ttm_np': item['ttm_np']}
# 加最后一个
if current_q:
    quarter_data.append(last_item)

# 从2018Q1开始
q_start = '2018Q1'
start_idx = 0
for i, qd in enumerate(quarter_data):
    if qd['quarter'] == q_start:
        start_idx = i
        break

quarter_data = quarter_data[start_idx:]
print(f"季度数据点: {len(quarter_data)}个")
print(f"第一个: {quarter_data[0]}")
print(f"最后一个: {quarter_data[-1]}")

# 保存季度数据CSV
os.makedirs(f'{BASE}/charts', exist_ok=True)
with open(f'{BASE}/charts/{CODE}_季度数据.csv', 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.writer(f)
    writer.writerow(['quarter', 'date', 'close', 'ttm_np_yi'])
    for qd in quarter_data:
        writer.writerow([qd['quarter'], qd['date'], qd['close'], round(qd['ttm_np'], 2)])

print(f"季度数据已保存到 {BASE}/charts/{CODE}_季度数据.csv")

# ===== 第二步：生成归一化图 =====
quarters = [qd['quarter'] for qd in quarter_data]
prices = [qd['close'] for qd in quarter_data]
profits = [qd['ttm_np'] for qd in quarter_data]

norm_price = [p / prices[0] for p in prices]
norm_profit = [p / profits[0] for p in profits]

fig, ax = plt.subplots(figsize=(11, 6), dpi=160)

x = np.arange(len(quarter_data))
tick_step = max(1, len(quarter_data) // 8)

ax.plot(x, norm_price, 'o-', color='#1E88E5', linewidth=2.2, markersize=4.5,
        label='归一化股价（未复权）', zorder=3)
ax.plot(x, norm_profit, 's-', color='#E53935', linewidth=2.2, markersize=4.5,
        label='归一化归母 TTM 利润（从PE反推）', zorder=3)
ax.fill_between(x, norm_price, norm_profit, alpha=0.08, color='gray', zorder=1)

ax.set_title(f'{NAME}（{CODE}）归一化对比：股价 vs 归母 TTM 利润',
             fontsize=13, fontweight='bold', pad=12)
ax.set_ylabel('归一化值（2018Q1 = 1）', fontsize=11)
ax.set_xticks(x[::tick_step])
ax.set_xticklabels([quarters[i] for i in range(0, len(quarters), tick_step)],
                   rotation=35, ha='right', fontsize=9)
ax.legend(loc='upper left', fontsize=9, framealpha=0.9)
ax.grid(True, alpha=0.3, linestyle='--', zorder=0)
ax.axhline(y=1, color='gray', linewidth=0.8, alpha=0.5, linestyle=':')

# 统计信息
corr = float(np.corrcoef(norm_price, norm_profit)[0, 1])
price_mult = norm_price[-1]
profit_mult = norm_profit[-1]
info_text = (f'相关系数: {corr:.3f}\n'
             f'股价涨幅: {price_mult:.1f}x\n'
             f'利润涨幅: {profit_mult:.1f}x')
ax.text(0.02, 0.97, info_text, transform=ax.transAxes, va='top',
        fontsize=9.5, bbox=dict(boxstyle='round,pad=0.5', facecolor='#FFF8E1',
                                 edgecolor='#FFC107', alpha=0.9))

# 末点标注
ax.annotate(f'{price_mult:.1f}x', xy=(x[-1], norm_price[-1]),
            xytext=(10, 0), textcoords='offset points',
            fontsize=9, color='#1E88E5', fontweight='bold')
ax.annotate(f'{profit_mult:.1f}x', xy=(x[-1], norm_profit[-1]),
            xytext=(10, 0), textcoords='offset points',
            fontsize=9, color='#E53935', fontweight='bold')

# 图注
ax.text(0.98, 0.02, f'利润数据从PE(TTM)反推，非扣非口径｜价格截至{quarter_data[-1]["date"]}',
        transform=ax.transAxes, ha='right', fontsize=7.5, color='gray', alpha=0.8)

plt.tight_layout()
out_path = f'{BASE}/charts/{CODE}_归一化_股价vs归母TTM.png'
fig.savefig(out_path, bbox_inches='tight', facecolor='white')
plt.close(fig)

print(f"\n归一化图已生成: {out_path}")
print(f"  股价涨幅: {price_mult:.2f}x")
print(f"  利润涨幅: {profit_mult:.2f}x")
print(f"  相关系数: {corr:.3f}")
