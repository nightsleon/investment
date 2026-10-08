#!/usr/bin/env python3
"""Validate fixed-28-item 3R JSON embedded in Markdown or supplied as JSON."""

import json
import re
import sys
from pathlib import Path


def load_payload(path: Path):
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return json.loads(text)
    match = re.search(r"```json\s*(.*?)\s*```", text, re.S)
    if not match:
        raise ValueError("Markdown中未找到```json代码块")
    return json.loads(match.group(1))


def half_point(value):
    return abs(float(value) * 2 - round(float(value) * 2)) < 1e-9


def base_rating(total):
    if total >= 85:
        return "重点候选"
    if total >= 75:
        return "关注"
    if total >= 65:
        return "观察"
    return "不碰"


def validate_company(company):
    name = company.get("company", "<未命名>")
    errors = []
    dimensions = company["business"]["dimensions"]
    business_items = [item for dim in dimensions for item in dim["items"]]
    people_items = company["people"]["items"]
    price_items = company["price"]["items"]
    all_items = business_items + people_items + price_items

    expected_ids = [f"B{i}" for i in range(1, 22)] + [f"P{i}" for i in range(1, 4)] + [f"V{i}" for i in range(1, 5)]
    actual_ids = [item.get("id") for item in all_items]
    if len(all_items) != 28:
        errors.append(f"项目数为{len(all_items)}，应为28")
    if actual_ids != expected_ids:
        errors.append("项目ID缺失、重复或顺序错误")

    for item in all_items:
        score, maximum = item["score"], item["max"]
        if not half_point(score):
            errors.append(f"{item.get('id')}得分{score}不是0.5粒度")
        if score < 0 or score > maximum:
            errors.append(f"{item.get('id')}得分{score}超出0-{maximum}")
        if not item.get("evidence"):
            errors.append(f"{item.get('id')}缺少证据")

    for dim in dimensions:
        subtotal = sum(item["score"] for item in dim["items"])
        if abs(subtotal - dim["score"]) > 1e-9:
            errors.append(f"维度“{dim['name']}”子项和{subtotal} != {dim['score']}")

    business = sum(item["score"] for item in business_items)
    people = sum(item["score"] for item in people_items)
    price = sum(item["score"] for item in price_items)
    if abs(business - company["business"]["score"]) > 1e-9:
        errors.append("Business模块加总错误")
    if abs(people - company["people"]["score"]) > 1e-9:
        errors.append("People模块加总错误")
    if abs(price - company["price"]["score"]) > 1e-9:
        errors.append("Price模块加总错误")
    total = business + people + price
    if abs(total - company["total"]) > 1e-9:
        errors.append(f"总分应为{total}，实际为{company['total']}")

    thresholds = company["thresholds"]
    expected_thresholds = {
        "business_pass": business >= 36,
        "people_pass": people >= 12,
        "price_pass": price >= 10,
    }
    for key, expected in expected_thresholds.items():
        if thresholds.get(key) is not expected:
            errors.append(f"门槛{key}应为{expected}")

    ranks = {"不碰": 0, "观察": 1, "关注": 2, "重点候选": 3}
    mechanical = base_rating(total)
    final = company.get("rating")
    if final not in ranks:
        errors.append(f"未知评级：{final}")
    elif all(expected_thresholds.values()) and not thresholds.get("major_red_flag", False):
        if final != mechanical:
            errors.append(f"无门槛/红线降级时评级应为{mechanical}，实际为{final}")
    elif ranks[final] > ranks[mechanical]:
        errors.append("触发门槛或红线后，最终评级不得高于机械评级")

    return name, errors


def main():
    if len(sys.argv) != 2:
        raise SystemExit("用法: verify_3r_json.py <report.md|result.json>")
    data = load_payload(Path(sys.argv[1]))
    companies = data.get("companies", [])
    if not companies:
        raise SystemExit("FAIL: companies为空")
    failed = False
    for company in companies:
        name, errors = validate_company(company)
        if errors:
            failed = True
            print(f"FAIL {name}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"PASS {name}: 28项、加总、粒度、门槛与评级均有效")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
