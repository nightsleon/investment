#!/usr/bin/env python3
"""Generate China Shenhua ten-year PE chart."""
from pathlib import Path
import json

import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DATA, OUT = BASE / "data", BASE / "charts"


def font() -> FontProperties:
    for p in ("/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/Hiragino Sans GB.ttc", "/System/Library/Fonts/STHeiti Medium.ttc"):
        if Path(p).exists():
            return FontProperties(fname=p)
    return FontProperties()


FONT = font(); plt.rcParams["axes.unicode_minus"] = False
v = pd.read_csv(DATA / "valuation_history.csv", parse_dates=["TRADE_DATE"])
v["PE_TTM"] = pd.to_numeric(v["PE_TTM"], errors="coerce")
v = v[(v["PE_TTM"] > 0) & v["PE_TTM"].notna()].sort_values("TRADE_DATE")
latest_date = v["TRADE_DATE"].max(); v = v[v["TRADE_DATE"] >= latest_date - pd.DateOffset(years=10)]
q25, q50, q75 = v["PE_TTM"].quantile([0.25, 0.5, 0.75]); latest = v.iloc[-1]
percentile = float((v["PE_TTM"] <= latest["PE_TTM"]).mean() * 100)
fig, ax = plt.subplots(figsize=(16, 8))
ax.axhspan(v["PE_TTM"].min(), q25, color="#DCFCE7", alpha=0.65, label="0%-25%分位")
ax.axhspan(q25, q75, color="#FEF3C7", alpha=0.55, label="25%-75%分位")
ax.axhspan(q75, v["PE_TTM"].max(), color="#FEE2E2", alpha=0.45, label="75%-100%分位")
ax.plot(v["TRADE_DATE"], v["PE_TTM"], color="#2563EB", lw=1.8, label="PE(TTM)")
ax.scatter([latest["TRADE_DATE"]], [latest["PE_TTM"]], color="#DC2626", s=55, zorder=4)
ax.annotate(f"当前 {latest['PE_TTM']:.1f}倍\n近十年约{percentile:.1f}%分位", (latest["TRADE_DATE"], latest["PE_TTM"]),
            xytext=(-120, -50), textcoords="offset points", fontproperties=FONT, color="#DC2626", arrowprops={"arrowstyle": "->", "color": "#DC2626"})
ax.set_title("中国神华：近十年PE(TTM)区间", fontproperties=FONT, fontsize=17, weight="bold", pad=18)
ax.text(0.5, 1.01, "东方财富A股展示口径；当前PE受重组先增股、后并表的时点错配抬高", transform=ax.transAxes,
        ha="center", va="bottom", fontproperties=FONT, fontsize=10, color="#64748B")
ax.set_ylabel("PE(TTM，倍)", fontproperties=FONT); ax.grid(axis="y", alpha=0.2)
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
for label in ax.get_xticklabels() + ax.get_yticklabels(): label.set_fontproperties(FONT)
ax.legend(prop=FONT, frameon=False, ncol=4, loc="upper left")
OUT.mkdir(parents=True, exist_ok=True); path = OUT / "601088_5.2_近十年PE区间图.png"
fig.savefig(path, dpi=180, bbox_inches="tight", facecolor="white"); plt.close(fig)
print(path)
print(json.dumps({"q25": q25, "median": q50, "q75": q75, "latest": float(latest["PE_TTM"]), "percentile": percentile}, ensure_ascii=False))
