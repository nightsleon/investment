# Total-return delivery audit

Use this note when comparing dividend, low-volatility, cross-border, ETF, feeder, and OTC index products.

## Required return series

1. Prefer the provider's official gross-total-return (TR) or net-total-return (NTR) series; record currency and cutoff date.
2. Use the fund's official share-class NAV growth or reconstruct adjusted return:
   - cash distribution: assume immediate reinvestment at ex-distribution NAV when evaluating compounding;
   - share split/consolidation: adjust units before comparing endpoint NAVs;
   - do not use raw unit NAV across a split or repeated distributions.
3. Calculate on identical dates:
   - cumulative fund return;
   - cumulative index return;
   - fund CAGR and index CAGR;
   - cumulative delivery gap and annualized delivery gap.
   - annualize endpoint returns using the actual elapsed time (`calendar days / 365.2425`) unless the source period is exactly an integer number of years. A range labeled “10 years” may actually be 10 years and 1 month; applying a `1/10` exponent overstates CAGR.
4. Repeat with a second window when possible, such as five complete calendar years plus the latest rolling five years, to detect endpoint effects.

## Benchmark trap

A fund may report strong excess return against a contractual benchmark that is:

- a price-return index rather than a total-return index;
- `95% × price index + 5% × cash`;
- a different tax, currency, or dividend convention.

Always show three rows separately: gross/NTR index, fund, and contractual benchmark. “Outperformed benchmark” does not prove that the fund delivered the index's economic total return.

Do not infer the benchmark's return convention from a generic label such as `指数收益率`. Resolve the exact provider series/code and verify whether it is price return, net total return, or gross total return. When the fund manager's reported annual index gain differs materially from the provider's official TR factsheet, treat them as different return variants until proven otherwise; do not call the entire difference manager underperformance.

For cross-provider work, prefer official daily index levels for exact endpoint calculations. Factsheet “five-year annualized” figures may use provider-specific date/trading-day conventions and can differ from endpoint CAGR; disclose which method is used instead of silently mixing them.

## Risk-metric comparison

When comparing 3-year and 5-year fund risk/return from annual reports:

- compute CAGR from the disclosed cumulative share-class NAV growth: `(1 + cumulative return)^(1/years) - 1`;
- fund reports commonly disclose the standard deviation of daily NAV growth, not annualized volatility;
- annualize it as `daily standard deviation × sqrt(250)` and state the convention;
- use the same cutoff date and share class for both funds;
- present cumulative return, CAGR, and annualized volatility together so a lower-volatility product is not penalized by return-only ranking.
- match the provider's volatility convention before comparing: if an official factsheet defines risk from monthly returns, recompute other series from month-end levels and annualize with `sqrt(12)` rather than mixing it with daily `sqrt(252)` volatility.
- put each risk metric's cutoff date beside the value. Older official factsheets can support an approximate structural comparison, but not a strict same-date ranking.
- if daily levels are unavailable for one index, do not invent or infer maximum drawdown. State which indices have drawdown evidence, keep the missing value unknown, and give the risk score an explicit uncertainty margin.

## ETF versus OTC mechanics

Verify each prospectus. Ordinary open-end index funds may require at least 5% cash or short government bonds and may impose a 90–95% equity band. In-kind ETFs often avoid that fixed redemption reserve and can hold around 99% equities, but still carry cash substitution, settlement, distribution, rebalance, and derivatives-margin cash.

Compare all-in implementation:

- ETF: management/custody fee + brokerage commission + bid/ask spread + premium/discount;
- OTC A share: management/custody fee + purchase/redemption fee + cash drag;
- feeder: target-ETF assets may be exempt from duplicated management/custody charges, but flow and cash layers remain.

## Delivery-gap decomposition

Investigate in this order:

1. **Equity exposure** — compare actual average/period-end stock exposure. A 90–95% OTC mandate can materially lag a 99% ETF in strong markets.
2. **Explicit fees** — management, custody, sales service, index license, and class-specific charges.
3. **Dividend taxation** — especially Stock Connect withholding and A-share holding-period tax. Gross TR is not directly investable.
4. **Trading and rebalance friction** — turnover, stamp duty, bid/ask spread, unavailable or suspended constituents.
5. **Cash-flow friction** — subscriptions/redemptions, mandatory cash, distribution preparation, and delayed reinvestment.
6. **Launch effects** — building positions and rapid scale growth; separate mature-year evidence from inception-year evidence.
7. **Corporate-action/index convention** — verify how ordinary and special dividends, FX, and divisor changes are treated before attributing the entire gap to manager skill.

Do not force an exact attribution without daily holdings, cash flows, dividend receipts, taxes, and trades. Give evidence-backed ranges and label residuals.

## Decision rules

- Same index: realized delivery, fees, liquidity, and channel dominate methodology.
- Different indices: compare the **investable funds** end to end on realized CAGR, volatility, drawdown, and recovery; then attribute the result to index return versus wrapper drag. Do not use a strict “best index wins” ladder.
- Use `expected investable return ≈ expected index total return − sustainable delivery drag` for the forward view. A persistent structural gap can consume the entire theoretical index advantage.
- Keep time direction clear: realized delivery is backward-looking evidence; explicit fees and contractual cash constraints are forward-looking friction. Do not double-count past fees inside both the delivery score and cost score.
- Separate **proven delivery leader** from **low-fee forward-looking candidate**. A newer fund with lower fees and adequate liquidity may be attractive, but do not rank it above a longer-lived wrapper solely from the fee schedule when the longest common live period has not yet shown better realized delivery. Show both labels and the common-period evidence.
- ETF feeder: do not double-count fees on target-ETF assets; the feeder can still lag through cash and an extra flow layer.
- No five-year history: write “insufficient live history,” then compare a common shorter period and recent mature years.
- For a newly launched ETF, show both inception/common-period results and at least one mature full calendar year when available; launch/building-position effects can dominate the short history.
- If the wrapper's annualized delivery gap erases the underlying index's annualized advantage over another index, rank on realized investor outcome rather than headline index backtest.

## Reusable evidence pattern

For a concise recommendation, show:

| Product/index | Period | Cumulative return | CAGR | Annualized gap vs TR |
|---|---|---:|---:|---:|

Then add:

- same-index ETF vs OTC/feeder difference;
- stock-exposure difference;
- fixed-fee difference;
- tax and cross-market caveats;
- whether the conclusion is based on five-year live data or a shorter period.
