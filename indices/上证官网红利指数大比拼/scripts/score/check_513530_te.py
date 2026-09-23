# -*- coding: utf-8 -*-
"""复查513530 TE计算，找出不一致原因"""
import pandas as pd, numpy as np
base = "A股红利指数大比拼/sources"

nav = pd.read_csv(f"{base}/fund-nav-correct/513530_华泰柏瑞港股通高股息ETF_净值.csv", encoding='utf-8-sig')
idx = pd.read_csv(f"{base}/performance-data-30index/930914_港股通高股息_全收益.csv", encoding='utf-8-sig')
idx.columns = ["date","close"]
nav["date"] = pd.to_datetime(nav["date"]); idx["date"] = pd.to_datetime(idx["date"])
nav = nav.set_index("date").sort_index(); idx = idx.set_index("date").sort_index()

common_start = max(idx.index.min(), nav.index.min())
common_end = min(idx.index.max(), nav.index.max())
idx_c = idx.loc[common_start:common_end]
nav_c = nav["reinvested_nav"].loc[common_start:common_end]
r_idx = idx_c.pct_change().dropna()
r_nav = nav_c.pct_change().dropna()
common = r_idx.index.intersection(r_nav.index)
r_i = r_idx.loc[common]; r_n = r_nav.loc[common]
diff = r_n - r_i
print("共同交易日:", len(common))
print("diff std:", diff.std(), "年化TE:", diff.std()*np.sqrt(252)*100)
print("diff max:", diff.max(), "min:", diff.min())
# 看极端值
print("|diff|>1%的天数:", (diff.abs()>0.01).sum())
print(diff.abs().nlargest(5))
