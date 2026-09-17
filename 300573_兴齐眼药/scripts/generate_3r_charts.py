#!/usr/bin/env python3
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data' / '300573_annual_financial_summary.csv'
OUT = ROOT / 'charts'
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams['font.sans-serif'] = ['PingFang SC', 'Heiti SC', 'Arial Unicode MS', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

df = pd.read_csv(DATA)
df['year'] = df['year'].astype(str)

# 1. 4.1_ROE与杜邦三因子趋势图
fig, ax1 = plt.subplots(figsize=(10, 5.5), dpi=160)
ax1.bar(df['year'], df['roe_simple'], color='#E53935', alpha=0.25, label='简单ROE')
ax1.plot(df['year'], df['roe_simple'], 'o-', color='#E53935', linewidth=2.2, label='简单ROE (%)')
ax1.set_ylabel('简单ROE (%)', color='#E53935')
ax1.set_ylim(0, max(df['roe_simple']) * 1.25)
for x, v in zip(df['year'], df['roe_simple']):
    ax1.text(x, v + 0.8, f'{v:.1f}%', ha='center', va='bottom', fontsize=9, color='#C62828', fontweight='bold')

ax2 = ax1.twinx()
ax2.plot(df['year'], df['net_margin'], '^-', color='#FB8C00', linewidth=1.8, label='净利率 (%)')
ax2.plot(df['year'], df['asset_turnover'], 'd-', color='#43A047', linewidth=1.8, label='总资产周转率 (次)')
ax2.plot(df['year'], df['equity_multiplier'], 'v-', color='#8E24AA', linewidth=1.8, label='权益乘数 (倍)')
ax2.set_ylabel('净利率(%) / 周转率(次) / 权益乘数(倍)')
ax1.set_title('兴齐眼药 ROE与杜邦三因子趋势图 (2020-2025)')

lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, ncol=4, loc='upper left', fontsize=8.5)
ax1.grid(alpha=0.25)
fig.tight_layout()
fig.savefig(OUT / '300573_4.1_ROE与杜邦三因子趋势图.png', bbox_inches='tight')
plt.close(fig)

# 2. 4.2_利润趋势与同比增速图
fig, ax1 = plt.subplots(figsize=(10, 5.5), dpi=160)
ax1.bar(df['year'], df['non_gaap_yi'], color='#1E88E5', alpha=0.75, width=0.45, label='扣非净利润 (亿元)')
ax1.set_ylabel('扣非净利润（亿元）', color='#1E88E5')
ax1.set_ylim(0, max(df['non_gaap_yi']) * 1.25)
for x, v in zip(df['year'], df['non_gaap_yi']):
    ax1.text(x, v + 0.15, f'{v:.2f}亿', ha='center', va='bottom', fontsize=9, fontweight='bold', color='#1565C0')

ax2 = ax1.twinx()
yoy = df['non_gaap_yi'].pct_change() * 100
ax2.plot(df['year'], yoy, 's-', color='#E53935', linewidth=2.0, label='扣非同比增速 (%)')
ax2.axhline(0, color='gray', linewidth=0.8, linestyle='--')
ax2.set_ylabel('同比增速（%）', color='#E53935')
for x, v in zip(df['year'][1:], yoy[1:]):
    ax2.text(x, v + 3, f'{v:.1f}%', ha='center', va='bottom', fontsize=8.5, color='#B71C1C')

ax1.set_title('兴齐眼药 4.2_利润趋势与同比增速图 (2020-2025)')
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=9)
ax1.grid(axis='y', alpha=0.25)
fig.tight_layout()
fig.savefig(OUT / '300573_4.2_利润趋势与同比增速图.png', bbox_inches='tight')
plt.close(fig)

# 3. 4.4_净利润经营现金流自由现金流对比图
fig, ax = plt.subplots(figsize=(10, 5.5), dpi=160)
import numpy as np
x = np.arange(len(df['year']))
width = 0.25
ax.bar(x - width, df['net_profit_yi'], width, label='归母净利润', color='#1E88E5', alpha=0.8)
ax.bar(x, df['cfo_yi'], width, label='经营现金流(CFO)', color='#43A047', alpha=0.8)
ax.bar(x + width, df['fcf_yi'], width, label='自由现金流(FCF)', color='#FB8C00', alpha=0.8)

for i in x:
    ax.text(i - width, df['net_profit_yi'][i] + 0.1, f"{df['net_profit_yi'][i]:.2f}", ha='center', va='bottom', fontsize=8)
    ax.text(i, df['cfo_yi'][i] + 0.1, f"{df['cfo_yi'][i]:.2f}", ha='center', va='bottom', fontsize=8)
    ax.text(i + width, df['fcf_yi'][i] + 0.1, f"{df['fcf_yi'][i]:.2f}", ha='center', va='bottom', fontsize=8)

ax.set_xticks(x)
ax.set_xticklabels(df['year'])
ax.set_ylabel('金额（亿元）')
ax.set_title('兴齐眼药 4.4_净利润经营现金流自由现金流对比图 (2020-2025)')
ax.legend(loc='upper left', fontsize=9)
ax.grid(axis='y', alpha=0.25)
fig.tight_layout()
fig.savefig(OUT / '300573_4.4_净利润经营现金流自由现金流对比图.png', bbox_inches='tight')
plt.close(fig)

print("兴齐眼药标准三图生成成功！")
