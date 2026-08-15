#!/usr/bin/env python3
"""采集并整理同花顺移动端ETF历史前十大持仓。"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
from collections import defaultdict
from pathlib import Path

API_TEMPLATE = "https://fund.10jqka.com.cn/bff-server/v1/fund/position_rank?fund_code={code}"
PAGE_TEMPLATE = (
    "https://fund.10jqka.com.cn/fefund/fundAssetTrace/ifundapp_web/public/"
    "positionReview.html?fundCode={code}&share=true"
)
USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 Mobile/15E148 MicroMessenger/8.0"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="采集同花顺ETF历史前十大持仓")
    parser.add_argument("fund_code", help="基金代码，如512890")
    parser.add_argument("--output-dir", type=Path, required=True, help="输出目录")
    parser.add_argument("--input-json", type=Path, help="使用已保存原始JSON离线整理")
    return parser.parse_args()


def download(fund_code: str) -> dict:
    api_url = API_TEMPLATE.format(code=fund_code)
    page_url = PAGE_TEMPLATE.format(code=fund_code)
    command = [
        "curl", "-L", "--http1.1", "-sS", "--retry", "3",
        "--retry-all-errors", "--max-time", "120", "-A", USER_AGENT,
        "-H", f"Referer: {page_url}", api_url,
    ]
    result = subprocess.run(command, check=True, capture_output=True)
    return json.loads(result.stdout)


def load_payload(fund_code: str, input_json: Path | None) -> dict:
    payload = (
        json.loads(input_json.read_text(encoding="utf-8"))
        if input_json
        else download(fund_code)
    )
    if payload.get("status_code") != 0:
        raise RuntimeError(payload.get("status_msg") or "接口返回失败")
    if "pastYearRate" not in payload.get("data", {}):
        raise ValueError("接口缺少 data.pastYearRate")
    return payload


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def collect(payload: dict) -> tuple[list[dict], list[dict], list[dict], dict]:
    periods = payload["data"]["pastYearRate"]
    available = {
        report_date: data
        for report_date, data in periods.items()
        if data.get("heavyStock")
    }
    if not available:
        raise ValueError("接口没有有效前十大持仓")

    holding_rows: list[dict] = []
    industry_rows: list[dict] = []
    change_rows: list[dict] = []

    for report_date in sorted(available):
        data = available[report_date]
        stocks = data["heavyStock"]
        top_total = float(data["share_per"])
        calculated_total = sum(float(s.get("marketValueRatio") or 0) for s in stocks)
        if len(stocks) != 10:
            raise ValueError(f"{report_date}: 前十大持仓数量不是10")
        if abs(calculated_total - top_total) > 0.02:
            raise ValueError(f"{report_date}: 前十大持仓合计不一致")

        industry_actual: dict[str, float] = defaultdict(float)
        for rank, stock in enumerate(stocks, start=1):
            nav_weight = float(stock.get("marketValueRatio") or 0)
            industry_actual[stock["industry"]] += nav_weight
            holding_rows.append({
                "报告期": report_date,
                "排名": rank,
                "证券代码": stock["sec_code"],
                "证券名称": stock["sec_name"],
                "同花顺行业大类": stock["industry"],
                "占基金净值比例(%)": f"{nav_weight:.2f}",
                "前十大持仓合计(%)": f"{top_total:.2f}",
            })

        api_industry = {
            item["industry"]: float(item["rate"])
            for item in data.get("shareClassPosition", [])
        }
        if abs(sum(api_industry.values()) - 100) > 0.02:
            raise ValueError(f"{report_date}: API行业构成合计不为100%")
        for industry, actual_weight in sorted(
            industry_actual.items(), key=lambda item: item[1], reverse=True
        ):
            normalized = actual_weight / top_total * 100
            api_rate = api_industry.get(industry)
            if api_rate is None or abs(normalized - api_rate) > 0.06:
                raise ValueError(f"{report_date}: {industry}行业构成无法复核")
            industry_rows.append({
                "报告期": report_date,
                "同花顺行业大类": industry,
                "前十大中占比(%)": f"{api_rate:.2f}",
                "占基金净值比例(%)": f"{actual_weight:.2f}",
                "前十大持仓合计(%)": f"{top_total:.2f}",
            })

    report_dates = sorted(available)
    for previous_date, current_date in zip(report_dates, report_dates[1:]):
        previous = {s["sec_code"]: s for s in available[previous_date]["heavyStock"]}
        current = {s["sec_code"]: s for s in available[current_date]["heavyStock"]}
        added = [f'{current[c]["sec_code"]}_{current[c]["sec_name"]}' for c in current.keys() - previous.keys()]
        removed = [f'{previous[c]["sec_code"]}_{previous[c]["sec_name"]}' for c in previous.keys() - current.keys()]
        change_rows.append({
            "上期报告期": previous_date,
            "本期报告期": current_date,
            "连续进入前十大数量": len(current.keys() & previous.keys()),
            "新进入前十大": "；".join(sorted(added)),
            "退出前十大": "；".join(sorted(removed)),
            "本期前十大持仓合计(%)": f'{float(available[current_date]["share_per"]):.2f}',
        })

    summary = {
        "接口报告期数": len(periods),
        "空报告期": [d for d, data in periods.items() if not data.get("heavyStock")],
        "有效报告期数": len(available),
        "起始报告期": report_dates[0],
        "最新报告期": report_dates[-1],
        "持仓明细行数": len(holding_rows),
        "季度变化行数": len(change_rows),
    }
    return holding_rows, industry_rows, change_rows, summary


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    payload = load_payload(args.fund_code, args.input_json)
    holdings, industries, changes, summary = collect(payload)
    prefix = args.fund_code

    (args.output_dir / f"{prefix}_position_rank_raw.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    write_csv(args.output_dir / f"{prefix}_季度前十大持仓.csv", [
        "报告期", "排名", "证券代码", "证券名称", "同花顺行业大类",
        "占基金净值比例(%)", "前十大持仓合计(%)",
    ], holdings)
    write_csv(args.output_dir / f"{prefix}_前十大持仓行业构成.csv", [
        "报告期", "同花顺行业大类", "前十大中占比(%)",
        "占基金净值比例(%)", "前十大持仓合计(%)",
    ], industries)
    write_csv(args.output_dir / f"{prefix}_季度前十大持仓变化.csv", [
        "上期报告期", "本期报告期", "连续进入前十大数量",
        "新进入前十大", "退出前十大", "本期前十大持仓合计(%)",
    ], changes)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
