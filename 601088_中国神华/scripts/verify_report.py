#!/usr/bin/env python3
"""Verify China Shenhua report links, datasets, quarter sums, valuation and scores."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
from python_calamine import CalamineWorkbook

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"
REPORT = BASE / "reports" / "中国神华_投资分析报告_2026-07-21.md"


def close(a: float, b: float, tolerance: float = 2e-5) -> bool:
    return abs(a - b) <= tolerance * max(1.0, abs(a), abs(b))


def main() -> None:
    checks: dict[str, object] = {}
    text = REPORT.read_text(encoding="utf-8")
    images = re.findall(r"!\[[^]]*\]\(([^)]+)\)", text)
    missing = [path for path in images if not (REPORT.parent / path).resolve().exists()]
    generated = list((BASE / "charts").glob("601088_*.png"))
    checks["image_links"] = {"embedded": len(images), "generated": len(generated), "missing": missing,
                             "ok": len(images) == 8 and len(generated) == 10 and not missing}

    annual = pd.read_csv(DATA / "annual_core.csv")
    required = ["营收", "净利润", "扣非净利润", "经营现金流", "资本开支", "货币资金", "现金头寸_近似", "应收账款", "存货", "合同负债"]
    nan_years = annual.loc[annual[required].isna().any(axis=1), "年份"].tolist()
    checks["annual_completeness"] = {"years": annual["年份"].tolist(), "nan_years": nan_years,
                                     "ok": annual["年份"].tolist() == list(range(2020, 2026)) and not nan_years}

    rows = CalamineWorkbook.from_path(str(DATA / "601088_main_year.xls")).get_sheet_by_index(0).to_python()
    xls = {str(row[0]): row[1] for row in rows[1:] if row and row[0]}
    a2025 = annual[annual["年份"] == 2025].iloc[0]
    checks["xls_2025"] = {"revenue": float(xls["营业总收入(元)"]) / 1e8, "profit": float(xls["净利润(元)"]) / 1e8,
                           "deduct": float(xls["扣非净利润(元)"]) / 1e8,
                           "ok": close(float(xls["营业总收入(元)"]) / 1e8, float(a2025["营收"]))
                           and close(float(xls["净利润(元)"]) / 1e8, float(a2025["净利润"]))
                           and close(float(xls["扣非净利润(元)"]) / 1e8, float(a2025["扣非净利润"]))}

    q = pd.read_csv(DATA / "601088_季度数据.csv", parse_dates=["date"])
    q2025 = q[q["date"].dt.year == 2025]
    checks["quarter_sum_2025"] = {"revenue_source": 2949.16, "net_profit": float(q2025["net_profit_yi"].sum()),
                                   "deduct_profit": float(q2025["non_gaap_yi"].sum()),
                                   "ok": close(float(q2025["net_profit_yi"].sum()), 528.49)
                                   and close(float(q2025["non_gaap_yi"].sum()), 485.89)}

    snapshot = json.loads((DATA / "market_snapshot.json").read_text(encoding="utf-8"))
    checks["market_snapshot"] = {"trade_date": snapshot["trade_date"], "a_close": snapshot["a_close"],
                                  "reported_deduct_pe": snapshot["reported_deduct_pe_a_equivalent"],
                                  "ok": snapshot["trade_date"] == "2026-07-20" and close(snapshot["a_close"], 46.14)
                                  and close(snapshot["reported_deduct_profit_ttm_yi"], 475.96)
                                  and close(snapshot["proforma_2024_deduct_profit_yi"], 668.51)}

    acquisition = json.loads((DATA / "acquisition_snapshot.json").read_text(encoding="utf-8"))
    checks["acquisition"] = {"price": acquisition["final_transaction_price_yi"], "shares": acquisition["post_issue_total_shares"],
                              "ok": close(acquisition["final_transaction_price_yi"], 1335.98)
                              and acquisition["post_issue_total_shares"] == 21_689_434_304}

    modules = {"好行业": 12.5, "好公司·定性": 15.5, "好公司·定量": 30.0, "好时机": 8.5}
    total = sum(modules.values())
    checks["scores"] = {"modules": modules, "total": total, "ok": close(total, 66.5) and "**66.5**" in text and "**45.5/60**" in text}
    checks["forbidden_forecasts"] = {"ok": "券商目标价" not in text and text.count("一致预期") == 1
                                      and "没有引用券商一致预期" in text}
    checks["all_ok"] = all(value.get("ok", False) for value in checks.values() if isinstance(value, dict))
    print(json.dumps(checks, ensure_ascii=False, indent=2))
    if not checks["all_ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
