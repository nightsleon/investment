# -*- coding: utf-8 -*-
"""验证3070HK(港元) vs H11140(人民币) 的TE来源：汇率噪音 vs 真实跟踪"""
import pandas as pd, numpy as np
base = "A股红利指数大比拼/sources"

nav = pd.read_csv(f"{base}/fund-nav-correct/3070HK_中国平安CSI香港高息股ETF_净值.csv", encoding='utf-8-sig')
idx = pd.read_csv(f"{base}/performance-data-30index/H11140_香港红利_全收益.csv", encoding='utf-8-sig')
idx.columns = ["date","close"]
nav["date"] = pd.to_datetime(nav["date"]); idx["date"] = pd.to_datetime(idx["date"])
nav = nav.set_index("date").sort_index(); idx = idx.set_index("date").sort_index()

# 共同区间
common_start = max(idx.index.min(), nav.index.min())
common_end = min(idx.index.max(), nav.index.max())
r_n = nav.loc[common_start:common_end,"reinvested_nav"].pct_change().dropna()
r_i = idx.loc[common_start:common_end,"close"].pct_change().dropna()
common = r_n.index.intersection(r_i.index)
a, b = r_i.loc[common], r_n.loc[common]
diff = b - a

print(f"共同区间: {common.min().date()} ~ {common.max().date()}  共{len(common)}天")
print(f"3070HK 净值币种: 港元（Yahoo前复权，首值10.52=港元累计净值）")
print(f"H11140 指数币种: 人民币全收益")
print()
print(f"日收益相关性: lag0={b.corr(a):.4f}")
print(f"日收益差 std: {diff.std()*100:.3f}% → 年化TE {diff.std()*np.sqrt(252)*100:.2f}%")
print(f"diff 均值: {diff.mean()*100:.3f}%（系统性偏移，若为汇率单边走势则偏大）")
print()
# 如果汇率主导，diff应与港币/人民币汇率日收益高度相关。用 USDCNH 代理？先看 diff 的走势特征
print("diff 按年度分解（日收益差的均值，单位%）:")
d2 = diff.to_frame("d")
d2["year"] = d2.index.year
print(d2.groupby("year")["d"].agg(["mean","std"]).round(4)*100)
