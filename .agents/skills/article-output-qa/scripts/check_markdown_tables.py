#!/usr/bin/env python3
"""校验 Markdown 文件中所有表格：表头/分隔行/数据行的单元格数必须一致。

用法: python3 check_markdown_tables.py 文章.md [文章2.md ...]
退出码: 0 = 全部表格列数一致; 1 = 存在异常表。

局限: 按顶层 '|' 切分，单元格内含转义竖线 '\\|' 会误计数（表格会偏多一格），
遇此类表格以人工复核为准。连续行以 | 开头视为同一表，空行分隔。
"""
import sys


def check(path: str) -> int:
    try:
        lines = open(path, encoding="utf-8").read().splitlines()
    except OSError as e:
        print(f"无法读取 {path}: {e}")
        return 1

    tables, cur = [], []
    for ln in lines:
        if ln.strip().startswith("|"):
            cur.append(ln)
        elif cur:
            tables.append(cur)
            cur = []
    if cur:
        tables.append(cur)

    bad = 0
    for i, t in enumerate(tables, 1):
        cols = [len(x.strip().strip("|").split("|")) for x in t]
        if len(set(cols)) != 1:
            bad += 1
            print(f"[异常] {path} 表{i}: 各行格数 {cols}")
            print(f"   表头行: {t[0].strip()}")
            print(f"   分隔行: {t[1].strip() if len(t) > 1 else '(无分隔行)'}")

    if bad:
        print(f"{path}: 共 {len(tables)} 张表，{bad} 张列数不一致")
        return 1
    print(f"{path}: 共 {len(tables)} 张表，列数全部一致")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    rc = 0
    for p in sys.argv[1:]:
        rc = max(rc, check(p))
    return rc


if __name__ == "__main__":
    sys.exit(main())
