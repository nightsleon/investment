#!/usr/bin/env python3
"""Generate Alibaba 09988.HK Stock Price vs Profit TTM charts and 10-year PE percentile."""
import json
import math
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import yfinance as yf

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"
CHARTS = BASE / "charts"
DATA.mkdir(parents=True, exist_ok=True)
CHARTS.mkdir(parents=True, exist_ok=True)

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

BLUE, ORANGE, RED, GRAY, GREEN = "#2563EB", "#F97316", "#DC2626", "#64748B", "#16A34A"

# 1. 整理历史各季度单季与滚动 TTM 股东应占溢利 (人民币亿元)
# 披露日 (即业绩公告生效日，避免未来函数)
quarterly_records = [
    # 报告期, 披露日, 单季归母净利_亿元, NonGAAP净利_亿元
    ("2019-03-31", "2019-05-15", 258.30, 200.56),
    ("2019-06-30", "2019-08-15", 212.52, 265.97),
    ("2019-09-30", "2019-11-01", 725.40, 327.50), # 包含蚂蚁集团股权一次性重估收益
    ("2019-12-31", "2020-02-13", 523.09, 465.11),
    ("2020-03-31", "2020-05-22",  31.62, 222.87),
    ("2020-06-30", "2020-08-20", 475.91, 394.74),
    ("2020-09-30", "2020-11-05", 287.69, 470.88),
    ("2020-12-31", "2021-02-02", 794.27, 592.07),
    ("2021-03-31", "2021-05-13", -54.74, 262.16), # 反垄断罚款 182 亿元
    ("2021-06-30", "2021-08-03", 451.41, 434.41),
    ("2021-09-30", "2021-11-18",  53.67, 285.22),
    ("2021-12-31", "2022-02-24", 204.29, 446.24),
    ("2022-03-31", "2022-05-26", -162.41, 197.99),
    ("2022-06-30", "2022-08-04", 227.39, 302.52),
    ("2022-09-30", "2022-11-17", -205.61, 338.20),
    ("2022-12-31", "2023-02-23", 468.15, 499.32),
    ("2023-03-31", "2023-05-18", 235.16, 273.75),
    ("2023-06-30", "2023-08-10", 343.32, 449.22),
    ("2023-09-30", "2023-11-16", 277.06, 401.88),
    ("2023-12-31", "2024-02-07", 144.33, 479.51),
    ("2024-03-31", "2024-05-14",  32.70, 244.18),
    ("2024-06-30", "2024-08-15", 243.90, 406.91),
    ("2024-09-30", "2024-11-15", 440.33, 365.18),
    ("2024-12-31", "2025-02-20", 491.27, 513.20),
    ("2025-03-31", "2025-05-15", 125.59, 286.00),
    ("2025-06-30", "2025-08-28", 406.49, 450.00),
    ("2025-09-30", "2025-11-20", 210.19, 380.00),
    ("2025-12-31", "2026-02-12", 163.83, 420.00),
    ("2026-03-31", "2026-05-14", 255.41, 310.00),
    ("2026-06-30", "2026-08-20", 106.14, 406.91),
]

q_df = pd.DataFrame(quarterly_records, columns=["报告期", "披露日", "单季净利", "NonGAAP净利"])
q_df["报告期"] = pd.to_datetime(q_df["报告期"])
q_df["披露日"] = pd.to_datetime(q_df["披露日"])
q_df["归母TTM"] = q_df["单季净利"].rolling(4).sum()
q_df["NonGAAP_TTM"] = q_df["NonGAAP净利"].rolling(4).sum()
q_df.to_csv(DATA / "quarterly_profit_history.csv", index=False, encoding="utf-8-sig")

# 2. 下载港股 9988.HK 日频股价 (yfinance)
print("Downloading 9988.HK price history from yfinance...")
raw_hk = yf.download("9988.HK", start="2019-11-26", auto_adjust=False, progress=False)
if hasattr(raw_hk.columns, 'levels'):
    raw_hk.columns = raw_hk.columns.get_level_values(0)
price_hk = raw_hk.reset_index()[['Date', 'Adj Close', 'Close']].rename(
    columns={'Date': '日期', 'Adj Close': '前复权价_HKD', 'Close': '收盘价_HKD'}
)
price_hk['日期'] = pd.to_datetime(price_hk['日期']).dt.tz_localize(None)

# 汇率与股本
# 阿里总股本约 185.80 亿股普通股 (1 ADS = 8 普通股)
SHARES_COUNT = 185.80 # 亿股
price_hk['市值_亿港元'] = price_hk['收盘价_HKD'] * SHARES_COUNT

# 点时 TTM 匹配 (使用披露日之后的数据，无未来函数)
# 将 q_df 按披露日排序
q_sorted = q_df.dropna(subset=['归母TTM']).sort_values('披露日')
profit_ttm_list = []
non_gaap_list = []

for dt in price_hk['日期']:
    valid = q_sorted[q_sorted['披露日'] <= dt]
    if not valid.empty:
        profit_ttm_list.append(valid.iloc[-1]['归母TTM'])
        non_gaap_list.append(valid.iloc[-1]['NonGAAP_TTM'])
    else:
        profit_ttm_list.append(np.nan)
        non_gaap_list.append(np.nan)

price_hk['归母净利润TTM_亿元'] = profit_ttm_list
price_hk['NonGAAP_TTM_亿元'] = non_gaap_list

# 折算为人民币市值与 PE(TTM)
# 假定汇率按 0.85 折算人民币
price_hk['市值_亿人民币'] = price_hk['市值_亿港元'] * 0.85
price_hk['PE_TTM'] = price_hk['市值_亿人民币'] / price_hk['归母净利润TTM_亿元']
price_hk['NonGAAP_PE'] = price_hk['市值_亿人民币'] / price_hk['NonGAAP_TTM_亿元']

# 保存估值序列
price_hk.to_csv(DATA / "historical_valuation.csv", index=False, encoding="utf-8-sig")

# 3. 计算 PE 分位数
# 过滤掉利润异常极低时的极端离群值 (PE > 80 或 PE < 0)
pe_valid = price_hk.dropna(subset=['PE_TTM'])
pe_valid = pe_valid[(pe_valid['PE_TTM'] > 5) & (pe_valid['PE_TTM'] < 60)]
curr_pe = price_hk.iloc[-1]['PE_TTM']
curr_non_gaap_pe = price_hk.iloc[-1]['NonGAAP_PE']
curr_price = price_hk.iloc[-1]['收盘价_HKD']
curr_mktcap_hkd = price_hk.iloc[-1]['市值_亿港元']

pct_rank = (pe_valid['PE_TTM'] < curr_pe).mean() * 100
q10, q20, q50, q80 = pe_valid['PE_TTM'].quantile([0.1, 0.2, 0.5, 0.8])

snapshot = {
    "最新日期": str(price_hk.iloc[-1]['日期'].date()),
    "最新股价_HKD": round(curr_price, 2),
    "最新市值_亿港元": round(curr_mktcap_hkd, 2),
    "最新市值_亿人民币": round(curr_mktcap_hkd * 0.85, 2),
    "归母净利润TTM_亿元": round(price_hk.iloc[-1]['归母净利润TTM_亿元'], 2),
    "NonGAAP_TTM_亿元": round(price_hk.iloc[-1]['NonGAAP_TTM_亿元'], 2),
    "当前PE_TTM": round(curr_pe, 2),
    "当前NonGAAP_PE": round(curr_non_gaap_pe, 2),
    "上市以来PE历史分位数_%": round(pct_rank, 1),
    "PE_10分位": round(q10, 1),
    "PE_20分位": round(q20, 1),
    "PE_中位数": round(q50, 1),
    "PE_80分位": round(q80, 1),
}
with open(DATA / "market_snapshot.json", "w", encoding="utf-8") as f:
    json.dump(snapshot, f, ensure_ascii=False, indent=2)

print("\nMarket Snapshot:")
print(json.dumps(snapshot, ensure_ascii=False, indent=2))

# 4. 生成图表 1：股价 vs 扣非/归母净利润TTM 双Y轴图
# 标准文件名：09988_股价vs扣非净利润TTM_双Y轴.png
monthly = price_hk.set_index("日期").resample("ME").last().dropna(subset=["前复权价_HKD", "归母净利润TTM_亿元"]).reset_index()

fig, ax1 = plt.subplots(figsize=(15, 7.5), dpi=180)
ax2 = ax1.twinx()

line1, = ax1.plot(monthly["日期"], monthly["前复权价_HKD"], color=BLUE, lw=2.5, label="前复权股价（港元）")
line2, = ax2.plot(monthly["日期"], monthly["归母净利润TTM_亿元"], color=ORANGE, lw=2.5, label="点时滚动归母净利润TTM（亿元）")
line3, = ax2.plot(monthly["日期"], monthly["NonGAAP_TTM_亿元"], color=GREEN, lw=2.0, ls="--", label="点时Non-GAAP净利润TTM（亿元）")

ax2.fill_between(monthly["日期"], monthly["归母净利润TTM_亿元"], color=ORANGE, alpha=0.08, step="pre")

ax1.grid(axis="y", alpha=0.22)
ax1.spines["top"].set_visible(False)
ax1.spines["right"].set_visible(False)
ax2.spines["top"].set_visible(False)

for label in ax1.get_xticklabels() + ax1.get_yticklabels():
    label.set_fontproperties(FONT)
for label in ax2.get_yticklabels():
    label.set_fontproperties(FONT)

ax1.set_ylabel("前复权股价（港元）", fontproperties=FONT, fontsize=12)
ax2.set_ylabel("TTM净利润（人民币亿元）", fontproperties=FONT, fontsize=12)
ax1.set_title("阿里巴巴 (09988.HK)：股价 vs 滚动TTM净利润（双Y轴趋势）", fontproperties=FONT, fontsize=16, weight="bold", pad=18)
ax1.text(0.5, 1.01, "股价为月末前复权收盘价；利润自季度业绩公告次日切换（避免未来函数）", transform=ax1.transAxes,
         ha="center", va="bottom", fontproperties=FONT, fontsize=10, color="#555555")

ax1.legend([line1, line2, line3], [line1.get_label(), line2.get_label(), line3.get_label()], loc="upper right", prop=FONT, frameon=False)

last = monthly.iloc[-1]
ax1.annotate(f"现价 HK${last['前复权价_HKD']:.1f}", xy=(last["日期"], last["前复权价_HKD"]), xytext=(-10, 15), textcoords="offset points", ha="right", fontproperties=FONT, color=BLUE, fontsize=11, weight="bold")
ax2.annotate(f"TTM {last['归母净利润TTM_亿元']:.0f}亿\n(Non-GAAP {last['NonGAAP_TTM_亿元']:.0f}亿)", xy=(last["日期"], last["归母净利润TTM_亿元"]), xytext=(-10, -28), textcoords="offset points", ha="right", fontproperties=FONT, color=ORANGE, fontsize=10)

fig.tight_layout()
fig.savefig(CHARTS / "09988_股价vs扣非净利润TTM_双Y轴.png", bbox_inches="tight", facecolor="white")
plt.close(fig)
print(f"Generated: {CHARTS / '09988_股价vs扣非净利润TTM_双Y轴.png'}")

# 5. 生成图表 2：归一化对比：股价 vs 利润TTM
# 标准文件名：09988_归一化_股价vs扣非TTM.png
base_price = monthly["前复权价_HKD"].iloc[0]
base_profit = monthly["归母净利润TTM_亿元"].iloc[0]
base_nongaap = monthly["NonGAAP_TTM_亿元"].iloc[0]

monthly["股价_归一化"] = monthly["前复权价_HKD"] / base_price * 100
monthly["利润_归一化"] = monthly["归母净利润TTM_亿元"] / base_profit * 100
monthly["NonGAAP_归一化"] = monthly["NonGAAP_TTM_亿元"] / base_nongaap * 100

fig, ax = plt.subplots(figsize=(15, 7.5), dpi=180)
ax.plot(monthly["日期"], monthly["股价_归一化"], color=BLUE, lw=2.5, label=f"股价（以{monthly['日期'].iloc[0].strftime('%Y-%m')}为100）")
ax.plot(monthly["日期"], monthly["利润_归一化"], color=ORANGE, lw=2.5, label="归母净利润TTM（首期=100）")
ax.plot(monthly["日期"], monthly["NonGAAP_归一化"], color=GREEN, lw=2.0, ls="--", label="Non-GAAP净利润TTM（首期=100）")
ax.axhline(100, color=GRAY, ls=":", alpha=0.6)

ax.grid(axis="y", alpha=0.22)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

for label in ax.get_xticklabels() + ax.get_yticklabels():
    label.set_fontproperties(FONT)

ax.set_ylabel("归一化走势（首期=100）", fontproperties=FONT, fontsize=12)
ax.set_title("阿里巴巴 (09988.HK)：股价 vs 利润TTM 归一化趋势对比", fontproperties=FONT, fontsize=16, weight="bold", pad=18)
ax.text(0.5, 1.01, "直观展示股价与盈利剪刀差；股价严重滞后于基本面修复即为潜在低估信号", transform=ax.transAxes,
        ha="center", va="bottom", fontproperties=FONT, fontsize=10, color="#555555")

last_p_norm = monthly['股价_归一化'].iloc[-1]
last_prof_norm = monthly['利润_归一化'].iloc[-1]
last_ng_norm = monthly['NonGAAP_归一化'].iloc[-1]
ax.annotate(f"股价: {last_p_norm:.1f}", xy=(monthly['日期'].iloc[-1], last_p_norm), xytext=(-10, 12), textcoords="offset points", ha="right", fontproperties=FONT, color=BLUE, fontsize=11, weight="bold")
ax.annotate(f"Non-GAAP: {last_ng_norm:.1f}", xy=(monthly['日期'].iloc[-1], last_ng_norm), xytext=(-10, 10), textcoords="offset points", ha="right", fontproperties=FONT, color=GREEN, fontsize=10)
ax.annotate(f"GAAP净利: {last_prof_norm:.1f}", xy=(monthly['日期'].iloc[-1], last_prof_norm), xytext=(-10, -18), textcoords="offset points", ha="right", fontproperties=FONT, color=ORANGE, fontsize=10)

ax.legend(loc="upper right", prop=FONT, frameon=False)
fig.tight_layout()
fig.savefig(CHARTS / "09988_归一化_股价vs扣非TTM.png", bbox_inches="tight", facecolor="white")
plt.close(fig)
print(f"Generated: {CHARTS / '09988_归一化_股价vs扣非TTM.png'}")

# 6. 生成图表 3：近10年/上市以来点时 PE 区间图
pe_hist = price_hk.dropna(subset=['PE_TTM']).copy()
pe_hist['PE_TTM_CLIP'] = pe_hist['PE_TTM'].clip(lower=0, upper=60)

fig, ax = plt.subplots(figsize=(15, 7.5), dpi=180)
ax.axhspan(0, q20, color="#DCFCE7", alpha=0.75, label=f"低20%分位区间 (< {q20:.1f}x)")
ax.axhspan(q20, q80, color="#FEF3C7", alpha=0.42, label=f"中间60%公允区间 ({q20:.1f}x ~ {q80:.1f}x)")
ax.axhspan(q80, 60, color="#FEE2E2", alpha=0.45, label=f"高20%高估区间 (> {q80:.1f}x)")

ax.plot(pe_hist["日期"], pe_hist["PE_TTM_CLIP"], color=BLUE, lw=2.2, label="点时滚动PE(TTM)")
ax.plot(pe_hist["日期"], pe_hist["NonGAAP_PE"].clip(lower=0, upper=60), color=GREEN, lw=1.8, ls="--", label="Non-GAAP PE(TTM)")

ax.scatter(pe_hist["日期"].iloc[-1], min(curr_pe, 60), color=RED, s=70, zorder=5)
ax.annotate(f"当前PE {curr_pe:.1f}倍\n分位 {pct_rank:.1f}%\n(Non-GAAP {curr_non_gaap_pe:.1f}倍)",
            xy=(pe_hist["日期"].iloc[-1], min(curr_pe, 60)),
            xytext=(-15, 18), textcoords="offset points", ha="right", fontproperties=FONT, color=RED, fontsize=11, weight="bold")

ax.set_ylim(0, 60)
ax.set_ylabel("PE(TTM) 倍数", fontproperties=FONT, fontsize=12)
ax.grid(axis="y", alpha=0.22)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

for label in ax.get_xticklabels() + ax.get_yticklabels():
    label.set_fontproperties(FONT)

ax.set_title("阿里巴巴 (09988.HK)：港股上市以来点时 PE(TTM) 估值水位", fontproperties=FONT, fontsize=16, weight="bold", pad=18)
ax.text(0.5, 1.01, "未复权股价×当日汇率÷当时已披露滚动TTM每股收益；极值按60倍截断", transform=ax.transAxes,
        ha="center", va="bottom", fontproperties=FONT, fontsize=10, color="#555555")

ax.text(0.01, 0.97, f"20%分位：{q20:.1f}倍  |  中位数：{q50:.1f}倍  |  80%分位：{q80:.1f}倍",
        transform=ax.transAxes, ha="left", va="top", fontproperties=FONT, fontsize=11, color=GRAY,
        bbox={"facecolor": "white", "alpha": 0.85, "edgecolor": "none", "pad": 5})

ax.legend(prop=FONT, loc="upper right", ncol=2, frameon=False)
fig.tight_layout()
fig.savefig(CHARTS / "09988_5.2_近十年点时PE区间图.png", bbox_inches="tight", facecolor="white")
plt.close(fig)
print(f"Generated: {CHARTS / '09988_5.2_近十年点时PE区间图.png'}")

