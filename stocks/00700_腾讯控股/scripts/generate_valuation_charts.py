#!/usr/bin/env python3
"""Generate Tencent stock-profit and ten-year point-in-time PE charts."""
from pathlib import Path
import json

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"
OUT = BASE / "charts"
OUT.mkdir(parents=True, exist_ok=True)


def detect_font() -> FontProperties:
    for path in [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
    ]:
        if Path(path).exists():
            return FontProperties(fname=path)
    return FontProperties()


FONT = detect_font()
plt.rcParams["axes.unicode_minus"] = False
BLUE, ORANGE, RED, GRAY = "#2563EB", "#F97316", "#DC2626", "#64748B"


def style(ax):
    ax.grid(axis="y", alpha=0.22)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontproperties(FONT)


market = pd.read_csv(DATA / "historical_valuation.csv", parse_dates=["日期"])
snapshot = json.loads((DATA / "market_snapshot.json").read_text(encoding="utf-8"))

# 主图：股价与当时已经披露的核心TTM利润。
monthly = market.set_index("日期").resample("ME").last().dropna(subset=["收盘价_HKD", "NonIFRS归母TTM_百万元"]).reset_index()
monthly["NonIFRS归母TTM_亿元"] = monthly["NonIFRS归母TTM_百万元"] / 100
fig, ax1 = plt.subplots(figsize=(16, 8), dpi=180)
ax2 = ax1.twinx()
line1, = ax1.plot(monthly["日期"], monthly["收盘价_HKD"], color=BLUE, lw=2.5, label="月末股价（HKD）")
line2, = ax2.plot(monthly["日期"], monthly["NonIFRS归母TTM_亿元"], color=ORANGE, lw=2.5, label="点时可得Non-IFRS TTM利润（亿元）")
ax2.fill_between(monthly["日期"], monthly["NonIFRS归母TTM_亿元"], color=ORANGE, alpha=0.08, step="pre")
style(ax1)
ax2.spines["top"].set_visible(False)
for label in ax2.get_yticklabels():
    label.set_fontproperties(FONT)
ax1.set_ylabel("股价（港元）", fontproperties=FONT)
ax2.set_ylabel("Non-IFRS TTM股东应占溢利（人民币亿元）", fontproperties=FONT)
ax1.set_title("腾讯控股：股价与点时可得核心TTM利润", fontproperties=FONT, fontsize=18, weight="bold", pad=18)
ax1.text(0.5, 1.01, "月末不复权收盘价；利润从业绩公告后下一交易日切换；双轴只比较趋势与斜率", transform=ax1.transAxes,
         ha="center", va="bottom", fontproperties=FONT, fontsize=10, color="#555555")
ax1.legend([line1, line2], [line1.get_label(), line2.get_label()], loc="upper left", prop=FONT, frameon=False)
last = monthly.iloc[-1]
ax1.annotate(f"HK${last['收盘价_HKD']:.1f}", xy=(last["日期"], last["收盘价_HKD"]), xytext=(-10, 14), textcoords="offset points", ha="right", fontproperties=FONT, color=BLUE)
ax2.annotate(f"{last['NonIFRS归母TTM_亿元']:.0f}亿", xy=(last["日期"], last["NonIFRS归母TTM_亿元"]), xytext=(-10, -18), textcoords="offset points", ha="right", fontproperties=FONT, color=ORANGE)
fig.tight_layout()
fig.savefig(OUT / "00700_5.1_股价与点时可得核心TTM利润图.png", bbox_inches="tight", facecolor="white")
plt.close(fig)

# 十年GAAP点时PE：价格按港元转人民币，EPS按当时已披露TTM切换。
end = market["日期"].max()
pe = market[(market["日期"] >= end - pd.DateOffset(years=10)) & market["GAAP_PE_TTM"].notna()].copy()
q20, q50, q80 = pe["GAAP_PE_TTM"].quantile([0.2, 0.5, 0.8])
upper = min(max(pe["GAAP_PE_TTM"].quantile(0.98) * 1.1, q80 * 1.1), 100)
fig, ax = plt.subplots(figsize=(16, 8), dpi=180)
ax.axhspan(0, q20, color="#DCFCE7", alpha=0.75, label="历史低20%区间")
ax.axhspan(q20, q80, color="#FEF3C7", alpha=0.42, label="历史中间60%区间")
ax.axhspan(q80, upper, color="#FEE2E2", alpha=0.45, label="历史高20%区间")
ax.plot(pe["日期"], pe["GAAP_PE_TTM"].clip(upper=upper), color=BLUE, lw=2.1, label="GAAP点时PE（极值按图上限截断）")
current = float(snapshot["GAAP_PE_TTM"])
ax.scatter(pe["日期"].iloc[-1], min(current, upper), color=RED, s=60, zorder=5)
ax.annotate(f"当前 {current:.1f}倍\n分位 {snapshot['近十年GAAP点时PE百分位_%']:.1f}%", xy=(pe["日期"].iloc[-1], min(current, upper)),
            xytext=(-15, 18), textcoords="offset points", ha="right", fontproperties=FONT, color=RED, fontsize=11)
ax.set_ylim(0, upper)
ax.set_ylabel("GAAP PE（倍）", fontproperties=FONT)
style(ax)
ax.set_title("腾讯控股：近十年点时GAAP PE区间", fontproperties=FONT, fontsize=18, weight="bold", pad=18)
ax.text(0.5, 1.01, "未复权股价×当日HKD/CNY÷点时TTM基本EPS；公告后下一交易日生效，避免未来函数", transform=ax.transAxes,
        ha="center", va="bottom", fontproperties=FONT, fontsize=10, color="#555555")
ax.text(0.01, 0.97, f"20%分位：{q20:.1f}倍  |  中位数：{q50:.1f}倍  |  80%分位：{q80:.1f}倍",
        transform=ax.transAxes, ha="left", va="top", fontproperties=FONT, fontsize=10, color=GRAY,
        bbox={"facecolor": "white", "alpha": 0.82, "edgecolor": "none", "pad": 5})
ax.legend(prop=FONT, loc="upper right", ncol=2, frameon=False)
fig.tight_layout()
fig.savefig(OUT / "00700_5.2_近十年点时GAAP_PE区间图.png", bbox_inches="tight", facecolor="white")
plt.close(fig)

print(OUT / "00700_5.1_股价与点时可得核心TTM利润图.png")
print(OUT / "00700_5.2_近十年点时GAAP_PE区间图.png")
