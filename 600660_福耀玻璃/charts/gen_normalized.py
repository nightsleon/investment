#!/usr/bin/env python3
"""生成福耀玻璃归一化股价vs扣非TTM利润图（2018Q1起，末点价格9月2日）"""
import csv
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

CODE = '600660'
NAME = '福耀玻璃'
BASE = '/Users/pidan-l/Documents/AI-Investment/investment/600660_福耀玻璃'
CSV_PATH = f'{BASE}/charts/{CODE}_季度数据.csv'
OUT_PATH = f'{BASE}/charts/{CODE}_归一化_股价vs扣非TTM.png'

# 设置字体
plt.rcParams['font.sans-serif'] = ['PingFang SC', 'Heiti SC', 'Arial Unicode MS', 'STHeiti']
plt.rcParams['axes.unicode_minus'] = False

# 读取数据
with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

# 从2018Q1开始
start_idx = None
for i, row in enumerate(rows):
    if row['quarter'] == '2018Q1':
        start_idx = i
        break

data = rows[start_idx:]
quarters = [r['quarter'] for r in data]
adj_close = [float(r['adj_close']) for r in data]
non_gaap_ttm = [float(r['non_gaap_ttm_yi']) for r in data]

# 归一化
norm_price = [p / adj_close[0] for p in adj_close]
norm_profit = [p / non_gaap_ttm[0] for p in non_gaap_ttm]

# 画图 - 11x6（用户偏好）
fig, ax = plt.subplots(figsize=(11, 6), dpi=160)

x = np.arange(len(data))
tick_step = max(1, len(data) // 8)

ax.plot(x, norm_price, 'o-', color='#1E88E5', linewidth=2.2, markersize=4.5,
        label='归一化股价（前复权）', zorder=3)
ax.plot(x, norm_profit, 's-', color='#E53935', linewidth=2.2, markersize=4.5,
        label='归一化扣非 TTM 利润', zorder=3)
ax.fill_between(x, norm_price, norm_profit, alpha=0.08, color='gray', zorder=1)

ax.set_title(f'{NAME}（{CODE}）归一化对比：股价 vs 扣非 TTM 利润',
             fontsize=13, fontweight='bold', pad=12)
ax.set_ylabel('归一化值（2018Q1 = 1）', fontsize=11)
ax.set_xticks(x[::tick_step])
ax.set_xticklabels([quarters[i] for i in range(0, len(data), tick_step)],
                   rotation=35, ha='right', fontsize=9)
ax.legend(loc='upper left', fontsize=10, framealpha=0.9)
ax.grid(True, alpha=0.3, linestyle='--', zorder=0)
ax.axhline(y=1, color='gray', linewidth=0.8, alpha=0.5, linestyle=':')

# 统计信息框
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

plt.tight_layout()
fig.savefig(OUT_PATH, bbox_inches='tight', facecolor='white')
plt.close(fig)

print(f'已生成: {OUT_PATH}')
print(f'文件大小: {os.path.getsize(OUT_PATH)/1024:.0f}KB')
print(f'数据点: {len(data)}个季度 ({quarters[0]} ~ {quarters[-1]})')
print(f'基期股价: {adj_close[0]:.2f}元, 基期扣非TTM: {non_gaap_ttm[0]:.2f}亿')
print(f'期末股价: {adj_close[-1]:.2f}元(前复权), 期末扣非TTM: {non_gaap_ttm[-1]:.2f}亿')
print(f'归一化末点: 股价{price_mult:.2f}x / 利润{profit_mult:.2f}x')
print(f'相关系数: {corr:.3f}')
