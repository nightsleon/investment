#!/usr/bin/env python3
"""Build verified analysis datasets for Salted Shop (002847.SZ)."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import requests
from python_calamine import CalamineWorkbook

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"
API = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
SECUCODE = "002847.SZ"
YEARS = range(2020, 2026)

# Official annual-report balance sheets; blank current-period cells are zero.
CONTRACT_LIABILITY = {
    2020: 70_855_046.08,
    2021: 63_384_012.94,
    2022: 106_349_691.23,
    2023: 100_170_706.10,
    2024: 89_263_361.66,
    2025: 78_394_739.13,
}
LONG_LOAN = {
    2020: 130_144_444.44,
    2021: 2_000_000.00,
    2022: 137_102_485.69,
    2023: 0.0,
    2024: 260_798_850.50,
    2025: 222_903_609.99,
}
TRADING_ASSETS = {year: 0.0 for year in YEARS}
BONDS = {year: 0.0 for year in YEARS}
RESTRICTED_CASH = {
    2020: 17_000_000.00,
    2021: 20_613_000.20,
    2022: 11_569_948.00,
    2023: 6_314_602.19,
    2024: 3_821_067.46,
    2025: 4_919_067.23,
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


def read_xls(name: str) -> tuple[list[object], dict[str, list[object]]]:
    rows = CalamineWorkbook.from_path(str(DATA / name)).get_sheet_by_index(0).to_python()
    return rows[0][1:], {str(row[0]): row[1:] for row in rows[1:] if row and row[0]}


def pct(value: object) -> float | None:
    if value in (None, "", "--"):
        return None
    return float(str(value).replace("%", ""))


def fetch_valuation(secucode: str) -> pd.DataFrame:
    params = {
        "reportName": "RPT_VALUEANALYSIS_DET",
        "columns": "ALL",
        "filter": f'(SECUCODE="{secucode}")',
        "pageSize": 100,
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
    DATA.mkdir(parents=True, exist_ok=True)
    headers, xls = read_xls("002847_main_year.xls")
    years = [int(value) for value in headers if value]
    xls_year = {
        metric: dict(zip(years, values[: len(years)]))
        for metric, values in xls.items()
    }
    balance = annual_rows(load_json("RPT_DMSK_FN_BALANCE.json"))
    cashflow = annual_rows(load_json("RPT_DMSK_FN_CASHFLOW.json"))

    output: list[dict] = []
    for year in YEARS:
        bal = balance[year]
        cf = cashflow[year]
        assets = float(bal["TOTAL_ASSETS"])
        equity = float(bal["TOTAL_EQUITY"])
        prev_assets = float(balance.get(year - 1, bal)["TOTAL_ASSETS"])
        prev_equity = float(balance.get(year - 1, bal)["TOTAL_EQUITY"])
        revenue = float(xls_year["营业总收入(元)"][year])
        net_profit = float(xls_year["净利润(元)"][year])
        monetary = float(bal["MONETARYFUNDS"])
        cfo = float(cf["NETCASH_OPERATE"])
        capex = float(cf["CONSTRUCT_LONG_ASSET"])
        cash_position = monetary + TRADING_ASSETS[year] - LONG_LOAN[year] - BONDS[year]
        output.append({
            "年份": year,
            "营收": revenue / 1e8,
            "净利润": net_profit / 1e8,
            "扣非净利润": float(xls_year["扣非净利润(元)"][year]) / 1e8,
            "净资产收益率": pct(xls_year["净资产收益率"][year]),
            "销售净利率": pct(xls_year["销售净利率"][year]),
            "销售毛利率": pct(xls_year["销售毛利率"][year]),
            "总资产周转率": revenue / ((assets + prev_assets) / 2),
            "权益乘数": ((assets + prev_assets) / 2) / ((equity + prev_equity) / 2),
            "经营现金流": cfo / 1e8,
            "资本开支": capex / 1e8,
            "自由现金流": (cfo - capex) / 1e8,
            "资产负债率": pct(xls_year["资产负债率"][year]),
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
        ["魔芋零食", 17.3738001206, 107.23, 34.48],
        ["海味零食", 7.5995492435, 12.53, 45.64],
        ["健康蛋制品", 6.2817433473, 8.35, 27.73],
        ["休闲豆制品", 3.6017073961, -0.39, 30.25],
        ["果干果冻", 7.4916822621, 4.32, 20.93],
        ["烘焙薯类", 8.9811769150, -22.43, 27.42],
        ["其他产品及业务", 6.2926380298, -35.32, None],
    ], columns=["业务", "收入_亿元", "同比_%", "毛利率_%"])
    product.to_csv(DATA / "product_structure.csv", index=False)

    valuation = pd.DataFrame(load_json("valuation_history_raw.json"))
    valuation["TRADE_DATE"] = pd.to_datetime(valuation["TRADE_DATE"])
    valuation = valuation.sort_values("TRADE_DATE")
    valuation.to_csv(DATA / "valuation_history.csv", index=False)
    latest = valuation.iloc[-1]
    window = valuation[valuation["TRADE_DATE"] >= latest["TRADE_DATE"] - pd.DateOffset(years=10)]
    pe = pd.to_numeric(window["PE_TTM"], errors="coerce")
    pe = pe[(pe > 0) & pe.notna()]
    current_pe = float(latest["PE_TTM"])
    close = float(latest["CLOSE_PRICE"])
    market_cap = float(latest["TOTAL_MARKET_CAP"])
    shares = float(latest["TOTAL_SHARES"])
    deduct_ttm = 7.14924000 - 1.5626028426 + 2.0384702541
    cash_position_q1 = (316_536_270.25 - 426_794_044.15) / 1e8
    snapshot = {
        "trade_date": latest["TRADE_DATE"].strftime("%Y-%m-%d"),
        "close": close,
        "market_cap_yi": market_cap / 1e8,
        "total_shares_yi": shares / 1e8,
        "pe_ttm_parent": current_pe,
        "pb_mrq": float(latest["PB_MRQ"]),
        "pe_10y_percentile": float((pe <= current_pe).mean() * 100),
        "pe_10y_min": float(pe.min()),
        "pe_10y_p10": float(pe.quantile(0.10)),
        "pe_10y_p25": float(pe.quantile(0.25)),
        "pe_10y_median": float(pe.median()),
        "pe_10y_max": float(pe.max()),
        "deduct_profit_ttm_yi": deduct_ttm,
        "deduct_pe_ttm": market_cap / 1e8 / deduct_ttm,
        "dividend_per_share_2025": 1.40,
        "dividend_yield_2025_pct": 1.40 / close * 100,
        "cash_position_2026q1_yi": cash_position_q1,
        "cash_position_per_share_2026q1": cash_position_q1 / (shares / 1e8),
        "financial_cutoff": "2026Q1",
    }
    (DATA / "market_snapshot.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    peer_specs = [
        ("002847.SZ", "多品类制造/魔芋"),
        ("003000.SZ", "鱼制零食"),
        ("002991.SZ", "籽类/坚果"),
        ("002557.SZ", "瓜子坚果"),
        ("300783.SZ", "线上综合零食"),
        ("603719.SH", "综合零食"),
    ]
    peers = []
    for secucode, role in peer_specs:
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
