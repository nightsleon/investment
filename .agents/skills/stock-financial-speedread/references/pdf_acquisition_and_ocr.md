# 财报 PDF 获取、验证与 OCR 排障指南

## 一、PDF 来源优先级链

### 1. A 股财报获取
- **主选**：巨潮资讯网公告列表接口（POST）：
  ```
  https://www.cninfo.com.cn/new/hisAnnouncement/query
  （带 plate=sz|sh + stock=代码）
  ```
- **备选**：东方财富公告接口：
  ```
  https://np-anotice-stock.eastmoney.com/api/security/ann?sr=-1&page_size=50&ann_type=A&client_source=web&stock_list={代码}
  ```
  获取 `art_code` 拼接对应 PDF 下载链接。
- **反爬注意**：巨潮资讯网部分 CDN 节点（`static.cninfo.com.cn/finalpage/...`）开启了 WAF 防护，裸 curl 可能返回 403。需携带标准浏览器 Header（Referer、Accept-Language、Cookie），若直接下载受阻可用 `web_extract` 提取。

---

### 2. 港股财报获取优先级
港交所披露易的 URL 模式不规律（如 `2026/0825/2026082500511_c.pdf`），不能盲目硬猜。按以下顺序尝试：

1. **公司官网 IR 页 / 自有 CDN（最可靠）**：
   - 绝大多数成熟港股公司在官网设有 IR/投资者关系/财务报告页面，PDF 托管在公司自有 CDN（如农夫山泉托管在 `file-cloud.yst.com.cn`）。
   - 检索方式：`{公司名} 官网 财务信息` 或 `{公司名} IR page`，直接获取公告列表中的 PDF 链接。
2. **券商镜像站**：
   - moomoo（`newsfile.moomoo.com`）、富途牛牛等平台会镜像托管公告 PDF 全文。
   - 检索：`{公司名} {年份} 中期业绩 site:moomoo.com`。
3. **港交所披露易（HKEXnews）**：
   - 访问 `https://www1.hkexnews.hk/search/titlesearch.xhtml`，通过股票代码检索。
4. **`_c` 后缀规则**：
   - 港股公告 PDF 通常以 `_c.pdf` 结尾表示中文版。如果搜索结果是不带 `_c` 的 URL（如 `2025082600883.pdf`），**应立即追加 `_c`**。无后缀的 URL 常返回 404 HTML。

---

## 二、下载后立即验证（防范 404 与牛熊证陷阱）

下载后必须用 `file` 命令或 Python 脚本立即验证，避免误拿无效文件：
1. **文件合法性**：检查文件前 4 字节是否为 `%PDF`。很多返回 2KB 大小的文件实际是 404 错误 HTML 页面。
2. **主体匹配**：确认公司全称、股票代码与报告期（如“农夫山泉股份有限公司”、“9633”、“截至2026年6月30日止六个月”）。
3. **排查衍生品噪音**：搜索结果排名靠前的港股公告常为 J.P. Morgan 等机构发行的 CBBC 牛熊证或衍生品到期通告，切勿当成上市公司业绩公告。

---

## 三、扫描版 PDF 提取与 OCR 强制回退链

部分港股公告 PDF 是纯扫描件（无可提取文本层）。当 `read_file` 报错 `"PDF has no extractable text"` 或 `"OCR is required"` 时，**严禁反复重试 `read_file`**，立即按以下回退链执行：

### 1. 第一级：用 PyMuPDF 探查
```bash
python3 -c "
import fitz
doc = fitz.open('path/to/report.pdf')
for i, page in enumerate(doc):
    print(f'--- Page {i+1} ---')
    print(page.get_text())
"
```

### 2. 第二级：纯图像扫描件 OCR 处理
若 `fitz.get_text()` 依然返回空文本，执行本地 OCR 工具：
- **首选**：`marker-pdf`（`marker_single path/to/report.pdf`）；
- **备选**：`tesseract + pdf2image` 处理关键财务报表页码。
