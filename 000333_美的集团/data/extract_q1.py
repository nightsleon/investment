#!/usr/bin/env python3
"""提取美的集团一季报核心数据"""
import pdfplumber

pdf_path = "/Users/pidan-l/Documents/AI-Investment/investment/000333_美的集团/年报/美的集团：2026年第一季度报告.pdf"

with pdfplumber.open(pdf_path) as pdf:
    print(f"总页数: {len(pdf.pages)}")
    all_text = ""
    for i in range(len(pdf.pages)):
        text = pdf.pages[i].extract_text() or ""
        all_text += f"\n===== 第{i+1}页 =====\n{text}"
    
    out_path = "/Users/pidan-l/Documents/AI-Investment/investment/000333_美的集团/data/一季报全文.txt"
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(all_text)
    print(f"已保存: {out_path} ({len(all_text)}字)")
