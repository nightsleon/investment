#!/usr/bin/env python3
"""
非标/跨境指数官方单张 (Factsheet) 自动化下载与结构化解析引擎
支持标普道琼斯 (S&P DJI) 等受 Akamai/反爬防护指数单张的自动化下载与指标解析。
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
DEFAULT_TARGET_DIR = os.path.join(PROJECT_ROOT, "indices", "sources", "index-factsheets")

PRESET_URLS = {
    "sp": {
        "SPAHLVCP_TR": "https://www.spglobal.com/spdji/zh/idsenhancedfactsheet/file.pdf?calcFrequency=M&force_download=true&hostIdentifier=48190c8c-42c4-46af-8d1a-0cd5db894797&languageId=142&indexId=92321368",
        "SPAHLVCP_NTR": "https://www.spglobal.com/spdji/zh/idsenhancedfactsheet/file.pdf?calcFrequency=M&force_download=true&hostIdentifier=48190c8c-42c4-46af-8d1a-0cd5db894797&languageId=142&indexId=92321363",
    }
}


def trigger_chrome_download(url: str, delay_sec: int = 4) -> bool:
    """通过 AppleScript 调度宿主机 Chrome 新建标签页打开直链触发下载并自动清理。"""
    script = f'''
    tell application "Google Chrome"
        tell front window
            set newTab to make new tab with properties {{URL:"{url}"}}
            delay {delay_sec}
            try
                close newTab
            end try
        end tell
    end tell
    '''
    res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    return res.returncode == 0 or "tab id" in res.stderr


def sync_from_downloads(target_dir: str, pattern: str = "fs-sp-access", timeout_sec: int = 15) -> str:
    """通过 Finder AppleScript 检查 Downloads 目录下的最新文件并同步至目标目录。"""
    os.makedirs(target_dir, exist_ok=True)
    target_posix = os.path.abspath(target_dir)

    script = f'''
    tell application "Finder"
        set downFolder to folder (POSIX file "{os.path.expanduser('~/Downloads')}" as text)
        set targetFolder to folder (POSIX file "{target_posix}" as text)
        set targetFiles to (every file of downFolder whose name contains "{pattern}")
        if (count of targetFiles) is 0 then
            return "NOT_FOUND"
        end if
        
        set latestFile to item 1 of targetFiles
        set latestDate to modification date of latestFile
        repeat with aFile in targetFiles
            if (modification date of aFile) > latestDate then
                set latestFile to aFile
                set latestDate to modification date of aFile
            end if
        end repeat
        
        set fName to name of latestFile
        duplicate latestFile to targetFolder with replacing
        return fName
    end tell
    '''
    start_time = time.time()
    while time.time() - start_time < timeout_sec:
        res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
        out = res.stdout.strip()
        if out and out != "NOT_FOUND" and not out.startswith("ERROR"):
            return out
        time.sleep(1.5)

    return ""


def parse_sp_factsheet(pdf_path: str) -> dict:
    """使用 PyMuPDF 解析标普 Factsheet PDF 并提取关键财务指标与前十大持仓。"""
    try:
        import pymupdf as fitz
    except ImportError:
        try:
            import fitz
        except ImportError:
            print("[!] 缺少 pymupdf / fitz，请在项目虚拟环境中运行 (.venv/bin/python)...")
            sys.exit(1)

    doc = fitz.open(pdf_path)
    full_text = "\n".join([page.get_text() for page in doc])

    data = {
        "file_path": os.path.abspath(pdf_path),
        "file_name": os.path.basename(pdf_path),
        "parse_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "provider": "S&P Dow Jones Indices",
        "index_name": "S&P Access Hong Kong Low Volatility High Dividend Index",
        "fundamentals": {},
        "top_constituents": [],
    }

    # 1. 提取截至日期
    as_of_match = re.search(r"截至\s+([A-Z]+ \d+, \d{4})", full_text, re.IGNORECASE)
    if as_of_match:
        data["as_of_date"] = as_of_match.group(1).strip()

    # 2. 提取基本面（PE, PB, 股息率等）
    for page in doc:
        p_text = page.get_text()
        if "基本面" in p_text and "股息率" in p_text:
            lines = [l.strip() for l in p_text.split("\n") if l.strip()]
            for i, line in enumerate(lines):
                if line == "基本面":
                    sub_lines = lines[i : i + 25]
                    for val in sub_lines:
                        if "%" in val and "dividend_yield" not in data["fundamentals"]:
                            data["fundamentals"]["dividend_yield"] = val
                    num_matches = [l for l in sub_lines if re.match(r"^\d+\.\d+$", l)]
                    if len(num_matches) >= 5:
                        data["fundamentals"]["trailing_pe"] = float(num_matches[0])
                        data["fundamentals"]["projected_pe"] = float(num_matches[1])
                        data["fundamentals"]["pb"] = float(num_matches[2])
                        # 标普单张第5列为市销率 (0.59)，第6列为市现率 (5.67)
                        data["fundamentals"]["price_to_sales"] = float(num_matches[3])
                        data["fundamentals"]["price_to_cash_flow"] = float(num_matches[4])

    # 3. 提取前十大持仓
    for page in doc:
        p_text = page.get_text()
        if "按指数权重的十大成分股" in p_text:
            lines = [l.strip() for l in p_text.split("\n") if l.strip()]
            for i, line in enumerate(lines):
                if "CONSTITUENT" in line or "代码" in line:
                    stock_lines = lines[i + 1 : i + 35]
                    idx = 0
                    while idx < len(stock_lines) and len(data["top_constituents"]) < 10:
                        name = stock_lines[idx]
                        if idx + 2 < len(stock_lines) and re.match(r"^\d{5}$", stock_lines[idx + 1]):
                            code = stock_lines[idx + 1]
                            sector = stock_lines[idx + 2]
                            data["top_constituents"].append({
                                "rank": len(data["top_constituents"]) + 1,
                                "name": name,
                                "code": code,
                                "sector": sector,
                            })
                            idx += 3
                        else:
                            idx += 1

    return data


def main():
    parser = argparse.ArgumentParser(description="非标指数单张自动化下载与解析")
    parser.add_argument("--provider", choices=["sp", "hsi", "ftse"], default="sp", help="指数提供商")
    parser.add_argument("--index", choices=["SPAHLVCP_TR", "SPAHLVCP_NTR"], default="SPAHLVCP_NTR", help="预设指数代码")
    parser.add_argument("--url", type=str, default="", help="自定义单张下载直链")
    parser.add_argument("--pattern", type=str, default="fs-sp-access", help="Downloads 目录文件匹配前缀")
    parser.add_argument("--target-dir", type=str, default=DEFAULT_TARGET_DIR, help="目标保存目录")
    parser.add_argument("--pdf-path", type=str, default="", help="直接指定已有本地 PDF 进行解析")
    parser.add_argument("--no-download", action="store_true", help="不重新下载，仅解析已有文件")

    args = parser.parse_args()
    target_pdf = args.pdf_path

    if not target_pdf and not args.no_download:
        if args.url:
            download_url = args.url
        elif args.provider in PRESET_URLS and args.index in PRESET_URLS[args.provider]:
            download_url = PRESET_URLS[args.provider][args.index]
        else:
            print(f"[!] 未找到指数 {args.index} 的预设下载直链，请通过 --url 传入。")
            sys.exit(1)

        print(f"[*] 启动 Chrome 自动化触发单张下载: {download_url[:80]}...")
        trigger_chrome_download(download_url, delay_sec=4)

        print(f"[*] 正在通过 Finder 监听并同步最新文件 (匹配: {args.pattern})...")
        synced_name = sync_from_downloads(args.target_dir, pattern=args.pattern, timeout_sec=10)
        if synced_name:
            raw_path = os.path.join(args.target_dir, synced_name)
            clean_name = re.sub(r"\s+\(\d+\)\.pdf$", ".pdf", synced_name)
            target_pdf = os.path.join(args.target_dir, clean_name)
            if clean_name != synced_name and os.path.exists(raw_path):
                import shutil
                shutil.move(raw_path, target_pdf)
            print(f"[+] 成功将最新单张归档至: {target_pdf}")
        else:
            print("[!] 未能在 Downloads 中检测到新下载的文件。")
            sys.exit(1)

    if target_pdf and os.path.exists(target_pdf):
        print(f"[*] 结构化解析单张: {target_pdf}...")
        parsed = parse_sp_factsheet(target_pdf)
        json_path = os.path.splitext(target_pdf)[0] + "_metrics.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(parsed, f, ensure_ascii=False, indent=2)
        print(f"[+] 结构化指标已保存至: {json_path}")
        print("\n=== 核心估值与基本面快照 ===")
        print(f"  指数名称: {parsed.get('index_name')}")
        print(f"  截至日期: {parsed.get('as_of_date')}")
        for k, v in parsed.get("fundamentals", {}).items():
            print(f"  {k}: {v}")
        print(f"  前十大重仓总数: {len(parsed.get('top_constituents', []))}")


if __name__ == "__main__":
    main()
