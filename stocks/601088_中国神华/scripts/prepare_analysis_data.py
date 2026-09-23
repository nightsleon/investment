#!/usr/bin/env python3
"""Prepare verified analysis datasets for China Shenhua (601088.SH)."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import requests
from python_calamine import CalamineWorkbook

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"
API = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
SECUCODE = "601088.SH"
YEARS = range(2020, 2026)

# Official annual-report balance sheets. 2024 figures use the 2025 report's restated comparative.
LONG_LOAN = {2020: 50_251e6, 2021: 49_193e6, 2022: 38_438e6, 2023: 29_636e6, 2024: 31_682e6, 2025: 28_268e6}
LONG_BONDS = {2020: 3_241e6, 2021: 3_172e6, 2022: 3_453e6, 2023: 2_972e6, 2024: 0.0, 2025: 0.0}
TRADING_ASSETS = {2020: 0.0, 2021: 0.0, 2022: 0.0, 2023: 24_906.72, 2024: 17_302e6, 2025: 0.0}
CONTRACT_LIABILITY = {2020: 5_256e6, 2021: 6_864e6, 2022: 5_597e6, 2023: 7_208e6, 2024: 4_001e6, 2025: 3_810e6}


def load_json(name: str) -> list[dict]:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def latest_annual(rows: list[dict]) -> dict[int, dict]:
    frame = pd.DataFrame(rows)
    frame["REPORT_DATE"] = pd.to_datetime(frame["REPORT_DATE"])
    frame["NOTICE_DATE"] = pd.to_datetime(frame["NOTICE_DATE"])
    frame = frame[(frame["REPORT_DATE"].dt.month == 12) & (frame["REPORT_DATE"].dt.day == 31)]
    frame = frame.sort_values(["REPORT_DATE", "NOTICE_DATE"]).groupby(frame["REPORT_DATE"].dt.year).tail(1)
    return {int(row.REPORT_DATE.year): row.to_dict() for _, row in frame.iterrows()}


def read_year_xls() -> dict[str, dict[int, object]]:
    rows = CalamineWorkbook.from_path(str(DATA / "601088_main_year.xls")).get_sheet_by_index(0).to_python()
    years = [int(v) for v in rows[0][1:] if v]
    return {str(row[0]): dict(zip(years, row[1 : 1 + len(years)])) for row in rows[1:] if row and row[0]}


def pct(value: object) -> float:
    return float(str(value).replace("%", ""))


def fetch_latest(secucode: str) -> dict:
    params = {"reportName": "RPT_VALUEANALYSIS_DET", "columns": "ALL", "filter": f'(SECUCODE="{secucode}")',
              "pageSize": 1, "sortColumns": "TRADE_DATE", "sortTypes": "-1", "source": "HSF10", "client": "PC"}
    payload = requests.get(API, params=params, timeout=60).json()
    return payload["result"]["data"][0]


def main() -> None:
    xls = read_year_xls()
    balance = latest_annual(load_json("RPT_DMSK_FN_BALANCE.json"))
    cashflow = latest_annual(load_json("RPT_DMSK_FN_CASHFLOW.json"))
    output = []
    for year in YEARS:
        bal, cf = balance[year], cashflow[year]
        prev = balance[year - 1]
        assets = float(bal["TOTAL_ASSETS"]); prev_assets = float(prev["TOTAL_ASSETS"])
        equity = float(bal["TOTAL_EQUITY"]); prev_equity = float(prev["TOTAL_EQUITY"])
        revenue = float(xls["营业总收入(元)"][year]); net_profit = float(xls["净利润(元)"][year])
        monetary = float(bal["MONETARYFUNDS"]); cfo = float(cf["NETCASH_OPERATE"]); capex = float(cf["CONSTRUCT_LONG_ASSET"])
        cash_position = monetary + TRADING_ASSETS[year] - LONG_LOAN[year] - LONG_BONDS[year]
        output.append({
            "年份": year, "营收": revenue / 1e8, "净利润": net_profit / 1e8,
            "扣非净利润": float(xls["扣非净利润(元)"][year]) / 1e8,
            "净资产收益率": pct(xls["净资产收益率"][year]), "简单ROE": net_profit / ((equity + prev_equity) / 2) * 100,
            "销售净利率": pct(xls["销售净利率"][year]), "净利率": pct(xls["销售净利率"][year]),
            "销售毛利率": pct(xls["销售毛利率"][year]), "毛利率": pct(xls["销售毛利率"][year]),
            "总资产周转率": revenue / ((assets + prev_assets) / 2), "权益乘数": ((assets + prev_assets) / 2) / ((equity + prev_equity) / 2),
            "经营现金流": cfo / 1e8, "资本开支": capex / 1e8, "自由现金流": (cfo - capex) / 1e8,
            "资产负债率": pct(xls["资产负债率"][year]), "应收账款": float(bal["ACCOUNTS_RECE"]) / 1e8,
            "存货": float(bal["INVENTORY"]) / 1e8, "合同负债": CONTRACT_LIABILITY[year] / 1e8,
            "货币资金": monetary / 1e8, "交易性金融资产": TRADING_ASSETS[year] / 1e8,
            "长期借款": LONG_LOAN[year] / 1e8, "应付债券": LONG_BONDS[year] / 1e8, "现金头寸_近似": cash_position / 1e8,
        })
    annual = pd.DataFrame(output)
    annual.to_csv(DATA / "annual_core.csv", index=False)

    # 2025 segment data before inter-segment elimination, from the annual report.
    product = pd.DataFrame([
        ["煤炭", 2212.32, -17.7, 30.1, 465.97], ["发电", 891.39, -7.1, 18.0, 126.27],
        ["铁路", 437.10, 1.4, 37.9, 129.01], ["港口", 70.20, 2.6, 46.7, 26.31],
        ["航运", 39.89, -20.2, 11.5, 2.69], ["煤化工", 57.22, 1.6, 7.2, 0.58],
    ], columns=["业务", "收入_亿元", "同比_%", "毛利率_%", "利润总额_亿元"])
    product.to_csv(DATA / "product_structure.csv", index=False)

    valuation = pd.DataFrame(load_json("valuation_history_raw.json"))
    valuation["TRADE_DATE"] = pd.to_datetime(valuation["TRADE_DATE"])
    valuation = valuation.sort_values("TRADE_DATE")
    valuation.to_csv(DATA / "valuation_history.csv", index=False)
    latest = valuation.iloc[-1]
    window = valuation[valuation["TRADE_DATE"] >= latest["TRADE_DATE"] - pd.DateOffset(years=10)].copy()
    pe = pd.to_numeric(window["PE_TTM"], errors="coerce"); pe = pe[(pe > 0) & pe.notna()]
    current_pe = float(latest["PE_TTM"]); close = float(latest["CLOSE_PRICE"])
    total_shares = 21_689_434_304; a_shares = 18_311_952_304; h_shares = 3_377_482_000
    h_close_hkd = 43.60; hkd_cny = 0.863834
    strict_equity = a_shares * close + h_shares * h_close_hkd * hkd_cny
    deduct_ttm = 485.89 - 117.05 + 107.12
    cash_q1 = 1185.85 - 296.73
    total_dividend_ps = 0.98 + 1.03
    snapshot = {
        "trade_date": str(latest["TRADE_DATE"].date()), "a_close": close, "h_close_hkd": h_close_hkd,
        "hkd_cny": hkd_cny, "total_shares_yi": total_shares / 1e8, "a_shares_yi": a_shares / 1e8, "h_shares_yi": h_shares / 1e8,
        "eastmoney_a_equivalent_market_cap_yi": float(latest["TOTAL_MARKET_CAP"]) / 1e8,
        "strict_ah_equity_value_yi_cny": strict_equity / 1e8, "pe_ttm_parent": current_pe, "pb_mrq": float(latest["PB_MRQ"]),
        "pe_10y_percentile": float((pe <= current_pe).mean() * 100), "pe_10y_min": float(pe.min()),
        "pe_10y_p25": float(pe.quantile(0.25)), "pe_10y_median": float(pe.median()), "pe_10y_p75": float(pe.quantile(0.75)), "pe_10y_max": float(pe.max()),
        "reported_deduct_profit_ttm_yi": deduct_ttm, "reported_deduct_pe_a_equivalent": float(latest["TOTAL_MARKET_CAP"]) / 1e8 / deduct_ttm,
        "proforma_2024_deduct_profit_yi": 668.51, "proforma_2024_pe_strict_ah": strict_equity / 1e8 / 668.51,
        "dividend_per_existing_share_2025": total_dividend_ps, "dividend_yield_existing_share_pct": total_dividend_ps / close * 100,
        "cash_position_2026q1_yi": cash_q1, "cash_position_per_post_issue_share": cash_q1 / (total_shares / 1e8),
        "short_borrowing_2026q1_yi": 867.00, "financial_cutoff": "2026Q1（新资产4月起纳入运营口径，Q1利润尚不可代表重组后完整盈利）",
    }
    (DATA / "market_snapshot.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    peer_specs = [("601088.SH", "煤电运化一体化"), ("601225.SH", "优质动力煤"), ("601898.SH", "煤炭全产业链"), ("600188.SH", "煤炭/煤化工")]
    peers = []
    for secucode, role in peer_specs:
        row = fetch_latest(secucode)
        peers.append({"代码": secucode, "公司": row["SECURITY_NAME_ABBR"], "日期": str(row["TRADE_DATE"])[:10],
                      "市值_亿元": float(row["TOTAL_MARKET_CAP"]) / 1e8, "PE_TTM": pd.to_numeric(row["PE_TTM"], errors="coerce"),
                      "PB_MRQ": pd.to_numeric(row["PB_MRQ"], errors="coerce"), "定位": role})
    pd.DataFrame(peers).to_csv(DATA / "peer_snapshot.csv", index=False)

    acquisition = {
        "final_transaction_price_yi": 1335.98, "share_consideration_yi": 400.795043, "cash_consideration_yi": 935.188435,
        "asset_issue_price": 29.40, "asset_issue_shares": 1_363_248_446, "placement_issue_price": 43.70,
        "placement_issue_shares": 457_665_903, "placement_net_proceeds_yi": 199.674927,
        "post_issue_total_shares": total_shares, "target_2024_revenue_yi": 1139.74, "target_2024_deduct_profit_yi": 94.28,
        "proforma_2024_revenue_yi": 4321.83, "proforma_2024_deduct_profit_yi": 668.51,
        "proforma_2025_1_7_revenue_yi": 2065.09, "proforma_2025_1_7_deduct_profit_yi": 326.37,
        "proforma_2024_debt_asset_ratio_pct": 43.60, "resource_after_yi_ton": 684.9, "recoverable_after_yi_ton": 345.0,
        "source": "2026-02-13重组报告书、2026-03-18及2026-04-09实施公告",
    }
    (DATA / "acquisition_snapshot.json").write_text(json.dumps(acquisition, ensure_ascii=False, indent=2), encoding="utf-8")
    print(annual.to_string(index=False)); print(product.to_string(index=False)); print(json.dumps(snapshot, ensure_ascii=False, indent=2)); print(pd.DataFrame(peers).to_string(index=False))


if __name__ == "__main__":
    main()
