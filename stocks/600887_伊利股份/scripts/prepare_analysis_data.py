#!/usr/bin/env python3
"""Prepare verified analysis datasets for Yili (600887.SH).

Annual income/ROE: Tonghuashun main_year.xls.
Balance sheet/cash flow/valuation: Eastmoney API.
Contract liabilities, deposit products and long-term debt: annual-report PDF notes.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import requests
from python_calamine import CalamineWorkbook

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"
API = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
SECUCODE = "600887.SH"


def fetch(report: str, page_size: int = 5000, sort_column: str = "REPORT_DATE") -> list[dict]:
    params = {
        "reportName": report,
        "columns": "ALL",
        "filter": f'(SECUCODE="{SECUCODE}")',
        "pageSize": page_size,
        "sortColumns": sort_column,
        "sortTypes": "-1",
        "source": "HSF10",
        "client": "PC",
    }
    response = requests.get(API, params=params, timeout=60)
    response.raise_for_status()
    payload = response.json()
    if not payload.get("success") or not payload.get("result"):
        raise RuntimeError(f"Eastmoney request failed: {report}: {payload}")
    return payload["result"]["data"]


def annual_rows(rows: list[dict]) -> dict[int, dict]:
    result: dict[int, dict] = {}
    for row in rows:
        date = pd.to_datetime(row["REPORT_DATE"])
        if date.month == 12 and date.day == 31 and date.year not in result:
            result[date.year] = row
    return result


def read_year_xls() -> dict[str, dict[int, object]]:
    path = BASE / "600887_main_year.xls"
    rows = CalamineWorkbook.from_path(str(path)).get_sheet_by_index(0).to_python()
    years = [int(value) for value in rows[0][1:] if value]
    return {
        str(row[0]): dict(zip(years, row[1 : 1 + len(years)]))
        for row in rows[1:]
        if row and row[0]
    }


def pct(value: object) -> float | None:
    if value in (None, "", "--"):
        return None
    return float(str(value).replace("%", ""))


# Official annual-report note values, in CNY. Deposits include only explicitly
# identified large-denomination certificates of deposit / term deposits.
CONTRACT_LIABILITY = {
    2020: 6_055_897_909.28,
    2021: 7_891_327_615.01,
    2022: 8_912_550_921.83,
    2023: 8_695_772_664.08,
    2024: 12_072_785_359.81,
    2025: 10_564_239_506.92,
}
DEPOSITS = {
    2020: 0.0,
    2021: 0.0,
    2022: 6_235_858_855.55,
    2023: 17_630_148_346.08,
    2024: 7_646_992_933.15 + 11_826_346_397.86 + 27_976_779_910.00,
    2025: 10_872_708_266.94 + 13_553_651_021.36 + 28_108_793_007.06,
}
LONG_LOAN = {
    2020: 1_375_031_694.72,
    2021: 5_380_176_540.25,
    2022: 9_298_211_409.85,
    2023: 11_705_395_738.36,
    2024: 4_686_530_047.22,
    2025: 472_479_632.72,
}
BONDS = {
    2020: 3_762_450_000.00,
    2021: 3_187_850_000.00,
    2022: 3_482_300_000.00,
    2023: 3_541_350_000.00,
    # 2024 current-period column is blank; 3.54135bn is the comparative 2023 balance.
    2024: 0.0,
    2025: 0.0,
}


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    xls = read_year_xls()
    balance = annual_rows(fetch("RPT_DMSK_FN_BALANCE", 500))
    cashflow = annual_rows(fetch("RPT_DMSK_FN_CASHFLOW", 500))

    output = []
    for year in range(2020, 2026):
        bal = balance[year]
        cf = cashflow[year]
        assets = bal["TOTAL_ASSETS"]
        equity = bal["TOTAL_EQUITY"]
        prev_assets = balance.get(year - 1, bal)["TOTAL_ASSETS"]
        prev_equity = balance.get(year - 1, bal)["TOTAL_EQUITY"]
        revenue = float(xls["营业总收入(元)"][year])
        net_profit = float(xls["净利润(元)"][year])
        monetary = float(bal["MONETARYFUNDS"])
        trading = {
            2020: 123_219_805.15,
            2021: 37_213_241.15,
            2022: 30_150_175.79,
            2023: 11_457_348.28,
            2024: 6_121_518.30,
            2025: 3_300_546.52,
        }[year]
        cash_position = monetary + DEPOSITS[year] + trading - LONG_LOAN[year] - BONDS[year]
        cfo = float(cf["NETCASH_OPERATE"])
        capex = float(cf["CONSTRUCT_LONG_ASSET"])
        output.append(
            {
                "年份": year,
                "营收": revenue / 1e8,
                "净利润": net_profit / 1e8,
                "扣非净利润": float(xls["扣非净利润(元)"][year]) / 1e8,
                "净资产收益率": pct(xls["净资产收益率"][year]),
                "销售净利率": pct(xls["销售净利率"][year]),
                "销售毛利率": pct(xls["销售毛利率"][year]),
                "总资产周转率": revenue / ((assets + prev_assets) / 2),
                "权益乘数": ((assets + prev_assets) / 2) / ((equity + prev_equity) / 2),
                "经营现金流": cfo / 1e8,
                "资本开支": capex / 1e8,
                "自由现金流": (cfo - capex) / 1e8,
                "资产负债率": pct(xls["资产负债率"][year]),
                "应收账款": float(bal["ACCOUNTS_RECE"]) / 1e8,
                "存货": float(bal["INVENTORY"]) / 1e8,
                "合同负债": CONTRACT_LIABILITY[year] / 1e8,
                "货币资金": monetary / 1e8,
                "大额存单及定期存款": DEPOSITS[year] / 1e8,
                "交易性金融资产": trading / 1e8,
                "长期借款": LONG_LOAN[year] / 1e8,
                "应付债券": BONDS[year] / 1e8,
                "现金头寸_近似": cash_position / 1e8,
            }
        )
    annual = pd.DataFrame(output)
    annual.to_csv(DATA / "annual_core.csv", index=False)

    product = pd.DataFrame(
        [
            ["液体乳", 704.2248001397, -6.11, 31.43],
            ["奶粉及奶制品", 327.6863471063, 10.42, 41.58],
            ["冷饮产品", 98.2249866985, 12.63, 37.89],
            ["其他", 15.3167944294, 112.26, 1.78],
        ],
        columns=["业务", "收入_亿元", "同比_%", "毛利率_%"],
    )
    product.to_csv(DATA / "product_structure.csv", index=False)

    valuation = pd.DataFrame(fetch("RPT_VALUEANALYSIS_DET", 5000, "TRADE_DATE"))
    valuation["TRADE_DATE"] = pd.to_datetime(valuation["TRADE_DATE"])
    valuation = valuation.sort_values("TRADE_DATE")
    valuation.to_csv(DATA / "valuation_history.csv", index=False)
    latest = valuation.iloc[-1]
    ten_year = valuation[valuation["TRADE_DATE"] >= latest["TRADE_DATE"] - pd.DateOffset(years=10)]
    pe_series = pd.to_numeric(ten_year["PE_TTM"], errors="coerce")
    pe_series = pe_series[(pe_series > 0) & pe_series.notna()]
    snapshot = {
        "trade_date": latest["TRADE_DATE"].strftime("%Y-%m-%d"),
        "close": float(latest["CLOSE_PRICE"]),
        "market_cap_yi": float(latest["TOTAL_MARKET_CAP"]) / 1e8,
        "total_shares_yi": float(latest["TOTAL_SHARES"]) / 1e8,
        "pe_ttm": float(latest["PE_TTM"]),
        "pb_mrq": float(latest["PB_MRQ"]),
        "pe_10y_percentile": float((pe_series <= float(latest["PE_TTM"])).mean() * 100),
        "pe_10y_min": float(pe_series.min()),
        "pe_10y_median": float(pe_series.median()),
        "pe_10y_max": float(pe_series.max()),
        "dividend_per_share_2025": 1.38,
        "dividend_yield_2025_pct": 1.38 / float(latest["CLOSE_PRICE"]) * 100,
        "financial_cutoff": "2026Q1",
    }
    (DATA / "market_snapshot.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    print(annual.to_string(index=False))
    print(product.to_string(index=False))
    print(json.dumps(snapshot, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
