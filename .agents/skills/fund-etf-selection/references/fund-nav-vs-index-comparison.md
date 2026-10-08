# Fund NAV vs Index TR Comparison (Phase 2)

## Overview

Phase 2 workflow: compare real ETF/fund NAV returns against the corresponding index total-return (TR) series, rank by a 4-dimension score (40/30/15/15), benchmark against a reference fund (e.g. 华泰柏瑞红利低波ETF 512890), and generate tracking deviation + benchmark comparison charts.

## Workflow

### 1. Hard filter

- Fund must have ≥2 years of live NAV data (≈480 trading days) to enter the main ranking pool.
- Funds <2 years go to an observation pool (tracking error only, no ranking).
- Minimum AUM: ETF ≥2亿, OTC index fund ≥5亿.

### 2. NAV data collection

All fund NAV data comes from the Eastmoney fund API: `https://api.fund.eastmoney.com/f10/lsjz`

```python
params = {
    "fundCode": fund_code,
    "pageIndex": 1,
    "pageSize": 200,
    "startDate": "",
    "endDate": "",
}
headers = {"Referer": "https://fundf10.eastmoney.com/", "User-Agent": "Mozilla/5.0"}
```

Response JSON: `Data.LSJZList` array, each item has:
- `FSRQ`: date string "YYYY-MM-DD"
- `DWJZ`: unit NAV (单位净值)
- `LJJZ`: accumulated NAV (累计净值)
- `FHSP`: fund share event description (分红/分拆描述)
- `JZZZL`: daily change %

**CRITICAL — Pagination:** Despite `pageSize=200`, the API returns only 20 records per page. TotalCount may report 1108 but each page returns 20, requiring ~56 pages. Always loop through all pages.

### 3. NAV口径 — CRITICAL: 不用K线前复权，用净值接口+手工复权

**这步是跟踪误差计算中最容易出错的地方，直接影响计算结果。**

跟踪误差的比较对象是**全收益指数（TR）**，它假设每次分红都按指数价格再投。因此基金侧的净值也必须用**"分红再投"口径**，才能与全收益指数严格可比。

三种口径的差异：

| 口径 | 数据来源 | 分红处理方式 | 是否等价于全收益指数 | 适用场景 |
|---|---|---|---|---|
| **手工分红再投净值** | 单位净值(DWJZ) + 现金分红记录(FHSP) | 每次除权日：`wealth *= (nav * split_ratio + div) / prev_nav` | ✅ 是 | 所有ETF/基金，最准确 |
| **前复权交易价** | 东方财富K线接口(fqt=1) | 按除权比例调整历史价格 | ⚠️ 无现金分红的ETF可用；有现金分红的ETF不准 | 仅做快速参考 |
| **累计净值(LJJZ)** | 东方财富基金净值接口 | 简单相加：LJJZ = DWJZ + 累计分红金额 | ❌ 不是（低估真实分红再投收益） | 仅有分拆/份额变动，无现金分红的ETF |

**为什么累计净值(LJJZ)不等价于分红再投？**

累计净值只是把每份的历史分红金额简单加起来，不是"分红再投"的复利计算。以515300（嘉实300红利低波）为例，近5年：
- 累计净值收益：55.49%
- 手工分红再投净值（正确）：~52.70%
- **前复权交易价（东方财富K线接口，fqt=1）：72.55%（错误，偏高约20个百分点）**

**⚠️ 关键发现：东方财富K线接口的前复权交易价，对有现金分红的ETF，数据不准。**

验证：515300有7次现金分红，东方财富K线前复权（fqt=1）返回的近5年收益是72.55%，而正确的手工分红再投净值是52.70%，雪球前复权也是52.17%。差距20个百分点。原因可能是东方财富K线接口的前复权算法将分红处理方式与全收益指数不一致。

**因此，做跟踪误差分析和收益对比，必须用基金净值接口（api.fund.eastmoney.com/f10/lsjz）拿单位净值+分红事件，自己复算分红再投净值，不能用K线接口的前复权交易价。**

**正确的做法：**

```python
import re
DIVIDEND_RE = re.compile(r'每10份派现金([0-9.]+)元')
SPLIT_RE = re.compile(r'每(\d+)份分拆([0-9.]+)份|每份基金份额分拆([0-9.]+)份')

def parse_dividend_and_split(fhsp):
    """返回 (每份现金分红, 每份拆分后的新份额数)"""
    if not fhsp:
        return 0.0, 1.0
    div = 0.0
    m = DIVIDEND_RE.search(fhsp)
    if m:
        div = float(m.group(1)) / 10
    split_ratio = 1.0
    m2 = SPLIT_RE.search(fhsp)
    if m2:
        if m2.group(3):  # 每份基金份额分拆X份
            split_ratio = float(m2.group(3))
        elif m2.group(1) and m2.group(2):  # 每N份分拆M份
            split_ratio = float(m2.group(2)) / float(m2.group(1))
    return div, split_ratio

def reconstruct_reinvested_nav(rows):
    """从单位净值+现金分红+分拆，复算分红再投净值（全收益口径）。"""
    obs = []
    for r in rows:
        if not r.get('DWJZ'):
            continue
        div, split = parse_dividend_and_split(r.get('FHSP') or '')
        obs.append((datetime.strptime(r['FSRQ'], '%Y-%m-%d').date(), float(r['DWJZ']), div, split))
    obs.sort()
    if not obs:
        return {}
    
    adjusted = {obs[0][0]: obs[0][1]}
    wealth = obs[0][1]
    prev_nav = obs[0][1]
    for day, nav, div, split in obs[1:]:
        # 分拆处理：每1份拆成N份，净值除以N，但总资产不变
        # 当天的等效价值 = 净值 × 分拆比例 + 现金分红
        wealth *= (nav * split + div) / prev_nav
        adjusted[day] = wealth
        prev_nav = nav
    return adjusted
```

**分拆处理的解释：** 分拆（如1拆2）使单位净值从1.6降到0.8，但份额翻倍，总资产不变。如果公式只用 `(nav + div) / prev_nav`，分拆日会算出 `0.8/1.6 = 0.5`，相当于-50%亏损，这是错误的。正确做法是 `(nav * split_ratio + div) / prev_nav`，此时 `(0.8 * 2 + 0) / 1.6 = 1.0`，当天收益率为0%，正确。

**什么时候可以用累计净值(LJJZ)？**

只有确认该ETF**没有现金分红记录**（`FHSP`字段中没有"派现金"）时，累计净值=手工复权净值，因为单位净值的变化只来自分拆/份额变动，而累计净值已经正确处理了。例如512890（华泰柏瑞红利低波ETF）只有1次分拆，无现金分红，累计净值≈手工复权净值。

### 4. 分组和统一评价区间 — CRITICAL

**不要用"共同区间交集"（各基金的最晚起点~最早终点），改用固定时间段。**

原因：如果用共同区间，最晚成立的基金决定了整个组的起点，老基金的历史被截短了，破坏了"5年评价"的初衷。

**正确做法：固定区间，数据不够就跳过。**

| 组别 | 固定区间 | 需要数据 | 跳过条件 |
|---|---|---|---|
| 5年组 | 2021-08-02 ~ 2026-08-10 | 至少100天 | 不够100天的不参与排名 |
| 2年组 | 2024-08-10 ~ 2026-08-10 | 至少100天 | 不够100天的不参与排名 |

```python
# 固定区间，不依赖共同交集
FIVE_YEAR_START = pd.Timestamp("2021-08-02")
FIVE_YEAR_END = pd.Timestamp("2026-08-10")
TWO_YEAR_START = pd.Timestamp("2024-08-10")
TWO_YEAR_END = pd.Timestamp("2026-08-10")

if group == "5年组":
    start, end = FIVE_YEAR_START, FIVE_YEAR_END
else:
    start, end = TWO_YEAR_START, TWO_YEAR_END

nav_clip = nav.loc[start:end]
if len(nav_clip) < 100:
    skip  # 数据不足，不参与排名
```

### 5. 4-dimension scoring

Same weight as index phase 1:
- Return 40%: CAGR
- Risk 30%: max drawdown
- Efficiency 15%: CAGR / monthly volatility
- Stability 15%: annual win rate (50%) + rolling 3-year median (50%)

**2年组不参与稳定性评分**（数据不足以支持有意义的年度胜率和滚动3年中位数），改用三维度：收益50%、风险30%、效率20%。

Relative ranking: `rank(pct=True) * 100` per indicator, then weighted sum.

### 6. Benchmark comparison

Use 华泰柏瑞红利低波ETF (512890) as the reference benchmark. Compare each fund's total score against the benchmark:
- ≥ benchmark + 3: Tier 1 (significantly better)
- ≥ benchmark - 3: Tier 2 (comparable)
- < benchmark - 3: Tier 3 (lags behind)

### 7. Tracking deviation calculation

Compare fund NAV (correctly reconstructed dividend-reinvested) against the matching index TR series over the same dates.

```python
# 日收益差
fund_return = fund_nav[t] / fund_nav[t-1] - 1
index_return = idx[t] / idx[t-1] - 1
diff = fund_return - index_return

# 年化跟踪误差（日收益差的标准差 × √252）
annualized_te = std(diff) * sqrt(252)

# 注意：这个值≠每年差4.86%。它衡量的是日收益差的波动幅度。
# 逐年看可能逐年递减（如515300：2021年6.96%→2025年2.19%），
# 所以"年化跟踪误差"是区间平均，不是每年都差这么多。

# 平均年化超额（与跟踪误差含义不同）
annual_excess = mean(diff) * 252  # 基金平均每年跑赢/跑输指数多少

# 累计偏离（用于图表）
fund_norm = fund_nav / fund_nav[0] * 100
idx_norm = idx / idx[0] * 100
cumulative_deviation = fund_norm - idx_norm
```

- Pure passive ETFs should have tracking error < 1% annualized.
- With dividend reinvestment time lag, 1-2% is acceptable.
- >3% suggests structural tracking issues (e.g., cash drag, sampling error, or incorrect NAV口径).
- Positive tracking deviation can come from IPO subscription lotteries (打新), which is real alpha, not a flaw.

### 8. Charts — 参考 generate_512890_article_charts.py 样式

使用 `scripts/chart/generate_512890_article_charts.py` 中 `plot_tracking_difference()` 函数的双子图样式：

**跟踪偏离度图（上下子图）：**
- 上子图：两条线——基金分红再投净值 vs 全收益指数，同日起点归一化为100
- 下子图：累计收益差（百分点），填色区域，正值表示ETF领先
- 右上角标注终点数值（"ETF XX.X"和"全收益指数 XX.X"）
- 下子图右上角标注"上市以来 +XX.X个百分点"
- 可选：添加"近5年起点"垂直虚线
- 标题：`ETF复权净值与全收益指数`
- 副标题：`同日起点归一为100 | 基金累计净值对比税前全收益指数 | 下图正值表示ETF领先`
- 白底，简约风格，去掉顶部和右边框

**对比基准图：**
- 使用 `generate_512890_article_charts.py` 中的方法，不再单独画简单折线图

**组内总图：**
- 所有基金归一化=100，按累计收益从低到高依次绘制
- 基准用灰色虚线，其他用不同颜色实线
- 图例左上角，显示名称+累计收益
- 白底，图高7.5英寸

## Pitfalls

- **LJJZ is NOT dividend-reinvested**: For ETFs with cash dividends, LJJZ underestimates true dividend-reinvested returns. Always reconstruct from DWJZ + FHSP.
- **东方财富K线前复权（fqt=1）对有现金分红的ETF不准**：验证发现515300偏差20个百分点。只能用净值接口。
- **分拆事件必须用 `(nav * split_ratio + div) / prev_nav` 公式**：否则分拆日会被算成-50%亏损。
- **Different fund ages**: Use fixed periods, not common intersection of all funds' start dates. Skip funds that don't have enough data for the period.
- **Eastmoney pagination**: OTC fund API returns only 20 records per page despite pageSize=200. Loop through all pages.
- **BOM in CSV files**: Eastmoney responses may have UTF-8 BOM. Use `encoding='utf-8-sig'` when reading.
- **Fund name cleanup**: strip suffixes like "交易型开放式指数证券投资基金" to "ETF", "指数型证券投资基金" to empty.
- **NAV vs index TR**: always use reconstructed dividend-reinvested NAV for the fund side. Index side must be TR (全收益), not price index.
- **Capital gains from IPO subscriptions**: Chinese ETFs can earn extra returns from IPO lotteries (打新), which creates a positive tracking deviation that is not a tracking error. This is real alpha, not a flaw.
- **图表和数据必须用同一区间**: 确保calculate_metrics和图表使用相同的start_date/end_date，否则图表中的累计收益和表格中的CAGR不匹配（之前bug：图表用共同区间，指标用固定区间，导致CAGR和累计收益排序相反）。

## Observation pool (观察池) handling

Funds with < 3 years live history (≈720 trading days) do not participate in ranking but should still be listed and optionally given benchmark comparison charts.

### Table format

List by inception date (oldest first). Columns: fund name, code, trading days, CAGR, max drawdown, annualized tracking error, AUM. No score or tier columns.

### Marking key observation candidates

When the user asks "which in the observation pool are worth watching" or "we're missing category X," evaluate on two layers:

1. **Index quality (not just short-term fund performance):** Look up the tracked index's long-term metrics (CAGR, max drawdown, return/vol, rolling 3Y positive rate). Critically, compare the **pre/post-publication return gap** (`pre_post_gap` in 全部指标.json):
   - Gap near 0 or slightly negative (e.g., -1.15pp): backtest is consistent with live performance, no overfitting signal.
   - Large positive gap (e.g., +11.89pp): backtest significantly outperforms post-publication live history, suggesting index construction may be overfit to past data. This is a red flag even if the backtest looks excellent.
   - When two funds share a category label (e.g., both "红利质量") but track different indices, compare this metric to identify which index is more trustworthy. Do NOT assume same category = same index.

2. **Fund wrapper:** AUM and liquidity relative to same-index peers; tracking error over the fund's short life.

Add a `> ★ 重点观察` callout above the table explaining the rationale, and bold the highlighted row.

### Chart generation for observation pool

For benchmark comparison charts of observation pool funds, use the **fund's own inception date** as the chart start (not the group's fixed period). The chart still compares three series: fund reinvested NAV, benchmark 512890, and tracked index TR, all normalized to 100 from the first common trading day.

In the chart script, add an `"obs"` group with `GROUP_START = None` and use `fund_nav.index[0]` as the start:

```python
GROUP_START = {"5y": ..., "3y": ..., "obs": None}

if group == "obs":
    common = common[common >= fund_nav.index[0]].sort_values()
else:
    common = common[common >= GROUP_START[group]].sort_values()
```

In the report, place observation pool charts after the ranked groups, with a note that the fund has < 3 years live history and the chart is for reference only (not scoring).