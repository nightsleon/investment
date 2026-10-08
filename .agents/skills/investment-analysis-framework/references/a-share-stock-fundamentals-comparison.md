# Stock-Fundamentals Comparison: Analytical Frameworks

## Peter Lynch's Price-vs-Earnings Method

From "One Up on Wall Street":
> 判断股票价格是不是被高估的快捷方法就是比较股票价格走势线与收益线是否相符。

Key concepts:
- **收益线 (Earnings Line)**: EPS or net profit absolute value trend over time
- **Price Line**: Stock price trend over time
- For quality growth companies, these two should track closely over the long term
- Buy when price line is below earnings line; sell when price line is far above

**Important:** Lynch uses EPS/profit **level**, not growth rate. The growth rate comparison (同比增长率) is a different analysis — useful for momentum, not for valuation.

## Which Metric to Use When

| Metric | Best For | Pitfall |
|---|---|---|
| Quarterly profit (absolute) | Short-term check | Seasonal sawtooth (Q4 often negative) |
| TTM (trailing 12mo) | **Lynch-style trend comparison** | Requires 4+ quarters of data |
| YoY growth rate | Momentum, acceleration | Can mislead — high growth rate with small base |
| Annual-only (Q4 cumulative) | Quick year-over-year view | Only 1 data point/year, loses granularity |
| EPS | Per-share comparison | Needs shares outstanding data |

## TTM Calculation Detail

TTM at any quarter = sum of most recent 4 quarters of net profit.

- 2026Q1 TTM = 2025Q2 + 2025Q3 + 2025Q4 + 2026Q1
- 2026Q2 TTM = 2025Q3 + 2025Q4 + 2026Q1 + 2026Q2
- 2026Q3 TTM = 2025Q4 + 2026Q1 + 2026Q2 + 2026Q3
- 2026Q4 TTM = 2026Q1 + 2026Q2 + 2026Q3 + 2026Q4 = full year profit

Q4 TTM equals annual total, making it the natural comparison point for year-end analysis.

## Chinese Financial XLS Data Structure

Typical layout from 东方财富/同花顺:

```
Row 0: empty
Row 1: 科目\时间 | 2026-03-31 | 2025-12-31 | 2025-09-30 | 2025-06-30 | ...
Row 2: 净利润(元) | val | val | val | val | ...
Row 3: 净利润同比增长率 | val | val | val | val | ...
Row 4: 扣非净利润(元) | val | val | val | val | ...
Row 5: 扣非净利润同比增长率 | val | val | val | val | ...
...
```

- Dates are in **descending** order (newest first)
- 12月31日 values may be cumulative annual OR single-quarter depending on data source — always verify (see `references/q4-seasonality.md`)
- If Q3 cumulative > Q4 cumulative, Q4 was a loss (year-end write-offs, impairments)
- 扣非净利润 = non-GAAP net profit (excluding non-recurring items) — often better for trend analysis

## Case Study: Midea Group (000333)

Period: 2013Q3 — 2026Q1 (12.5 years)

| Method | Price Growth | Profit Growth | Correlation | Notes |
|---|---|---|---|---|
| YoY growth rate | 10.0x | N/A (rate, not level) | -0.39 | Weak negative — misleading |
| Quarterly profit (absolute) | 10.0x | 9.2x | 0.77 | Sawtooth pattern from Q4 seasonality |
| **TTM (净利润)** | **10.0x** | **9.4x** | **0.93** | **Strong: R²=0.86** |
| **TTM (扣非)** | **10.0x** | **12.6x** | **0.92** | **Strong: R²=0.84** |
| Annual Q4 only | 8.8x | 4.7x | 0.88 | Loses mid-year data |

### Capital Gain Decomposition

Using TTM 净利润:
- Stock: 7.64 → 76.35 (10.0x)
- TTM Profit: 47.2亿 → 442.0亿 (9.4x)
- Implied P/E: ~10.2x → ~9.6x (slight compression)
- Conclusion: Stock return almost entirely driven by profit growth; PE contributed negatively

Using TTM 扣非:
- Stock: 7.64 → 76.35 (10.0x)
- TTM 扣非: 31.4亿 → 394.8亿 (12.6x)
- Implied P/E compressed even more
- Both metrics confirm: profit-driven stock appreciation

### Why Both Metrics Agree

The gap between 净利润 TTM and 扣非 TTM represents non-recurring income (政府补贴, asset disposal, etc.). For Midea, this gap is relatively stable over time, meaning non-recurring income is actually quite "recurring" for this company. This strengthens the Lynch-style analysis conclusion.

## Chart Type Selection

| Chart Type | When to Use |
|---|---|
| Dual Y-axis (price left, profit right) | Show absolute values, different scales |
| Normalized (both start at 1) | Compare growth multiples directly |
| Dual Y-axis + bar chart for quarterly + line for TTM | Show seasonality AND trend together |
| Lag comparison (profit shifted 1-2Q) | Test if earnings leads/lags price |
