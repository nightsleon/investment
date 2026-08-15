#!/usr/bin/env python3
"""30只红利指数排名评分与md文档生成。"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[2]
METRICS_PATH = BASE / "sources" / "performance-data-30index" / "全部指标.json"
HOLDINGS_DIR = BASE / "sources" / "holdings-30index"
OUTPUT_PATH = BASE / "01_主报告" / "30只红利指数样本指标及排名.md"

# 评分权重
WEIGHTS = {
    "return": 0.35,
    "risk": 0.25,
    "efficiency": 0.15,
    "stability": 0.15,
    "phase": 0.10,
}


def load_metrics() -> list[dict]:
    with open(METRICS_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_holdings_summary() -> dict:
    """从holdings目录读取每只指数的top10和行业摘要。"""
    summaries = {}
    for fname in os.listdir(HOLDINGS_DIR):
        if not fname.endswith(".json"):
            continue
        parts = fname.replace(".json", "").split("_")
        code = parts[0]
        name = parts[1] if len(parts) > 1 else ""

        with open(HOLDINGS_DIR / fname, encoding="utf-8") as f:
            data = json.load(f)

        if "前十大" in fname:
            top10_list = data.get("top10", [])
            top5_sum = data.get("top5Sum")
            top10_sum = data.get("top10Sum")
            summaries.setdefault(code, {})["top10"] = top10_list
            summaries[code]["top5_sum"] = float(top5_sum) if top5_sum else None
            summaries[code]["top10_sum"] = float(top10_sum) if top10_sum else None
        elif "行业权重" in fname:
            industries = data.get("industryWeightList", [])
            if industries:
                sorted_ind = sorted(industries, key=lambda x: float(x.get("weightPct", 0)), reverse=True)
            else:
                sorted_ind = []
            summaries.setdefault(code, {})["industries"] = sorted_ind

    return summaries


def score_group(metrics_list: list[dict], period: str) -> pd.DataFrame:
    """对一组指数按指定周期做相对排名评分。"""
    rows = []
    for m in metrics_list:
        period_data = m[f"metrics_{period}"]
        if not period_data.get("sufficient_data"):
            continue
        rows.append({
            "price_code": m["price_code"],
            "name": m["name"],
            "market": m["market"],
            "launch_date": m.get("launch_date", ""),
            "cagr": period_data.get("cagr", float("nan")),
            "monthly_vol": period_data.get("monthly_vol", float("nan")),
            "max_drawdown": period_data.get("max_drawdown", float("nan")),
            "return_over_vol": period_data.get("return_over_vol", float("nan")),
            "annual_win_rate": period_data.get("annual_win_rate", "N/A"),
            "worst_year": period_data.get("worst_year", float("nan")),
            "rolling3_median": period_data.get("rolling3_median", float("nan")),
            "rolling3_positive_pct": period_data.get("rolling3_positive_pct", float("nan")),
            "rolling5_median": period_data.get("rolling5_median", float("nan")),
            "rolling5_positive_pct": period_data.get("rolling5_positive_pct", float("nan")),
            "backtest_ratio": period_data.get("backtest_ratio", ""),
            "pre_post_gap": period_data.get("pre_post_gap", ""),
            "record_count": period_data.get("record_count", 0),
        })

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    # 相对排名评分（百分位制，0-100）
    # 收益：CAGR越高越好
    df["score_return"] = df["cagr"].rank(pct=True) * 100

    # 风险：最大回撤绝对值越小越好（回撤是负数，越接近0越好）
    df["score_risk"] = df["max_drawdown"].rank(pct=True) * 100

    # 效率：收益/波动越高越好
    df["score_efficiency"] = df["return_over_vol"].rank(pct=True) * 100

    # 稳定性：综合年度胜率+滚动3年中位数
    # 先提取年度胜率分子分母
    def parse_win_rate(wr):
        if wr == "N/A":
            return float("nan")
        parts = wr.split("/")
        if len(parts) == 2:
            return int(parts[0]) / int(parts[1])
        return float("nan")

    df["win_rate_num"] = df["annual_win_rate"].apply(parse_win_rate)
    # 稳定性 = 0.5*胜率百分位 + 0.3*滚动3年中位数百分位 + 0.2*最差年度百分位
    df["score_stability"] = (
        df["win_rate_num"].rank(pct=True) * 50
        + df["rolling3_median"].rank(pct=True) * 30
        + df["worst_year"].rank(pct=True) * 20
    )

    # 分阶段（简化：用最差年度作为下行风险代理，CAGR作为上行收益代理）
    # 这里用worst_year的排名作为阶段防御性得分
    df["score_phase"] = df["worst_year"].rank(pct=True) * 100

    # 总分
    df["total_score"] = (
        df["score_return"] * WEIGHTS["return"]
        + df["score_risk"] * WEIGHTS["risk"]
        + df["score_efficiency"] * WEIGHTS["efficiency"]
        + df["score_stability"] * WEIGHTS["stability"]
        + df["score_phase"] * WEIGHTS["phase"]
    )

    df = df.sort_values("total_score", ascending=False).reset_index(drop=True)
    df["rank"] = df.index + 1

    return df


def format_pct(val) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "N/A"
    return f"{val:.2%}"


def format_num(val, decimals=4) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "N/A"
    return f"{val:.{decimals}f}"


def generate_md(metrics_list: list[dict], holdings: dict) -> str:
    # 分境内和跨市场
    domestic = [m for m in metrics_list if m["market"] == "境内"]
    cross = [m for m in metrics_list if m["market"] == "跨市场"]

    lines = []
    lines.append("# 30只红利类指数样本数据主要指标及排名")
    lines.append("")
    lines.append("> 本期为30只红利类指数的总体分析，从样本池中采集全收益历史数据，计算收益、风险、稳定性等指标并排名。后续二期再从中挑选各类代表进行横评。")
    lines.append("")

    # 数据说明
    lines.append("## 数据说明")
    lines.append("")
    lines.append("- 样本来源：中证指数官网，筛选条件为热点=红利/高股息且有ETF跟踪产品，共30只。")
    lines.append(f"- 回报类型：全部使用人民币全收益指数（TR），现金分红再投资。")
    lines.append(f"- 数据截止：2026-08-07（最近交易日）。")
    lines.append(f"- 回溯区间：10年（2016-08-08起）、5年（2021-08-09起）、3年（2023-08-08起）。")
    lines.append("- 评分方法：相对排名百分位制，组内排名转0-100分，不设绝对阈值。")
    lines.append("- 分组：境内（22只）和跨市场（8只）独立排名，不跨组比较。")
    lines.append("- 回溯数据：发布日之前的数据为回溯试算，标注回溯占比和发布前后CAGR落差。")
    lines.append("")

    # 评分权重
    lines.append("## 评分权重")
    lines.append("")
    lines.append("| 维度 | 权重 | 核心指标 |")
    lines.append("|---|---:|---|")
    lines.append("| 收益能力 | 35% | CAGR |")
    lines.append("| 风险控制 | 25% | 最大回撤 |")
    lines.append("| 风险收益效率 | 15% | 收益/月频波动 |")
    lines.append("| 稳定性 | 15% | 年度胜率50% + 滚动3年中位数30% + 最差年度20% |")
    lines.append("| 分阶段表现 | 10% | 最差年度（下行风险代理） |")
    lines.append("")
    lines.append("> 总分 = 各维度百分位得分 × 权重之和。总分差3-5分以内视为同档。")
    lines.append("")

    # 生成各组的表格
    for group_name, group_list, group_label in [
        ("境内", domestic, "境内红利指数"),
        ("跨市场", cross, "跨市场红利指数"),
    ]:
        lines.append(f"## {group_label}（{len(group_list)}只）")
        lines.append("")

        for period, period_label in [("10y", "10年"), ("5y", "5年"), ("3y", "3年")]:
            df = score_group(group_list, period)
            if df.empty:
                lines.append(f"### {period_label}回溯")
                lines.append("")
                lines.append("数据不足，无法评分。")
                lines.append("")
                continue

            lines.append(f"### {period_label}回溯（{period}）")
            lines.append("")

            # 主指标表
            lines.append("| 排名 | 指数 | 代码 | 总分 | CAGR | 月频波动 | 最大回撤 | 收益/波动 | 年度胜率 | 最差年度 | 滚动3年中位数 | 回溯占比 | 前后落差 |")
            lines.append("|---:|---|---|---:|---:|---:|---:|---:|---|---:|---:|---|---|")

            for _, row in df.iterrows():
                lines.append(
                    f"| {int(row['rank'])} | {row['name']} | {row['price_code']} | {row['total_score']:.1f} | "
                    f"{format_pct(row['cagr'])} | {format_pct(row['monthly_vol'])} | {format_pct(row['max_drawdown'])} | "
                    f"{format_num(row['return_over_vol'], 4)} | {row['annual_win_rate']} | {format_pct(row['worst_year'])} | "
                    f"{format_pct(row['rolling3_median'])} | {row['backtest_ratio']} | {row['pre_post_gap']} |"
                )
            lines.append("")

            # 维度得分明细
            lines.append(f"<details><summary>{period_label}维度得分明细</summary>")
            lines.append("")
            lines.append("| 指数 | 收益 | 风险 | 效率 | 稳定性 | 阶段 | 总分 |")
            lines.append("|---|---:|---:|---:|---:|---:|---:|")
            for _, row in df.iterrows():
                lines.append(
                    f"| {row['name']} | {row['score_return']:.1f} | {row['score_risk']:.1f} | "
                    f"{row['score_efficiency']:.1f} | {row['score_stability']:.1f} | {row['score_phase']:.1f} | {row['total_score']:.1f} |"
                )
            lines.append("")
            lines.append("</details>")
            lines.append("")

    # 持仓快照
    lines.append("## 持仓快照（截至2026-08-07）")
    lines.append("")
    lines.append("> 只展示当前持仓事实，不做规则评价。截面数据不能反推历史结构。")
    lines.append("")

    # 整理持仓表
    lines.append("| 指数 | 代码 | 前五大合计 | 前十大合计 | 前三大行业 |")
    lines.append("|---|---|---:|---:|---|")

    for m in sorted(metrics_list, key=lambda x: (x["market"], x["name"])):
        code = m["price_code"]
        name = m["name"]
        h = holdings.get(code, {})

        top5 = h.get("top5_sum")
        top10 = h.get("top10_sum")
        industries = h.get("industries", [])

        top5_str = f"{top5:.2f}%" if top5 else "N/A"
        top10_str = f"{top10:.2f}%" if top10 else "N/A"

        if industries:
            top3 = industries[:3]
            ind_str = ", ".join(f"{i.get('csiType', '?')} {float(i.get('weightPct', 0)):.1f}%" for i in top3)
        else:
            ind_str = "N/A"

        lines.append(f"| {name} | {code} | {top5_str} | {top10_str} | {ind_str} |")
    lines.append("")

    # 回溯数据可信度
    lines.append("## 回溯数据可信度")
    lines.append("")
    lines.append("回溯数据是指数公司用当前编制规则套用到发布日之前的历史数据机械反算的序列。主要风险：规则设计可能带后视镜偏差；成分股调整与真实运行有差异；不含摩擦成本。")
    lines.append("")
    lines.append("检验方法：比较同一只指数发布前回溯段与发布后实盘段的CAGR落差。落差大说明回溯过度乐观。")
    lines.append("")
    lines.append("| 指数 | 代码 | 发布日期 | 10年回溯占比 | 前后CAGR落差 | 可信度提示 |")
    lines.append("|---|---|---|---|---|---|")

    for m in sorted(metrics_list, key=lambda x: x["price_code"]):
        m10 = m["metrics_10y"]
        if not m10.get("sufficient_data"):
            continue
        code = m["price_code"]
        name = m["name"]
        launch = m.get("launch_date", "")
        bt = m10.get("backtest_ratio", "")
        gap = m10.get("pre_post_gap", "")

        # 可信度判断
        if not bt or bt == "":
            confidence = "发布前已有数据，实盘验证充分"
        elif gap == "发布后数据不足":
            confidence = "发布后数据不足，难以验证"
        elif gap:
            gap_num = float(gap.replace("pp", "").replace("+", ""))
            if abs(gap_num) > 8:
                confidence = "⚠ 前后落差大，回溯可信度低"
            elif abs(gap_num) > 4:
                confidence = "前后落差中等，回溯仅供参考"
            else:
                confidence = "前后落差小，回溯可信度较高"
        else:
            confidence = "发布前已有数据"

        lines.append(f"| {name} | {code} | {launch} | {bt} | {gap} | {confidence} |")
    lines.append("")

    # 数据来源
    lines.append("## 数据来源")
    lines.append("")
    lines.append("- 全收益代码：中证指数官网衍生指数接口 `get-derivative-index`")
    lines.append("- 历史数据：中证指数官网Excel导出 `downloadindex-perf`")
    lines.append("- 基础信息：中证指数官网 `index-basic-info`")
    lines.append("- 持仓数据：中证指数官网 `top10new` 和 `industry-weight-two-new` 接口")
    lines.append("- 原始Excel归档：`sources/excel-30index/`")
    lines.append("- 解析后CSV：`sources/performance-data-30index/`")
    lines.append("- 持仓JSON：`sources/holdings-30index/`")
    lines.append("- 完整指标JSON：`sources/performance-data-30index/全部指标.json`")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*本文档为30只红利类指数的总体分析排名，后续二期将从中挑选各类代表进行深度横评。*")

    return "\n".join(lines)


def main() -> None:
    metrics_list = load_metrics()
    holdings = load_holdings_summary()
    md = generate_md(metrics_list, holdings)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"文档已生成: {OUTPUT_PATH}")
    print(f"文件大小: {OUTPUT_PATH.stat().st_size} bytes")


if __name__ == "__main__":
    main()
