#!/usr/bin/env python3
"""Generate a China Shenhua-specific segment chart with legible small negative labels."""
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import pandas as pd

BASE = Path(__file__).resolve().parents[1]; DATA = BASE / "data"; OUT = BASE / "charts"


def font() -> FontProperties:
    for p in ("/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/Hiragino Sans GB.ttc", "/System/Library/Fonts/STHeiti Medium.ttc"):
        if Path(p).exists(): return FontProperties(fname=p)
    return FontProperties()


FONT = font(); plt.rcParams["axes.unicode_minus"] = False
p = pd.read_csv(DATA / "product_structure.csv")
p["抵销前占比"] = p["收入_亿元"] / p["收入_亿元"].sum() * 100
p["上年收入"] = p["收入_亿元"] / (1 + p["同比_%"] / 100); p["收入增量"] = p["收入_亿元"] - p["上年收入"]
fig, axes = plt.subplots(1, 2, figsize=(16, 7), dpi=180, gridspec_kw={"width_ratios": [1.35, 1]})
left = p.sort_values("收入_亿元", ascending=True)
colors = ["#CBD5E1", "#DDD6FE", "#A7F3D0", "#FDE68A", "#FDBA74", "#93C5FD"]
axes[0].barh(left["业务"], left["收入_亿元"], height=0.52, color=colors)
for y, rev, share, margin in zip(left["业务"], left["收入_亿元"], left["抵销前占比"], left["毛利率_%"]):
    axes[0].text(rev + 28, y, f"{rev:.0f}亿 / {share:.1f}% / 毛利率{margin:.1f}%", va="center", fontproperties=FONT, fontsize=9)
axes[0].set_xlim(0, left["收入_亿元"].max() * 1.43); axes[0].set_xlabel("分部收入（亿元，合并抵销前）", fontproperties=FONT)

inc = p.sort_values("收入增量", ascending=True); bar_colors = ["#16A34A" if v >= 0 else "#DC2626" for v in inc["收入增量"]]
axes[1].barh(inc["业务"], inc["收入增量"], height=0.52, color=bar_colors); axes[1].axvline(0, color="#94A3B8", lw=0.9)
for y, value, yoy in zip(inc["业务"], inc["收入增量"], inc["同比_%"]):
    label = f"{value:+.1f}亿 / {yoy:+.1f}%"
    if value <= -120:
        axes[1].text(value / 2, y, label, ha="center", va="center", color="white", fontproperties=FONT, fontsize=9)
    elif value < 0:
        axes[1].text(value - 10, y, label, ha="right", va="center", color="#B91C1C", fontproperties=FONT, fontsize=9)
    else:
        axes[1].text(value + 8, y, label, ha="left", va="center", color="#16A34A", fontproperties=FONT, fontsize=9)
axes[1].set_xlim(inc["收入增量"].min() * 1.25, 120); axes[1].set_xlabel("收入增量（亿元，按同比反推）", fontproperties=FONT)
axes[1].set_title("收入增量贡献", fontproperties=FONT, fontsize=12, pad=10)
for ax in axes:
    ax.grid(axis="y", alpha=0.20); ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    for label in ax.get_xticklabels() + ax.get_yticklabels(): label.set_fontproperties(FONT)
axes[0].set_title("中国神华：分部收入结构", fontproperties=FONT, fontsize=17, weight="bold", pad=18)
axes[0].text(0.5, 1.01, "合并抵销前口径；左图看规模和毛利率，右图看2025年收入增量", transform=axes[0].transAxes,
             ha="center", va="bottom", fontproperties=FONT, fontsize=10, color="#64748B")
fig.tight_layout(); path = OUT / "601088_4.3_收入结构与产品增速图.png"
fig.savefig(path, bbox_inches="tight", facecolor="white"); plt.close(fig); print(path)
