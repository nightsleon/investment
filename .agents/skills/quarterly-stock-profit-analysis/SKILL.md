---
name: quarterly-stock-profit-analysis
description: "季度股价与利润趋势对比分析：数据采集、TTM计算、归一化/双Y轴图表生成"
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [investment, stock, finance, chart, TTM, visualization]
    category: data-science
---

# 季度股价与利润趋势对比分析

用于分析A股上市公司季度股价走势与利润趋势的对比，基于彼得林奇的"收益线"方法。

## 适用场景

- 验证股价是否跟随利润增长
- 判断当前股价相对利润的位置（高估/低估）
- 归一化对比、双Y轴图、单季度季节性图

## 数据源

### 数据源优先级
- **有同花顺Excel时**：以同花顺数据为准，东方财富API交叉验证
- **无同花顺Excel时**：以东方财富API为准
- 同花顺净利润数据比东方财富API更准确（API系统性偏高0.1-0.8亿/年）
- ROE应使用同花顺的加权ROE（比手动用年末净资产算的杜邦ROE更准确）

### 股价数据（主选）
Yahoo Finance（yfinance库），前复权收盘价（Adj Close），代码格式：
- 深市A股：`{code}.SZ`
- 沪市A股：`{code}.SS`
- 港股：`{code}.HK`（如泡泡玛特 `9992.HK`）
- 港股用不复权Close时注意汇率（港币 vs 人民币）

### 财务数据（两级策略）

**有同花顺Excel时（优先）：**
- 先按表头和报告期识别文件类型，不能仅凭文件名假定数据频率。
- `main_simple.xls` 常见为单季度数据；`keyindex_report.xls` 等关键指标表可能同时包含年度列和H1累计列，没有季度数据。
- 若只有年度+H1累计：H2=全年-H1；年中TTM=上年全年+本年H1-上年H1。不得按四季度滚动，也不得把H1当单季度。
- 优先用 `python_calamine.CalamineWorkbook` 读取 `.xls`；若不可用，再按本地 `xlrd` 版本支持的参数尝试兼容读取。

**无同花顺Excel时：**
- 东方财富API（datacenter.eastmoney.com）
- ⚠️ 东方财富API返回的是**累计数据**（报告期累计），不是单季度
- 需要手动转换：当季单季度 = 本期累计 - 上期累计
- Q1的累计=单季度，Q2/Q3/Q4需要减去上一期

### 东方财富API调用方式

```
fetch('https://datacenter.eastmoney.com/securities/api/data/v1/get?reportName=RPT_DMSK_FN_INCOME&columns=SECUCODE,REPORT_DATE,PARENT_NETPROFIT,DEDUCT_PARENT_NETPROFIT&filter=(SECUCODE="{code}.{market}")&pageSize=50&sortColumns=REPORT_DATE&sortTypes=-1&source=HSF10&client=PC')
```

- 深市：SECUCODE=`{code}.SZ`
- 沪市：SECUCODE=`{code}.SS`

## 核心指标

### 单季度数据
- 净利润（net_profit）
- 扣非净利润（non_gaap / deduct_parent_netprofit）—— 推荐用这个

### TTM（Trailing Twelve Months）
- 滚动4个季度求和，消除季节性波动
- `ttm = rolling(window=4).sum()`
- 不足4个季度时TTM为空

## 图表类型（三张）

### 图2：归一化对比（辅助图）
- 股价 / 基期股价 vs 扣非TTM / 基期扣非TTM
- 基期=第一个有效数据点；但若第一个有效利润TTM <= 0，不能直接作为归一化基期，应改用第一个正利润TTM点，或明确跳过归一化图
- ⚠️ **注意**：归一化图会被基期PE永久扭曲，不能用来判断"谁高谁低"或"高估/低估"。只能看两条线的大致走势是否同步。
- ⚠️ 若基期利润TTM为负，后续正常正利润除以负数会被画成负数，造成“利润线仍为负”的假象；这不是利润真的为负，而是归一化基期选错
- 用途：快速看走势同步性，不做估值判断

### 图1：双Y轴折线（主图，用于股价vs利润趋势对比）
- 左轴：股价（元）
- 右轴：扣非TTM（亿元）
- **必须用折线**，不用柱状图——折线对比斜率（增幅）更直观
### 图2：双Y轴（股价 + 扣非TTM）
- 左轴：股价（折线）
- 右轴：扣非TTM（亿元）（折线，带浅色填充）
- ⚠️ 用户偏好双折线图，不用柱状图——两条折线更清晰，避免柱状图遮挡
- 归一化对比看图1即可，图2主要看绝对数值走势

### 图3：双Y轴（股价 + 单季度扣非）
- 展示季节性锯齿
- 左轴：股价（折线）
- 右轴：单季度扣非净利润（折线，带浅色填充）
- ⚠️ 同样用折线不用柱状图

## Python脚本模板

**推荐方式**：使用 skill 内置的通用脚本，传参即可运行；不要直接信任项目根目录下同名 `scripts/generate_charts.py`，它可能是某家公司历史分析留下的硬编码脚本。

**有同花顺 `main_simple.xls` 时的优先规则**：如果公司研究包已有 `data/{code}_main_simple.xls`，应优先用该文件生成图表，因为它已经是单季度数据且通常比东方财富 API 更准。做法是复制/改造脚本为公司目录 `scripts/generate_charts.py`，用 `python_calamine` 按行名读取“净利润(元)”“扣非净利润(元)”“营业总收入(元)”“基本每股收益(元)”，计算 TTM 后再用 yfinance 对齐股价，输出到公司 `charts/`。只有没有同花顺 Excel 时，才用东方财富累计值转单季度。

```bash
# 从skill复制脚本到目标公司目录，避免误用项目里的旧脚本
cp .agents/skills/quarterly-stock-profit-analysis/scripts/generate_charts.py stocks/{code}/scripts/generate_charts.py

# 运行 A 股脚本（参数：代码 市场 公司名）
cd ~/Documents/AI投资/{code}
python3 generate_charts.py 600660 SH 福耀玻璃
python3 generate_charts.py 000333 SZ 美的集团
python3 generate_charts.py 002847 SZ 盐津铺子

# 运行港股脚本（参数：代码 公司名 [可选参数]）
python3 generate_charts_hk.py 09633 农夫山泉 --latest-h1 88.87 --latest-price 39.38
python3 generate_charts_hk.py 09992 泡泡玛特

```

运行前快速校验脚本是否真支持传参：

```bash
python3 generate_charts.py --help 2>/dev/null || sed -n '1,40p' generate_charts.py
```

如果脚本前40行里硬编码了 `CODE = "600660"`、`YF_CODE = "600660.SS"` 且没有读取 `sys.argv`，不要用它批量生成多家公司图表；先替换为 skill 内置通用脚本。运行后用 `git status` 或 `find` 检查是否在错误目录生成了 `600660_*.png/csv` 这类 stray 文件。

脚本自动完成：东方财富API取财务数据 → 累计转单季度 → TTM → yfinance取股价 → 季度末对齐 → 生成3张图+1个CSV。

**yfinance代码映射**（已固化在脚本中）：
- 沪市A股：`{code}.SS`（如 600660.SS）
- 深市A股：`{code}.SZ`（如 000333.SZ）
- 港股：`{code}.HK`（如 9992.HK）— 港股需单独处理半年报TTM，不能用此脚本
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
from pathlib import Path

# === 1) 读取财务数据 ===
# 方式A：从同花顺Excel读取（单季度）
from python_calamine import CalamineWorkbook
book = CalamineWorkbook.from_path('XXXX/XXXX_main_simple.xls')
rows = book.get_sheet_by_index(0).to_python()
headers = rows[0]
# 行名通常在第0列；按行名定位净利润、扣非净利润、EPS，不要硬编码行号。

# 方式B：从东方财富API获取（累计，需转换为单季度）
# 见"东方财富API调用方式"，拿到后：
# fin['net_profit'] = fin['net_profit_cum'].diff()  # 简化版，Q1需特殊处理

# === 2) 计算TTM ===
fin['non_gaap_ttm'] = fin['non_gaap'].rolling(4).sum()

# === 3) 获取股价 ===
raw = yf.download('{code}.{SZ|SS}', start='{ipo_date}', end='{end_date}', auto_adjust=False, progress=False)
if isinstance(raw.columns, pd.MultiIndex):
    raw.columns = raw.columns.get_level_values(0)
price = raw.reset_index()[['Date', 'Adj Close']].rename(columns={'Date': 'trade_date', 'Adj Close': 'adj_close'})

# === 4) 对齐：季度末取<=该日的最后一个交易日收盘价 ===
matched = []
for _, row in fin.dropna(subset=['non_gaap_ttm']).iterrows():
    q = row['date']
    sub = price[price['trade_date'] <= q]
    if sub.empty: continue
    last = sub.iloc[-1]
    matched.append({...})

# === 5) 绘图 ===
plt.rcParams['font.sans-serif'] = ['PingFang SC', 'Heiti SC', 'Arial Unicode MS', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

# 图1：归一化
# 如果第一个有效TTM为负/零，不要用它做基期；改用第一个正TTM点，或不画归一化图。
base_df = merged[merged['non_gaap_ttm'] > 0]
if base_df.empty:
    raise ValueError('没有正利润TTM，归一化图不适用')
base_idx = base_df.index[0]
norm_close = merged.loc[base_idx:, 'adj_close'] / merged.loc[base_idx, 'adj_close']
norm_ttm = merged.loc[base_idx:, 'non_gaap_ttm'] / merged.loc[base_idx, 'non_gaap_ttm']
# ... plot ...

# 图2：双Y轴（双折线，不用柱状图）
fig, ax1 = plt.subplots(figsize=(18, 9), dpi=150)
ax2 = ax1.twinx()
line1, = ax1.plot(merged['date'], merged['adj_close'], 'o-', color='#2196F3', linewidth=2.5, markersize=5, label='股价(前复权)')
line2, = ax2.plot(merged['date'], merged['non_gaap_ttm'], 's-', color='#FF5722', linewidth=2.5, markersize=5, label='扣非TTM(亿)')
ax1.legend(handles=[line1, line2], fontsize=12, loc='upper left')
# ...

# === 6) 统计 ===
corr = merged['adj_close'].corr(merged['non_gaap_ttm'])
price_mult = merged['adj_close'].iloc[-1] / merged['adj_close'].iloc[0]
ttm_mult = merged['non_gaap_ttm'].iloc[-1] / merged['non_gaap_ttm'].iloc[0]
```

## 港股TTM计算

港股要先判断披露频率，不能一概按A股季度，也不能一概按半年报：

### 普通港股：半年报 + 年报

多数港股没有单季度财报，只有半年报（H1累计）和年报（全年）。TTM计算方式：

- **年末TTM** = 年报利润（本身就是全年）
- **年中TTM（H1）** = 上年年报 + 本年H1 - 上年H1

泡泡玛特实例（统一使用股东应占溢利/归母口径，不能混入年度利润总额或全体股东利润）：
```
2024年报: 31.25亿 → TTM=31.25亿
2025H1:   45.74亿 → TTM=31.25+45.74-9.21=67.78亿
2025年报: 127.76亿 → TTM=127.76亿
```

注意：H1、全年和同比基期必须使用同一利润口径。若年度用“股东应占溢利”，上年H1也必须用股东应占溢利；误用集团期间利润会让TTM偏差。历史日频PE必须使用真实业绩公告日，默认从**公告后的下一个交易日**切换新利润；只有已核实公告在开市前发布时才可从公告日生效。统一近似日期时必须在图注说明。港股只有半年度数据点时，图表天然较稀疏；yfinance代码使用去掉前导零的 `{code}.HK`。报告定稿后应冻结行情/汇率快照，验证和重绘优先读取冻结数据，避免港股收市后汇率继续波动造成报告与图表轻微漂移。

### 披露季度业绩的港股：累计值转单季，再滚动4季

部分港股（如小米集团-W `1810.HK` / 东方财富 `01810.HK`）披露季度业绩。此时可用东方财富港股财务接口：

```python
import akshare as ak
# stock 用 5 位港股代码；yfinance 用去掉前导0的 {code}.HK
df = ak.stock_financial_hk_report_em(stock='01810', symbol='利润表', indicator='报告期')
profit = df[df['STD_ITEM_NAME'].eq('股东应占溢利')]
```

该接口的季度利润表通常仍是**年初至报告期累计值**：
- Q1 单季 = Q1累计
- Q2/Q3/Q4 单季 = 本期累计 - 上一期累计
- TTM = 最近4个单季利润滚动求和

港股/A股区别要在图上写清楚：
- 股价：`1810.HK`，单位港元；
- 利润：东方财富港股财报字段，常用“股东应占溢利”；
- 利润币种按公司财报/接口列报口径，不能默认和港元股价同币种；图中不要把两者直接相除；
- 东方财富港股代码常带前导0（如 `01810.HK`），yfinance 常用 `1810.HK`。

## 关键注意事项（含踩坑经验）

1. **同花顺Excel是单季度，东方财富API是累计**——两者不能直接混用
2. **yfinance代码格式**：深市=`{code}.SZ`，沪市=`{code}.SS`
3. **前复权（Adj Close）包含分红收益**，不复权（Close）不含
4. **归一化基期**：取第一个有效数据点，通常是上市后第一个有TTM的季度
5. **中文显示**：必须设置中文字体；在 macOS 上若图例/标题/注释仍出现方块字，不要只改 `rcParams['font.sans-serif']`，应使用 `matplotlib.font_manager` 显式加载字体文件，并把 `fontproperties` 传给标题、图例、说明框、脚注等文本对象。可优先尝试 `/System/Library/Fonts/Hiragino Sans GB.ttc`、`/System/Library/Fonts/STHeiti Medium.ttc`、`/System/Library/Fonts/Supplemental/Arial Unicode.ttf`。
6. **季度末对齐**：如果季度末非交易日，取<=该日的最后一个交易日
7. **读取同花顺XLS先识别频率和解析器能力**：优先用 `python-calamine`；回退到 `xlrd` 时先检查当前版本支持的函数参数。关键是按表头确认年度、H1累计还是单季度，而不是固定依赖某个兼容参数。
8. **归一化图不能用来判断估值高低**：归一化图被基期PE永久扭曲（基期PE低→后续Ratio永远>1→误判"一直高估"）。判断股价vs利润的趋势对比用双Y轴折线图。
9. **股价vs利润线看趋势一致性，不看绝对位置**：利润线在股价线下方但两者同步增长=OK。关键是斜率（增幅）是否匹配，不是谁在上谁在下。
10. **2021年蓝筹白马泡沫不要误判**：2020Q4-2021Q1 PE~25-30倍是高估期，不是"股价低于利润线的好时机"。要结合实际PE水平判断。；Excel中可能有`--`表示缺失值，读取时需跳过
8. **现金头寸必须用财报PDF校验**——东方财富API摘要接口可能遗漏定期存款、短期投资或负债明细。彼得林奇简化现金头寸按主框架统一为：现金及现金等价物 + 已核实定期存款 + 有价证券 - 长期有息债务。短期借款不扣；租赁负债不混入主口径，可另列“扣租赁负债后的保守净金融现金”。
9. **港股代码格式**：yfinance用`{code}.HK`，东方财富港股用`0{code}.HK`格式
10. **东方财富API利润表返回的是累计数据（报告期累计），不是单季度**——如果有同花顺Excel（单季度），优先用同花顺；没有的话需要手动转换：Q1累计=单季度，Q2/Q3/Q4单季度=本期累计-上期累计
11. **东方财富API列名经常报错**——首次查询务必用`columns=ALL`探查有效列名，再构造精确查询。详细踩坑见 `references/data-source-pitfalls.md`"东方财富API列名踩坑"章节
12. **产品结构分类口径年年变**——2023年按产品分（暖通空调/消费电器），2024年起按业务模式分（智能家居/工业解决方案），做跨年对比需注意映射
11. **现金头寸公式（彼得林奇）**：每股现金头寸 =（现金及现金等价物 + 已核实定期存款 + 有价证券 - 长期有息债务）/ 总股本。长期有息债务按年报逐项核实，主口径不扣短期借款，也不把租赁负债混入；租赁负债可另列保守敏感性口径。不得用“流通股数”代替总股本。
12. **杜邦分析要看趋势，不能只看当前值**——曾错误地将盐津铺子(002847)分类为"效率+杠杆混合型"（基于当前值：净利率13%、周转率1.4、权益乘数1.9），实际上趋势显示净利率从6.8%翻倍到13%是ROE提升的最大驱动力，同时权益乘数从2.38降到1.91（去杠杆）。正确结论：ROE从17%提升至35%，靠净利率翻倍驱动+杠杆下降，是最健康的杜邦模式。净利率在提升是最健康的信号；ROE提升如果主要靠加杠杆是风险信号。
9. **PE计算**：EPS(TTM) = 滚动4季度EPS之和，PE = 不复权股价 / EPS(TTM)。前复权PE用于收益分解分析。
10. **收益分解**：股价涨幅 = 利润增长 × PE变化，用对数归因算贡献比例（利润贡献% + PE贡献% = 100%）
11. **东方财富API利润表接口**：reportName=RPT_DMSK_FN_INCOME 或 RPT_F10_FINANCE_GINCOME，返回的PARENT_NETPROFIT和DEDUCT_PARENT_NETPROFIT都是累计值
12. **美的集团案例**：Q4利润系统性低于Q3（14/14年），原因是年末计提减值、费用集中确认、利润管理。这是A股普遍现象，不是个例。
13. **盐津铺子案例**：交叉验证发现东方财富API返回累计数据，同花顺Excel是单季度。Q1完全一致，Q2/Q3/Q4差异=累计-单季度。必须确认数据类型后再使用。
14. **泡泡玛特案例**：港股没有单季度财报，只有半年报和年报。TTM用"上年年报+本年H1-上年H1"估算。产品结构分析中LABUBU是绝对大单品（100亿+），不能遗漏最大的IP。
15. **产品结构分析是必填项**——曾因东方财富API港股经营分析接口不可用就跳过了产品结构分析，被用户指出。必须通过年报、研报、新闻等渠道获取数据，不能因数据获取困难而省略。
14. **PE百分位计算**：用东方财富估值API（RPT_VALUEANALYSIS_DET）获取历史PE(TTM)，然后计算当前PE在历史区间的百分位。API: `filter=(SECUCODE="{code}.{SZ|SS|HK}")`。
15. **PEG计算**：PEG = PE(TTM) / 扣非净利润3年CAGR。3年CAGR = (最新扣非TTM / 3年前扣非TTM)^(1/3) - 1。彼得林奇认为PEG 0.5-1为合理区间，<1可能低估，>2偏贵。注意：增速>30%时PEG参考价值下降。
16. **收益分解实例**：美的集团——股价涨10倍=EPS涨2.67倍×PE涨3.74倍，利润贡献43%，PE贡献57%。盐津铺子——股价涨3倍=利润涨12倍×PE压缩到1/4，说明买入时的PE决定了最终收益。

## 统计指标

输出CSV时包含：
- quarter, date, trade_date
- adj_close, close（前复权/不复权股价）
- net_profit_yi, non_gaap_yi（单季度，亿元）
- net_profit_ttm_yi, non_gaap_ttm_yi（TTM，亿元）
- eps, eps_ttm（每股收益）

## 输出文件命名

- CSV: `{code}/{code}_季度数据.csv`
- 图1: `{code}/{code}_归一化_股价vs扣非TTM.png`
- 图2: `{code}/{code}_股价vs扣非净利润TTM_双Y轴.png`
- 图3: `{code}/{code}_股价vs扣非净利润_单季度.png`

## 报告中嵌入图表

图表生成后，用相对路径嵌入到投资分析报告中：
```markdown
![归一化对比：股价 vs 扣非TTM利润](600660_归一化_股价vs扣非TTM.png)
```
报告和图表在同一目录下时用相对路径，Markdown编辑器可直接显示。

如果用户要求把图嵌入第四章这类基本面章节，默认排版是：图 → 表 → 简洁结论。
- 图用于快速判断趋势；
- 表用于保留原始数字，方便用户复核；
- 结论压成 1 句话 + 2~3 条要点即可。
除非用户明确要求删表，否则不要把原有数据表直接替换掉。

### 第四章 4.2「利润增长来源与持续性」的默认画法

当目标不是做“季度波动观察”，而是给第四章 4.2 这类基本面章节配图时，优先考虑**年度口径**，尤其是在图下已经有 2020-2025 年年度表格时。

先判断这一节要回答什么问题：

1. 如果重点是“利润修复后增速是否放缓”
- 默认优先画 `2020-2025 年扣非净利润柱状 + 扣非同比折线`；
- 这种画法比“单季度折线 + 同比柱状”更适合和年度表格配套，也更容易表达“利润修复后增速放缓”；
- 标题/副标题里直接点明主结论，例如：`2024-2025 年同比增速明显放缓，2026Q1 进一步降至 +7.69%`。

2. 如果重点是“利润增长来源与持续性”（更强调来源拆解）
- 优先画 `营收、扣非净利润双柱一组 + 毛利率、净利率双折线`；
- 这张图直接回答三件事：收入有没有扩张、利润有没有释放、利润率有没有持续改善；
- 图下若已有年度表格，这种画法通常比单独画同比更贴合“增长来源”这个小节标题；
- 报告文案也要同步切换，不再只写“增速放缓”，而要明确区分：`营收扩张是第一层来源，毛利率/净利率修复是第二层来源`。

3. 如果用户明确要求“既要来源拆解，也要保留扣非增长折线”
- 可以在上面的双柱+双折线基础上，**再加一条扣非同比折线**；
- 由于毛利率/净利率和扣非同比量纲都为百分比，但数值区间差异很大，通常需要**第三个右轴**承载扣非同比；
- 这类图信息密度很高，必须主动做减法：缩短说明文字、减少非必要标签、把低基数说明挪到注释区，避免 2022/2024 附近标注打架；
- 若画面过挤，优先保证“线都完整显示”而不是把每个点都写满标签。

低基数/负基数处理：
- 如果上一年利润为负或接近 0，导致同比出现极端值（如 -993% / +1000%），不要把该点当成主叙事；
- 做法优先级：`隐藏该同比点或不标数值` > `保留但加注“低基数参考意义有限”`；
- 当用户又要求保留同比折线时，至少要把 2021 这类异常点标成“参考意义有限/折线不展示”，不要让极端值压扁后续正常年份；
- 目标是让读者先看到修复后的正常斜率变化（如 +98.6% → +54.7% → +33.2% → +13.6%），而不是被异常基数噪音带偏。

版式偏好（本用户已验证）：
- 第四章默认遵循 `图 → 表 → 简洁结论`；
- 4.2 这类图里，若已经有营收/扣非双柱，就不要把“扣非同比折线”误删；用户会认为信息不完整；
- 图改结构后，报告 4.2 的一句话判断和 bullet 必须同步改口径，避免图在讲“来源拆解”，文字还在讲“单纯增速放缓”。

### 第四章 4.5「营运质量：应收/存货/合同负债」默认画法

当这一节目标是判断“渠道和库存是否在改善、最新季度有没有异常信号”，优先用**年度主图 + 最新季度补充观察**，不要只画最近 3-4 个点。

推荐结构：
- 主图：`2020-2025 年末应收账款 / 存货 / 合同负债` 分组柱状图；
- 小图：同期 `资产负债率` 折线；
- 右上角补充 `2026Q1` 最新观察值（应收、存货、合同负债、资产负债率），不要把 Q1 混进主序列破坏年度节奏。

表达重点：
- 主标题直接下结论，例如：`存货持续去化，2026Q1 应收抬头需观察`；
- 图下表格默认补 `2020-2025` 年度数据，方便复核；
- 正文 bullet 要区分“长期趋势改善”和“最新季度观察信号”，不要把 Q1 的单点变化直接写成全年恶化结论。

细节规则：
- 如果合同负债极小，柱子视觉上会很弱，这是量级问题，不要为了“看得见”强行改轴导致失真；
- 年度主图和正文口径必须一致；如果图改成 2020-2025 年度口径，4.5 文案也要改成“先看长期去化，再补最新季度观察”；
- 有年度图时，表格里 2020-2025 的合同负债可保留 `- / 0.00 / 0.01` 这类真实量级，不要擅自并表或放大。

### 第四章 4.6「产品结构与增长来源」默认画法

这一节最容易把“结构”和“增长来源”揉在一张图里，结果两边都不够清楚。对本用户，默认应拆成**主图看占比 + 小图看增速**。

推荐结构：
- 主图：`2025 年各产品收入占比` 横条图，条末只标 `收入 + 占比`；
- 小图：各产品 `同比增速` 点线图/横向 lollipop 图，单独表达“谁贡献弹性”；
- 标题直接结论化，例如：`阿胶主品占比 92.5%，第二曲线增速快但体量仍小`。

表达重点：
- 主品条形可用低饱和主色；
- “第二曲线”（如其他药品及保健品）用强调色高亮；
- 尾部业务统一弱化，避免抢戏；
- 如果主品占比 >90%，不要再用收入绝对值主图硬压其他小类，否则小类几乎贴轴，既看不清结构，也看不清增长来源。

正文联动：
- 一句话判断要写成：`增长仍高度依赖主品，第二曲线有进展但短期不足以改写结构`；
- bullet 里明确区分“基本盘贡献者”和“弹性来源”；
- 若用户要求更简洁，优先删信息框/冗长标签，不要把小图删掉。

⚠️ 图表中的股价数据来自yfinance，是前复权收盘价。报告抬头的股价/市值需要用东方财富估值API单独查询最新数据（非前复权），不能直接用图表中的数据。

## 参考资料

- `references/data-source-pitfalls.md` — 数据源踩坑记录：东方财富API vs 同花顺差异、其他流动资产辨析（汾酒/美的/福耀实例）、FINANCE_RECE字段含义、分红API字段单位
- `investment-analysis-framework/references/fundamental-charts.md` — 第四章“好公司·定量”少图表达模板；当用户不仅要“好时机”图，还要 ROE/现金流/营运/产品结构图时参考这里
- `references/investment-analysis-framework.md` — 好行业/好公司/好时机打分框架（100分制）
- `references/stock-code-mapping.md` — A股/港股代码映射表（yfinance、东方财富API格式）

- `references/investment-analysis-framework.md` — 好行业/好公司/好时机打分框架（100分制）
- `references/stock-code-mapping.md` — A股/港股代码映射表（yfinance、东方财富API格式）

## 关联 Skill

- `investment-analysis-framework` — 完整投资分析框架，本 skill 是其中"好时机"分析的图表生成工具。当用户要求完整投资分析时，应加载该 skill。
