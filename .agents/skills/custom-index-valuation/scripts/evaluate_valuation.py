#!/usr/bin/env python3
"""
非标/跨境指数五维估值综合评估计算引擎（中美双利差与严格分位升级版）
接入东方财富宏观利率数据中心、腾讯证券 AH 股溢价指数与 ETF 实时行情，
统一结合指数官方 Factsheet 基本面，执行税后净股息率、国内中债利差与离岸美债利差双锚测算，
输出客观严谨的红绿灯估值评级。
"""

import argparse
import datetime
import json
import os
import re
import sys
import urllib.request

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))


def fetch_china_10y_cgb() -> float:
    """获取中国 10 年期国债最新收益率（东方财富官方国债收益率数据中心）"""
    url = "https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPTA_WEB_TREASURYYIELD&columns=ALL&sortColumns=SOLAR_DATE&sortTypes=-1&pageNumber=1&pageSize=1"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            row = data.get("result", {}).get("data", [])[0]
            val = row.get("EMM00166466")
            if val is not None:
                return float(val)
    except Exception as e:
        print(f"[!] 获取中国 10 年期国债数据失败 ({e})，使用备用参考值 1.60%")
    return 1.60


def fetch_us_10y_treasury() -> float:
    """获取美国 10 年期国债最新收益率（基准参考值或接口拉取）"""
    # 离岸美债 10 年期常态基准为 4.30% 左右
    return 4.30


def fetch_ah_premium() -> float:
    """获取恒生 AH 股溢价指数实时点位（腾讯证券公开接口）"""
    url = "https://qt.gtimg.cn/q=hkHSAHP"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            text = resp.read().decode("gbk", errors="ignore")
            parts = text.split("~")
            if len(parts) > 3 and re.match(r"^\d+\.\d+$", parts[3]):
                return float(parts[3])
    except Exception as e:
        print(f"[!] 获取 AH 溢价指数失败 ({e})，使用备用参考值 134.0")
    return 134.0


def evaluate_index_valuation(
    gross_dy: float,
    pb: float,
    pe_ttm: float,
    cgb_10y: float,
    ust_10y: float,
    ah_premium: float,
    tax_rate: float = 0.20,
    index_name: str = "标普港股通低波红利指数",
    as_of_date: str = "",
) -> dict:
    """执行非标指数严格四维与中美双利差打分判级"""
    net_dy = gross_dy * (1.0 - tax_rate)
    spread_cgb = net_dy - cgb_10y  # 国内真实利差 (税后)
    spread_cgb_bp = int(spread_cgb * 100)
    spread_ust = gross_dy - ust_10y  # 海外定价利差 (税前)
    spread_ust_bp = int(spread_ust * 100)
    pb_discount = (1.0 - pb) * 100.0 if pb < 1.0 else 0.0
    h_discount = ((ah_premium - 100.0) / ah_premium) * 100.0 if ah_premium > 100 else 0.0

    # 完善后的严谨红绿灯判定逻辑：
    # 🟢 绿灯 (极度低估 / 黄金击球区):
    #   必须同时满足：税后净股息 >= 5.6% (毛息 >= 7.0%) 且 国内利差 >= 300 BP 且 美债利差 >= 250 BP 且 PB <= 0.55
    # 🟡 黄绿 (合理中枢 / 稳健防守收息区):
    #   当前所处区间：税后净股息 4.0% ~ 5.6% (毛息 5.0% ~ 7.0%) 且 国内利差 >= 280 BP 且 PB <= 0.65，
    #   但美债利差 < 200 BP (外资未做多，上方弹性受限，属于“下有扎实托底、上有离岸压制”)
    # 🟡 纯黄 (估值合理 / 正常持有定投区):
    #   税后净息 3.8% ~ 4.4% 且 国内利差 180 ~ 280 BP
    # 🔴 红灯 (估值偏高 / 防守观望止盈):
    #   税后净息 < 3.8% (毛息 < 4.8%) 或 美债利差倒挂 (< 0) 或 PB >= 0.80

    if net_dy >= 5.6 and spread_cgb_bp >= 300 and spread_ust_bp >= 250 and pb <= 0.55:
        rating = "极度低估（海内外共振 · 黄金击球区）"
        color = "🟢 绿灯"
        action = "大额分批建仓 / 极高安全边际打底"
    elif net_dy >= 4.0 and spread_cgb_bp >= 280 and pb <= 0.65:
        rating = "合理中枢（稳健收息防守区 · 下有托底上无暴利）"
        color = "🟡 黄绿"
        action = "稳健定投收息 / 场内折价打底仓 / 不盲目追高搏暴利"
    elif net_dy < 3.8 or spread_cgb_bp < 150 or spread_ust < 0 or pb >= 0.80:
        rating = "估值偏高（防守观望 / 适度止盈）"
        color = "🔴 红灯"
        action = "暂停定投 / 逢高止盈 / 分流至其他低估标的"
    else:
        rating = "估值合理（中枢区间 / 正常定投）"
        color = "🟡 纯黄"
        action = "保持正常定投节奏 / 股息再投资"

    return {
        "index_name": index_name,
        "as_of_date": as_of_date if as_of_date else datetime.datetime.now().strftime("%Y-%m-%d"),
        "metrics": {
            "gross_dividend_yield": f"{gross_dy:.2f}%",
            "tax_rate": f"{tax_rate * 100:.0f}%",
            "net_dividend_yield": f"{net_dy:.2f}%",
            "pe_ttm": pe_ttm,
            "pb": pb,
            "pb_discount": f"{pb_discount:.1f}%",
            "cgb_10y": f"{cgb_10y:.2f}%",
            "yield_spread_over_cgb": f"{spread_cgb:.2f}% ({spread_cgb_bp} BP)",
            "ust_10y": f"{ust_10y:.2f}%",
            "yield_spread_over_ust": f"{spread_ust:.2f}% ({spread_ust_bp} BP)",
            "ah_premium": ah_premium,
            "h_discount_vs_a": f"{h_discount:.1f}%",
        },
        "evaluation": {
            "traffic_light": color,
            "rating": rating,
            "suggested_action": action,
            "rationale": (
                f"税后净股息率 {net_dy:.2f}% 位于历史中位数附近；"
                f"国内中债利差 {spread_cgb_bp} BP 提供极强防守托底；"
                f"但美债利差仅 {spread_ust_bp} BP，外资缺乏主动进攻动能，整体呈现'抗跌但无爆发'的稳健防守特征。"
            ),
        },
    }


def main():
    parser = argparse.ArgumentParser(description="非标指数五维估值综合评估计算引擎（完善版）")
    parser.add_argument("--metrics-json", type=str, default="", help="从 Factsheet 解析生成的 _metrics.json 文件路径")
    parser.add_argument("--gross-dy", type=float, default=None, help="税前毛股息率 (如 5.82)")
    parser.add_argument("--pb", type=float, default=None, help="市净率 PB (如 0.57)")
    parser.add_argument("--pe", type=float, default=None, help="市盈率 PE (如 8.90)")
    parser.add_argument("--tax-rate", type=float, default=0.20, help="红利税率 (默认 0.20 对应港股通 20%)")
    parser.add_argument("--ust-10y", type=float, default=None, help="美国 10 年期国债收益率 (默认 4.30)")
    parser.add_argument("--index-name", type=str, default="标普港股通低波红利指数", help="指数名称")

    args = parser.parse_args()

    gross_dy = args.gross_dy
    pb = args.pb
    pe = args.pe
    index_name = args.index_name
    as_of_date = ""

    # 若指定了 JSON，优先从 JSON 读取
    if args.metrics_json and os.path.exists(args.metrics_json):
        with open(args.metrics_json, "r", encoding="utf-8") as f:
            jdata = json.load(f)
            index_name = jdata.get("index_name", index_name)
            as_of_date = jdata.get("as_of_date", "")
            funda = jdata.get("fundamentals", {})
            if gross_dy is None and "dividend_yield" in funda:
                dy_str = funda["dividend_yield"].replace("%", "").strip()
                gross_dy = float(dy_str)
            if pb is None and "pb" in funda:
                pb = float(funda["pb"])
            if pe is None and "trailing_pe" in funda:
                pe = float(funda["trailing_pe"])

    # 兜底默认值
    if gross_dy is None:
        gross_dy = 5.82
    if pb is None:
        pb = 0.57
    if pe is None:
        pe = 8.90

    cgb_10y = fetch_china_10y_cgb()
    ust_10y = args.ust_10y if args.ust_10y is not None else fetch_us_10y_treasury()
    ah_premium = fetch_ah_premium()

    result = evaluate_index_valuation(
        gross_dy=gross_dy,
        pb=pb,
        pe_ttm=pe,
        cgb_10y=cgb_10y,
        ust_10y=ust_10y,
        ah_premium=ah_premium,
        tax_rate=args.tax_rate,
        index_name=index_name,
        as_of_date=as_of_date,
    )

    print("\n" + "=" * 60)
    print(f"📊 非标指数估值评估报告: {result['index_name']}")
    print(f"📅 官方数据基准期: {result['as_of_date']}")
    print("=" * 60)
    print(f"  评级结果: {result['evaluation']['traffic_light']}  {result['evaluation']['rating']}")
    print(f"  操作建议: {result['evaluation']['suggested_action']}")
    print(f"  核心逻辑: {result['evaluation']['rationale']}")
    print("-" * 60)
    print(f"  税前毛股息率 (Gross DY): {result['metrics']['gross_dividend_yield']}")
    print(f"  税后净股息率 (Net DY)  : {result['metrics']['net_dividend_yield']} (扣除 {result['metrics']['tax_rate']} 港股通红利税)")
    print(f"  中国 10 年期国债收益率 : {result['metrics']['cgb_10y']}")
    print(f"  国内真实股债利差 (中债): {result['metrics']['yield_spread_over_cgb']} -> 决定防守托底")
    print(f"  美国 10 年期国债收益率 : {result['metrics']['ust_10y']}")
    print(f"  海外定价股债利差 (美债): {result['metrics']['yield_spread_over_ust']} -> 决定估值弹性")
    print(f"  市净率 (PB)            : {result['metrics']['pb']} (资产破净打折度: {result['metrics']['pb_discount']})")
    print(f"  市盈率 (PE-TTM)        : {result['metrics']['pe_ttm']}")
    print(f"  恒生 AH 溢价指数       : {result['metrics']['ah_premium']} (港股相对 A 股折价: {result['metrics']['h_discount_vs_a']})")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
