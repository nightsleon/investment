#!/usr/bin/env python3
"""采集同花顺移动端披露的512890历史前十大持仓。"""

from __future__ import annotations

import csv
import json
import subprocess
from collections import defaultdict
from pathlib import Path

FUND_CODE = "512890"
API_URL = (
    "https://fund.10jqka.com.cn/bff-server/v1/fund/position_rank"
    f"?fund_code={FUND_CODE}"
)
SOURCE_PAGE = (
    "https://fund.10jqka.com.cn/fefund/fundAssetTrace/ifundapp_web/public/"
    f"positionReview.html?fundCode={FUND_CODE}&share=true"
)
BASE_DIR = Path(__file__).resolve().parent
RAW_PATH = BASE_DIR / "512890_position_rank_raw.json"
HOLDINGS_PATH = BASE_DIR / "512890_季度前十大持仓.csv"
INDUSTRY_PATH = BASE_DIR / "512890_前十大持仓行业构成.csv"
CHANGES_PATH = BASE_DIR / "512890_季度前十大持仓变化.csv"


def download() -> dict:
    command = [
        "curl",
        "-L",
        "--http1.1",
        "-sS",
        "--retry",
        "3",
        "--retry-all-errors",
        "--max-time",
        "120",
        "-A",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15 Mobile/15E148 MicroMessenger/8.0",
        "-H",
        f"Referer: {SOURCE_PAGE}",
        API_URL,
    ]
    result = subprocess.run(command, check=True, capture_output=True)
    payload = json.loads(result.stdout)
    if payload.get("status_code") != 0:
        raise RuntimeError(payload.get("status_msg") or "接口返回失败")
    RAW_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    payload = download()
    periods = payload["data"]["pastYearRate"]
    available = {
        report_date: data
        for report_date, data in periods.items()
        if data.get("heavyStock")
    }

    holding_rows = []
    industry_rows = []
    change_rows = []

    for report_date, data in available.items():
        heavy_stock = data["heavyStock"]
        top10_total = float(data["share_per"])
        calculated_total = sum(
            float(stock.get("marketValueRatio") or 0) for stock in heavy_stock
        )
        if len(heavy_stock) != 10:
            raise ValueError(f"{report_date}: 前十大持仓数量不是10")
        if abs(calculated_total - top10_total) > 0.02:
            raise ValueError(f"{report_date}: 前十大持仓合计不一致")

        industry_actual = defaultdict(float)
        for rank, stock in enumerate(heavy_stock, start=1):
            nav_weight = float(stock.get("marketValueRatio") or 0)
            industry_actual[stock["industry"]] += nav_weight
            holding_rows.append(
                {
                    "报告期": report_date,
                    "排名": rank,
                    "证券代码": stock["sec_code"],
                    "证券名称": stock["sec_name"],
                    "同花顺行业大类": stock["industry"],
                    "占基金净值比例(%)": f"{nav_weight:.2f}",
                    "前十大持仓合计(%)": f"{top10_total:.2f}",
                }
            )

        api_industry = {
            item["industry"]: float(item["rate"])
            for item in data.get("shareClassPosition", [])
        }
        if abs(sum(api_industry.values()) - 100) > 0.02:
            raise ValueError(f"{report_date}: API行业构成合计不为100%")
        for industry, actual_weight in sorted(
            industry_actual.items(), key=lambda item: item[1], reverse=True
        ):
            normalized = actual_weight / top10_total * 100
            api_rate = api_industry.get(industry)
            if api_rate is None or abs(normalized - api_rate) > 0.06:
                raise ValueError(f"{report_date}: {industry}行业构成无法复核")
            industry_rows.append(
                {
                    "报告期": report_date,
                    "同花顺行业大类": industry,
                    "前十大中占比(%)": f"{api_rate:.2f}",
                    "占基金净值比例(%)": f"{actual_weight:.2f}",
                    "前十大持仓合计(%)": f"{top10_total:.2f}",
                }
            )

    report_dates = sorted(available)
    for previous_date, current_date in zip(report_dates, report_dates[1:]):
        previous = {
            stock["sec_code"]: stock
            for stock in available[previous_date]["heavyStock"]
        }
        current = {
            stock["sec_code"]: stock
            for stock in available[current_date]["heavyStock"]
        }
        added = [
            f'{current[code]["sec_code"]}_{current[code]["sec_name"]}'
            for code in current.keys() - previous.keys()
        ]
        removed = [
            f'{previous[code]["sec_code"]}_{previous[code]["sec_name"]}'
            for code in previous.keys() - current.keys()
        ]
        change_rows.append(
            {
                "上期报告期": previous_date,
                "本期报告期": current_date,
                "连续进入前十大数量": len(current.keys() & previous.keys()),
                "新进入前十大": "；".join(sorted(added)),
                "退出前十大": "；".join(sorted(removed)),
                "本期前十大持仓合计(%)": f'{float(available[current_date]["share_per"]):.2f}',
            }
        )

    write_csv(
        HOLDINGS_PATH,
        [
            "报告期",
            "排名",
            "证券代码",
            "证券名称",
            "同花顺行业大类",
            "占基金净值比例(%)",
            "前十大持仓合计(%)",
        ],
        holding_rows,
    )
    write_csv(
        INDUSTRY_PATH,
        [
            "报告期",
            "同花顺行业大类",
            "前十大中占比(%)",
            "占基金净值比例(%)",
            "前十大持仓合计(%)",
        ],
        industry_rows,
    )
    write_csv(
        CHANGES_PATH,
        [
            "上期报告期",
            "本期报告期",
            "连续进入前十大数量",
            "新进入前十大",
            "退出前十大",
            "本期前十大持仓合计(%)",
        ],
        change_rows,
    )

    print(
        json.dumps(
            {
                "接口报告期数": len(periods),
                "有效报告期数": len(available),
                "起始报告期": report_dates[0],
                "最新报告期": report_dates[-1],
                "持仓明细行数": len(holding_rows),
                "季度变化行数": len(change_rows),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
