#!/usr/bin/env python3
"""为ETF最新一期前十大持仓采集年度盈利与分红指标。"""

from __future__ import annotations

import argparse
import csv
import json
import math
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_DIR = Path(__file__).resolve().parent
MAIN_URL = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
BONUS_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://emweb.securities.eastmoney.com/",
}


def fetch_json(url: str, params: dict[str, str | int], retries: int = 3) -> dict:
    request = Request(f"{url}?{urlencode(params)}", headers=HEADERS)
    for attempt in range(retries):
        try:
            with urlopen(request, timeout=30) as response:
                return json.load(response)
        except Exception:
            if attempt + 1 == retries:
                raise
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError("unreachable")


def result_rows(payload: dict) -> list[dict]:
    result = payload.get("result") or {}
    return result.get("data") or []


def exchange(code: str) -> str:
    return "SH" if code.startswith(("5", "6", "9")) else "SZ"


def get_financials(code: str) -> list[dict]:
    params = {
        "reportName": "RPT_F10_FINANCE_MAINFINADATA",
        "columns": "ALL",
        "filter": f'(SECUCODE="{code}.{exchange(code)}")',
        "pageSize": 80,
        "sortColumns": "REPORT_DATE",
        "sortTypes": "-1",
        "source": "HSF10",
        "client": "PC",
    }
    return result_rows(fetch_json(MAIN_URL, params))


def get_dividends(code: str) -> list[dict]:
    params = {
        "reportName": "RPT_SHAREBONUS_DET",
        "columns": "ALL",
        "filter": f'(SECURITY_CODE="{code}")',
        "pageSize": 100,
        "sortColumns": "REPORT_DATE",
        "sortTypes": "-1",
        "source": "WEB",
        "client": "WEB",
    }
    return result_rows(fetch_json(BONUS_URL, params))


def as_float(value) -> float | None:
    if value in (None, ""):
        return None
    number = float(value)
    return None if math.isnan(number) else number


def fmt(value: float | None, digits: int = 2) -> str:
    return "" if value is None else f"{value:.{digits}f}"


def collect(etf_code: str, report_year: int) -> dict:
    etf_dir = BASE_DIR / etf_code
    holdings_path = etf_dir / f"{etf_code}_季度前十大持仓.csv"
    holdings = list(csv.DictReader(holdings_path.open(encoding="utf-8-sig")))
    latest_period = max(row["报告期"] for row in holdings)
    latest = [row for row in holdings if row["报告期"] == latest_period]
    if len(latest) != 10:
        raise ValueError(f"{etf_code} {latest_period}不是10只持仓")

    output_rows = []
    for holding in latest:
        code = holding["证券代码"]
        annual = {
            int(row["REPORT_DATE"][:4]): row
            for row in get_financials(code)
            if row.get("REPORT_TYPE") == "年报" and row.get("REPORT_DATE")
        }
        current = annual.get(report_year)
        base = annual.get(report_year - 4)
        if current is None:
            raise ValueError(f"{code}缺少{report_year}年报数据")

        profit = as_float(current.get("PARENTNETPROFIT"))
        base_profit = as_float(base.get("PARENTNETPROFIT")) if base else None
        cagr = None
        if profit is not None and base_profit is not None and profit > 0 and base_profit > 0:
            cagr = ((profit / base_profit) ** 0.25 - 1) * 100

        dps = 0.0
        dividend_years = set()
        for record in get_dividends(code):
            report_date = record.get("REPORT_DATE")
            cash_per_ten = as_float(record.get("PRETAX_BONUS_RMB"))
            if not report_date or cash_per_ten is None or cash_per_ten <= 0:
                continue
            year = int(report_date[:4])
            dividend_years.add(year)
            if year == report_year:
                dps += cash_per_ten / 10

        eps = as_float(current.get("EPSJB"))
        payout = dps / eps * 100 if eps and eps > 0 else None
        output_rows.append(
            {
                "证券代码": code,
                "证券名称": holding["证券名称"],
                "同花顺行业大类": holding["同花顺行业大类"],
                f"{latest_period[:4]}Q{(int(latest_period[4:6]) - 1) // 3 + 1}基金净值权重(%)": holding["占基金净值比例(%)"],
                f"{report_year}归母净利同比(%)": fmt(as_float(current.get("PARENTNETPROFITTZ"))),
                f"{report_year - 4}-{report_year}归母净利CAGR(%)": fmt(cagr),
                f"{report_year}加权ROE(%)": fmt(as_float(current.get("ROEJQ"))),
                f"{report_year}基本EPS(元)": fmt(eps),
                f"{report_year}每股税前分红(元)": fmt(dps, 3),
                f"{report_year}分红支付率(%)": fmt(payout, 1),
                "接口可见分红年份数": len(dividend_years),
            }
        )
        time.sleep(0.1)

    output_path = etf_dir / f"{etf_code}_{latest_period[:4]}Q{(int(latest_period[4:6]) - 1) // 3 + 1}前十大盈利分红_{report_year}.csv"
    with output_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=output_rows[0].keys())
        writer.writeheader()
        writer.writerows(output_rows)

    return {
        "ETF代码": etf_code,
        "最新报告期": latest_period,
        "输出文件": str(output_path),
        "证券数量": len(output_rows),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("etf_codes", nargs="+", help="ETF代码，可一次传入多个")
    parser.add_argument("--report-year", type=int, default=2025)
    args = parser.parse_args()
    print(json.dumps([collect(code, args.report_year) for code in args.etf_codes], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
