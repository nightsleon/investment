---
name: stock-earnings-line
description: "为 3R 投资分析中“好价格（Right Price）”提供彼得·林奇收益线分析：测算季度/TTM 净利润与前复权股价的匹配度，生成双 Y 轴及归一化趋势图，判断当前股价相对利润位置的高估/低估状态。"
version: 2.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [investment, stock, finance, chart, TTM, visualization, right-price]
    category: data-science
    related_skills: [stock-investment-analysis, stock-financial-charts, stock-financial-speedread]
---

# 个股彼得·林奇收益线分析（股价 vs 利润趋势）

基于彼得·林奇的“收益线（Earnings Line）”方法，对比 A 股 / 港股上市公司季度股价走势与利润趋势，作为 3R 投资分析中「好价格（Right Price）」维度验证股价与业绩匹配度的量化依据。

## 核心用途

1. **检验股价是否跟随业绩增长**：长期来看股价涨幅是否由扣非净利润/经营积累驱动；
2. **评估估值相对位置（高估/低估）**：通过双 Y 轴折线观察当前股价相对利润中枢是处于透支阶段还是超跌阶段；
3. **识别季节性波动**：观察单季度业绩节奏（如 Q4 减值与集中确认）。

## 数据源与提取策略

### 1. 财务数据（两级策略）
- **优先：同花顺单季度 Excel（`data/{code}_main_simple.xls`）**
  - 同花顺导出直接为单季度数据，精度高于东财 API；
  - 优先用 `python_calamine.CalamineWorkbook` 解析；按行名匹配“扣非净利润(元)”“净利润(元)”“营业总收入(元)”。
- **备选：东方财富 API**
  - 接口：`RPT_DMSK_FN_INCOME`，返回为**报告期累计数据**；
  - 必须转换为单季度：$Q1 = 累计$；$Q2/Q3/Q4 = 本期累计 - 上期累计$；
  - 列名探查先用 `columns=ALL`，避免字段失效。

### 2. 股价数据
- **Yahoo Finance（`yfinance`）**：采用前复权收盘价（`Adj Close`，包含分红再投资）；
- 标的代码：深市 `{code}.SZ`，沪市 `{code}.SS`，港股 `{code}.HK`。
- **交易日对齐**：季度报告期（如 3/31、6/30、9/30、12/31）非交易日时，取 $\le$ 该日期的最后一个交易日收盘价。

### 3. TTM 与港股特别口径
- **A 股 TTM**：滚动最近 4 个单季度扣非净利润求和（`rolling(4).sum()`）；
- **港股非季度披露（半年报+年报）**：
  - 年末 TTM = 全年年报利润；
  - 年中 TTM（H1）= 上年年报 + 本年 H1 - 上年 H1；
  - 统一使用“股东应占溢利/经调整净利润”口径，杜绝混用期间总溢利；
  - 估值跳变日以**业绩公告实际披露日（PIT）**为准。

## 标准输出图表（3 张）

| 图表 | 文件名命名 | 形式与规范 | 核心作用 |
|---|---|---|---|
| **图 1（主图）** | `{code}_股价vs扣非净利润TTM_双Y轴.png` | **双 Y 轴双折线图**（不用柱状图）：左轴股价（元），右轴扣非 TTM（亿元，浅色填充）。 | **核心判断图**。直观对比股价与业绩斜率，判断背离或共振。 |
| **图 2（辅助）** | `{code}_归一化_股价vs扣非TTM.png` | **双折线**：首期有效正利润点 = 100。 | 验证长期复合走势同步性。（⚠️ 勿直接用于判断高估低估） |
| **图 3（季节）** | `{code}_股价vs扣非净利润_单季度.png` | **双 Y 轴折线**：左轴股价，右轴单季扣非净利润。 | 观察淡旺季与年末集中计提特征。 |

> **归一化图警示**：归一化起点受基期 PE 永久锁定，若基期 PE 极低会导致后续 Ratio 长期 >1。因此**估值高低务必看双 Y 轴图与历史 PE 分位数，归一化图仅看走势一致性**。若首期 TTM $\le 0$，必须从第一个正利润点开始归一化。

## 执行命令

脚本内置于 Skill 目录中，支持参数传入直接运行：

```bash
# 复制脚本到公司分析目录
cp .agents/skills/stock-earnings-line/scripts/generate_charts.py stocks/{code}/scripts/generate_charts.py

# A 股运行（代码 市场 公司名）
python3 stocks/{code}/scripts/generate_charts.py 600660 SH 福耀玻璃
python3 stocks/{code}/scripts/generate_charts.py 300750 SZ 宁德时代

# 港股运行（代码 公司名 [可选参数]）
python3 .agents/skills/stock-earnings-line/scripts/generate_charts_hk.py 09633 农夫山泉 --latest-h1 88.87 --latest-price 39.38
```

## 核心注意事项

1. **字体与排版**：macOS 优先加载系统中文字体（如 `PingFang SC`, `Hiragino Sans GB`），防止中文方块字。
2. **前复权 vs 最新市价**：收益线历史图采用前复权收盘价；报告抬头的最新实时价格和市值需用东方财富官方估值接口（不复权真实市价）展示。
3. **收益分解逻辑**：股价涨幅 = 利润增幅 $\times$ PE 变化倍数。通过对数归因计算利润贡献与估值驱动比例。
4. **与 3R 报告联动**：生成后作为 3R 报告中「好价格」首图，正文紧跟“走势同步性、PE 分位与历史位置、赔率与情景推演”。

## 关联 Skill

- **`stock-investment-analysis`**：个股 3R 投资分析主入口，好价格章节调用本技能图表与收益分解。
- **`stock-financial-charts`**：负责好生意（Right Business）章节的 6 张基本面定量图表（ROE/杜邦、产品结构、现金流等）。
- **`stock-financial-speedread`**：单期财报速览文章共用此处的“股价 vs 利润 TTM”出图逻辑。
