#!/usr/bin/env python3
"""生成二期基金对比报告。"""
from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
DATA_DIR = BASE / "02_二期深度对比"
CHART_DIR = "charts"  # 相对路径
OUTPUT = BASE / "02_二期深度对比" / "红利基金实盘对比_二期.md"


def fmt_pct(v: float | None, decimals: int = 2, signed: bool = True) -> str:
    if v is None:
        return "N/A"
    sign = "+" if signed and v >= 0 else ""
    return f"{sign}{v:.{decimals}f}%"


def fmt_num(v: float | None, decimals: int = 2) -> str:
    if v is None:
        return "N/A"
    return f"{v:.{decimals}f}"


def load_aum_map() -> dict[str, float]:
    """从跟踪基金汇总加载基金规模。"""
    fund_dir = BASE / "sources" / "track-funds"
    aum_map = {}
    for f in fund_dir.glob("*_跟踪基金.json"):
        with open(f, encoding="utf-8") as fp:
            data = json.load(fp)
        if not isinstance(data, dict):
            continue
        for fund in data.get("funds", []):
            code = fund.get("fund_code", "")
            aum = fund.get("aum_yi")
            if code and aum is not None:
                aum_map[code] = aum
    return aum_map


def generate_report() -> None:
    with open(DATA_DIR / "基金对比_指标及排名.json", encoding="utf-8") as f:
        data = json.load(f)

    aum_map = load_aum_map()

    lines = []
    lines.append("# 红利类基金实盘对比（二期）")
    lines.append("")
    lines.append("> 基于基金实际净值，而非指数回溯数据。以华泰柏瑞红利低波ETF（512890）为基准。")
    lines.append("")

    # 说明
    lines.append("## 筛选与排名说明")
    lines.append("")
    lines.append("**分组规则：**")
    lines.append("- 5年组：基金成立满5年（约1200个交易日），四维度评分（收益40%、风险30%、效率15%、稳定性15%）")
    lines.append("- 2年组：基金成立2-5年，三维度评分（收益50%、风险30%、效率20%，稳定性因数据不足暂不参评）")
    lines.append("- 观察池：成立不足2年，仅供参考，不参与排名")
    lines.append("")
    lines.append("**比较基准：** 华泰柏瑞红利低波ETF（512890），当前规模最大的红利类ETF（324亿）。")
    lines.append("")
    lines.append("**分档规则：**")
    lines.append("- 第一梯队：总分 ≥ 基准 + 3分（综合显著更优）")
    lines.append("- 第二梯队：基准 - 3分 ≤ 总分 < 基准 + 3分（综合接近，各有千秋）")
    lines.append("- 第三梯队：总分 < 基准 - 3分（全面落后）")
    lines.append("")

    # 5年组
    group_5y = data.get("5年组", [])
    lines.append("## 5年组（5年以上实盘）")
    lines.append("")

    if group_5y:
        # 找基准
        bench = next((r for r in group_5y if r.get("tier") == "基准"), None)
        bench_score = bench["total_score"] if bench else None
        period = f"{group_5y[0].get('data_points', '?')}个交易日"

        lines.append(f"共同区间数据点：约{group_5y[0].get('data_points', 'N/A')}个交易日。")
        if bench:
            lines.append(f"基准得分：{bench_score:.1f}分。")
        lines.append("")

        lines.append("| 排名 | 基金 | 代码 | 总分 | 总收益 | CAGR | 最大回撤 | 收益/波动 | 年化跟踪误差 | 规模（亿） | 梯队 |")
        lines.append("|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|")

        for r in group_5y:
            rank = r.get("rank", 0)
            name = r["short_name"]
            code = r["fund_code"]
            score = r["total_score"]
            total_ret = fmt_pct(r.get("total_return_pct"), signed=False)
            cagr = fmt_pct(r.get("cagr_pct"), signed=False)
            mdd = fmt_pct(r.get("max_drawdown_pct"))
            rov = fmt_num(r.get("return_over_vol"))
            te = fmt_num(r.get("tracking_error_annual_pct"))
            tier = r.get("tier", "")
            aum = aum_map.get(code, "-")
            aum_str = f"{aum:.2f}" if isinstance(aum, (int, float)) else str(aum)
            marker = " ★基准" if tier == "基准" else ""

            lines.append(f"| {rank} | {name}{marker} | {code} | {score:.1f} | {total_ret} | {cagr} | {mdd} | {rov} | {te} | {aum_str} | {tier} |")
        lines.append("")

        # 5年组总图
        lines.append("![5年组对比](charts/组内对比_5年组.png)")
        lines.append("")

    # 2年组
    group_2y = data.get("2年组", [])
    lines.append("## 2年组（2-5年实盘）")
    lines.append("")
    lines.append("> 注：2年组数据周期较短，且不含稳定性维度，结论可信度低于5年组。近2年恰逢红利风格占优的市场环境，各基金表现可能偏乐观。")
    lines.append("")

    if group_2y:
        bench = next((r for r in group_2y if r.get("tier") == "基准"), None)
        bench_score = bench["total_score"] if bench else None

        lines.append(f"共同区间数据点：约{group_2y[0].get('data_points', 'N/A')}个交易日。")
        if bench:
            lines.append(f"基准得分：{bench_score:.1f}分（截取相同区间）。")
        lines.append("")

        lines.append("| 排名 | 基金 | 代码 | 总分 | 总收益 | CAGR | 最大回撤 | 收益/波动 | 年化跟踪误差 | 规模（亿） | 梯队 |")
        lines.append("|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|")

        for r in group_2y:
            rank = r.get("rank", 0)
            name = r["short_name"]
            code = r["fund_code"]
            score = r["total_score"]
            total_ret = fmt_pct(r.get("total_return_pct"), signed=False)
            cagr = fmt_pct(r.get("cagr_pct"), signed=False)
            mdd = fmt_pct(r.get("max_drawdown_pct"))
            rov = fmt_num(r.get("return_over_vol"))
            te = fmt_num(r.get("tracking_error_annual_pct"))
            tier = r.get("tier", "")
            aum = aum_map.get(code, "-")
            aum_str = f"{aum:.2f}" if isinstance(aum, (int, float)) else str(aum)
            marker = " ★基准" if tier == "基准" else ""

            lines.append(f"| {rank} | {name}{marker} | {code} | {score:.1f} | {total_ret} | {cagr} | {mdd} | {rov} | {te} | {aum_str} | {tier} |")
        lines.append("")

        lines.append("![2年组对比](charts/组内对比_2年组.png)")
        lines.append("")

    # 观察池
    obs = data.get("观察池", [])
    if obs:
        lines.append("## 观察池（不足2年）")
        lines.append("")
        lines.append("成立时间不足2年，实盘验证不充分，暂不参与排名。")
        lines.append("")
        lines.append("| 基金 | 代码 | 交易日 | CAGR | 最大回撤 |")
        lines.append("|---|---|---:|---:|---:|")
        for r in obs:
            name = r["short_name"]
            code = r["fund_code"]
            dp = r.get("data_points", 0)
            cagr = fmt_pct(r.get("cagr_pct"))
            mdd = fmt_pct(r.get("max_drawdown_pct"))
            lines.append(f"| {name} | {code} | {dp} | {cagr} | {mdd} |")
        lines.append("")

    # 跟踪误差汇总
    lines.append("## 跟踪误差分析")
    lines.append("")
    lines.append("跟踪误差反映基金净值相对跟踪指数全收益的偏离程度。纯被动ETF年化跟踪误差通常应小于1%，大于2%说明跟踪质量较差。")
    lines.append("")
    lines.append("> 注：跟踪误差为正=基金跑赢指数，为负=跑输。全收益指数含分红再投资，ETF现金分红方式下可能有自然偏离。")
    lines.append("")

    all_with_te = []
    for group in [group_5y, group_2y]:
        for r in group:
            if r.get("tracking_error_annual_pct") is not None:
                all_with_te.append(r)

    if all_with_te:
        all_with_te.sort(key=lambda x: abs(x.get("tracking_error_annual_pct", 0)))
        lines.append("| 基金 | 代码 | 年化跟踪误差 | 累计超额收益 | 评估 |")
        lines.append("|---|---|---:|---:|---|")
        for r in all_with_te:
            te = r.get("tracking_error_annual_pct", 0)
            excess = r.get("excess_return_pct")
            if abs(te) < 1.5:
                assess = "✓ 跟踪良好"
            elif abs(te) < 3:
                assess = "△ 跟踪一般"
            else:
                assess = "✗ 跟踪偏差大"
            lines.append(f"| {r['short_name']} | {r['fund_code']} | {te:.2f}% | {fmt_pct(excess)} | {assess} |")
        lines.append("")

    # 各基金详细对比图
    lines.append("## 各基金对比基准图")
    lines.append("")
    lines.append("每只基金与华泰柏瑞红利低波ETF（基准）的归一化走势对比，以及该基金相对跟踪指数的累计偏离。")
    lines.append("")

    for group_name, group in [("5年组", group_5y), ("2年组", group_2y)]:
        for r in group:
            code = r["fund_code"]
            name = r["short_name"]
            if r.get("tier") == "基准":
                continue

            lines.append(f"### {name}（{code}）")
            lines.append("")
            lines.append(f"- CAGR：{fmt_pct(r.get('cagr_pct'))} | 最大回撤：{fmt_pct(r.get('max_drawdown_pct'))} | 总分：{r['total_score']:.1f} | 梯队：{r.get('tier', '')}")
            lines.append("")
            lines.append(f"![vs基准](charts/对比基准_{code}.png)")
            lines.append("")
            lines.append(f"![跟踪偏离](charts/跟踪偏离_{code}.png)")
            lines.append("")

    # 数据来源
    lines.append("## 数据来源")
    lines.append("")
    lines.append("- 基金净值：东方财富历史净值接口，手工复算分红再投净值（口径与全收益指数一致）")
    lines.append("- 指数数据：中证指数官网全收益指数")
    lines.append("- 基金规模：中证指数官网跟踪产品数据")
    lines.append("- 原始净值数据：`sources/fund-nav-correct/`")
    lines.append("- 计算方法：`基金全收益计算方法说明.md`")
    lines.append("- 计算结果：`基金对比_指标及排名.json`")
    lines.append("")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"✓ 报告已生成: {OUTPUT}")
    print(f"  共{len(group_5y)}只5年组 + {len(group_2y)}只2年组 + {len(obs)}只观察池")


if __name__ == "__main__":
    generate_report()
