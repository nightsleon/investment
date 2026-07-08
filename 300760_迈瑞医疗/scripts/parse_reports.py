import re, json
from pathlib import Path
import fitz
BASE=Path(__file__).resolve().parents[1]; REPORTS=BASE/'年报'; DATA=BASE/'data'
keywords=['主营业务分产品','主营业务分行业','主营业务分地区','体外诊断','生命信息与支持','医学影像','货币资金','交易性金融资产','其他流动资产','长期借款','租赁负债','一年内到期的非流动负债','受限资产','所有权或使用权受到限制']
summary={}
for pdf in sorted(REPORTS.glob('*_年度报告.pdf')):
    doc=fitz.open(pdf)
    year=pdf.name[:4]
    hits=[]
    for i,p in enumerate(doc):
        txt=p.get_text()
        for kw in keywords:
            if kw in txt:
                hits.append({'page':i+1,'keyword':kw,'text':txt[:2000]})
                break
    # save all relevant page text around unique pages
    pages=sorted(set(h['page'] for h in hits))
    out=[]
    for pg in pages:
        txt=doc[pg-1].get_text()
        out.append(f'--- page {pg} ---\n{txt}')
    (DATA/f'{year}_pdf_key_pages.txt').write_text('\n'.join(out),encoding='utf-8')
    summary[year]=hits[:100]
(DATA/'pdf_keyword_hits.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({y:[h['page'] for h in hs[:20]] for y,hs in summary.items()},ensure_ascii=False,indent=2))
