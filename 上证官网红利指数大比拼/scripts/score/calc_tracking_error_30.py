# -*- coding: utf-8 -*-
"""计算30只指数代表产品的跟踪误差（分红再投净值 vs 指数全收益）"""
import json, os
import pandas as pd
import numpy as np

base = "A股红利指数大比拼/sources"
meta = json.load(open(f"{base}/fund-nav-correct/_汇总_基金净值.json"))
idx_dir = f"{base}/performance-data-30index"

def load_idx(code):
    # 找到对应指数csv
    for f in os.listdir(idx_dir):
        if f.startswith(code + "_") and f.endswith(".csv"):
            df = pd.read_csv(os.path.join(idx_dir, f), encoding='utf-8-sig')
            df.columns = ["date", "close"]
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date").set_index("date")
            return df["close"]
    return None

def load_nav(csv_file):
    df = pd.read_csv(os.path.join(base, "fund-nav-correct", csv_file), encoding='utf-8-sig')
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").set_index("date")
    return df

rows = []
for m in meta:
    ic = m["index_code"]
    idx = load_idx(ic)
    nav = load_nav(m["csv_file"])
    if idx is None:
        rows.append({**m, "error": "无指数csv"})
        continue
    # 对齐共同区间
    common_start = max(idx.index.min(), nav.index.min())
    common_end = min(idx.index.max(), nav.index.max())
    if common_start >= common_end:
        rows.append({**m, "error": "无共同区间"})
        continue
    idx_c = idx.loc[common_start:common_end]
    nav_c = nav["reinvested_nav"].loc[common_start:common_end]
    # 日收益率
    r_idx = idx_c.pct_change().dropna()
    r_nav = nav_c.pct_change().dropna()
    # 共同交易日
    common = r_idx.index.intersection(r_nav.index)
    if len(common) < 60:
        rows.append({**m, "error": f"共同交易日仅{len(common)}天"})
        continue
    r_i = r_idx.loc[common]
    r_n = r_nav.loc[common]
    # 跟踪差（累计）：指数与基金区间累计收益差
    cum_idx = (1 + r_i).prod() - 1
    cum_nav = (1 + r_n).prod() - 1
    td = cum_nav - cum_idx  # 基金相对指数的累计超额（负数=基金跑输）
    # 跟踪误差：日收益差标准差年化
    diff = r_n - r_i
    te_annual = diff.std() * np.sqrt(252)
    # 年化收益
    years = len(common) / 252
    cagr_idx = (1 + cum_idx) ** (1 / years) - 1
    cagr_nav = (1 + cum_nav) ** (1 / years) - 1
    rows.append({
        "index_code": ic, "index_name": m["index_name"],
        "fund_code": m["code"], "fund_name": m["name"],
        "共同起点": str(common_start.date()), "共同终点": str(common_end.date()),
        "共同交易日": len(common),
        "指数年化": round(cagr_idx * 100, 2), "基金年化": round(cagr_nav * 100, 2),
        "累计跟踪差": round(td * 100, 2),  # pp, 基金-指数
        "年化跟踪误差": round(te_annual * 100, 2),
        "error": ""
    })

out = {r["index_code"]: r for r in rows}
json.dump(out, open(f"{base}/tracking-products-verify/tracking_error.json", "w"), ensure_ascii=False, indent=1)
errs = [r for r in rows if r.get("error")]
print(f"共{len(rows)}只，出错{len(errs)}")
for r in errs: print("ERR", r["index_code"], r["index_name"], r.get("error"))
print("\n跟踪误差排序（年化，小→大）：")
for r in sorted([x for x in rows if not x.get("error")], key=lambda x: x["年化跟踪误差"]):
    print(f"{r['index_code']:>8} {r['index_name']:12s} TE={r['年化跟踪误差']:5.2f}% 累计差={r['累计跟踪差']:6.2f}pp 共{r['共同交易日']}天")
