# -*- coding: utf-8 -*-
"""重算30只代表产品跟踪误差（纯Series版本，修正DataFrame/Series广播问题）"""
import json, os
import pandas as pd
import numpy as np

base = "A股红利指数大比拼/sources"
meta = json.load(open(f"{base}/fund-nav-correct/_汇总_基金净值.json"))
idx_dir = f"{base}/performance-data-30index"

def load_idx_series(code):
    for f in os.listdir(idx_dir):
        if f.startswith(code + "_") and f.endswith(".csv"):
            df = pd.read_csv(os.path.join(idx_dir, f), encoding='utf-8-sig')
            df.columns = ["date", "close"]
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date").set_index("date")
            return df["close"].astype(float)
    return None

rows = []
for m in meta:
    ic = m["index_code"]
    idx = load_idx_series(ic)
    nav = pd.read_csv(os.path.join(base, "fund-nav-correct", m["csv_file"]), encoding='utf-8-sig')
    nav["date"] = pd.to_datetime(nav["date"])
    nav = nav.sort_values("date").set_index("date")
    if idx is None:
        rows.append({**m, "error": "无指数csv"}); continue
    r_i = idx.pct_change().dropna()
    r_n = nav["reinvested_nav"].astype(float).pct_change().dropna()
    common = r_i.index.intersection(r_n.index)
    if len(common) < 60:
        rows.append({**m, "error": f"共同交易日仅{len(common)}天"}); continue
    a, b = r_i.loc[common], r_n.loc[common]
    cum_i = (1 + a).prod() - 1
    cum_n = (1 + b).prod() - 1
    diff = b - a
    te = diff.std() * np.sqrt(252)
    years = len(common) / 252
    rows.append({
        "index_code": ic, "index_name": m["index_name"],
        "fund_code": m["code"], "fund_name": m["name"],
        "共同起点": str(common.min().date()), "共同终点": str(common.max().date()),
        "共同交易日": int(len(common)),
        "指数年化": round(((1+cum_i)**(1/years)-1)*100, 2),
        "基金年化": round(((1+cum_n)**(1/years)-1)*100, 2),
        "累计跟踪差": round((cum_n-cum_i)*100, 2),
        "年化跟踪误差": round(float(te)*100, 2),
        "error": ""
    })

out = {r["index_code"]: r for r in rows}
json.dump(out, open(f"{base}/tracking-products-verify/tracking_error.json", "w"), ensure_ascii=False, indent=1)
errs = [r for r in rows if r.get("error")]
print(f"共{len(rows)}只，出错{len(errs)}")
for r in errs: print("ERR", r["index_code"], r["index_name"], r.get("error"))
print("\n年化跟踪误差排序（小→大）：")
for r in sorted([x for x in rows if not x.get("error")], key=lambda x: x["年化跟踪误差"]):
    flag = ""
    if r["index_code"] in ("H11140","930914","931233","931722","930839","930917","CESFHY","931157"):
        flag = " [港股/沪港深]"
    print(f"{r['index_code']:>8} {r['index_name']:12s} TE={r['年化跟踪误差']:5.2f}% 累计差={r['累计跟踪差']:6.2f}pp 共{r['共同交易日']}天{flag}")
