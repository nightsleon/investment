#!/usr/bin/env python3
"""世代回溯报告：从中证官网采集23只指数（剔除规模偏小）基日至今的全收益历史数据。"""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
EXCEL_DIR = BASE / "sources" / "excel-30index"
OUT_DIR = BASE / "sources" / "performance-data-30index" / "generation-full-history"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# F表"规模偏小"剔除名单
SMALL = {"000821", "H50040", "CESFHY", "000824", "931231", "H30089", "H30366", "930917"}


def fetch(tr_code: str, start: str, end: str) -> list[dict]:
    url = (
        "https://www.csindex.com.cn/csindex-home/perf/index-perf"
        f"?indexCode={tr_code}&startDate={start}&endDate={end}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        d = json.load(resp)
    if d.get("code") != "200":
        raise RuntimeError(f"{tr_code}: {d.get('msg')}")
    return d["data"]


def main() -> None:
    info = json.load(open(EXCEL_DIR / "basic_info.json", encoding="utf-8"))
    manifest = []
    for it in info:
        code = it["price_code"]
        if code in SMALL:
            continue
        basic = it["basicDate"].replace("-", "")
        out = OUT_DIR / f"{code}_{it['name']}_基日至今.csv"
        rows = fetch(it["tr_code"], basic, "20260807")
        # 过滤close为空的行
        rows = [r for r in rows if r.get("close") is not None]
        with open(out, "w", encoding="utf-8-sig") as f:
            f.write("date,close\n")
            for r in rows:
                f.write(f"{r['tradeDate']},{r['close']}\n")
        manifest.append({
            "price_code": code, "name": it["name"], "tr_code": it["tr_code"],
            "basic_date": it["basicDate"], "publish_date": it["publishDate"],
            "rows": len(rows),
            "first": rows[0]["tradeDate"], "last": rows[-1]["tradeDate"],
            "first_close": rows[0]["close"], "last_close": rows[-1]["close"],
        })
        print(f"✓ {code} {it['name']}: {len(rows)}行 {rows[0]['tradeDate']}~{rows[-1]['tradeDate']} 基点{rows[0]['close']}")
        time.sleep(1)
    with open(OUT_DIR / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"\nmanifest: {OUT_DIR / 'manifest.json'}")


if __name__ == "__main__":
    main()
