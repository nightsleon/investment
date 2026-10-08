#!/usr/bin/env python3
"""Audit every 3R brief in an investment-research repository.

Checks fixed-four charts, chart reuse/placement, module arithmetic, blind-evaluation
 disclosure, image links, and README score/link consistency.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REQUIRED_IMAGES = {
    "roe": ("4.1_ROE",),
    "profit": ("4.2_利润",),
    "cashflow": ("4.4_净利润",),
    # A股常用“股价vs扣非净利润TTM”；仅披露半年/全年利润的港股
    # 可能使用完整报告中的“股价与点时可得TTM利润图”，二者都验证同一命题。
    "price_profit": ("股价vs扣非净利润TTM_双Y轴", "股价与点时可得TTM利润图", "股价与点时可得核心TTM利润图"),
}


def previous_nonempty(lines: list[str], index: int) -> str:
    for j in range(index - 1, -1, -1):
        text = lines[j].strip()
        if text:
            return text
    return ""


def is_prose(line: str) -> bool:
    return bool(line) and not line.startswith(("![", "|", "#", "- ", "* ", ">", "```"))


def readme_entries(readme: Path) -> dict[str, dict[str, object]]:
    if not readme.exists():
        return {}
    entries: dict[str, dict[str, object]] = {}
    for line in readme.read_text(encoding="utf-8").splitlines():
        if "[3R简报](" not in line or not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        match = re.search(r"\[3R简报\]\(([^)]+)\)", line)
        if not match or len(cells) < 2:
            continue
        try:
            score = float(cells[-2])
        except ValueError:
            score = None
        entries[match.group(1)] = {"company": cells[0], "score": score}
    return entries


def audit_report(root: Path, brief: Path, readme: dict[str, dict[str, object]]) -> dict[str, object]:
    text = brief.read_text(encoding="utf-8")
    lines = text.splitlines()
    rel = brief.relative_to(root).as_posix()
    images = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text)
    full_reports = [p for p in brief.parent.glob("*投资分析报告*.md") if "3R" not in p.name]
    full_texts = [p.read_text(encoding="utf-8") for p in full_reports]

    errors: list[str] = []
    if len(images) != 4:
        errors.append(f"expected exactly 4 images, found {len(images)}")

    category_paths: dict[str, str] = {}
    for category, tokens in REQUIRED_IMAGES.items():
        matches = [path for path in images if any(token in path for token in tokens)]
        if len(matches) != 1:
            errors.append(f"{category}: expected 1 matching image, found {len(matches)}")
        elif matches:
            category_paths[category] = matches[0]

    for image in images:
        if not (brief.parent / image).resolve().exists():
            errors.append(f"missing image: {image}")
        if not any(image in full_text for full_text in full_texts):
            errors.append(f"image not reused by a full report: {image}")

    for category, tokens in REQUIRED_IMAGES.items():
        index = next((i for i, line in enumerate(lines) if any(token in line for token in tokens)), None)
        if index is None:
            continue
        previous = previous_nonempty(lines, index)
        if not is_prose(previous):
            errors.append(f"{category}: image is not immediately after a prose analysis paragraph")

    modules = {k: float(v) for k, v in re.findall(
        r"^\| (Right Business|Right People|Right Price) \| ([0-9.]+)/", text, re.M
    )}
    total_match = re.search(r"3R总分：\*\*([0-9.]+)/100", text)
    if set(modules) != {"Right Business", "Right People", "Right Price"}:
        errors.append("missing or duplicate module scores")
        total = None
    elif not total_match:
        errors.append("missing top 3R total")
        total = None
    else:
        total = float(total_match.group(1))
        if abs(sum(modules.values()) - total) > 1e-9:
            errors.append(f"module sum {sum(modules.values())} != total {total}")

    if not ("盲评" in text and ("隔离" in text or "屏蔽" in text) and ("锁分" in text or "锁定" in text)):
        errors.append("blind-evaluation disclosure is incomplete")

    entry = readme.get(rel)
    if entry is None:
        errors.append("README has no matching 3R link")
    elif total is not None and entry["score"] != total:
        errors.append(f"README score {entry['score']} != report total {total}")

    return {
        "company": entry["company"] if entry else brief.parent.parent.name,
        "report": rel,
        "score": total,
        "images": images,
        "errors": errors,
        "ok": not errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, help="investment repository root")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    args = parser.parse_args()
    root = args.root.expanduser().resolve()
    briefs = sorted(root.glob("*/reports/*_3R投资分析简报_*.md"))
    readme = readme_entries(root / "README.md")
    results = [audit_report(root, brief, readme) for brief in briefs]
    payload = {"root": str(root), "count": len(results), "all_ok": all(r["ok"] for r in results), "reports": results}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for result in results:
            status = "PASS" if result["ok"] else "FAIL"
            print(f"{status} {result['company']}: {result['report']}")
            for error in result["errors"]:
                print(f"  - {error}")
        print(f"SUMMARY: {sum(r['ok'] for r in results)}/{len(results)} passed")
    return 0 if payload["all_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
