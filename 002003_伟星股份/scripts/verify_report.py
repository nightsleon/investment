#!/usr/bin/env python3
"""Verify Weixing Share report links, datasets, quarter sums, and scores."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
from python_calamine import CalamineWorkbook

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"
REPORT = BASE / "reports" / "伟星股份_投资分析报告_2026-07-21.md"


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
        "ok": len(images) == 8 and len(generated) == 10 and not missing,
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

    industry = [4.0, 2.5, 3.5, 2.0, 2.5]
    qualitative = [6.0, 4.0, 3.5, 2.5]
    quantitative = [7.0, 4.5, 5.0, 5.5, 4.5, 4.5]
    timing = [2.0, 2.5, 0.5, 2.5, 1.0, 2.0]
    modules = {
        "好行业": sum(industry),
        "好公司·定性": sum(qualitative),
        "好公司·定量": sum(quantitative),
        "好时机": sum(timing),
    }
    score_total = sum(modules.values())
    checks["scores"] = {
        "modules": modules,
        "good_company": modules["好公司·定性"] + modules["好公司·定量"],
        "total": score_total,
        "ok": modules == {"好行业": 14.5, "好公司·定性": 16.0, "好公司·定量": 31.0, "好时机": 10.5}
        and close(score_total, 72.0)
        and "**72.0**" in text
        and "**47.0/60**" in text,
    }

    snapshot = json.loads((DATA / "market_snapshot.json").read_text(encoding="utf-8"))
    checks["market_snapshot"] = {
        "trade_date": snapshot["trade_date"],
        "close": snapshot["close"],
        "market_cap_yi": snapshot["market_cap_yi"],
        "deduct_pe_ttm": snapshot["deduct_pe_ttm"],
        "ok": snapshot["trade_date"] == "2026-07-20"
        and close(snapshot["close"], 10.0)
        and close(snapshot["market_cap_yi"], 118.8889653)
        and close(snapshot["deduct_pe_ttm"], 19.1930923263),
    }

    manifest = json.loads((BASE / "年报" / "manifest.json").read_text(encoding="utf-8"))
    official_files = [BASE / item["file"] for item in manifest]
    checks["official_files"] = {
        "manifest_count": len(manifest),
        "missing": [str(path) for path in official_files if not path.exists()],
        "annual_years": sorted(int(item["file"].split("/")[-1][:4]) for item in manifest if "_伟星股份_年度报告.pdf" in item["file"]),
        "ok": all(path.exists() for path in official_files)
        and sorted(int(item["file"].split("/")[-1][:4]) for item in manifest if "_伟星股份_年度报告.pdf" in item["file"]) == list(range(2020, 2026)),
    }

    checks["all_ok"] = all(value.get("ok", False) for value in checks.values() if isinstance(value, dict))
    print(json.dumps(checks, ensure_ascii=False, indent=2))
    if not checks["all_ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
