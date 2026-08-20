#!/usr/bin/env python3
"""世代回溯报告（组内统一最晚基日版）：计算三组指标，含近3年年化波动。"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[2]
DATA_DIR = BASE / "sources" / "performance-data-30index" / "generation-full-history"
OUT = DATA_DIR / "世代回溯统一基日指标.json"

# 组内统一开始日期（该组最晚基日）
GROUP_START = {
    "2013前": "20131231",
    "2014-11": "20141114",
    "2016末": "20161230",
}
NEAR3_START = "20230808"  # 近3年窗口起点（2023-08-08）


def max_drawdown(s: pd.Series):
    rm = s.cummax()
    dd = s / rm - 1
    ti = dd.idxmin()
    pi = s.loc[:ti].idxmax()
    rec = s.loc[ti:][s.loc[ti:] >= s.loc[pi]]
    return float(dd.loc[ti]), pi, ti, (rec.index[0] if len(rec) else None)


def daily_ann_vol(s: pd.Series) -> float:
    r = s.pct_change().dropna()
    return r.std(ddof=1) * math.sqrt(242)


def calc(code: str, name: str, s_all: pd.Series, start: str, group: str, publish: str, basic: str) -> dict:
    s = s_all[s_all.index >= pd.Timestamp(start)]
    s = s[~s.index.duplicated(keep="last")].sort_index()
    st, en = s.index[0], s.index[-1]
    days = (en - st).days
    total_ret = s.iloc[-1] / s.iloc[0] - 1
    cagr = (s.iloc[-1] / s.iloc[0]) ** (365.2425 / days) - 1

    vol_full = daily_ann_vol(s)

    # 近3年波动
    s3 = s_all[s_all.index >= pd.Timestamp(NEAR3_START)]
    vol3 = daily_ann_vol(s3)

    rv = cagr / vol_full

    mdd, peak, trough, rec = max_drawdown(s)

    ye = s.resample("YE").last()
    annual = ye.pct_change().dropna()
    sy, ey = st.year + 1, en.year - 1
    comp = annual[(annual.index.year >= sy) & (annual.index.year <= ey)]
    win = f"{int((comp > 0).sum())}/{len(comp)}" if len(comp) else "N/A"

    monthly = s.resample("ME").last()
    roll3 = ((monthly / monthly.shift(36)) ** (1 / 3) - 1).dropna()
    roll3_med = float(roll3.median()) if len(roll3) else None

    pub = pd.Timestamp(publish)
    bt_ratio = None
    if pub > st:
        bt_ratio = (pub - st).days / days

    return {
        "price_code": code, "name": name, "group": group,
        "basic_date": basic, "publish_date": publish,
        "start": st.date().isoformat(), "end": en.date().isoformat(),
        "years": round(days / 365.2425, 2),
        "total_return": total_ret, "cagr": cagr,
        "vol_full": vol_full, "vol_3y": vol3,
        "rv": rv, "max_drawdown": mdd,
        "peak": peak.date().isoformat(), "trough": trough.date().isoformat(),
        "recovery": rec.date().isoformat() if rec is not None else None,
        "win_rate": win, "complete_years": len(comp),
        "worst_year": float(comp.min()) if len(comp) else None,
        "rolling3_median": roll3_med,
        "backtest_ratio": bt_ratio,
        "annual_data": {int(t.year): float(v) for t, v in comp.items()},
    }


def group_of(basic: str) -> str:
    for g, gs in GROUP_START.items():
        if basic.replace("-", "") <= gs:
            return g
    return "?"


def main() -> None:
    manifest = json.load(open(DATA_DIR / "manifest.json", encoding="utf-8"))
    out = []
    for m in manifest:
        df = pd.read_csv(DATA_DIR / f"{m['price_code']}_{m['name']}_基日至今.csv", dtype={"date": str})
        s = df.set_index("date")["close"].astype(float)
        s.index = pd.to_datetime(s.index, format="%Y%m%d")
        s = s[~s.index.duplicated(keep="last")].sort_index()
        g = group_of(m["basic_date"])
        gs = GROUP_START[g]
        out.append(calc(m["price_code"], m["name"], s, gs, g, m["publish_date"], m["basic_date"]))
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    for g in GROUPS_ORDER:
        rows = sorted([o for o in out if o["group"] == g], key=lambda x: -x["total_return"])
        print(f"\n===== {g} 起点统一{GROUP_START[g]} ({len(rows)}只) =====")
        for o in rows:
            r3 = f"{o['rolling3_median']:.2%}" if o["rolling3_median"] is not None else "N/A"
            print(f"{o['name']:<10} 总{o['total_return']:>8.1%} CAGR{o['cagr']:>7.2%} "
                  f"全程波动{o['vol_full']:>6.2%} 近3年波动{o['vol_3y']:>6.2%} 回撤{o['max_drawdown']:>7.2%} "
                  f"R/V{o['rv']:>5.2f} 胜率{o['win_rate']:>5} 滚3{r3:>8}")


GROUPS_ORDER = ["2013前", "2014-11", "2016末"]

if __name__ == "__main__":
    main()
