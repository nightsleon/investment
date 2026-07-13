#!/usr/bin/env python3
import requests,re,json
from pathlib import Path
H={'User-Agent':'Mozilla/5.0','Referer':'http://www.cninfo.com.cn/new/commonUrl/pageOfSearch?url=disclosure/list/search'}
data={'pageNum':1,'pageSize':100,'column':'szse','tabName':'fulltext','plate':'szse','stock':'000333,9900005965','searchkey':'','secid':'','category':'category_ndbg_szsh','trade':'','seDate':'2020-01-01~2025-12-31','sortName':'','sortType':'','isHLtitle':'true'}
j=requests.post('http://www.cninfo.com.cn/new/hisAnnouncement/query',headers=H,data=data,timeout=30).json()
base=Path(__file__).resolve().parents[1]/'年报'; items=[]
for a in j.get('announcements') or []:
    title=re.sub('<.*?>','',a.get('announcementTitle',''))
    m=re.search(r'(2020|2021|2022|2023)年年度报告$',title)
    if not m or '摘要' in title or '英文' in title: continue
    year=m.group(1); url='http://static.cninfo.com.cn/'+a['adjunctUrl']; path=base/f'美的集团：{year}年年度报告.pdf'
    r=requests.get(url,headers={'User-Agent':'Mozilla/5.0','Referer':'http://www.cninfo.com.cn/'},timeout=90); r.raise_for_status(); path.write_bytes(r.content)
    items.append({'year':year,'title':title,'url':url,'file':str(path),'bytes':path.stat().st_size})
    print(year,path,path.stat().st_size)
(base/'manifest.json').write_text(json.dumps(items,ensure_ascii=False,indent=2),encoding='utf-8')
