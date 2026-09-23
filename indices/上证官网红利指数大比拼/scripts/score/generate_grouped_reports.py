#!/usr/bin/env python3
"""按发布年限分组生成3份对比报告：≥10年、≥5年、全部。不区分境内/跨市场。"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[2]
METRICS_PATH = BASE / "sources" / "performance-data-30index" / "全部指标.json"
HOLDINGS_DIR = BASE / "sources" / "holdings-30index"
OUTPUT_DIR = BASE / "01_主报告"

WEIGHTS = {
    "return": 0.40,
    "risk": 0.30,
    "efficiency": 0.15,
    "stability": 0.15,
}

REF_DATE = datetime(2026, 8, 10)


def load_metrics() -> list[dict]:
    with open(METRICS_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_holdings_summary() -> dict:
    summaries = {}
    for fname in os.listdir(HOLDINGS_DIR):
        if not fname.endswith(".json"):
            continue
        parts = fname.replace(".json", "").split("_")
        code = parts[0]

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


def filter_by_years(metrics_list: list[dict], min_years: float | None) -> list[dict]:
    if min_years is None:
        return list(metrics_list)
    result = []
    for m in metrics_list:
        pd_str = m.get("launch_date", "")
        if not pd_str:
            continue
        pd_date = datetime.strptime(pd_str, "%Y-%m-%d")
        years = (REF_DATE - pd_date).days / 365.25
        if years >= min_years:
            result.append(m)
    return result


def score_group(metrics_list: list[dict], period: str) -> pd.DataFrame:
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
            "cumulative_return": period_data.get("cumulative_return", float("nan")),
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
            # annual_data 始终用10年区间的，分阶段不受period影响
            "annual_data": m["metrics_10y"].get("annual_data", {}) if m["metrics_10y"].get("sufficient_data") else m["metrics_5y"].get("annual_data", {}),
        })

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    df["score_return"] = df["cagr"].rank(pct=True) * 100
    df["score_risk"] = df["max_drawdown"].rank(pct=True) * 100
    df["score_efficiency"] = df["return_over_vol"].rank(pct=True) * 100

    def parse_win_rate(wr):
        if wr == "N/A":
            return float("nan")
        parts = wr.split("/")
        if len(parts) == 2:
            return int(parts[0]) / int(parts[1])
        return float("nan")

    df["win_rate_num"] = df["annual_win_rate"].apply(parse_win_rate)
    # 稳定性：年度胜率60% + 滚动3年中位数40%
    df["score_stability"] = (
        df["win_rate_num"].rank(pct=True) * 60
        + df["rolling3_median"].rank(pct=True) * 40
    )

    df["total_score"] = (
        df["score_return"] * WEIGHTS["return"]
        + df["score_risk"] * WEIGHTS["risk"]
        + df["score_efficiency"] * WEIGHTS["efficiency"]
        + df["score_stability"] * WEIGHTS["stability"]
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


def generate_report(metrics_list: list[dict], holdings: dict, min_years: float | None, output_path: Path) -> None:
    if min_years is not None:
        title_suffix = f"发布满{int(min_years)}年"
        filtered = filter_by_years(metrics_list, min_years)
    else:
        title_suffix = "全部"
        filtered = list(metrics_list)

    lines = []
    lines.append(f"# 红利类指数对比报告（{title_suffix}，{len(filtered)}只）")
    lines.append("")
    lines.append(f"> 本报告纳入{len(filtered)}只红利类指数，不区分境内与跨市场，统一排名。")
    lines.append("")

    # 数据说明
    lines.append("## 数据说明")
    lines.append("")
    lines.append("- 样本来源：中证指数官网，筛选条件为热点=红利/高股息且有ETF跟踪产品。")
    lines.append("- 回报类型：人民币全收益指数（TR），现金分红再投资。")
    lines.append("- 数据截止：2026-08-07。")
    lines.append("- 回溯区间：10年（2016-08-08起）、5年（2021-08-09起）、3年（2023-08-08起）。")
    lines.append("- 评分方法：相对排名百分位制，组内排名转0-100分，不设绝对阈值。")
    lines.append("- 回溯数据：发布日之前的数据为回溯试算，标注回溯占比和发布前后CAGR落差。")
    lines.append("")

    # 评分权重
    lines.append("## 评分权重")
    lines.append("")
    lines.append("| 维度 | 权重 | 核心指标 |")
    lines.append("|---|---:|---|")
    lines.append("| 收益能力 | 40% | CAGR |")
    lines.append("| 风险控制 | 30% | 最大回撤 |")
    lines.append("| 风险收益效率 | 15% | 收益/月频波动 |")
    lines.append("| 稳定性 | 15% | 年度胜率60% + 滚动3年中位数40% |")
    lines.append("")
    lines.append("**怎么打分？**")
    lines.append("")
    lines.append('不设"达到多少算优秀"的及格线，只看你在组里排第几。每个指标从小到大排队，排得越靠后（值越好）得分越高。')
    lines.append("")
    n = len(filtered)
    lines.append(f"以{n}只指数的CAGR为例：按CAGR从低到高排成一列，最高的排第{n}位，得分 = {n} ÷ {n} × 100 = 100分；最低的排第1位，得分 = 1 ÷ {n} × 100 = {1/n*100:.1f}分。")
    lines.append("")
    lines.append("每项得分 = 你的位置 ÷ 总只数 × 100，再乘以权重，就是该项贡献的分数。四项加起来就是总分。总分差3-5分以内视为同档。")
    lines.append("")

    # 各周期排名
    for period, period_label in [("10y", "10年"), ("5y", "5年"), ("3y", "3年")]:
        df = score_group(filtered, period)
        if df.empty:
            lines.append(f"## {period_label}回溯")
            lines.append("")
            lines.append("数据不足，无法评分。")
            lines.append("")
            continue

        lines.append(f"## {period_label}回溯")
        lines.append("")
        lines.append("| 排名 | 指数 | 总分 | 总收益 | CAGR | 月频波动 | 最大回撤 | 收益/波动 | 年度胜率 | 滚动3年中位数 | 发布日期 |")
        lines.append("|---:|---|---:|---:|---:|---:|---:|---:|---|---:|---|")

        for _, row in df.iterrows():
            lines.append(
                f"| {int(row['rank'])} | {row['name']}/{row['price_code']} | {row['total_score']:.1f} | "
                f"{format_pct(row['cumulative_return'])} | {format_pct(row['cagr'])} | "
                f"{format_pct(row['monthly_vol'])} | {format_pct(row['max_drawdown'])} | "
                f"{format_num(row['return_over_vol'], 4)} | {row['annual_win_rate']} | "
                f"{format_pct(row['rolling3_median'])} | {row['launch_date']} |"
            )
        lines.append("")

        # 维度得分明细
        lines.append(f"<details><summary>{period_label}维度得分明细</summary>")
        lines.append("")
        lines.append("| 指数 | 收益 | 风险 | 效率 | 稳定性 | 总分 |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for _, row in df.iterrows():
            lines.append(
                f"| {row['name']} | {row['score_return']:.1f} | {row['score_risk']:.1f} | "
                f"{row['score_efficiency']:.1f} | {row['score_stability']:.1f} | {row['total_score']:.1f} |"
            )
        lines.append("")
        lines.append("</details>")
        lines.append("")

    # 四阶段小结（10年数据）
    lines.append("## 四阶段表现小结")
    lines.append("")
    lines.append("> 用10年数据计算四个典型市场阶段的区间收益，观察不同类型红利指数在不同环境下的行为特征。数值仅供参考，不参与评分。")
    lines.append("")

    phases = [
        ("2018下跌", [2018], "中美贸易摩擦+去杠杆，A股单边下行"),
        ("2019-2020牛市", [2019, 2020], "核心资产牛市，消费科技领涨"),
        ("2021-2022回调", [2021, 2022], "新能源见顶+疫情冲击，市场深度回调"),
        ("2024反弹", [2024], "924行情+央企估值重塑，红利风格领涨"),
    ]

    # 计算各阶段收益
    phase_results = {}
    for phase_name, years, _ in phases:
        results = []
        for m in metrics_list:
            if m["price_code"] not in {x["price_code"] for x in filtered}:
                continue
            m10 = m["metrics_10y"]
            if not m10.get("sufficient_data"):
                continue
            annual = m10.get("annual_data", {})
            cumret = 1.0
            has_all = True
            for y in years:
                y_str = str(y)
                if y_str in annual:
                    cumret *= (1 + float(annual[y_str]))
                else:
                    has_all = False
                    break
            if has_all:
                results.append((m["name"], m["price_code"], cumret - 1))
        results.sort(key=lambda x: x[2], reverse=True)
        phase_results[phase_name] = results

    for phase_name, years, desc in phases:
        results = phase_results.get(phase_name, [])
        if not results:
            continue
        top3 = results[:3]
        bot3 = results[-3:]
        mid_idx = len(results) // 2
        median_ret = results[mid_idx][2]

        lines.append(f"### {phase_name}（{desc}）")
        lines.append("")
        top_str = "、".join(f"{n}（{r:+.2%}）" for n, c, r in top3)
        bot_str = "、".join(f"{n}（{r:+.2%}）" for n, c, r in bot3)
        lines.append(f"- **中位数**：{median_ret:+.2%}（{len(results)}只参与）")
        lines.append(f"- **表现最好**：{top_str}")
        lines.append(f"- **表现最差**：{bot_str}")
        lines.append("")

    # 指数分类
    lines.append("## 指数分类（基于编制方案）")
    lines.append("")
    lines.append("> 按策略逻辑分为六大类。样本空间（板块/主题/市场）是修饰标签，不改变策略本质。分类依据为中证指数官网发布的编制方案。")
    lines.append("")

    CLASSIFICATION = {
        "经典红利": {
            "desc": "以股息率为核心筛选指标，通过连续分红、分红稳定性等基础条件后，按股息率排序选样并加权。是红利指数最基础的形态。",
            "indices": [
                ("000015", "上证红利", "上证板块，50只"),
                ("000922", "中证红利", "全市场标杆，100只"),
                ("000821", "300红利", "沪深300板块"),
                ("000151", "上国红利", "上证+国企"),
                ("000824", "国企红利", "国企主题"),
                ("000825", "央企红利", "央企主题"),
                ("931231", "央企红利50", "央企主题，50只精选"),
                ("931132", "诚通央企红利", "央企主题，预期股息，定制"),
                ("932039", "央企股东回报", "央企主题，分红+回购"),
                ("H11140", "香港红利", "港股"),
                ("930914", "港股通高股息", "港股通，高股息"),
                ("930917", "SHS高股息", "沪港深，高股息"),
                ("931233", "港股通央企红利", "港股通+央企"),
                ("931722", "国新港股通央企红利", "港股通+央企，定制"),
                ("932305", "智选高股息", "定制，高股息"),
                ("CESFHY", "中华预期高股息", "跨市场，预期股息"),
                ("H30366", "高息策略", "股息率×70%+股利支付率×30%"),
            ],
        },
        "红利低波": {
            "desc": "在分红筛选基础上叠加低波动因子，目标是在获取红利收益的同时降低组合波动。是红利类指数中规模最大的子类。",
            "indices": [
                ("H30269", "红利低波", "50只，无行业上限"),
                ("930955", "红利低波100", "100只，20%行业上限"),
                ("930740", "300红利低波", "沪深300板块"),
                ("H50040", "上红低波", "上证板块"),
                ("931446", "东证红利低波", "定制，东方证券"),
                ("932422", "A500红利低波", "A500板块"),
            ],
        },
        "红利质量": {
            "desc": '在分红筛选基础上叠加质量因子（ROE、盈利稳定性、现金流质量等），目标是选出"能持续分红的好公司"，避免价值陷阱。',
            "indices": [
                ("931468", "红利质量", "定制，分红>再融资约束"),
                ("932315", "中证红利质量", "全指版，30%行业上限"),
                ("930839", "港股通高息精选", "港股通，质量精选30只"),
            ],
        },
        "红利成长": {
            "desc": "在分红筛选基础上叠加成长因子（盈利增长、股息增长等），目标是兼顾分红和成长。",
            "indices": [
                ("931157", "SHS红利成长LV", "沪港深，成长+低波"),
                ("H30089", "红利潜力", "EPS+未分配利润+ROE"),
            ],
        },
        "红利价值": {
            "desc": "在分红筛选基础上叠加价值因子（PB、股息支付率等），强调估值安全边际。",
            "indices": [
                ("H30270", "红利价值", "股息率+BP+盈利增长"),
            ],
        },
        "行业主题": {
            "desc": "限定在特定行业或主题内的红利指数，行业暴露集中，波动更大。",
            "indices": [
                ("H30094", "消费红利", "消费行业"),
            ],
        },
    }

    # 只展示 filtered 范围内的指数
    filtered_codes = {m["price_code"] for m in filtered}

    for cat_name, cat_info in CLASSIFICATION.items():
        cat_indices = [(c, n, d) for c, n, d in cat_info["indices"] if c in filtered_codes]
        if not cat_indices:
            continue
        lines.append(f"### {cat_name}（{len(cat_indices)}只）")
        lines.append("")
        lines.append(f"{cat_info['desc']}")
        lines.append("")
        lines.append("| 指数 | 特征标签 |")
        lines.append("|---|---|")
        for code, name, desc in cat_indices:
            lines.append(f"| {name}/{code} | {desc} |")
        lines.append("")

    # 持仓快照
    lines.append("## 持仓快照（截至2026-08-07）")
    lines.append("")
    lines.append("> 只展示当前持仓事实，不做规则评价。截面数据不能反推历史结构。")
    lines.append("")
    lines.append("| 指数 | 前五大合计 | 前十大合计 | 前三大行业 |")
    lines.append("|---|---:|---:|---|")

    for m in sorted(filtered, key=lambda x: x["name"]):
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

        lines.append(f"| {name}/{code} | {top5_str} | {top10_str} | {ind_str} |")
    lines.append("")

    # 回溯可信度
    lines.append("## 回溯数据可信度")
    lines.append("")
    lines.append("回溯数据是指数公司用当前编制规则套用到发布日之前的历史数据机械反算的序列。主要风险：规则设计可能带后视镜偏差；成分股调整与真实运行有差异；不含摩擦成本。")
    lines.append("")
    lines.append("检验方法：比较同一只指数发布前回溯段与发布后实盘段的CAGR落差。落差大说明回溯过度乐观。")
    lines.append("")
    lines.append("| 指数 | 发布日期 | 10年回溯占比 | 前后CAGR落差 | 可信度提示 |")
    lines.append("|---|---|---|---|---|")

    for m in sorted(filtered, key=lambda x: x["price_code"]):
        m10 = m["metrics_10y"]
        if not m10.get("sufficient_data"):
            continue
        code = m["price_code"]
        name = m["name"]
        launch = m.get("launch_date", "")
        bt = m10.get("backtest_ratio", "")
        gap = m10.get("pre_post_gap", "")

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

        lines.append(f"| {name}/{code} | {launch} | {bt} | {gap} | {confidence} |")
    lines.append("")

    # ETF可投资性
    lines.append("## ETF可投资性")
    lines.append("")
    lines.append("> 推荐规则：有ETF且规模≥2亿选规模最大的ETF；ETF规模<2亿且场外指数基金≥5亿选场外指数基金；否则优先ETF。LOF/指数增强为兜底选项。")
    lines.append("")
    lines.append("基金类型分两个维度：交易方式和投资策略。")
    lines.append("")
    lines.append("**交易方式维度：**")
    lines.append("")
    lines.append("- **ETF**：场内交易，费率最低（管理费0.15-0.5%），跟踪误差最小，流动性最好。A股ETF T+1交割，跨境ETF T+0。适合有股票账户的投资者。")
    lines.append("- **指数基金（场外）**：场外申购赎回，按日净值成交，费率中等（0.5-1%）。适合定投和没有股票账户的投资者。")
    lines.append("- **LOF**：场内场外均可，但场内成交量小、买卖价差大。不推荐作为首选。")
    lines.append("- **联接基金**：场外投资ETF的通道，多收一层管理费。不推荐，不如直接买ETF或普通指数基金。")
    lines.append("")
    lines.append("**投资策略维度：**")
    lines.append("")
    lines.append("- **纯被动指数**：完全复制指数，目标是跟踪误差最小化。ETF和普通指数基金大多属于此类。")
    lines.append("- **指数增强**：在跟踪指数基础上做主动操作，目标是跑赢指数。费率更高，跟踪误差更大，业绩不确定性高。")
    lines.append("")
    lines.append("**选择优先级：ETF > 场外指数基金 > LOF > 指数增强 > 联接基金。**")
    lines.append("")
    lines.append("| 指数 | 跟踪产品数 | 推荐标的 | 类型 | 规模（亿元） | 成立日期 |")
    lines.append("|---|---:|---|---|---:|---|")

    import os as _os
    etf_summary_path = BASE / "sources" / "track-funds" / "_汇总_跟踪基金统计.json"
    etf_map = {}
    if _os.path.exists(etf_summary_path):
        with open(etf_summary_path, encoding="utf-8") as f:
            etf_list = json.load(f)
        for item in etf_list:
            etf_map[item["index_code"]] = item

    for m in sorted(filtered, key=lambda x: x["name"]):
        code = m["price_code"]
        name = m["name"]
        detail_path = BASE / "sources" / "track-funds" / f"{code}_{m['name']}_跟踪基金.json"

        if not _os.path.exists(detail_path):
            lines.append(f"| {name}/{code} | N/A | N/A | N/A | N/A | N/A |")
            continue

        with open(detail_path, encoding="utf-8") as f:
            detail = json.load(f)
        funds = detail.get("funds", [])
        total = detail.get("total_funds", len(funds))

        # 分类
        etf_funds = [f for f in funds if f.get("fund_type") == "ETF"]
        index_funds = [f for f in funds if f.get("fund_type") == "指数基金"]
        lof_funds = [f for f in funds if f.get("fund_type") == "LOF"]
        enhanced_funds = [f for f in funds if f.get("fund_type") == "指数增强"]

        # 按推荐规则选
        recommended = None
        rec_type = ""

        # 规则1：有ETF且规模≥2亿，选最大的ETF
        if etf_funds:
            etf_funds.sort(key=lambda x: x.get("aum_yi", 0), reverse=True)
            if etf_funds[0].get("aum_yi", 0) >= 2:
                recommended = etf_funds[0]
                rec_type = "ETF"

        # 规则2：如果没选中，看场外指数基金有没有≥5亿的
        if recommended is None and index_funds:
            index_funds.sort(key=lambda x: x.get("aum_yi", 0), reverse=True)
            if index_funds[0].get("aum_yi", 0) >= 5:
                recommended = index_funds[0]
                rec_type = "指数基金"

        # 规则3：还是没有，退而选ETF（即使小）
        if recommended is None and etf_funds:
            etf_funds.sort(key=lambda x: x.get("aum_yi", 0), reverse=True)
            recommended = etf_funds[0]
            rec_type = "ETF（规模偏小）"

        # 规则4：没有ETF，选最大的指数基金（即使小）
        if recommended is None and index_funds:
            index_funds.sort(key=lambda x: x.get("aum_yi", 0), reverse=True)
            recommended = index_funds[0]
            rec_type = "指数基金（规模偏小）"

        # 规则5：兜底-LOF
        if recommended is None and lof_funds:
            lof_funds.sort(key=lambda x: x.get("aum_yi", 0), reverse=True)
            recommended = lof_funds[0]
            rec_type = "LOF"

        # 规则6：兜底-指数增强
        if recommended is None and enhanced_funds:
            enhanced_funds.sort(key=lambda x: x.get("aum_yi", 0), reverse=True)
            recommended = enhanced_funds[0]
            rec_type = "指数增强"

        if recommended:
            fname = recommended.get("fund_name", "N/A")
            # 去掉冗长后缀
            fname = fname.replace("交易型开放式指数证券投资基金", "ETF")
            fname = fname.replace("指数型证券投资基金", "")
            fname = fname.replace("指数型发起式证券投资基金", "")
            fname = fname.replace("指数增强型证券投资基金", "指数增强")
            fname = fname.replace("证券投资基金(LOF)", "（LOF）")
            fname = fname.replace("证券投资基金", "")
            fcode = recommended.get("fund_code", "N/A")
            aum = recommended.get("aum_yi", 0)
            inception = recommended.get("inception_date", "N/A")
            lines.append(f"| {name}/{code} | {total} | {fname}（{fcode}） | {rec_type} | {aum:.2f} | {inception} |")
        else:
            lines.append(f"| {name}/{code} | {total} | N/A | N/A | N/A | N/A |")
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

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"✓ {output_path.name}: {len(filtered)}只, {output_path.stat().st_size} bytes")


def main() -> None:
    metrics_list = load_metrics()
    holdings = load_holdings_summary()

    generate_report(metrics_list, holdings, None, OUTPUT_DIR / "红利指数对比_全部30只.md")


if __name__ == "__main__":
    main()
