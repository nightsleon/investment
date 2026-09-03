#!/usr/bin/env python3
"""提取美的集团2026中报关键财务页"""
import pdfplumber

pdf_path = "/Users/pidan-l/Documents/AI-Investment/investment/000333_美的集团/年报/美的集团：2026年半年度报告.pdf"
out_dir = "/Users/pidan-l/Documents/AI-Investment/investment/000333_美的集团/data"

with pdfplumber.open(pdf_path) as pdf:
    # 第3节管理层讨论与分析 - 财务分析部分
    # 第8节财务报告 - 利润表/资产负债表/现金流量表
    # 估计：财务报告从第95页开始
    
    # 提取30-60页（管理层讨论与分析的财务部分）
    text_p2 = ""
    for i in range(29, 60):  # 第30-60页 (0-indexed: 29-59)
        text = pdf.pages[i].extract_text() or ""
        text_p2 += f"\n===== 第{i+1}页 =====\n{text}"
    
    with open(f"{out_dir}/中报P30-60.txt", 'w', encoding='utf-8') as f:
        f.write(text_p2)
    
    # 提取95-115页（财务报表）
    text_p3 = ""
    for i in range(94, 115):  # 第95-115页
        if i >= len(pdf.pages):
            break
        text = pdf.pages[i].extract_text() or ""
        text_p3 += f"\n===== 第{i+1}页 =====\n{text}"
    
    with open(f"{out_dir}/中报P95-115.txt", 'w', encoding='utf-8') as f:
        f.write(text_p3)
    
    print(f"P30-60: {len(text_p2)}字")
    print(f"P95-115: {len(text_p3)}字")
