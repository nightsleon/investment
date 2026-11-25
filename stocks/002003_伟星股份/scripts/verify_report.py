#!/usr/bin/env python3
"""Verify Weixing Share report links, datasets, quarter sums, and scores for 2026-11-23."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
from python_calamine import CalamineWorkbook

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"
REPORT = BASE / "reports" / "伟星股份_投资分析报告_2026-11-23.md"


def close(a: float, b: float, tolerance: float = 1e-6) -> bool:
    return abs(a - b) <= tolerance * max(1.0, abs(a), abs(b))


def main() -> None:
    checks: dict[str, object] = {}
    text = REPORT.read_text(encoding="utf-8")

    images = re.findall(r"!\[[^]]*\]\(([^)]+)\)", text)
    missing = [path for path in images if not (REPORT.parent / path).resolve().exists()]
    generated = list((BASE / "charts").glob("002003_*.png"))
    checks["image_links"] = {
        "embedded_count": len(images),
        "generated_count": len(generated),
        "missing": missing,
        "ok": len(images) == 8 and not missing,
    }

    annual = pd.read_csv(DATA / "annual_core.csv")
    required = ["货币资金", "长期借款", "现金头寸_近似", "应收账款", "存货", "合同负债"]
    nan_rows = annual.loc[annual[required].isna().any(axis=1), "年份"].tolist()
    checks["annual_completeness"] = {
        "years": annual["年份"].tolist(),
        "nan_years": nan_rows,
        "ok": annual["年份"].tolist() == list(range(2020, 2026)) and not nan_rows,
    }

    product = pd.read_csv(DATA / "product_structure.csv")
    product_total = float(product["收入_亿元"].sum())
    annual_2025 = annual.loc[annual["年份"] == 2025].iloc[0]
    checks["product_total"] = {
        "product_sum": product_total,
        "revenue_2025": float(annual_2025["营收"]),
        "ok": close(product_total, float(annual_2025["营收"]), 2e-6),
    }

    q = pd.read_csv(DATA / "002003_季度数据.csv")
    q["date"] = pd.to_datetime(q["date"])
    q2025 = q[q["date"].dt.year == 2025]
    checks["quarter_sum_2025"] = {
        "quarters": len(q2025),
        "net_profit": float(q2025["net_profit_yi"].sum()),
        "annual_net_profit": float(annual_2025["净利润"]),
        "deduct_profit": float(q2025["non_gaap_yi"].sum()),
        "annual_deduct_profit": float(annual_2025["扣非净利润"]),
        "ok": len(q2025) == 4
        and close(float(q2025["net_profit_yi"].sum()), float(annual_2025["净利润"]), 2e-6)
        and close(float(q2025["non_gaap_yi"].sum()), float(annual_2025["扣非净利润"]), 2e-6),
    }

    rows = CalamineWorkbook.from_path(str(DATA / "002003_main_year.xls")).get_sheet_by_index(0).to_python()
    xls = {str(row[0]): row[1] for row in rows[1:] if row and row[0]}
    checks["xls_2025"] = {
        "revenue": float(xls["营业总收入(元)"]) / 1e8,
        "net_profit": float(xls["净利润(元)"]) / 1e8,
        "deduct_profit": float(xls["扣非净利润(元)"]) / 1e8,
        "ok": close(float(xls["营业总收入(元)"]) / 1e8, float(annual_2025["营收"]))
        and close(float(xls["净利润(元)"]) / 1e8, float(annual_2025["净利润"]))
        and close(float(xls["扣非净利润(元)"]) / 1e8, float(annual_2025["扣非净利润"])),
    }

    qualitative = [4.5, 6.0, 9.0, 7.0]
    quantitative = [12.0, 7.0, 9.0, 3.0]
    management = [4.0, 5.5]
    timing = [3.5, 3.0, 2.0]
    modules = {
        "好生意·定性": sum(qualitative),
        "好生意·定量": sum(quantitative),
        "好管理层": sum(management),
        "好价格": sum(timing),
    }
    score_total = sum(modules.values())
    checks["scores"] = {
        "modules": modules,
        "quality_total": modules["好生意·定性"] + modules["好生意·定量"] + modules["好管理层"],
        "total": score_total,
        "ok": modules == {"好生意·定性": 26.5, "好生意·定量": 31.0, "好管理层": 9.5, "好价格": 8.5}
        and close(score_total, 75.5)
        and "**75.5**" in text
        and "**67.0**" in text,
    }

    snapshot = json.loads((DATA / "market_snapshot.json").read_text(encoding="utf-8"))
    checks["market_snapshot"] = {
        "close": snapshot["close"],
        "pe_ttm_parent": snapshot["pe_ttm_parent"],
        "percentile": snapshot["pe_available_percentile"],
        "ok": f"{snapshot['close']}" in text
        and f"{snapshot['pe_ttm_parent']}" in text
        and f"{snapshot['pe_available_percentile']}%" in text,
    }

    all_ok = all(bool(v.get("ok")) for v in checks.values() if isinstance(v, dict))
    checks["ALL_PASS"] = all_ok
    print(json.dumps(checks, ensure_ascii=False, indent=2))
    if not all_ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
