#!/usr/bin/env python3
"""Prepare verified analysis datasets for Proya (603605.SH)."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import requests
from python_calamine import CalamineWorkbook

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"
API = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
SECUCODE = "603605.SH"
YEARS = range(2020, 2026)


def fetch(report: str, page_size: int = 5000, sort_column: str = "REPORT_DATE", secucode: str = SECUCODE) -> list[dict]:
    params = {
        "reportName": report,
        "columns": "ALL",
        "filter": f'(SECUCODE="{secucode}")',
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
    path = DATA / "603605_main_year.xls"
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


# Official annual-report balance sheets. Blank current-period cells are zero.
CONTRACT_LIABILITY = {
    2020: 30_618_778.99,
    2021: 91_151_985.32,
    2022: 174_602_833.91,
    2023: 301_014_873.58,
    2024: 153_710_588.62,
    2025: 167_287_402.83,
}
TRADING_ASSETS = {year: 0.0 for year in YEARS}
LONG_LOAN = {year: 0.0 for year in YEARS}
BONDS = {
    2020: 0.0,
    2021: 695_586_778.80,
    2022: 724_491_557.93,
    2023: 753_119_902.88,
    2024: 780_011_293.32,
    2025: 804_392_073.95,
}


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    xls = read_year_xls()
    balance = annual_rows(fetch("RPT_DMSK_FN_BALANCE", 500))
    cashflow = annual_rows(fetch("RPT_DMSK_FN_CASHFLOW", 500))

    output = []
    for year in YEARS:
        bal = balance[year]
        cf = cashflow[year]
        assets = float(bal["TOTAL_ASSETS"])
        equity = float(bal["TOTAL_EQUITY"])
        prev_assets = float(balance.get(year - 1, bal)["TOTAL_ASSETS"])
        prev_equity = float(balance.get(year - 1, bal)["TOTAL_EQUITY"])
        revenue = float(xls["营业总收入(元)"][year])
        net_profit = float(xls["净利润(元)"][year])
        monetary = float(bal["MONETARYFUNDS"])
        cash_position = monetary + TRADING_ASSETS[year] - LONG_LOAN[year] - BONDS[year]
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
                "大额存单及定期存款": 0.0,
                "交易性金融资产": TRADING_ASSETS[year] / 1e8,
                "长期借款": LONG_LOAN[year] / 1e8,
                "应付债券": BONDS[year] / 1e8,
                "现金头寸_近似": cash_position / 1e8,
            }
        )
    annual = pd.DataFrame(output)
    annual.to_csv(DATA / "annual_core.csv", index=False)

    product = pd.DataFrame(
        [
            ["珀莱雅", 76.89, -10.39, 73.52],
            ["彩棠", 12.55, 5.37, None],
            ["Off&Relax", 7.44, 102.19, None],
            ["悦芙媞", 3.71, 11.80, None],
            ["原色波塔", 2.56, 125.38, None],
            ["惊时", 0.96, 441.66, None],
            ["其他品牌", 1.74, 6.77, None],
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

    shares = float(latest["TOTAL_SHARES"])
    current_pe = float(latest["PE_TTM"])
    latest_close = float(latest["CLOSE_PRICE"])
    snapshot = {
        "trade_date": latest["TRADE_DATE"].strftime("%Y-%m-%d"),
        "close": latest_close,
        "market_cap_yi": float(latest["TOTAL_MARKET_CAP"]) / 1e8,
        "total_shares_yi": shares / 1e8,
        "pe_ttm": current_pe,
        "pb_mrq": float(latest["PB_MRQ"]),
        "pe_10y_percentile": float((pe_series <= current_pe).mean() * 100),
        "pe_10y_min": float(pe_series.min()),
        "pe_10y_median": float(pe_series.median()),
        "pe_10y_max": float(pe_series.max()),
        "dividend_per_share_2025": 2.00,
        "dividend_yield_2025_pct": 2.00 / latest_close * 100,
        "financial_cutoff": "2026Q1",
    }
    (DATA / "market_snapshot.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    peers = []
    for secucode, role in [
        ("603605.SH", "国货美妆龙头"),
        ("300957.SZ", "敏感肌护肤"),
        ("688363.SH", "生物活性物/护肤"),
        ("600315.SH", "综合日化"),
        ("603983.SH", "眼部护理/彩妆"),
    ]:
        rows = pd.DataFrame(fetch("RPT_VALUEANALYSIS_DET", 100, "TRADE_DATE", secucode))
        row = rows.iloc[0]
        peers.append({
            "代码": secucode,
            "公司": row["SECURITY_NAME_ABBR"],
            "日期": str(row["TRADE_DATE"])[:10],
            "市值_亿元": float(row["TOTAL_MARKET_CAP"]) / 1e8,
            "PE_TTM": pd.to_numeric(row["PE_TTM"], errors="coerce"),
            "定位": role,
        })
    pd.DataFrame(peers).to_csv(DATA / "peer_snapshot.csv", index=False)

    print(annual.to_string(index=False))
    print(product.to_string(index=False))
    print(json.dumps(snapshot, ensure_ascii=False, indent=2))
    print(pd.DataFrame(peers).to_string(index=False))


if __name__ == "__main__":
    main()
