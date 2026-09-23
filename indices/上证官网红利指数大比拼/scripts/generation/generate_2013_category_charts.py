#!/usr/bin/env python3
"""2013前世代：按四分类各生成一张 vs 红利低波基准 全收益对比图（统一起点2013-12-31）。"""
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
END = pd.Timestamp("2026-08-07")

plt.rcParams["font.sans-serif"] = ["PingFang SC", "Heiti SC", "STHeiti", "Arial Unicode MS", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

BENCH = ("H30269", "红利低波", "#7f8c8d")
PALETTE = ["#c0392b", "#2e86c1", "#27ae60", "#8e44ad", "#d35400", "#16a085"]

CATEGORIES = [
    ("稳定跑赢", "稳定跑赢型（超额多且逐年常胜）", [
        ("931446", "东证红利低波"), ("930955", "红利低波100")]),
    ("高超额但依赖时段", "高超额但依赖个别时段型", [
        ("932315", "中证红利质量"), ("931468", "红利质量"),
        ("932305", "智选高股息"), ("932422", "A500红利低波")]),
    ("与基准打平", "与基准打平型（图上两线纠缠）", [
        ("H30094", "消费红利"), ("000922", "中证红利"), ("H11140", "香港红利")]),
    ("稳定跑输", "稳定跑输型", [
        ("000015", "上证红利"), ("000825", "央企红利")]),
]


def load(code: str, name: str) -> pd.Series:
    df = pd.read_csv(DATA / f"{code}_{name}_基日至今.csv", dtype={"date": str})
    s = df.set_index("date")["close"].astype(float)
    s.index = pd.to_datetime(s.index, format="%Y%m%d")
    s = s[~s.index.duplicated(keep="last")].sort_index()
    return s[s.index >= START]


def main() -> None:
    bench = load(*BENCH[:2])
    bench_n = bench / bench.iloc[0]
    bench_ret = bench_n.iloc[-1] - 1
    summary = {}

    for key, title, members in CATEGORIES:
        fig, ax = plt.subplots(figsize=(13, 6), dpi=150)
        ax.plot(bench_n.index, bench_n.values, color=BENCH[2], lw=0.8, ls="--",
                label=f"红利低波(基准) {bench_ret:.0%}")
        rows = []
        for code, name in members:
            s = load(code, name)
            sn = s / s.iloc[0]
            ret = sn.iloc[-1] - 1
            rows.append({"name": name, "ret": ret})
            ax.plot(sn.index, sn.values, color=PALETTE[len(rows) - 1], lw=0.8,
                    label=f"{name} {ret:.0%}")
        order = sorted(rows, key=lambda r: -r["ret"])
        handles, labels = ax.get_legend_handles_labels()
        h_b, l_b = handles[0], labels[0]
        rest = {lbl: h for lbl, h in zip(labels, handles) if lbl != l_b}
        new_h = [h_b] + [rest[f"{r['name']} {r['ret']:.0%}"] for r in order]
        new_l = [l_b] + [f"{r['name']} {r['ret']:.0%}" for r in order]
        ax.legend(new_h, new_l, loc="upper left", fontsize=9)
        ax.set_title(f"{title} vs 红利低波（全局基准）：全收益对比（2013-12-31=1）", fontsize=12)
        ax.grid(alpha=0.25)
        ax.xaxis.set_major_locator(mdates.YearLocator(2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        fig.tight_layout()
        out = OUT_DIR / f"2013前_{key}_vs_红利低波.png"
        fig.savefig(out)
        plt.close(fig)
        summary[key] = [{"name": r["name"], "ret": r["ret"]} for r in order]
        print(f"✓ {key}: " + ", ".join(f"{r['name']}{r['ret']:.0%}" for r in order))

    with open(OUT_DIR / "2013前分类对比汇总.json", "w", encoding="utf-8") as f:
        json.dump({"bench": {"name": "红利低波", "ret": bench_ret}, "categories": summary},
                  f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
