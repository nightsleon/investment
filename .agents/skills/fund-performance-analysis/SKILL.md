---
name: fund-performance-analysis
description: Use when computing fund returns via reinvested NAV.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [investment, fund, ETF, performance, nav, tracking-error]
    related_skills: [dividend-index-analysis, index-performance-backtest]
---

# 基金/ETF全收益分析方法

## Overview

基金/ETF的长期收益分析必须使用正确的净值口径。**不推荐直接使用行情软件的前复权交易价格**，原因：

1. **交易价 ≠ 基金净值**：ETF交易价格包含折溢价，短期波动引入噪音，放大跟踪误差计算
2. **不同平台前复权算法不一致**：同一基金同一区间，不同平台可能差十几个百分点（实测515300近5年：雪球52% vs 东方财富72%）
3. **累计净值（LJJZ）不是复利口径**：累计净值 = 单位净值 + 历史累计分红金额，是简单相加，低估分红再投的复利收益

正确做法：**用东方财富基金净值接口获取单位净值（DWJZ）+ 分红事件（FHSP），手工复算分红再投净值**。

## When to Use

适用于：

- 计算基金/ETF的长期累计收益和CAGR
- 计算基金相对跟踪指数的跟踪误差
- 多只基金收益横向对比
- 基金与全收益指数对比分析
- 生成基金归一化走势对比图

不适用于：指数全收益直接计算（指数有独立数据源）、当天实时估值。

## 数据接口

### 东方财富基金净值接口

```
URL: https://api.fund.eastmoney.com/f10/lsjz
Params: fundCode={CODE}&pageIndex=1&pageSize=200&startDate=&endDate=
Headers: Referer: https://fundf10.eastmoney.com/
         User-Agent: Mozilla/5.0
```

返回字段（JSON格式，`Data.LSJZList`数组）：

| 字段 | 含义 | 说明 |
|------|------|------|
| FSRQ | 日期 | 格式 YYYY-MM-DD |
| DWJZ | 单位净值 | 基金当天实际净值，现金分红除权后下跌 |
| LJJZ | 累计净值 | 单位净值 + 历史累计分红金额，简单相加非复利 |
| FHSP | 分红拆分说明 | 如"每10份派现金0.6610元"或"每份基金份额分拆2.0份" |

### 翻页采集

首次请求返回 `TotalCount` 和 `PageSize`，计算总页数 `math.ceil(total / page_size)`，逐页采集后合并。单次请求约200条。

## 核心公式

### 分红再投净值（全收益口径）

```
wealth[t] = wealth[t-1] × (unit_nav[t] × split_ratio + dividend[t]) / unit_nav[t-1]
```

初始值：`wealth[0] = unit_nav[0]`

其中：
- `unit_nav[t]`：第t天的单位净值（DWJZ）
- `dividend[t]`：第t天的每份现金分红（如有，否则0）
- `split_ratio`：第t天的拆分比例（每1份拆成N份，如分拆则>1，否则1.0）

### 分红金额解析

```python
DIVIDEND_RE = re.compile(r"每10份派现金([0-9.]+)元")
def parse_dividend(fhsp):
    m = DIVIDEND_RE.search(fhsp or "")
    return float(m.group(1)) / 10 if m else 0.0
```

### 分拆处理

```python
SPLIT_RE = re.compile(r"每(\d+)份分拆([0-9.]+)份|每份基金份额分拆([0-9.]+)份")
def parse_split(fhsp):
    m = SPLIT_RE.search(fhsp or "")
    if not m: return 1.0
    if m.group(3): return float(m.group(3))
    return float(m.group(2)) / float(m.group(1))
```

### 完整复算函数

```python
def build_reinvested_nav(rows):
    obs = []
    for r in rows:
        if not r.get("DWJZ"): continue
        d = datetime.strptime(r["FSRQ"], "%Y-%m-%d").date()
        nav = float(r["DWJZ"])
        div = parse_dividend(r.get("FHSP") or "")
        split = parse_split(r.get("FHSP") or "")
        obs.append((d, nav, div, split))
    obs.sort()
    reinvested = {obs[0][0]: obs[0][1]}
    wealth = obs[0][1]
    prev_nav = obs[0][1]
    for day, nav, div, split in obs[1:]:
        wealth *= (nav * split + div) / prev_nav
        reinvested[day] = wealth
        prev_nav = nav
    return reinvested
```

## 计算示例

| 日期 | 单位净值 | 分红（元/份） | 财富指数 | 说明 |
|------|----------|--------------|----------|------|
| 8月1日 | 1.000 | - | 1.000 | 初始值 |
| 8月2日 | 1.050 | - | 1.050 | 净值上涨5% |
| 8月3日 | 1.000 | 0.050 | 1.050 | 分红除权日，净值下降但分红加回后财富不变 |
| 8月4日 | 1.020 | - | 1.071 | 净值上涨2% |
| 8月5日 | 1.050 | - | 1.102 | 继续上涨 |

## 比较基准

### 基准选择

以华泰柏瑞红利低波ETF（512890）为基准：规模最大红利类ETF（324亿），只有分拆无现金分红，成立时间早（2018年）。

### 组别排名

不同历史长度的基金不可混比，应分组：

| 组别 | 条件 | 评分维度 | 权重 |
|------|------|----------|------|
| 5年组 | ≥1200个交易日 | 收益/风险/效率/稳定性 | 40/30/15/15 |
| 2年组 | 480-1200个交易日 | 收益/风险/效率 | 50/30/20 |
| 观察池 | <480个交易日 | 仅参考，不排名 | - |

### 共同区间

组内所有基金（含基准）统一截取共同日期区间。**指标计算和图表展示必须使用同一个共同区间**，否则会出现CAGR和累计收益排序矛盾的问题。

## 跟踪误差

年化跟踪误差 = 日超额收益标准差 × √252

```
日超额收益 = fund_return[t] - index_return[t]
fund_return[t] = reinvested_nav[t] / reinvested_nav[t-1] - 1
index_return[t] = index_nav[t] / index_nav[t-1] - 1
```

纯被动ETF年化跟踪误差通常应小于1%，大于2%说明跟踪质量较差。基金有打新等增强收益时，可能长期跑赢全收益指数。

### 跑赢基准 ≠ 跑赢跟踪指数（解读陷阱）

组内排名/走势图显示"多数基金跑赢基准基金"时，必须区分两件事：

- **跑赢基准基金**：相对组内选定的那只基准（如512890）收益更高，反映的是不同跟踪**指数之间的风格差异**。
- **跑赢跟踪指数**：相对基金自己跟踪的全收益指数有正超额收益（看累计超额收益/跟踪差），才反映基金管理能力。

实测3年组：6只里5只跑赢基准512890，但5只相对自己跟踪指数是负超额（-17%、-21%等），仅1只正超额。所以"多数跑赢"主要是某段行情里港股高息/央企等风格占优，不是基金选股能力强。写小结时先点明这个区别，再分基金解释风格来源，并提醒短期跑赢不能外推为长期更优。

### 港股/QDII ETF 复权口径校验

港股/QDII ETF 无法走东方财富 `lsjz` 接口时，常用 Yahoo 前复权价代替，
但**不同平台对 ETF "复权"是否含分红并不一致**：实测雪球对 03070.HK 的
"后复权"漏算分红（价格涨幅 72%，全收益应为 144%）。必须用 Yahoo chart API
取**未复权收盘价 + 分红事件**手工复算 `wealth[t] = wealth[t-1]*(close[t]+div[t])/close[t-1]`
交叉验证，与平台复权价差异应 <1%；除息日价格跳变应与派息额吻合以确认派息真实。
详见 `references/hk-etf-adjusted-price-validation.md`。

## Workflow

1. 采集数据 → 调用东方财富基金净值接口，获取全部历史数据
2. 复算分红再投净值 → 解析分红和分拆事件，按公式递推
3. 验证 → 与雪球等平台交叉验证（差异应<1%）
4. 分割共同区间 → 组内所有基金取最大共同起止日
5. 评分与排名 → 5年组四维度，2年组三维度，相对排名制
6. 生成追踪误差 → 加载指数全收益，对齐日期，计算日收益差
7. 生成对比图 → 组内总图 + 每只基金单独图
   - 组内总图线多时，改为每大类型1只代表+基准的精简图
   - 单基金图推荐上下两栏合并图：上图=基金+基准+跟踪指数全收益三条归一化线，下图=基金相对跟踪指数的累计收益差，替代分开的两张图；指数数据截止晚于基金净值、累计差窗口均需脚注说明（见 references/common-interval-bug.md）

## Hard Rules

- 不要用前复权交易价格代替正确净值口径
- 不要用累计净值（LJJZ）的增长率代替分红再投收益率
- 分拆事件必须处理（`nav × split_ratio + dividend`）
- 指标计算和图表展示必须使用同一个共同区间
- 重做"分类代表"子集图时，起始日必须钉住已发布表格的共同起始日，不能用子集自然交集，否则图上收益与表格列对不上（见 references/common-interval-bug.md）
- 多基金总图线过多时，改为每大类型选1只最优代表+基准的精简图；全量披露交给排名表和附录的单基金vs基准图（见 references/common-interval-bug.md）
- 不同历史长度的基金不能混比，必须按组别排名
- 跟踪误差必须用分红再投净值口径

## Verification Checklist

- [ ] 净值数据来自 `api.fund.eastmoney.com/f10/lsjz`
- [ ] 已正确解析现金分红和分拆事件
- [ ] 分红再投净值与雪球等平台差异<1%
- [ ] 分拆事件已处理
- [ ] 组内所有基金使用同一个共同区间
- [ ] 指标计算和图表展示区间一致
- [ ] 5年组/2年组/观察池分组正确
- [ ] 基准参与了评分
- [ ] 跟踪误差使用分红再投净值口径