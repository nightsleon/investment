# Q4 Seasonality in Chinese A-Share Stocks

## The Pattern

Chinese A-share companies commonly show systematically lower Q4 profits compared to Q3. This is not random — it's a structural pattern.

## Midea Group (000333) Case Study

From 2013-2025, Q4 profit < Q3 profit in **14 out of 14 years** for 净利润, and **13 out of 13 years** for 扣非净利润.

Q4 is typically only **40%-65%** of Q3.

| Year | Q3 (亿) | Q4 (亿) | Q4/Q3 |
|------|---------|---------|-------|
| 2014 | 23.4    | 15.5    | 66%   |
| 2016 | 33.1    | 18.8    | 57%   |
| 2018 | 49.6    | 23.3    | 47%   |
| 2019 | 61.3    | 29.0    | 47%   |
| 2020 | 80.9    | 52.0    | 64%   |
| 2021 | 84.5    | 51.2    | 61%   |
| 2022 | 84.7    | 50.8    | 60%   |
| 2023 | 94.9    | 60.0    | 63%   |
| 2024 | 108.9   | 68.4    | 63%   |
| 2025 | 118.7   | 60.6    | 51%   |

## Root Causes

### 1. Year-End Impairment & Provisions (最大因素)
- 应收账款坏账准备 (bad debt provisions)
- 存货跌价准备 (inventory write-downs)
- 商誉减值测试 (goodwill impairment testing — required at year-end)
- 固定资产/在建工程减值
- These are typically recognized in Q4 during annual audit

### 2. Expense Concentration
- 年终奖、绩效奖金 (year-end bonuses)
- 年度审计费、咨询费 (audit/consulting fees)
- 营销推广费用 (marketing — budget flush before year-end)
- 研发费用结算 (R&D cost settlement)

### 3. Earnings Management / Profit Smoothing
- Management "reserves" profit in Q4 when Q3 YTD already meets annual targets
- Creates a buffer for next year's Q1
- Very common practice in A-share listed companies
- 扣非净利润 shows even more pronounced Q4 dips (less non-recurring income to mask it)

### 4. Revenue Timing
- Some orders deferred to next year's Q1
- Home appliance industry: Q4 is post-双十一 shipping wind-down
- Channel inventory adjustments

### 5. Tax Provisions
- Year-end tax settlement (所得税汇算清缴)
- Additional tax provisions booked in Q4

## Implications for Analysis

1. **Never compare single-quarter Q4 with other quarters** — it will always look like a decline
2. **Always use TTM** (rolling 4-quarter sum) for trend analysis — eliminates seasonality completely
3. **If using annual data**, use full-year cumulative, not Q4 alone
4. **扣非净利润 shows stronger seasonality** than 净利润, because 净利润 can include non-recurring income that partially offsets Q4 provisions

## Chinese Baijiu (白酒) — Reverse Pattern: H1-Heavy

Baijiu companies show the **opposite** pattern: profits are H1-heavy (春节旺季利润前置), not Q4-heavy.

Shanxi Fenjiu (600809) measured: H1 profit = **~69% of full-year** in both 2024 (84.1/122.4 = 68.7%) and 2025 (85.1/122.5 = 69.5%). Q4 is the smallest quarter; Q1 (spring festival) is the largest.

**Critical implication for mid-year reports:** never estimate full-year baijiu profit as `H1 × 2` — that overstates profit by ~38% and produces wrong PE / "historical low valuation" claims. Correct method: `全年 ≈ H1 ÷ 历史H1占比`, using that company's own 2-3 year history (白酒典型 65-70%，逐年计算，不要套用别家).

General rule: **before annualizing any half-year figure, check the company's own historical H1/full-year ratio first**; if no history exists, fall back to TTM only.

## How to Verify Data Type

If you're unsure whether XLS data is single-quarter or cumulative:
- Check if Q4 < Q3 consistently → likely single-quarter
- Check if Q4 > Q3 consistently → likely cumulative annual
- Ask the user to confirm the data source
