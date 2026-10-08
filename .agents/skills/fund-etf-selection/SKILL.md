---
name: fund-etf-selection
description: Compare and select index funds and ETFs by combining index quality with fund-level delivery, cost, liquidity, and investability.
---

# Fund and ETF Selection

Use for broad-market, factor, sector, thematic, cross-border, ETF, feeder, and OTC index products. Do not apply an individual-stock framework.

## Core model

Analyze two layers:

1. **Underlying index** — what the investor owns; main source of return and risk.
2. **Fund wrapper** — how much reaches the investor after fees, cash drag, tax, tracking, and trading friction.

`expected investable return ≈ expected index total return − sustainable delivery drag`

“Index first” identifies the exposure; it is not a rigid ranking rule. Wrapper loss can erase an index advantage, while a cheap wrapper cannot rescue a structurally weak index.

**ETF preference applies only within the same index.** Never rank an ETF above an OTC fund solely because it is an ETF when they track different indices.

## Workflow

### 1. Establish the objective

State missing assumptions: total return or cash income, holding period, drawdown tolerance, market/FX scope, ETF or OTC channel, lump sum or recurring purchase, tax/settlement tolerance, and existing overlap. Do not invent a personal-fit score without them.

### 2. Map indices to products

Group ETFs, feeders, OTC funds, and A/C/I share classes by underlying index before ranking. Similar names may track different rules.

For long reports, define each legal name, share class, code, and fixed short name once. Normally choose one wrapper per index; duplicate same-index exposure needs a specific channel, tax, or liquidity reason.

### 3. Evaluate the index

First distinguish the question being asked:

- **Index quality:** whether the methodology is sound and historically validated.
- **Buy timing:** whether the index is currently cheap or offers an attractive yield.
- **Fund delivery:** whether a specific ETF/fund tracks it efficiently.

Do not mix these layers. For an **index-only quality analysis**, exclude current PE/PB/yield percentiles and every wrapper metric; valuation is a time-varying buy-timing input, not a property of index quality. Use the dividend/low-volatility scoring framework in `references/dividend-low-volatility.md` when applicable.

For a full investable-product analysis, assess five dimensions:

1. **Methodology:** universe, screens, weighting, rebalance, quality/profitability/growth/value rules, and cyclical or recent-winner bias.
2. **Concentration:** constituents, top-10, stock/sector caps, full sector weights, geography, currency, ownership, and hidden factor exposure.
3. **Total return and risk:** aligned TR/NTR, CAGR, volatility, drawdown, recovery, rolling outcomes, and live versus backtest history.
4. **Valuation and income:** PE/PB/yield and own-history percentiles; use only for current attractiveness and income context, not the index-quality score.
5. **Portfolio role:** core/satellite, overlap, and rate, cycle, commodity, country, factor, and FX sensitivity.

### 4. Evaluate the wrapper

Verify current documents and live data:

- all-in fees, purchase/redemption/trading costs, actual exposure, and cash constraints;
- scale trend, ETF spread/turnover/premium-discount/depth, and OTC limits;
- inception, usable live history, operating continuity, and abnormal NAV events;
- realized delivery, distributions, tax, FX, calendars, quotas, and settlement.

Scale and liquidity are thresholds; once adequate, bigger is not automatically better. For feeders, verify target-ETF fee exemptions while retaining cash and extra-flow drag.

### 5. Audit realized delivery

Compare adjusted fund returns with the matching gross- or net-total-return index over identical dates.

`annualized delivery gap = fund CAGR − index CAGR`

A negative value means lag. This is not statistical tracking error, which is the annualized dispersion of periodic active returns.

Requirements:

- align dates, currency, tax convention, share class, and dividend reinvestment;
- adjust distributions and share splits/consolidations;
- when using Eastmoney history, do NOT use the K-line forward-adjusted price (`fqt=1` from `push2his.eastmoney.com/api/qt/stock/kline/get`) — it has been verified to produce wrong returns for ETFs with cash dividends (e.g., 515300 showed 72.55% vs correct 52.70%, a 20-percentage-point error). Always use the fund NAV API (`api.fund.eastmoney.com/f10/lsjz`): reconstruct adjusted NAV from unit NAV (DWJZ), applying `(NAV_t * split_ratio + cash_dividend_per_share) / NAV_{t-1}` on each ex-dividend/split date, and reject or explicitly handle every unrecognized event;
- the share split formula `(NAV_t + dividend) / NAV_{t-1}` is WRONG when a split occurs — a 1:2 split drops NAV from 1.6 to 0.8, yielding `(0.8+0)/1.6 = 0.5` (a 50% loss). The correct formula is `(NAV_t * split_ratio + dividend) / NAV_{t-1}` where `split_ratio` is the number of new shares per old share;
- show the contractual benchmark separately when it differs from official TR/NTR;
- if a screenshot omits its cutoff, label the comparison approximate;
- if five-year live history is unavailable, use a common shorter period and state the limit;
- **do NOT use the "common intersection of all fund start dates" as the comparison period** — use fixed periods (e.g., 2021-08-02 ~ 2026-08-10 for 5-year group, 2024-08-10 ~ 2026-08-10 for 2-year group). Skip funds that don't have enough data for the fixed period rather than dragging the whole group's start date later;
- honor user-designated source precedence and remove stale figures after a reset.

### 6. Rank the investable endpoint

1. define acceptable index exposures;
2. compare realized fund CAGR, risk, drawdown, and recovery;
3. attribute index return versus wrapper drag;
4. estimate forward drag from fees, cash, tax, spread, and recurring friction;
5. apply scale/liquidity thresholds;
6. use company and operating history as tie-breakers.

Realized delivery looks backward; fees and contractual constraints estimate future friction. Do not double-count historical fees inside both delivery and cost scores.

## Reference router

| Trigger | Reference |
|---|---|
| Screenshots are the return source | `references/screenshot-return-audit.md` |
| Exact TR/NTR comparison or loss decomposition | `references/total-return-delivery-audit.md` |
| Dividend or low-volatility methodology | `references/dividend-low-volatility.md` |
| ETF holdings-history article, proxy-data boundaries, charts, or narrative refactor | `references/etf-holdings-history-article.md` |
| Report refactor, evidence archive, or link validation | `references/report-readability-and-evidence-archive.md` |
| Official downloads work interactively but scripts/headless receive 403 | `references/browser-download-and-data-archive.md` |
| Tracking fund listing by index code (CSIndex API) | `references/csindex-api-data-sources.md` |
| Multi-index parallel ranking, scoring, grouping, and report structure | `references/csi-index-scoring-and-ranking.md` |
| Phase 2 — fund NAV vs index TR comparison, benchmark ranking, tracking deviation charts | `references/fund-nav-vs-index-comparison.md` |
| Dividend index classification from official methodology PDFs | `references/dividend-index-classification.md` |

## Decision rules

- **Same index:** delivery, forward cost, liquidity, channel, and evidence length dominate.
- **Different indices:** compare investable products end to end; index quality and delivery explain the result but are not separate trophies.
- **New low-fee fund:** treat as a forward candidate until common-period delivery supports promotion over a longer-lived wrapper.
- **No same-index ETF:** assess the available OTC wrapper; do not substitute a different-index ETF mechanically.
- **ETF versus OTC:** verify the prospectus. ETFs are not always 100% invested; OTC convenience may justify modest extra cost.

## Output

Lead with:

1. product glossary grouped by index;
2. one table covering exposure, realized CAGR/risk, delivery gap, forward cost, and evidence length;
3. one primary recommendation based on realizable risk-adjusted outcome;
4. at most one or two conditional alternatives;
5. same-index wrapper choice and duplicate-product warning;
6. assumptions, dates, limitations, and evidence that could overturn the decision.

For long reports: decision card → index routes → realized delivery → actionable plans → same-index wrappers → review indicators → sources. Use `fact → judgment → decision` for product conclusions.

When producing a research package, create and use classified source folders before downloading: `index-methodologies/`, `index-factsheets/`, `performance-data/`, and `index-data/`. Keep temporary extraction files outside the project, and maintain `sources/README.md` with canonical URLs, internal data/version dates, archive dates, and cutoff limitations. See `references/report-readability-and-evidence-archive.md`.

If scripts or hosted automation receive 403 but the user confirms that a normal browser can download, do not stop at an archive snapshot or merely rewrite the caveat. Use the host machine's real browser session, verify one file, then download and classify the current PDF/XLS files. Preserve original binaries, convert derived CSV separately, and verify XLS-to-CSV equality row by row. See `references/browser-download-and-data-archive.md`.

When several funds track different strategy indices, explain each index route before showing historical returns. Use a visually scannable sequence:

`universe → dividend/quality screens → yield ranking → low-volatility selection → weighting/caps`

For each route, add exactly one core advantage and one core disadvantage; include current sector weights in the concentration judgment rather than saying only “financials-heavy” or “well diversified.” Adapt detail to the document: full chain plus advantage/disadvantage in an index comparison, compressed chain plus one “core trade-off” in a fund-selection article. Do not paste the full methodology into every related document.

## Hard rules

- Never overwrite a user-supplied prompt, research brief, or source-note file with the generated report/article; preserve the input and write output to a separate artifact.
- Do not generalize an environment-specific HTTP 403 into “the official link cannot be downloaded”; distinguish current-agent access from link validity and prefer a user-downloaded current official file over an archive snapshot.
- Do not rank by current yield, recent return, low fee, or scale alone.
- Do not compare price-index returns with adjusted fund returns; use aligned TR/NTR.
- Do not mix dates, currencies, tax treatments, or live/backtest history without disclosure.
- Do not call an approximate return gap exact tracking error.
- Do not substitute since-inception return for missing fixed-period history.
- Do not treat distributions as newly created return.
- Do not extend ETF preference across indices.
- Do not double-count feeder/ETF fees or past delivery drag/forward fees.
- Do not recommend duplicate same-index wrappers without a reason.
- Do not present past factor performance as a forecast.
- Scores require explicit dimensions, weights, and investable-outcome logic.
