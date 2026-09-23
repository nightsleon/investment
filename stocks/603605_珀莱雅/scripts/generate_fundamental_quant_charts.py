#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate standardized charts for investment report chapter:
四、好公司·定量：利润是不是真，增长是否健康？

Input defaults assume company package structure:
  {base}/data/annual_core.csv
  {base}/data/product_structure.csv   optional
  {base}/data/quarterly_profit.csv    optional
  {base}/charts/

The script is intentionally conservative:
- Missing fields skip the relevant chart instead of inventing data.
- Titles are neutral; conclusions belong in report text.
- Asset-liability ratio axis starts at 0 to avoid visual exaggeration.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, Optional

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties


COLORS = {
    "blue": "#2563EB",
    "blue_light": "#93C5FD",
    "orange": "#F97316",
    "orange_light": "#FDBA74",
    "green": "#16A34A",
    "green_light": "#86EFAC",
    "red": "#DC2626",
    "red_light": "#FCA5A5",
    "purple": "#7C3AED",
    "yellow_light": "#FDE68A",
    "gray": "#64748B",
    "gray_light": "#CBD5E1",
}


def detect_font() -> FontProperties:
    candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
    ]
    for fp in candidates:
        if Path(fp).exists():
            return FontProperties(fname=fp)
    return FontProperties()


FONT = detect_font()
plt.rcParams["axes.unicode_minus"] = False


def style(ax):
    ax.grid(axis="y", alpha=0.22)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontproperties(FONT)


def set_title(ax, text: str, sub: Optional[str] = None):
    ax.set_title(text, fontproperties=FONT, fontsize=17, weight="bold", pad=16)
    if sub:
        ax.text(
            0.5, 1.01, sub,
            transform=ax.transAxes, ha="center", va="bottom",
            fontproperties=FONT, fontsize=10, color="#555555",
        )


def save(fig, out_dir: Path, filename: str):
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / filename
    fig.savefig(out, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(out)


def first_existing(df: pd.DataFrame, candidates: Iterable[str]) -> Optional[str]:
    for col in candidates:
        if col in df.columns:
            return col
    return None


def require(df: pd.DataFrame, mapping: dict[str, list[str]], chart_name: str) -> Optional[dict[str, str]]:
    resolved = {}
    missing = []
    for key, candidates in mapping.items():
        col = first_existing(df, candidates)
        if col is None:
            missing.append(f"{key}({','.join(candidates)})")
        else:
            resolved[key] = col
    if missing:
        print(f"SKIP {chart_name}: missing columns: {'; '.join(missing)}")
        return None
    return resolved


def read_annual(path: Path, start_year: Optional[int], end_year: Optional[int]) -> pd.DataFrame:
    df = pd.read_csv(path)
    # If first unnamed/index-like column contains dates, keep it as date source.
    if "年份" in df.columns:
        year = df["年份"].astype(str).str.extract(r"(\d{4})")[0].astype(int)
    elif "date" in df.columns:
        year = pd.to_datetime(df["date"]).dt.year
    elif "日期" in df.columns:
        year = pd.to_datetime(df["日期"]).dt.year
    else:
        first = df.columns[0]
        maybe_year = df[first].astype(str).str.extract(r"(\d{4})")[0]
        if maybe_year.notna().sum() >= max(1, len(df) // 2):
            year = maybe_year.astype(int)
        else:
            raise ValueError("annual file needs 年份/date/日期 or first column containing year/date")
    df = df.copy()
    df["__year"] = year
    if start_year is not None:
        df = df[df["__year"] >= start_year]
    if end_year is not None:
        df = df[df["__year"] <= end_year]
    df = df.sort_values("__year").reset_index(drop=True)
    if df.empty:
        raise ValueError("annual data is empty after year filtering")
    return df


def years_x(df: pd.DataFrame):
    years = df["__year"].astype(str).tolist()
    x = np.arange(len(years))
    return years, x


def as_pct(series: pd.Series) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    # Accept both 0.156 and 15.6; if median abs <= 1.5, treat as ratio.
    valid = s.dropna().abs()
    if len(valid) and valid.median() <= 1.5:
        return s * 100
    return s


def plot_roe_dupont(df: pd.DataFrame, out_dir: Path, code: str, company: str):
    cols = require(df, {
        "roe": ["简单ROE", "ROE", "净资产收益率", "roe"],
        "net_margin": ["净利率", "销售净利率", "net_margin"],
        "asset_turnover": ["总资产周转率", "asset_turnover"],
        "equity_multiplier": ["权益乘数", "equity_multiplier"],
    }, "4.1 ROE/DuPont")
    if not cols:
        return
    years, x = years_x(df)
    roe = as_pct(df[cols["roe"]])
    fig = plt.figure(figsize=(15, 8), dpi=180)
    gs = fig.add_gridspec(2, 1, height_ratios=[1.15, 1], hspace=0.34)
    ax0 = fig.add_subplot(gs[0])
    ax0.bar(x, roe, width=0.46, color=COLORS["blue_light"])
    ax0.axhline(0, color="#999999", lw=0.8)
    ax0.set_xticks(x); ax0.set_xticklabels(years, fontproperties=FONT)
    ax0.set_ylabel("ROE %", fontproperties=FONT)
    style(ax0)
    set_title(ax0, f"{company}：ROE与杜邦三因子趋势", "杜邦三因子按首年=100归一化；只比较趋势，不比较绝对高低")
    span = max(roe.max() - min(0, roe.min()), 1)
    for i, v in enumerate(roe):
        if pd.notna(v):
            ax0.text(i, v + span * 0.025, f"{v:.1f}%", ha="center", va="bottom", fontproperties=FONT, fontsize=9)

    ax1 = fig.add_subplot(gs[1])
    metrics = [
        ("净利率", cols["net_margin"], "%", COLORS["red"]),
        ("总资产周转率", cols["asset_turnover"], "次", COLORS["green"]),
        ("权益乘数", cols["equity_multiplier"], "倍", COLORS["purple"]),
    ]
    offsets = {"净利率": 0, "总资产周转率": -10, "权益乘数": 10}
    for label, col, unit, color in metrics:
        raw = as_pct(df[col]) if unit == "%" else pd.to_numeric(df[col], errors="coerce")
        if raw.dropna().empty or raw.dropna().iloc[0] == 0:
            continue
        norm = raw / raw.dropna().iloc[0] * 100
        ax1.plot(x, norm, marker="o", color=color, lw=2.4, label=f"{label}（首年=100）")
        last_idx = norm.last_valid_index()
        if last_idx is not None:
            actual = f"{raw.iloc[last_idx]:.1f}{unit}" if unit == "%" else f"{raw.iloc[last_idx]:.2f}{unit}"
            ax1.annotate(f"{label} {actual}", xy=(x[last_idx], norm.iloc[last_idx]), xytext=(12, offsets[label]),
                         textcoords="offset points", fontproperties=FONT, color=color, va="center", fontsize=10)
    ax1.axhline(100, color="#999999", lw=0.9, ls="--", alpha=0.8)
    ax1.set_xticks(x); ax1.set_xticklabels(years, fontproperties=FONT)
    ax1.set_ylabel("归一化（首年=100）", fontproperties=FONT)
    ax1.set_xlim(x[0] - 0.35, x[-1] + 0.95)
    style(ax1)
    ax1.legend(prop=FONT, loc="upper left", ncol=3, frameon=False)
    fig.tight_layout()
    save(fig, out_dir, f"{code}_4.1_ROE与杜邦三因子趋势图.png")


def latest_ttm_from_quarterly(path: Optional[Path], label: Optional[str]) -> Optional[float]:
    if not path or not path.exists():
        return None
    q = pd.read_csv(path)
    ttm_col = first_existing(q, ["profit_ttm_yi", "利润TTM_亿元", "净利润TTM", "ttm_profit"])
    if not ttm_col:
        return None
    if label and "quarter_label" in q.columns and (q["quarter_label"].astype(str) == label).any():
        return float(pd.to_numeric(q.loc[q["quarter_label"].astype(str) == label, ttm_col], errors="coerce").dropna().iloc[-1])
    return float(pd.to_numeric(q[ttm_col], errors="coerce").dropna().iloc[-1])


def plot_profit(df: pd.DataFrame, out_dir: Path, code: str, company: str, profit_col_arg: Optional[str], quarterly: Optional[Path], latest_label: Optional[str]):
    profit_col = profit_col_arg if profit_col_arg in df.columns else first_existing(df, ["股东应占溢利", "扣非净利润", "净利润", "归母净利润", "profit"])
    if not profit_col:
        print("SKIP 4.2 Profit: missing profit column")
        return
    years, _ = years_x(df)
    profit_values = pd.to_numeric(df[profit_col], errors="coerce").tolist()
    labels = years[:]
    latest_ttm = latest_ttm_from_quarterly(quarterly, latest_label)
    if latest_ttm is not None:
        labels.append(f"{latest_label or '最新'}\nTTM")
        profit_values.append(latest_ttm)
    x = np.arange(len(labels))
    fig, ax1 = plt.subplots(figsize=(15, 7.5), dpi=180)
    ax2 = ax1.twinx()
    bar_colors = [COLORS["orange_light"]] * len(years) + ([COLORS["red_light"]] if latest_ttm is not None else [])
    bars = ax1.bar(x, profit_values, width=0.46, color=bar_colors, label=f"{profit_col}/TTM（亿元）")
    ax1.axhline(0, color="#999999", lw=0.8)
    ax1.set_xticks(x); ax1.set_xticklabels(labels, fontproperties=FONT)
    ax1.set_ylabel("亿元", fontproperties=FONT)
    style(ax1)
    yoy = list(pd.Series(profit_values[:len(years)]).pct_change() * 100)
    if latest_ttm is not None:
        yoy.append(np.nan)
    line, = ax2.plot(x, yoy, marker="o", color=COLORS["blue"], lw=2.2, label="年度同比")
    ax2.axhline(0, color="#999999", lw=0.8, ls="--", alpha=0.7)
    ax2.set_ylabel("同比 %", fontproperties=FONT)
    ax2.spines["top"].set_visible(False)
    for label in ax2.get_yticklabels():
        label.set_fontproperties(FONT)
    set_title(ax1, f"{company}：利润趋势与同比增速", f"利润口径：{profit_col}；如含最新TTM，需在正文说明季度口径")
    span = max(pd.Series(profit_values).max() - min(0, pd.Series(profit_values).min()), 1)
    for i, v in enumerate(profit_values):
        if pd.notna(v):
            ax1.text(i, v + span * 0.025, f"{v:.0f}", ha="center", fontproperties=FONT, fontsize=9)
    for i, v in enumerate(yoy):
        if pd.notna(v) and np.isfinite(v) and i > 0:
            ax2.text(i, v + (12 if v >= 0 else -12), f"{v:.0f}%", ha="center", va="bottom" if v >= 0 else "top",
                     fontproperties=FONT, fontsize=8, color=COLORS["blue"])
    ax1.legend([bars, line], [f"{profit_col}/TTM（亿元）", "年度同比"], loc="upper left", prop=FONT, frameon=False)
    fig.tight_layout()
    save(fig, out_dir, f"{code}_4.2_利润趋势与同比增速图.png")


def plot_product(product_path: Optional[Path], out_dir: Path, code: str, company: str):
    if not product_path or not product_path.exists():
        print("SKIP 4.3 Product: product file not provided")
        return
    product = pd.read_csv(product_path)
    cols = require(product, {
        "business": ["业务", "产品", "分部", "segment"],
        "revenue": ["收入_亿元", "收入", "revenue_yi", "revenue"],
        "yoy": ["同比_%", "同比", "yoy", "yoy_%"],
    }, "4.3 Product")
    if not cols:
        return
    if product[cols["business"]].astype(str).duplicated().any():
        duplicates = sorted(product.loc[product[cols["business"]].astype(str).duplicated(keep=False), cols["business"]].astype(str).unique())
        print(f"SKIP 4.3 Product: duplicate businesses suggest a multi-period long table: {', '.join(duplicates)}; filter to one report period first")
        return
    product = product.copy()
    product[cols["revenue"]] = pd.to_numeric(product[cols["revenue"]], errors="coerce")
    product[cols["yoy"]] = pd.to_numeric(product[cols["yoy"]], errors="coerce")
    gm_col = first_existing(product, ["毛利率_%", "毛利率", "gross_margin", "gross_margin_%"])
    if gm_col:
        product[gm_col] = as_pct(product[gm_col])
    total = product[cols["revenue"]].sum()
    product["__share"] = product[cols["revenue"]] / total * 100
    product["__prev_rev"] = product[cols["revenue"]] / (1 + product[cols["yoy"]] / 100)
    product["__increment"] = product[cols["revenue"]] - product["__prev_rev"]

    fig, axes = plt.subplots(1, 2, figsize=(16, 7), dpi=180, gridspec_kw={"width_ratios": [1.35, 1]})
    palette = [COLORS["blue_light"], COLORS["orange_light"], COLORS["yellow_light"], "#A7F3D0", COLORS["gray_light"], "#DDD6FE"]
    color_map = {biz: palette[i % len(palette)] for i, biz in enumerate(product[cols["business"]])}
    prod = product.sort_values(cols["revenue"], ascending=True)
    axes[0].barh(prod[cols["business"]], prod[cols["revenue"]], height=0.52, color=[color_map[b] for b in prod[cols["business"]]])
    style(axes[0]); axes[0].set_xlabel("收入（亿元）", fontproperties=FONT)
    offset = max(prod[cols["revenue"]].max() * 0.015, 2)
    for y, val, pct, gm in zip(prod[cols["business"]], prod[cols["revenue"]], prod["__share"], prod[gm_col] if gm_col else [np.nan]*len(prod)):
        gm_text = "" if pd.isna(gm) else f" / 毛利率{gm:.1f}%"
        axes[0].text(val + offset, y, f"{val:.0f}亿 / {pct:.1f}%{gm_text}", va="center", fontproperties=FONT, fontsize=9)

    inc = product.sort_values("__increment", ascending=True)
    inc_colors = [COLORS["green"] if v >= 0 else COLORS["red"] for v in inc["__increment"]]
    axes[1].barh(inc[cols["business"]], inc["__increment"], height=0.52, color=inc_colors)
    axes[1].axvline(0, color="#999999", lw=0.8)
    style(axes[1]); axes[1].set_xlabel("收入增量（亿元，按同比反推）", fontproperties=FONT)
    for y, inc_val, yoy in zip(inc[cols["business"]], inc["__increment"], inc[cols["yoy"]]):
        positive = inc_val >= 0
        axes[1].annotate(
            f"{inc_val:+.0f}亿 / {yoy:+.1f}%",
            xy=(inc_val, y),
            xytext=(12 if positive else -12, 0),
            textcoords="offset points",
            va="center",
            ha="left" if positive else "right",
            fontproperties=FONT,
            fontsize=9,
            color=COLORS["green"] if positive else COLORS["red"],
        )
    max_abs = max(abs(inc["__increment"].min()), abs(inc["__increment"].max()), 1)
    axes[1].set_xlim(min(inc["__increment"].min() * 1.60, -max_abs * 0.12), inc["__increment"].max() * 1.35)
    set_title(axes[0], f"{company}：产品收入结构", "左图为收入/占比/毛利率；右图为按同比反推的收入增量贡献")
    axes[1].set_title("收入增量贡献", fontproperties=FONT, fontsize=12, pad=10)
    fig.tight_layout()
    save(fig, out_dir, f"{code}_4.3_收入结构与产品增速图.png")


def plot_cashflow(df: pd.DataFrame, out_dir: Path, code: str, company: str, profit_col_arg: Optional[str]):
    profit_candidates = [profit_col_arg] if profit_col_arg else []
    profit_candidates += ["股东应占溢利", "扣非净利润", "净利润", "归母净利润", "profit"]
    cols = require(df, {
        "profit": [c for c in profit_candidates if c],
        "ocf": ["经营现金流", "经营活动现金流量净额", "ocf"],
    }, "4.4 Cashflow")
    if not cols:
        return
    fcf_col = first_existing(df, ["自由现金流", "fcf"])
    capex_col = first_existing(df, ["资本开支", "购建固定资产无形资产和其他长期资产支付的现金", "capex"])
    if not fcf_col and not capex_col:
        print("SKIP 4.4 Cashflow: missing 自由现金流 or 资本开支")
        return
    years, x = years_x(df)
    profit = pd.to_numeric(df[cols["profit"]], errors="coerce")
    ocf = pd.to_numeric(df[cols["ocf"]], errors="coerce")
    fcf = pd.to_numeric(df[fcf_col], errors="coerce") if fcf_col else ocf - pd.to_numeric(df[capex_col], errors="coerce").abs()

    fig, axes = plt.subplots(2, 1, figsize=(15, 10), dpi=180, sharex=True, gridspec_kw={"height_ratios": [1.5, 1]})
    w = 0.25
    axes[0].bar(x - w, profit, width=w, color=COLORS["orange_light"], label=cols["profit"])
    axes[0].bar(x, ocf, width=w, color=COLORS["blue_light"], label="经营现金流")
    axes[0].bar(x + w, fcf, width=w, color=COLORS["green_light"], label="自由现金流")
    axes[0].axhline(0, color="#999999", lw=0.8)
    style(axes[0]); axes[0].set_ylabel("亿元", fontproperties=FONT)
    axes[0].legend(prop=FONT, loc="upper left")
    set_title(axes[0], f"{company}：现金流与利润对比", "上图为利润、经营现金流和自由现金流；下图为现金流覆盖率")

    opf = ocf / profit.replace(0, np.nan) * 100
    fcf_cov = fcf / profit.replace(0, np.nan) * 100
    for series, color, label, marker in [(opf, COLORS["blue"], "经营现金流/利润", "o"), (fcf_cov, COLORS["red"], "自由现金流/利润", "s")]:
        clipped = series.clip(lower=-100, upper=250)
        axes[1].plot(x, clipped, marker=marker, color=color, lw=2.2, label=label)
        for i, raw in enumerate(series):
            if pd.notna(raw) and (raw < -100 or raw > 250):
                axes[1].annotate("极值\n已截断", xy=(i, -100 if raw < -100 else 250), xytext=(0, -24 if raw > 250 else 14),
                                 textcoords="offset points", ha="center", va="top" if raw > 250 else "bottom",
                                 fontproperties=FONT, fontsize=8, color=COLORS["gray"])
    axes[1].axhline(100, color="#999999", lw=0.8, ls="--")
    axes[1].set_ylim(-120, 270)
    axes[1].set_xticks(x); axes[1].set_xticklabels(years, fontproperties=FONT)
    axes[1].set_ylabel("%", fontproperties=FONT)
    style(axes[1]); axes[1].legend(prop=FONT, loc="upper right")
    last = len(x) - 1
    if pd.notna(opf.iloc[-1]):
        axes[1].annotate(f"{opf.iloc[-1]:.0f}%", xy=(last, np.clip(opf.iloc[-1], -100, 250)), xytext=(10, 0), textcoords="offset points",
                         va="center", fontproperties=FONT, fontsize=9, color=COLORS["blue"])
    if pd.notna(fcf_cov.iloc[-1]):
        axes[1].annotate(f"{fcf_cov.iloc[-1]:.0f}%", xy=(last, np.clip(fcf_cov.iloc[-1], -100, 250)), xytext=(10, -10), textcoords="offset points",
                         va="center", fontproperties=FONT, fontsize=9, color=COLORS["red"])
    fig.tight_layout()
    save(fig, out_dir, f"{code}_4.4_净利润经营现金流自由现金流对比图.png")


def plot_cash_position(df: pd.DataFrame, out_dir: Path, code: str, company: str, recent_years: int):
    cols = require(df, {
        "cash_position": ["现金头寸_近似", "现金头寸", "cash_position"],
        "liability_ratio": ["资产负债率", "liability_ratio", "负债率"],
    }, "4.5 Cash position")
    if not cols:
        return
    recent = df.tail(recent_years).copy()
    years, x = years_x(recent)
    cash = pd.to_numeric(recent[cols["cash_position"]], errors="coerce")
    lr = as_pct(recent[cols["liability_ratio"]])
    missing_mask = cash.isna() | lr.isna()
    if missing_mask.any():
        missing_years = recent.loc[missing_mask, "__year"].astype(str).tolist()
        print(f"SKIP 4.5 Cash position: unverified/missing values for years: {', '.join(missing_years)}")
        return
    fig, ax1 = plt.subplots(figsize=(15, 7.5), dpi=180)
    ax2 = ax1.twinx()
    bars = ax1.bar(x, cash, width=0.46, color=COLORS["blue_light"], label="现金头寸近似（亿元）")
    line, = ax2.plot(x, lr, marker="o", color=COLORS["red"], lw=2.2, label="资产负债率")
    ax1.axhline(0, color="#999999", lw=0.8)
    ax1.set_xticks(x); ax1.set_xticklabels(years, fontproperties=FONT)
    ax1.set_ylabel("现金头寸（亿元）", fontproperties=FONT)
    ax2.set_ylabel("资产负债率 %", fontproperties=FONT)
    # Prevent visual exaggeration when liability ratio only moves a few percentage points.
    upper = 100 if lr.max() > 60 else 60
    ax2.set_ylim(0, upper)
    style(ax1); ax2.spines["top"].set_visible(False)
    for label in ax2.get_yticklabels():
        label.set_fontproperties(FONT)
    set_title(ax1, f"{company}：现金头寸与资产负债率", "现金头寸明细见表格；资产负债率右轴从0开始以避免视觉夸大")
    cash_span = max(cash.max() - min(0, cash.min()), 1)
    for i, v in enumerate(cash):
        if pd.notna(v):
            ax1.text(i, v + cash_span * 0.025, f"{v:.0f}亿", ha="center", fontproperties=FONT, fontsize=9, color=COLORS["blue"])
    for i, v in enumerate(lr):
        if pd.notna(v):
            ax2.annotate(f"{v:.1f}%", xy=(i, v), xytext=(0, 10), textcoords="offset points",
                         ha="center", va="bottom", fontproperties=FONT, fontsize=9, color=COLORS["red"])
    ax1.legend([bars, line], ["现金头寸近似（亿元）", "资产负债率"], loc="upper left", prop=FONT, frameon=False)
    fig.tight_layout()
    save(fig, out_dir, f"{code}_4.5_现金头寸拆解与资产负债安全垫图.png")


def plot_operating_quality(df: pd.DataFrame, out_dir: Path, code: str, company: str, recent_years: int):
    cols = require(df, {
        "revenue": ["营收", "营业收入", "收入", "revenue"],
        "receivable": ["应收账款", "应收账款及票据", "贸易应收款项及应收票据", "应收款项", "trade_receivables", "receivable"],
        "inventory": ["存货", "inventory"],
        "contract": ["合同负债", "预收款项", "合同负债/预收", "contract_liability"],
    }, "4.6 Operating quality")
    if not cols:
        return
    recent = df.tail(recent_years).copy()
    years, x = years_x(recent)
    revenue = pd.to_numeric(recent[cols["revenue"]], errors="coerce")
    receivable = pd.to_numeric(recent[cols["receivable"]], errors="coerce")
    inventory = pd.to_numeric(recent[cols["inventory"]], errors="coerce")
    contract = pd.to_numeric(recent[cols["contract"]], errors="coerce")
    missing_mask = pd.concat([revenue, receivable, inventory, contract], axis=1).isna().any(axis=1)
    if missing_mask.any():
        missing_years = recent.loc[missing_mask, "__year"].astype(str).tolist()
        print(f"SKIP 4.6 Operating quality: unverified/missing values for years: {', '.join(missing_years)}")
        return
    fig, axes = plt.subplots(2, 1, figsize=(15, 10), dpi=180, sharex=True, gridspec_kw={"height_ratios": [1.4, 1]})
    w = 0.25
    axes[0].bar(x - w, receivable, width=w, color="#BFDBFE", label="应收账款")
    axes[0].bar(x, inventory, width=w, color=COLORS["yellow_light"], label="存货")
    axes[0].bar(x + w, contract, width=w, color="#BBF7D0", label="合同负债/预收")
    style(axes[0]); axes[0].set_ylabel("亿元", fontproperties=FONT)
    axes[0].legend(prop=FONT, loc="upper left")
    set_title(axes[0], f"{company}：应收、存货与合同负债变化", "观察重点是存货是否快于收入增长，以及合同负债/订单是否匹配")
    rev_yoy = revenue.pct_change() * 100
    inv_yoy = inventory.pct_change() * 100
    inv_rev = inventory / revenue.replace(0, np.nan) * 100
    axes[1].bar(x - 0.15, rev_yoy, width=0.3, color=COLORS["blue_light"], label="营收同比")
    axes[1].bar(x + 0.15, inv_yoy, width=0.3, color=COLORS["orange_light"], label="存货同比")
    axes[1].plot(x, inv_rev, marker="o", color=COLORS["red"], label="存货/营收")
    axes[1].axhline(0, color="#999999", lw=0.8)
    axes[1].set_xticks(x); axes[1].set_xticklabels(years, fontproperties=FONT)
    axes[1].set_ylabel("%", fontproperties=FONT)
    style(axes[1]); axes[1].legend(prop=FONT, loc="upper left")
    fig.tight_layout()
    save(fig, out_dir, f"{code}_4.6_应收存货合同负债变化图.png")


def parse_args():
    p = argparse.ArgumentParser(description="Generate standardized chapter 4 fundamental quant charts")
    p.add_argument("--base", required=True, help="Company package directory, e.g. 1810_小米集团")
    p.add_argument("--code", required=True, help="Stock code prefix for output filenames")
    p.add_argument("--company", required=True, help="Company name for chart titles")
    p.add_argument("--annual", default="data/annual_core.csv", help="Annual core CSV path relative to base, or absolute path")
    p.add_argument("--product", default="data/product_structure.csv", help="Optional product structure CSV path")
    p.add_argument("--quarterly", default="", help="Optional quarterly profit CSV path for latest TTM")
    p.add_argument("--latest-ttm-label", default="", help="Quarter label to pick from quarterly file, e.g. 2026Q1")
    p.add_argument("--profit-col", default="", help="Override profit column name")
    p.add_argument("--start-year", type=int, default=None)
    p.add_argument("--end-year", type=int, default=None)
    p.add_argument("--recent-years", type=int, default=5, help="Years shown in 4.5/4.6")
    return p.parse_args()


def resolve(base: Path, value: str) -> Optional[Path]:
    if not value:
        return None
    p = Path(value)
    return p if p.is_absolute() else base / p


def main():
    args = parse_args()
    base = Path(args.base).expanduser().resolve()
    annual_path = resolve(base, args.annual)
    product_path = resolve(base, args.product)
    quarterly_path = resolve(base, args.quarterly)
    out_dir = base / "charts"
    if not annual_path or not annual_path.exists():
        raise FileNotFoundError(f"annual file not found: {annual_path}")
    df = read_annual(annual_path, args.start_year, args.end_year)
    profit_col_arg = args.profit_col or None
    latest_label = args.latest_ttm_label or None

    plot_roe_dupont(df, out_dir, args.code, args.company)
    plot_profit(df, out_dir, args.code, args.company, profit_col_arg, quarterly_path, latest_label)
    plot_product(product_path if product_path and product_path.exists() else None, out_dir, args.code, args.company)
    plot_cashflow(df, out_dir, args.code, args.company, profit_col_arg)
    plot_cash_position(df, out_dir, args.code, args.company, args.recent_years)
    plot_operating_quality(df, out_dir, args.code, args.company, args.recent_years)


if __name__ == "__main__":
    main()
