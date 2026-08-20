#!/usr/bin/env python3
"""央企定制世代：3只指数 + 全局基准红利低波 全收益对比图（统一起点2016-12-30）。"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

BASE = Path(__file__).resolve().parents[2]
DATA = BASE / "sources" / "performance-data-30index" / "generation-full-history"
OUT_DIR = BASE / "01_主报告" / "世代对比图"
OUT_DIR.mkdir(parents=True, exist_ok=True)

START = pd.Timestamp("2016-12-30")
END = pd.Timestamp("2026-08-07")

plt.rcParams["font.sans-serif"] = ["PingFang SC", "Heiti SC", "STHeiti", "Arial Unicode MS", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

INDICES = [
    ("931132", "诚通央企红利", "#c0392b"),
    ("931722", "国新港股通央企红利", "#2e86c1"),
    ("932039", "央企股东回报", "#27ae60"),
]
BENCH = ("H30269", "红利低波", "#7f8c8d")


def load(code: str, name: str) -> pd.Series:
    df = pd.read_csv(DATA / f"{code}_{name}_基日至今.csv", dtype={"date": str})
    s = df.set_index("date")["close"].astype(float)
    s.index = pd.to_datetime(s.index, format="%Y%m%d")
    s = s[~s.index.duplicated(keep="last")].sort_index()
    return s[s.index >= START]


def mdd(s: pd.Series) -> float:
    return float((s / s.cummax() - 1).min())


def main() -> None:
    bench = load(*BENCH[:2])
    bench_n = bench / bench.iloc[0]
    years = (END - START).days / 365.2425
    bench_ret = bench_n.iloc[-1] - 1
    bench_cagr = bench_n.iloc[-1] ** (1 / years) - 1

    ye_b = bench_n.resample("YE").last().pct_change().dropna()
    be = {int(t.year): float(v) for t, v in ye_b.items()}

    fig, ax = plt.subplots(figsize=(13, 6), dpi=150)
    ax.plot(bench_n.index, bench_n.values, color=BENCH[2], lw=0.8, ls="--",
            label=f"红利低波(基准) {bench_ret:.0%}")

    rows = []
    for code, name, color in INDICES:
        s = load(code, name)
        sn = s / s.iloc[0]
        ret = sn.iloc[-1] - 1
        cagr = sn.iloc[-1] ** (1 / years) - 1
        ye_x = sn.resample("YE").last().pct_change().dropna()
        xe = {int(t.year): float(v) for t, v in ye_x.items()}
        yrs = sorted(set(xe) & set(be))
        win = sum(1 for y in yrs if xe[y] > be[y])
        rows.append({
            "name": name, "code": code, "ret": ret, "cagr": cagr,
            "win": f"{win}/{len(yrs)}", "mdd": mdd(sn),
            "excess": ret - bench_ret,
        })
        ax.plot(sn.index, sn.values, color=color, lw=0.8, label=f"{name} {ret:.0%}")

    order = sorted(rows, key=lambda r: -r["ret"])
    handles, labels = ax.get_legend_handles_labels()
    h_b, l_b = handles[0], labels[0]
    rest = {lbl: h for lbl, h in zip(labels, handles) if lbl != l_b}
    new_h = [h_b] + [rest[f"{r['name']} {r['ret']:.0%}"] for r in order]
    new_l = [l_b] + [f"{r['name']} {r['ret']:.0%}" for r in order]
    ax.legend(new_h, new_l, loc="upper left", fontsize=9)

    ax.set_title("央企定制世代 vs 红利低波（全局基准）：全收益对比（2016-12-30=1）", fontsize=12)
    ax.grid(alpha=0.25)
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.tight_layout()
    out = OUT_DIR / "央企定制世代_vs_红利低波.png"
    fig.savefig(out)
    plt.close(fig)

    print(f"基准红利低波: 总收益{bench_ret:.1%} CAGR{bench_cagr:.2%}")
    for r in sorted(rows, key=lambda x: -x["ret"]):
        print(f"{r['name']:<10} 总{r['ret']:>7.1%} CAGR{r['cagr']:>7.2%} 超额{(r['excess'])*100:+.1f}pp 年度胜{r['win']} 回撤{r['mdd']:.1%}")

    with open(OUT_DIR / "央企定制世代对比汇总.json", "w", encoding="utf-8") as f:
        json.dump({"bench": {"name": "红利低波", "ret": bench_ret, "cagr": bench_cagr}, "indices": rows},
                  f, ensure_ascii=False, indent=2)
    print(f"\n图: {out}")


if __name__ == "__main__":
    main()
