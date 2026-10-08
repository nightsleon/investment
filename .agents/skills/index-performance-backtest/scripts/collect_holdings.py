#!/usr/bin/env python3
"""采集中证指数最新持仓快照（前十大权重 + 行业分布）。

用法:
    python collect_holdings.py --codes 000922,H00922 --output-dir ./holdings

参数:
    --codes: 价格指数代码列表（逗号分隔），用于查前十大和行业权重
    --output-dir: 输出目录
"""
from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path

BASE_URL = "https://www.csindex.com.cn/csindex-home"


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def collect_top10(price_code: str, output_dir: Path) -> dict | None:
    url = f"{BASE_URL}/index/weight/top10new/{price_code}"
    try:
        data = fetch_json(url)
        if data.get("code") != 200:
            print(f"  {price_code} 前十大接口返回异常: {data.get('code')}")
            return None
        result = data.get("data", {})
        update_date = result.get("updateDate", "未知")
        top10_list = result.get("top10", [])

        print(f"  {price_code} 前十大 (截至 {update_date}):")
        for item in top10_list:
            name = item.get("secNameCn", "?")
            weight = item.get("weight", 0)
            print(f"    {name}: {weight:.2f}%")
        print(f"  前五合计: {result.get('top5Sum', 'N/A')}%")
        print(f"  前十合计: {result.get('top10Sum', 'N/A')}%")

        out_path = output_dir / f"{price_code}_前十大权重_{update_date}.json"
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  已保存: {out_path}")
        return result
    except Exception as e:
        print(f"  {price_code} 前十大采集失败: {e}")
        return None


def collect_industry(price_code: str, output_dir: Path) -> dict | None:
    url = f"{BASE_URL}/index/weight/industry-weight-two-new/{price_code}?cicsType=1"
    try:
        data = fetch_json(url)
        if data.get("code") != 200:
            print(f"  {price_code} 行业权重接口返回异常: {data.get('code')}")
            return None
        result = data.get("data", {})
        update_date = result.get("updateDate", "未知")
        industries = result.get("industryList", [])

        sorted_ind = sorted(industries, key=lambda x: float(x.get("weight", 0)), reverse=True)
        print(f"  {price_code} 行业分布 (截至 {update_date}):")
        for item in sorted_ind[:5]:
            name = item.get("industryNameCn", "?")
            weight = item.get("weight", 0)
            print(f"    {name}: {weight:.2f}%")

        top3_sum = sum(float(x.get("weight", 0)) for x in sorted_ind[:3])
        print(f"  前三大行业合计: {top3_sum:.2f}%")

        # 集中度提示
        for item in sorted_ind:
            if float(item.get("weight", 0)) > 40:
                print(f"  ⚠ {item.get('industryNameCn', '?')} 占比 {item['weight']:.2f}%，超40%")

        out_path = output_dir / f"{price_code}_行业权重_{update_date}.json"
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  已保存: {out_path}")
        return result
    except Exception as e:
        print(f"  {price_code} 行业权重采集失败: {e}")
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="采集中证指数最新持仓快照")
    parser.add_argument("--codes", required=True, help="价格指数代码，逗号分隔，如 000922,H00922")
    parser.add_argument("--output-dir", default=".", help="输出目录")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    codes = [c.strip() for c in args.codes.split(",") if c.strip()]
    for code in codes:
        print(f"\n=== {code} ===")
        collect_top10(code, output_dir)
        collect_industry(code, output_dir)


if __name__ == "__main__":
    main()
