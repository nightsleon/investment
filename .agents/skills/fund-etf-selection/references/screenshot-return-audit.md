# Screenshot-Based Fund Return Audit

Use this workflow when the user designates screenshots as the authoritative source for fund returns.

## 1. Lock source precedence

Write down the source of truth before calculating:

- index return/risk: the exact user-designated article, table, or official factsheet;
- fund return: the exact user-designated screenshot set;
- fees, holdings, scale, and contract constraints may come from other documents, but must not overwrite return figures.

A source reset invalidates earlier API-, annual-report-, or self-built return tables unless the user explicitly asks to preserve them.

## 2. Transcribe screenshot values

For every fund, record only values visibly shown:

- product name and share class;
- 1-year, 2-year, 3-year, and 5-year cumulative return;
- since-inception return and inception date when relevant;
- screenshot warnings, such as abnormal NAV movement caused by a large redemption;
- screenshot cutoff date, if shown.

Use native vision first. For dense local screenshots, independently verify with OCR (for example macOS Vision). Resolve discrepancies by re-reading the image; do not average conflicting OCR outputs.

## 3. Calculate CAGR correctly

For an exact `N`-year cumulative return `R`:

`CAGR = (1 + R)^(1/N) - 1`

Rules:

- convert percentages to decimals before calculation;
- do not annualize “since inception” unless the exact start and end dates are known;
- do not invent 3-year or 5-year returns for products with shorter histories;
- label calculated CAGR separately from values directly displayed in the screenshot.

## 4. Compare with the index safely

An exact delivery gap requires matching:

- start and end dates;
- currency;
- gross/net/price total-return convention;
- dividend reinvestment treatment;
- fund share class and distribution adjustment.

If the screenshot does not show its cutoff date, do not publish an exact tracking gap. A comparison against an index with a known cutoff may be shown only as an **approximate annualized delivery difference**, with the mismatch stated beside the table.

## 5. Compare multi-fund portfolios

For a static no-rebalance portfolio with same-window cumulative returns:

`portfolio cumulative return ≈ Σ(weight_i × cumulative_return_i)`

Then annualize the portfolio cumulative return over the common period. Label this as a static approximation and state that rebalancing, fees, spreads, taxes, and weight drift are omitted.

## 6. Mandatory stale-number audit

After replacing the source:

1. search the report for every superseded cumulative return, CAGR, volatility, and delivery-gap figure;
2. verify every new screenshot number appears in the intended table;
3. recompute all CAGRs deterministically;
4. ensure narrative conclusions, summary tables, README entries, and recommendations use the new values;
5. preserve unrelated fee, scale, holdings, and contract data unless the source change also affects them.

## Common failure modes

- mixing annual-report returns with app screenshot returns under one date label;
- treating a screenshot’s cumulative return as CAGR;
- comparing a screenshot with an unknown cutoff to an index cutoff and calling the result an exact tracking gap;
- retaining stale numbers in the recommendation section after fixing the main table;
- ignoring warning banners about large redemptions, share splits, or abnormal NAV movements;
- allowing a theoretically better index to win after the actual fund wrapper has erased its return advantage.
