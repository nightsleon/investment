#!/usr/bin/env python3
"""提取美的集团2026中报核心数据"""
import pdfplumber
import json

pdf_path = "/Users/pidan-l/Documents/AI-Investment/investment/000333_美的集团/年报/美的集团：2026年半年度报告.pdf"

with pdfplumber.open(pdf_path) as pdf:
    print(f"总页数: {len(pdf.pages)}")
    
    # 提取前10页（主要财务数据通常在前面）
    all_text = ""
    for i in range(min(30, len(pdf.pages))):
        text = pdf.pages[i].extract_text() or ""
        all_text += f"\n===== 第{i+1}页 =====\n{text}"
    
    # 保存到文件
    out_path = "/Users/pidan-l/Documents/AI-Investment/investment/000333_美的集团/data/中报前30页.txt"
    import os
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(all_text)
    
    print(f"已保存前30页文本到: {out_path}")
    print(f"总字数: {len(all_text)}")
