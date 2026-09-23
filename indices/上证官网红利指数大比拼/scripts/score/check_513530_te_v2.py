# -*- coding: utf-8 -*-
"""精确复核513530与930914的日收益差"""
import pandas as pd, numpy as np
base = "A股红利指数大比拼/sources"

nav = pd.read_csv(f"{base}/fund-nav-correct/513530_华泰柏瑞港股通高股息ETF_净值.csv", encoding='utf-8-sig')
idx = pd.read_csv(f"{base}/performance-data-30index/930914_港股通高股息_全收益.csv", encoding='utf-8-sig')
idx.columns = ["date","close"]
nav["date"] = pd.to_datetime(nav["date"]); idx["date"] = pd.to_datetime(idx["date"])
nav = nav.set_index("date").sort_index(); idx = idx.set_index("date").sort_index()

r_i = idx["close"].astype(float).pct_change().dropna()
r_n = nav["reinvested_nav"].astype(float).pct_change().dropna()
common = r_i.index.intersection(r_n.index)
a, b = r_i.loc[common], r_n.loc[common]
diff = b - a
print("共同交易日:", len(common))
print("diff std (日):", diff.std())
print("年化TE (sqrt252):", diff.std()*np.sqrt(252)*100)
print("diff 绝对值>2% 的天数:", (diff.abs()>0.02).sum())
print("diff 绝对值>1% 的天数:", (diff.abs()>0.01).sum())
print("diff 最大的5天:")
print(diff.abs().nlargest(5))
print("\n3070HK 币种检查——净值首值:", nav["unit_nav"].iloc[0], "（港元计价ETF，2012年面值应为10港元）")
print("3070HK reinvested_nav 首尾:", nav["reinvested_nav"].iloc[0], "->", nav["reinvested_nav"].iloc[-1])
