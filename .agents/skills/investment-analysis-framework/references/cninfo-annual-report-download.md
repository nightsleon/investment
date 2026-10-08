# 巨潮资讯网年报下载与复核流程

适用：A股公司投资分析报告、公司研究包初始化、现金头寸/分部附注复核。

## 核心规则

写个股深度报告、3R简报、财报速览等任何涉及公司财务数据的任务，**第一步都是从巨潮资讯网下载对应期数的官方财报PDF**到公司研究包 `年报/` 目录，再写/校验报告。不要只用东方财富 API 或新闻解读替代财报 PDF。

适用范围：年度报告、半年度报告（中报）、季度报告。深度报告至少近5年年报 + 最新中报/季报；财报速览只需对应单期报告PDF。

## 查询 orgId

巨潮公告查询 `stock` 参数通常不能只传股票代码。应先用 topSearch 查询 orgId：

```python
import requests
headers = {
    'User-Agent': 'Mozilla/5.0',
    'Referer': 'http://www.cninfo.com.cn/new/fulltextSearch',
}
r = requests.post(
    'http://www.cninfo.com.cn/new/information/topSearch/query',
    headers=headers,
    data={'keyWord': '特变电工', 'maxSecNum': 10},
    timeout=20,
)
print(r.text)
# 示例返回：{"code":"600089", "orgId":"gssh0600089", ...}
```

## 查询年度报告公告

使用 `stock={code},{orgId}`。例如特变电工是 `600089,gssh0600089`，只传 `600089` 会查不到公告。

```python
import requests, re
headers = {
    'User-Agent': 'Mozilla/5.0',
    'Referer': 'http://www.cninfo.com.cn/new/commonUrl/pageOfSearch?url=disclosure/list/search',
}
url = 'http://www.cninfo.com.cn/new/hisAnnouncement/query'
data = {
    'pageNum': 1,
    'pageSize': 50,
    'column': 'sse',          # 沪市；深市视情况调整
    'tabName': 'fulltext',
    'plate': 'sse',
    'stock': '600089,gssh0600089',
    'searchkey': '',
    'secid': '',
    'category': 'category_ndbg_szsh',  # 年度报告；半年报用 category_bndbg_szsh；一季报 category_yjdbg_szsh；三季报 category_sjdbg_szsh
    'trade': '',
    'seDate': '2020-01-01~2026-06-24',
    'sortName': '',
    'sortType': '',
    'isHLtitle': 'true',
}
j = requests.post(url, headers=headers, data=data, timeout=30).json()
for a in j.get('announcements') or []:
    title = re.sub('<.*?>', '', a.get('announcementTitle', ''))
    if '年度报告' in title and '摘要' not in title and '英文' not in title:
        print(title, 'http://static.cninfo.com.cn/' + a['adjunctUrl'])
```

## 下载到研究包

```python
from pathlib import Path
import requests, re, json

base = Path('600089_特变电工/年报')
base.mkdir(parents=True, exist_ok=True)
manifest = []
for year, title, adjunct_url in items:
    full_url = 'http://static.cninfo.com.cn/' + adjunct_url
    path = base / f'{year}_特变电工_年度报告.pdf'
    r = requests.get(full_url, headers={'User-Agent':'Mozilla/5.0','Referer':'http://www.cninfo.com.cn/'}, timeout=60)
    r.raise_for_status()
    path.write_bytes(r.content)
    manifest.append({'year': year, 'title': title, 'url': full_url, 'file': str(path), 'bytes': path.stat().st_size})
(base / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
```

## PDF 附注复核重点

用 PyMuPDF 抽取全文并搜索以下关键词：

- 现金头寸：`货币资金`、`交易性金融资产`、`一年内到期的非流动资产`、`其他流动资产`、`大额存单`、`定期存款`、`受限制的货币资金`、`所有权或使用权受限资产`。
- 长期负债：`长期借款`、`一年内到期的非流动负债`、`应付债券`、`租赁负债`。
- 产品结构：`主营业务分产品情况`、`主营业务分地区情况`。

现金头寸不能只看 API 字段：
- `其他流动资产` 不能整体计入，只能计入年报附注明确为大额存单/理财/定期存款的部分。
- 若货币资金中披露大额受限资金，应同时给出“形式现金头寸”和“可用现金头寸”。
- 受限货币资金常见来源：票据保证金、保函保证金、环境恢复治理保障基金、司法冻结、期货/外汇保证金、定期及通知存款等。

## 报告写法

报告末尾“数据校验结果”应明确：
- 年报 PDF 下载年份与来源；
- 产品结构是否用年报主营构成复核；
- 现金头寸使用了哪些附注项目；
- 若仍有未复核项，列入“待复核”，不要把已复核项继续写成待复核。
