# 行情与PE数据源调查（2026-09实测，v2 更新）

## PE 百分位获取：瀑布式降级

```
1. 首选 10 年：东财接口 → 不足则补 AKShare/Tushare
   → 覆盖 ≥9.5 年 → 报"近 10 年 X% 分位"
2. 不足 10 年：取上市以来全部日频 PE-TTM
   → 报"上市以来（YYYY 年起，约 N 年）X% 分位"
3. 上市不足 3 年：放弃分位，只报当前 PE + 同业横向对比
```

**禁止**：用短窗口冒充长窗口（如 8 年数据写"近 10 年"）。
**标注规范**：分位必须写明数据起始日和实际覆盖年限。

---

## A 股数据源

### 东方财富（主用）

**快捷获取（首选）：**
```bash
python3 scripts/fetch_valuation.py 600809  # 或 000333
```
脚本已内置东财主用接口与腾讯备用通道，自动返回现价、总市值、官方 PE(TTM) 与 PB。

**底层接口原理：**
```
https://push2.eastmoney.com/api/qt/stock/get?secid=市场.代码&fields=f43,f116,f162,f164&fltt=2&invt=2
```
- 沪市 `secid=1.600xxx`，深市 `secid=0.300xxx`
- 带 `fltt=2` 时返回值已是浮点，**不要再 ÷100**
- f43 = 现价、f116 = 总市值（÷1e8 得亿）
- **f162 = 动态 PE**（市值÷最新报告期净利年化，H1×2、Q3×4/3）——**不是 TTM**
- **f164 = PE(TTM)**（市值÷滚动12月）——**用这个**
- 实测差异：f162 与 f164 相差可达 20%+

**历史 PE 逐日序列**：
```
https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_VALUEANALYSIS_DET&filter=(SECURITY_CODE="代码")&pageSize=5000
```
- 字段：`PE_TTM`、`PB_MRQ`、`CLOSE_PRICE`、`TOTAL_MARKET_CAP`、`TRADE_DATE`
- **数据窗口**：通常只返回 2018 年以来（约 2100 交易日 / 8.5 年）
- **不足 10 年时**：补 AKShare / Tushare（见下）
- 存 `个股目录/data/pe_history.csv`，日频，这是行情数据的**权威源**（季度 CSV 的 close 可能是错的）

**公告 PDF 兜底**：
```
https://np-anotice-stock.eastmoney.com/api/security/ann?sr=-1&page_size=50&ann_type=A&client_source=web&stock_list=代码
```
拿 `art_code` 后拼 PDF：`https://pdf.dfcfw.com/pdf/H2_{art_code}_1.pdf`

**F10 财务累计值**：
```
https://datacenter.eastmoney.com/.../RPT_F10_FINANCE_MAINFINADATA
```
字段 `PARENTNETPROFIT`（归母净利累计值）

### AKShare（补充 10 年 PE 历史）

当东财接口不足 10 年时：
- `stock_a_lg_indicator()` → 返回 PE/PE_TTM/PB/PS 历史序列，部分公司可回溯到 2010 年
- `stock_zh_a_hist()` → 日频收盘价（前复权/后复权/不复权）
- 合并方法：东财 2018+ 日频 + AKShare 更早年份，按日期拼接去重

### Tushare Pro（补充 10 年 PE 历史）

- `daily_basic` 接口 → 字段 `pe_ttm`、`pb`、`total_mv`，部分公司可回溯到 2010 年
- 需 token，有调用频次限制
- 与东财数据合并时以日期对齐

### 同花顺（交叉验证）

- 财务指标：`https://basic.10jqka.com.cn/new/{code}/finance.html`（必须带 User-Agent + Referer）
- 同花顺网页的 PE_TTM 是前端拿市值÷财务数据自算的，等于手工 TTM 口径（≈东财 f164）
- 不提供可直接抓取的 PE 字段；要用同花顺口径就自己拉财务净利+市值计算

---

## yfinance（港股首选，2026-09 实测验证）

**港股历史股价最稳定的数据源**：yfinance 库，代码格式 `{code}.HK`（去掉前导零，如农夫山泉 `9633.HK`、泡泡玛特 `9992.HK`）。

```python
import yfinance as yf
raw = yf.download("9633.HK", start="2020-09-08", auto_adjust=False, progress=False)
# 返回 MultiIndex columns，需展平：
if isinstance(raw.columns, pd.MultiIndex):
    raw.columns = raw.columns.get_level_values(0)
price = raw.reset_index()[['Date', 'Adj Close', 'Close']]
```

- `Adj Close` = 前复权（含分红），用于归一化对比图
- `Close` = 不复权，用于 PE 计算
- 2026-09 实测：农夫山泉 1479 个交易日数据完整返回，无连接问题

**与东方财富的关系**：yfinance 获取股价，东方财富获取 PE/财务数据，两者互补不冲突。

---

## 本地参考实现（data-api）

**路径**：`~/Documents/AI-Investment/investment/data-api/`

该目录包含三个开源数据获取库的完整源码，可作为 API 调用的参考实现：

- **efinance**（推荐）：`efinance/stock/getter.py` 中的 `get_quote_history_single()` 函数展示了如何调用东财 push2his API
- **akshare**：`akshare/stock/stock_hk_hist.py` 包含港股历史数据获取逻辑
- **tushare**：Tushare Pro API 的完整实现

**使用场景**：
1. 当直接调用 API 失败时，查阅源码确认正确的 URL 格式和参数
2. 复用其中的数据解析和清洗逻辑
3. 了解各数据源的字段映射关系

---

## 网络可靠性与降级策略

**已知风险**：外部数据 API（东财、Yahoo Finance、新浪、腾讯）可能因网络问题、反爬机制、服务不稳定等原因失败。

**降级策略**：
1. **多源尝试**：按优先级依次尝试不同数据源（东财 → Yahoo → 新浪 → 腾讯）
2. **查阅 data-api 源码**：如果直接调用失败，查阅 `~/Documents/AI-Investment/investment/data-api/` 中的参考实现，确认正确的请求格式
3. **跳过图表生成**：如果所有数据源均失败，可跳过股价vs利润TTM对比图，但仍需完成文字分析
4. **标注数据缺失**：在文章中明确标注"历史股价数据暂不可用，图表待补充"
5. **硬门禁豁免**：G5（图已生成）在网络故障时可豁免，但 G1-G4 仍需满足

**常见失败模式**：
- `RemoteDisconnected`：服务端主动断开连接，通常是反爬或网络不稳定
- `HTTP 429 Too Many Requests`：请求过于频繁，需要降低频率或更换数据源
- `HTTP 404`：URL 错误或资源不存在，检查参数格式
- `Connection refused`：网络层面被阻断，可能需要代理或更换网络环境

---

## 港股数据源

### 本地参考实现：`data-api/` 代码库

**路径**：`~/Documents/AI-Investment/investment/data-api/`

该项目包含 akshare、efinance、tushare 三个开源库的完整源码，是港股数据接口调用的**权威参考实现**。遇到 API 调用问题时，先读源码确认正确的 URL 和参数格式：

- **efinance**（推荐首选）：`efinance/efinance/common/getter.py` 的 `get_quote_history_single()` 函数统一处理所有市场（含港股）的K线获取，调用 `push2his.eastmoney.com`。`efinance/efinance/common/config.py` 定义了市场编号映射。
- **akshare**：`akshare/akshare/stock_fundamental/stock_finance_hk_em.py` 提供港股财务报表数据（资产负债表/利润表/现金流量表），调用 `datacenter.eastmoney.com`。akshare 的港股历史K线函数 `stock_hk_hist()` 底层通过 efinance 的 common getter 统一调用。
- **tushare**：`tushare/tushare/stock/` 目录下的文件主要面向 A 股，港股支持有限。

### 东财港股接口（实测验证）

**历史K线**（efinance 实现确认）：
```
https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=116.代码&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61&klt=101&fqt=1&beg=20200908&end=20500101
```
- 港股历史K线 secid 前缀 **`116.`**（如 `116.09633`）
- klt=101 日K、102 周K、103 月K
- fqt=0 不复权、1 前复权、2 后复权
- **必须带 Referer header**：`Referer: https://quote.eastmoney.com/`，否则可能被拒绝连接

**实时行情**：
```
https://push2.eastmoney.com/api/qt/stock/get?secid=116.代码&fields=f43,f116,f162,f164&fltt=2&invt=2
```
- f43 现价（港币）、f116 总市值（港币）
- f164 港股可返回 PE-TTM（2026-09 实测农夫山泉 09633 返回 22.87）
- f162/f164 字段港股**有时可返回有效值**，不再一定为 0——但仍建议手工复算交叉验证

**港股行情列表**（批量获取所有港股实时行情）：
```
https://push2.eastmoney.com/api/qt/clist/get?fs=m:128+t:3,m:128+t:4,m:128+t:1,m:128+t:2
```
- 港股列表用市场编号 **`128`**（不是 116）
- **116 用于单股K线/行情查询，128 用于列表枚举**——两个编号用途不同，不要混用

### AKShare（补充）

- `stock_hk_hist()` → 日频 OHLCV（底层调用同东财 push2his 接口）
- `stock_hk_spot_em()` → 实时行情（现价、市值、PE、PB）
- 历史 PE 不直接提供，需自行计算：日频收盘价 × 总股本 ÷ 最近四个季度归母溢利

### 港股 PE-TTM 手工计算与量化对齐规范

#### 1. 快捷获取（首选）：
直接运行内置轻量脚本，自动完成币种汇率折算并提取官方 PE-TTM：
```bash
python3 scripts/fetch_valuation.py 09633
# 或输出纯 JSON
python3 scripts/fetch_valuation.py 09633 --json
```

#### 2. 手工计算与历史回算方法：
```
TTM 归母溢利 = 上年全年 − 上年同期累计 + 本期累计（母公司拥有人应占溢利，通常为人民币 RMB）
PE(TTM) = 当日总市值（港币 HKD）× 当日汇率（HKD/CNY）÷ TTM 归母溢利（人民币 RMB）
```

#### 3. 港股历史序列回测两大铁律（避免同花顺/Wind数据对不上）：

* **铁律一：Point-in-Time (PIT) 点时原则（杜绝前视偏差 Look-ahead Bias）**：
  * TTM 利润阶梯函数的跳变生效日，必须是**公司官方实际发布业绩公告的日期（Announcement Date）**，**严禁使用财报截止日（Period End Date）**！
  * **翻车教训**：农夫山泉 2024H1 财报是在 2024 年 8 月 27 日正式发布的。如果脚本在 2024 年 7 月 2 日就提前套用新利润计算 TTM，会导致 7 月至 8 月底的 PE 被人为虚假拉低 8%，凭空产生十几个虚假的“低 PE 交易日”，导致最终历史分位数算成 3.2%（而同花顺真实分位是 0.81%）。
  * 必须维护或读取类似 `data/profit_disclosure_events.csv` 的公告日表，通过 `pd.merge_asof(..., direction='backward')` 向前填充生效。

* **铁律二：逐日动态汇率折算（严禁全历史固定汇率）**：
  * 中资港股股价是港元（HKD），财报净利润是人民币（RMB）。
  * 港元兑人民币汇率历史上在 0.81～0.93 宽幅波动。**严禁在全历史 1000+ 交易日中一刀切套用固定估算汇率（如 0.90）**，必须匹配每日真实的外汇中间价序列（如 yfinance `HKDCNY=X` 或外汇交易中心 CFETS 数据）。

* **铁律三：明确分位数的时间窗口**：
  * 终端中的分位通常分为：**近 3 年（约 730 交易日）**、**近 5 年（约 1215 交易日）**、**上市以来**。
  * 引用时必须严格标注窗口与样本基数，例如：`同花顺近5年 0.81% 分位` 或 `上市以来（2020年起，6年）1.2% 分位`。

---

## PE(TTM) 口径判定（最终裁决）

手工 TTM 净利 = 上年全年归母 − 上年同期累计 + 本期累计；市值 ÷ TTM 净利 = 真 PE(TTM)。
- A 股与 f164 一致 → f162 是动态口径（单季/半年年化），不可作为 TTM
- 港股优先调用 `scripts/fetch_valuation.py`（东财/腾讯官方折算 f164/TTM 接口），并用 PIT 披露日净利核对
- **任何平台的"默认显示PE"都不能盲目引用。必须确认其为 TTM 口径且理解其汇率与披露日对齐逻辑。**

