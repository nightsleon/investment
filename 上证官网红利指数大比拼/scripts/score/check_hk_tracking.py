# -*- coding: utf-8 -*-
"""验证港股ETF跟踪误差：检查日期错位与汇率影响"""
import pandas as pd, numpy as np
base = "A股红利指数大比拼/sources"

def load_pair(fund_fn, idx_fn):
    nav = pd.read_csv(f"{base}/fund-nav-correct/{fund_fn}", encoding='utf-8-sig')
    idx = pd.read_csv(f"{base}/performance-data-30index/{idx_fn}", encoding='utf-8-sig')
    idx.columns = ["date","close"]
    nav["date"] = pd.to_datetime(nav["date"]); idx["date"] = pd.to_datetime(idx["date"])
    nav = nav.set_index("date").sort_index(); idx = idx.set_index("date").sort_index()
    common = nav.index.intersection(idx.index)
    r_n = nav.loc[common,"reinvested_nav"].pct_change().dropna()
    r_i = idx.loc[common,"close"].pct_change().dropna()
    both = pd.concat([r_n.rename("nav"), r_i.rename("idx")], axis=1).dropna()
    return both

for name, fund_fn, idx_fn in [
    ("513530 港股通高股息", "513530_华泰柏瑞港股通高股息ETF_净值.csv", "930914_港股通高股息_全收益.csv"),
    ("513910 港股通央企红利", "513910_华夏中证港股通央企红利ETF_净值.csv", "931233_港股通央企红利_全收益.csv"),
]:
    both = load_pair(fund_fn, idx_fn)
    print(f"== {name} 共{len(both)}天 ==")
    for lag in [-2,-1,0,1,2]:
        c = both["nav"].corr(both["idx"].shift(lag))
        print(f"  lag={lag}: corr={c:.4f}")
    diff = both["nav"]-both["idx"]
    print(f"  diff mean={diff.mean()*10000:.2f}bp std={diff.std()*100:.2f}%")
