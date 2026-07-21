#!/usr/bin/env python3
"""Build verified analysis datasets for Weixing Share (002003.SZ)."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import requests
from python_calamine import CalamineWorkbook

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"
API = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
SECUCODE = "002003.SZ"
YEARS = range(2020, 2026)

# Official annual-report balance sheets; blank current-period cells are zero.
CONTRACT_LIABILITY = {
    2020: 35_753_587.52,
    2021: 40_664_816.80,
    2022: 49_830_999.95,
    2023: 40_403_059.59,
    2024: 46_181_411.24,
    2025: 41_957_594.80,
}
LONG_LOAN = {
    2020: 14_663_013.86,
    2021: 4_775_908.53,
    2022: 199_351_925.00,
    2023: 98_104_805.06,
    2024: 0.0,
    2025: 0.0,
}
TRADING_ASSETS = {year: 0.0 for year in YEARS}
BONDS = {year: 0.0 for year in YEARS}
RESTRICTED_CASH = {
    2020: 10_785_000.00,
    2021: 10_818_030.00,
    2022: 10_839_735.00,
    2023: 20_840_638.19,
    2024: 16_543_227.10,
    2025: 19_008_312.49,
}


def load_json(name: str) -> list[dict]:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def annual_rows(rows: list[dict]) -> dict[int, dict]:
    result: dict[int, dict] = {}
    for row in rows:
        date = pd.to_datetime(row["REPORT_DATE"])
        if date.month == 12 and date.day == 31 and date.year not in result:
            result[date.year] = row
    return result


def read_year_xls() -> dict[str, dict[int, object]]:
    rows = CalamineWorkbook.from_path(str(DATA / "002003_main_year.xls")).get_sheet_by_index(0).to_python()
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


def fetch_valuation(secucode: str) -> pd.DataFrame:
    params = {
        "reportName": "RPT_VALUEANALYSIS_DET",
        "columns": "ALL",
        "filter": f'(SECUCODE="{secucode}")',
        "pageSize": 5000,
        "sortColumns": "TRADE_DATE",
        "sortTypes": "-1",
        "source": "HSF10",
        "client": "PC",
    }
    response = requests.get(API, params=params, timeout=60)
    response.raise_for_status()
    payload = response.json()
    if not payload.get("success") or not payload.get("result"):
        raise RuntimeError(f"Valuation API failed: {secucode}: {payload}")
    return pd.DataFrame(payload["result"]["data"])


def main() -> None:
    xls = read_year_xls()
    balance = annual_rows(load_json("RPT_DMSK_FN_BALANCE.json"))
    cashflow = annual_rows(load_json("RPT_DMSK_FN_CASHFLOW.json"))

    output: list[dict] = []
    for year in YEARS:
        bal = balance[year]
        cf = cashflow[year]
        assets = float(bal["TOTAL_ASSETS"])
        equity = float(bal["TOTAL_EQUITY"])
        prev_assets = float(balance[year - 1]["TOTAL_ASSETS"])
        prev_equity = float(balance[year - 1]["TOTAL_EQUITY"])
        revenue = float(xls["营业总收入(元)"][year])
        net_profit = float(xls["净利润(元)"][year])
        monetary = float(bal["MONETARYFUNDS"])
        cfo = float(cf["NETCASH_OPERATE"])
        capex = float(cf["CONSTRUCT_LONG_ASSET"])
        cash_position = monetary + TRADING_ASSETS[year] - LONG_LOAN[year] - BONDS[year]
        output.append({
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
            "受限货币资金": RESTRICTED_CASH[year] / 1e8,
            "大额存单及定期存款": 0.0,
            "交易性金融资产": TRADING_ASSETS[year] / 1e8,
            "长期借款": LONG_LOAN[year] / 1e8,
            "应付债券": BONDS[year] / 1e8,
            "现金头寸_近似": cash_position / 1e8,
        })
    annual = pd.DataFrame(output)
    annual.to_csv(DATA / "annual_core.csv", index=False)

    product = pd.DataFrame([
        ["钮扣", 19.8940558808, 1.79, 41.76],
        ["拉链", 25.6027270901, 3.07, 42.99],
        ["其他服饰辅料", 1.7412553786, 6.03, None],
        ["其他", 0.7651106718, 6.84, None],
    ], columns=["业务", "收入_亿元", "同比_%", "毛利率_%"])
    product.to_csv(DATA / "product_structure.csv", index=False)

    valuation = pd.DataFrame(load_json("valuation_history_raw.json"))
    valuation["TRADE_DATE"] = pd.to_datetime(valuation["TRADE_DATE"])
    valuation = valuation.sort_values("TRADE_DATE")
    valuation.to_csv(DATA / "valuation_history.csv", index=False)
    latest = valuation.iloc[-1]
    available = valuation[valuation["TRADE_DATE"] >= latest["TRADE_DATE"] - pd.DateOffset(years=10)]
    pe = pd.to_numeric(available["PE_TTM"], errors="coerce")
    pe = pe[(pe > 0) & pe.notna()]
    current_pe = float(latest["PE_TTM"])
    close = float(latest["CLOSE_PRICE"])
    market_cap = float(latest["TOTAL_MARKET_CAP"])
    shares = float(latest["TOTAL_SHARES"])
    deduct_ttm = (628_571_380.04 - 97_535_484.11 + 88_400_322.47) / 1e8
    cash_position_q1 = 1_267_717_511.75 / 1e8
    snapshot = {
        "trade_date": latest["TRADE_DATE"].strftime("%Y-%m-%d"),
        "close": close,
        "market_cap_yi": market_cap / 1e8,
        "total_shares_yi": shares / 1e8,
        "pe_ttm_parent": current_pe,
        "pb_mrq": float(latest["PB_MRQ"]),
        "pe_available_percentile": float((pe <= current_pe).mean() * 100),
        "pe_history_start": available["TRADE_DATE"].min().strftime("%Y-%m-%d"),
        "pe_history_end": available["TRADE_DATE"].max().strftime("%Y-%m-%d"),
        "pe_available_min": float(pe.min()),
        "pe_available_p10": float(pe.quantile(0.10)),
        "pe_available_p25": float(pe.quantile(0.25)),
        "pe_available_median": float(pe.median()),
        "pe_available_max": float(pe.max()),
        "deduct_profit_ttm_yi": deduct_ttm,
        "deduct_pe_ttm": market_cap / 1e8 / deduct_ttm,
        "dividend_per_share_2025": 0.50,
        "dividend_yield_2025_pct": 0.50 / close * 100,
        "cash_position_2026q1_yi": cash_position_q1,
        "cash_position_per_share_2026q1": cash_position_q1 / (shares / 1e8),
        "short_loan_2026q1_yi": 10.6194265036,
        "financial_cutoff": "2026Q1",
    }
    (DATA / "market_snapshot.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    peers = []
    for secucode, role in [
        ("002003.SZ", "综合服饰辅料/钮扣拉链"),
        ("002098.SZ", "SBS品牌/拉链"),
    ]:
        row = fetch_valuation(secucode).iloc[0]
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
