#!/usr/bin/env python3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "charts" / "300573_季度数据.csv"
OUT_DIR = ROOT / "charts"

# 1. 检查并追加 2026Q2 数据
df = pd.read_csv(CSV_PATH)
if "2026Q2" not in df["quarter"].values:
    new_row = {
        "date": "2026-06-30",
        "quarter": "2026Q2",
        "net_profit_yi": 2.239657,
        "non_gaap_yi": 2.254050,
        "revenue_yi": 7.179726,
        "eps": 0.63,
        "net_profit_ttm_yi": 7.914092,
        "non_gaap_ttm_yi": 7.978304,
        "eps_ttm": 2.94,
        "trade_date": "2026-06-30",
        "adj_close": 37.06,
        "close": 37.06
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_csv(CSV_PATH, index=False)
    print("已追加 2026Q2 数据到 300573_季度数据.csv")
else:
    print("2026Q2 已存在于 300573_季度数据.csv")

# 2. 绘制双Y轴图
plt.rcParams['font.sans-serif'] = ['PingFang SC', 'Heiti SC', 'Arial Unicode MS', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

merged = df.dropna(subset=["non_gaap_ttm_yi", "adj_close"]).reset_index(drop=True)

fig, ax1 = plt.subplots(figsize=(12, 6), dpi=160)
x = np.arange(len(merged))
color1 = "#1f77b4"
color2 = "#d62728"

ax1.plot(x, merged["adj_close"], color=color1, linewidth=2.2, label="股价（前复权，元）")
ax1.set_ylabel("股价（元）", color=color1, fontsize=11, fontweight="bold")
ax1.tick_params(axis="y", labelcolor=color1)

ax2 = ax1.twinx()
ax2.plot(x, merged["non_gaap_ttm_yi"], color=color2, linewidth=2.2, linestyle="--", label="扣非净利润TTM（亿元）")
ax2.set_ylabel("扣非净利润TTM（亿元）", color=color2, fontsize=11, fontweight="bold")
ax2.tick_params(axis="y", labelcolor=color2)

# 最新点标注
last_row = merged.iloc[-1]
ax1.scatter([x[-1]], [last_row["adj_close"]], color=color1, s=60, zorder=5)
ax1.text(x[-1], last_row["adj_close"] * 1.03, f"{last_row['adj_close']:.2f}元", color=color1, fontweight="bold", ha="center")

ax2.scatter([x[-1]], [last_row["non_gaap_ttm_yi"]], color=color2, s=60, zorder=5)
ax2.text(x[-1], last_row["non_gaap_ttm_yi"] * 1.03, f"{last_row['non_gaap_ttm_yi']:.2f}亿", color=color2, fontweight="bold", ha="center")

step = max(1, len(merged) // 10)
ticks = list(range(0, len(merged), step))
if (len(merged) - 1) not in ticks:
    ticks.append(len(merged) - 1)
labels = [merged["quarter"].iloc[i] for i in ticks]
ax1.set_xticks(ticks)
ax1.set_xticklabels(labels, rotation=45, ha="right", fontsize=9)
ax1.grid(True, alpha=0.25)

lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=10)

ax1.set_title("兴齐眼药(300573) 股价 vs 扣非净利润TTM 双Y轴走势 (截至2026H1/2026Q2)", fontsize=13, fontweight="bold", pad=12)
fig.tight_layout()
fig.savefig(OUT_DIR / "300573_股价vs扣非净利润TTM_双Y轴.png", bbox_inches="tight")
plt.close(fig)
print("已成功重新生成 300573_股价vs扣非净利润TTM_双Y轴.png")
