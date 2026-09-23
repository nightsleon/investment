#!/usr/bin/env python3
"""世代回溯：2013前组每只指数 vs 红利低波(H30269) 全收益对比图（统一起点2013-12-31，归一化）。"""
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

START = pd.Timestamp("2013-12-31")
BENCH = "红利低波"
END = pd.Timestamp("2026-08-07")

plt.rcParams["font.sans-serif"] = ["PingFang SC", "Heiti SC", "STHeiti", "Arial Unicode MS", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

GROUP13 = [
    ("932315", "中证红利质量"), ("931446", "东证红利低波"), ("931468", "红利质量"),
    ("932305", "智选高股息"), ("932422", "A500红利低波"), ("H30094", "消费红利"),
    ("930955", "红利低波100"), ("H11140", "香港红利"), ("930740", "300红利低波"),
    ("000922", "中证红利"), ("000151", "上国红利"), ("H30270", "红利价值"),
    ("000015", "上证红利"), ("000825", "央企红利"), ("H30269", "红利低波"),
]


def load(code: str, name: str) -> pd.Series:
    df = pd.read_csv(DATA / f"{code}_{name}_基日至今.csv", dtype={"date": str})
    s = df.set_index("date")["close"].astype(float)
    s.index = pd.to_datetime(s.index, format="%Y%m%d")
    s = s[~s.index.duplicated(keep="last")].sort_index()
    return s


def main() -> None:
    bench = load("H30269", "红利低波")
    bench = bench[bench.index >= START]
    bench_n = bench / bench.iloc[0]

    summary = []
    for code, name in GROUP13:
        if name == BENCH:
            continue
        s = load(code, name)
        s = s[s.index >= START]
        sn = s / s.iloc[0]

        # 指标
        years = (sn.index[-1] - sn.index[0]).days / 365.2425
        ret_x = sn.iloc[-1] - 1
        ret_b = bench_n.iloc[-1] - 1
        cagr_x = (sn.iloc[-1]) ** (1 / years) - 1
        cagr_b = (bench_n.iloc[-1]) ** (1 / years) - 1
        # 年度胜负对比
        ye_x = sn.resample("YE").last().pct_change().dropna()
        ye_b = bench_n.resample("YE").last().pct_change().dropna()
        xe = {int(t.year): float(v) for t, v in ye_x.items()}
        be = {int(t.year): float(v) for t, v in ye_b.items()}
        yrs = sorted(set(xe) & set(be))
        win_yrs = [y for y in yrs if xe[y] > be[y]]
        # 最大回撤差
        def mdd(s_):
            dd = s_ / s_.cummax() - 1
            return dd.min()
        summary.append({
            "name": name, "code": code,
            "ret_x": ret_x, "ret_b": ret_b,
            "cagr_x": cagr_x, "cagr_b": cagr_b,
            "win_years": f"{len(win_yrs)}/{len(yrs)}",
            "mdd_x": mdd(sn), "mdd_b": mdd(bench_n),
        })

        # 画图
        fig, ax = plt.subplots(figsize=(13, 6), dpi=150)
        ax.plot(sn.index, sn.values, color="#c0392b", lw=0.8, label=f"{name} {ret_x:.0%}")
        ax.plot(bench_n.index, bench_n.values, color="#7f8c8d", lw=0.8, ls="--",
                label=f"红利低波(基准) {ret_b:.0%}")
        ax.axhline(1, color="#bdc3c7", lw=0.5)
        # 线尾标注
        ax.annotate(f"{name} {ret_x:.0%}", xy=(sn.index[-1], sn.iloc[-1]), fontsize=9, color="#c0392b", va="center")
        ax.annotate(f"红利低波 {ret_b:.0%}", xy=(bench_n.index[-1], bench_n.iloc[-1]), fontsize=9, color="#7f8c8d", va="center")
        ax.set_title(f"{name}（{code}） vs 红利低波（H30269）全收益对比（2013-12-31=1）", fontsize=12)
        ax.legend(loc="upper left", fontsize=9)
        ax.grid(alpha=0.25)
        ax.xaxis.set_major_locator(mdates.YearLocator(2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        fig.tight_layout()
        fig.savefig(OUT_DIR / f"{code}_{name}_vs_红利低波.png")
        plt.close(fig)
        print(f"✓ {name}: 总收益{ret_x:.1%} vs 基准{ret_b:.1%}, CAGR差{(cagr_x-cagr_b)*100:+.1f}pp, 年度胜{len(win_yrs)}/{len(yrs)}")

    with open(OUT_DIR / "对比汇总.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\n输出目录: {OUT_DIR}")


if __name__ == "__main__":
    main()
