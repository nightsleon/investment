#!/usr/bin/env python3
"""Build a score-blind evidence packet from a completed investment report.

Usage:
  python build_blind_evidence.py INPUT.md OUTPUT.md --company 美的集团

The script deliberately fails if score/rating/scenario contamination remains.
Review the output manually before giving it to blind evaluators.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

BLOCK_HEADING_TOKENS = (
    "毛估估",
    "情景估值",
    "决策摘要",
    "评分",
    "打分",
    "胜率",
    "赔率",
    "评级",
    "行动",
)
STOP_HEADING_TOKENS = (
    "投资结论",
    "评级与行动",
    "投资逻辑",
    "证伪条件",
    "维度打分",
    "维度评分",
)
DIRECTIONAL_TOKENS = (
    "强烈关注",
    "关注池",
    "评级：",
    "评级:",
    "总分：",
    "总分:",
    "行动建议",
    "当前行动",
    "胜率",
    "赔率",
    "毛估估",
)
DIRECTIONAL_PREFIX = re.compile(
    r"^(?:>\s*)?(?:核心结论|结论先行|结论|判断|一句话|最终判断)[：:]"
    r"|^\*\*初筛结论[：:]"
    r"|^它不是.*(?:投资价值|主要风险)"
)
EVALUATIVE_HEADING_REWRITES = {
    "先说结论：这是一门什么生意？": "业务模式概述",
    "一、公司画像、能力圈与红线": "一、公司画像与风险事实",
    "二、好行业：刚需属性仍在，但总量增长已慢下来": "二、行业需求与竞争格局",
    "三、好公司·定性：护城河宽，但定价权没有想象中强": "三、护城河、定价权与治理事实",
    "四、好公司·定量：ROE恢复、现金很多，但增长质量仍需验证": "四、财务与经营数据",
    "五、好时机：价格便宜，但不是“无条件低估”": "五、估值与股东回报数据",
}
SCORE_BLOCK = re.compile(
    r"(?:好行业|好公司|好时机).*(?:评分|小计)|(?:评分|总分|评级)[：:].*\d"
)
SCORE_TABLE_ROW = re.compile(r"\|\s*(?:得分|满分|小计|总分)\s*\|")
EVALUATIVE_COLUMNS = (
    "判断",
    "结论",
    "理由",
    "解读",
    "怎么理解",
    "核心判断",
    "增长判断",
    "主要判断",
    "对应判断",
    "稳固程度",
)
CONTAMINATION_PATTERNS = {
    "score heading": re.compile(r"(?:好行业|好公司|好时机).*评分"),
    "rating/total": re.compile(r"(?:强烈关注|评级[：:]|总分[：:])"),
    "old scenario": re.compile(r"(?:毛估估|情景估值|\|\s*(?:压力|保守|中性|乐观)(?:档)?\s*\||目标PE|三年总回报)"),
    "valuation judgment": re.compile(r"(?:现在买贵不贵|PE与历史分位：.*(?:便宜|贵)|表面上很便宜|合理偏低|当前约[^\n]*不贵)"),
    "score table": SCORE_TABLE_ROW,
}


def heading(line: str) -> tuple[int, str] | None:
    match = re.match(r"^(#{2,6})\s+(.*)", line)
    return (len(match.group(1)), match.group(2)) if match else None


def split_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def sanitize_table(block: list[str]) -> list[str]:
    if not block:
        return []
    header = split_table_row(block[0])
    drop = {
        i
        for i, cell in enumerate(header)
        if any(token in cell for token in EVALUATIVE_COLUMNS)
    }
    output: list[str] = []
    for line in block:
        cells = split_table_row(line)
        kept = [cell for i, cell in enumerate(cells) if i not in drop]
        joined = " | ".join(kept)
        if any(token in joined for token in DIRECTIONAL_TOKENS):
            continue
        if re.search(r"(?:评分|评级|总分)", joined):
            continue
        output.append(f"| {joined} |")
    return output


def first_pass(lines: list[str]) -> list[str]:
    """Remove complete analysis blocks, not only their headings.

    The active skip state is checked for every line. This avoids the durable
    failure where a heading disappears but its score/scenario table remains.
    """
    output: list[str] = []
    skip_level: int | None = None
    skip_to_h2 = False

    for line in lines:
        parsed = heading(line)
        level, title = parsed if parsed else (None, "")

        if skip_level is not None:
            if parsed and level <= skip_level:
                skip_level = None
            else:
                continue

        if skip_to_h2:
            if parsed and level == 2:
                skip_to_h2 = False
            else:
                continue

        if parsed:
            if any(token in title for token in STOP_HEADING_TOKENS):
                break
            if any(token in title for token in BLOCK_HEADING_TOKENS):
                skip_level = level
                continue
            if title in EVALUATIVE_HEADING_REWRITES:
                line = f"{'#' * level} {EVALUATIVE_HEADING_REWRITES[title]}"

        if SCORE_BLOCK.search(line):
            # In existing reports these summaries occur at the end of an H2.
            skip_to_h2 = True
            continue
        if any(token in line for token in DIRECTIONAL_TOKENS):
            continue
        if DIRECTIONAL_PREFIX.match(line.strip()):
            continue
        if SCORE_TABLE_ROW.search(line):
            continue
        output.append(line)

    return output


def second_pass(lines: list[str]) -> list[str]:
    output: list[str] = []
    i = 0
    while i < len(lines):
        if lines[i].startswith("|"):
            block: list[str] = []
            while i < len(lines) and lines[i].startswith("|"):
                block.append(lines[i])
                i += 1
            output.extend(sanitize_table(block))
            continue
        output.append(lines[i])
        i += 1
    return output


def validate(text: str) -> None:
    failures = [name for name, pattern in CONTAMINATION_PATTERNS.items() if pattern.search(text)]
    required_groups = {
        "ROE": ("ROE",),
        "利润": ("扣非", "归母净利润", "股东应占溢利"),
        "经营现金流": ("经营现金流",),
        "PE": ("PE",),
    }
    missing = [
        label
        for label, alternatives in required_groups.items()
        if not any(token in text for token in alternatives)
    ]
    if failures or missing:
        details = []
        if failures:
            details.append("contamination=" + ", ".join(failures))
        if missing:
            details.append("missing key evidence=" + ", ".join(missing))
        raise SystemExit("Blind evidence validation failed: " + "; ".join(details))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--company", required=True)
    args = parser.parse_args()

    lines = args.input.read_text(encoding="utf-8").splitlines()
    body = second_pass(first_pass(lines))
    packet = (
        f"# {args.company} 3R独立评估事实包\n\n"
        "> 来源范围：原完整投资分析报告内的财务、业务、治理、估值数据及图表。\n"
        "> 已移除历史分数、方向性标签、原估值情景、投资结论和行动内容。\n\n"
        + "\n".join(body).strip()
        + "\n"
    )
    validate(packet)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(packet, encoding="utf-8")
    print(f"PASS: {args.output} ({len(packet.splitlines())} lines)")


if __name__ == "__main__":
    main()
