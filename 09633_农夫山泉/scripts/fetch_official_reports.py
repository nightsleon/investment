#!/usr/bin/env python3
"""下载农夫山泉港交所官方财报，并生成来源台账。"""
from pathlib import Path
import csv
import requests

BASE = Path(__file__).resolve().parents[1]
REPORT_DIR = BASE / "年报"
DATA_DIR = BASE / "data"

SOURCES = [
    ("2020年报", "https://www1.hkexnews.hk/listedco/listconews/sehk/2021/0427/2021042701532.pdf", "annual_report_2020.pdf"),
    ("2021年报", "https://www1.hkexnews.hk/listedco/listconews/sehk/2022/0428/2022042803673.pdf", "annual_report_2021.pdf"),
    ("2022年报", "https://www1.hkexnews.hk/listedco/listconews/sehk/2023/0414/2023041400852.pdf", "annual_report_2022.pdf"),
    ("2023年报", "https://www1.hkexnews.hk/listedco/listconews/sehk/2024/0418/2024041802052.pdf", "annual_report_2023.pdf"),
    ("2024年报", "https://www1.hkexnews.hk/listedco/listconews/sehk/2025/0425/2025042503151.pdf", "annual_report_2024.pdf"),
    ("2025年报", "https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0417/2026041701389.pdf", "annual_report_2025.pdf"),
    ("2020中报", "https://www1.hkexnews.hk/listedco/listconews/sehk/2020/0924/2020092401511.pdf", "interim_report_2020.pdf"),
    ("2021中报", "https://www1.hkexnews.hk/listedco/listconews/sehk/2021/0924/2021092400741.pdf", "interim_report_2021.pdf"),
    ("2022中报", "https://www1.hkexnews.hk/listedco/listconews/sehk/2022/0923/2022092301828.pdf", "interim_report_2022.pdf"),
    ("2023中报", "https://www1.hkexnews.hk/listedco/listconews/sehk/2023/0922/2023092200818.pdf", "interim_report_2023.pdf"),
    ("2024中报", "https://www1.hkexnews.hk/listedco/listconews/sehk/2024/0920/2024092001250.pdf", "interim_report_2024.pdf"),
    ("2025中报", "https://www1.hkexnews.hk/listedco/listconews/sehk/2025/0923/2025092300352.pdf", "interim_report_2025.pdf"),
    ("2026年6月证券变动月报", "https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0706/2026070601336.pdf", "monthly_return_2026-06.pdf"),
]


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    ledger = []
    for title, url, filename in SOURCES:
        path = REPORT_DIR / filename
        if not path.exists() or path.stat().st_size < 10_000:
            response = session.get(url, timeout=90)
            response.raise_for_status()
            if not response.content.startswith(b"%PDF"):
                raise RuntimeError(f"{title} 返回内容不是 PDF: {url}")
            path.write_bytes(response.content)
        ledger.append({"资料": title, "文件": str(path.relative_to(BASE)), "来源": url, "字节数": path.stat().st_size})
        print(f"{title}: {path.name} ({path.stat().st_size:,} bytes)")
    with (DATA_DIR / "sources.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["资料", "文件", "来源", "字节数"])
        writer.writeheader()
        writer.writerows(ledger)


if __name__ == "__main__":
    main()
