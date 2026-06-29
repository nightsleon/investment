from pathlib import Path
import fitz, re, json

BASE=Path(__file__).resolve().parents[1]
pdf=BASE/'年报'/'2025_特变电工_年度报告.pdf'
out=BASE/'data'/'annual_report_2025_extract.txt'
json_out=BASE/'data'/'annual_report_2025_snippets.json'

doc=fitz.open(pdf)
terms=[
    '货币资金','其他流动资产','交易性金融资产','债权投资','短期借款','长期借款','一年内到期的非流动负债','应付债券','租赁负债',
    '受限制的货币资金','所有权或使用权受到限制','主营业务分行业','主营业务分产品','主营业务分地区','分行业','分产品','高纯多晶硅','现金及现金等价物'
]
# Extract all text to searchable file
texts=[]
for i,page in enumerate(doc):
    txt=page.get_text('text')
    texts.append(f'\n\n===== PAGE {i+1} =====\n'+txt)
out.write_text('\n'.join(texts),encoding='utf-8')

snips=[]
for i,page in enumerate(doc):
    txt=page.get_text('text')
    for term in terms:
        if term in txt:
            # get compact surrounding blocks by lines
            lines=txt.splitlines()
            idxs=[j for j,l in enumerate(lines) if term in l]
            for idx in idxs[:3]:
                start=max(0,idx-8); end=min(len(lines),idx+18)
                snips.append({'page':i+1,'term':term,'text':'\n'.join(lines[start:end])})
json_out.write_text(json.dumps(snips,ensure_ascii=False,indent=2),encoding='utf-8')
print('pages',len(doc),'snippets',len(snips))
print(out)
print(json_out)
