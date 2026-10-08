# Common Pitfall: Metric vs Chart Interval Mismatch

## The Bug

In `phase2_compare.py`, the `calculate_metrics()` function used a hardcoded `START_DATE:END_DATE` (2021-08-09 ~ 2026-08-07) while the chart generation used `common_start:common_end` (the group's actual common interval, e.g. 2020-03-26 ~ 2026-08-10).

This caused the table to show one CAGR ranking and the chart to show a different cumulative return ranking — because they were computed over different time windows.

## The Fix

Ensure both metric calculation and chart generation are called with the **same** interval. The correct approach:

1. Find the group's common interval first
2. Use that interval for both calculate_metrics() and generate_group_chart()
3. Never hardcode a global START_DATE/END_DATE when grouping by fund age

## Prevention

If a `calculate_metrics()` function takes no start/end parameters and instead reads globals, it's a red flag. Always pass the interval explicitly.

## Variant: Representative-Subset Charts Drift From the Published Table

A crowded group chart (11 lines) is unreadable. The natural fix is to redraw a
representative chart keeping only ~4-5 lines (one best fund per category, plus
the benchmark). This reintroduces the interval-mismatch bug in a new shape:

- The table's common interval was constrained by the *oldest/shortest-lived
  fund in the full group* (e.g. 2020-03-26, limited by 008928).
- After dropping that fund, the subset's freshly recomputed common interval
  starts earlier (e.g. 2019-11-26, the 515180 inception date).
- Chart收益数字 then differ from the table columns (e.g. benchmark +101.2% on
  chart vs +116.2% in table). Readers catch this instantly.

Fix: when redrawing a subset chart of an already-published table, **pin the
start date to the table's common start date** (filter each nav to `>= START`)
instead of taking the subset's raw intersection. The end date can stay as the
data's latest common date. Verify the chart's end labels match the table's
总收益/CAGR before considering it done.

Also: exclude any fund that lacks data over the FULL table interval — a
"quality" category fund with <5 years of live data does not belong in a 5-year
representative chart; put it in the shorter-interval group or an appendix
instead, even if it leaves that category unrepresented in the main chart.

## Chart Design: De-cluttering a Crowded Multi-Fund Chart

When a group chart has too many lines, do not try to fix it with line width or
more colors. Reduce information density instead:

- Keep the benchmark (grey dashed line, drawn on top with zorder).
- Keep one best representative per major category (e.g. classic dividend,
  dividend-low-vol, dividend-growth, cross-market HK).
- Full fund set stays in the ranking table; each fund still has its own
  vs-benchmark chart in the appendix, so disclosure is not lost.
- Sort non-benchmark lines by ending cumulative return, descending.
- Benchmark fixed at top of legend; add line-end labels "简称 +收益%" colored
  to match the line. Extend xlim by ~180 days on the right for label room.
- Footnote the exact common interval and NAV basis (reinvested; note any
  foreign-currency/QDII price source).

## Chart Design: Two-Panel Per-Fund Comparison (fund + benchmark + index)

Instead of emitting two separate images per fund (a `对比基准_<code>.png`
fund-vs-benchmark line chart AND a `跟踪偏离_<code>.png` cumulative-diff
chart), combine them into one stacked two-panel figure — this is what the
512890 article's `ETF与全收益指数累计表现.png` does and it reads much better:

- **Top panel (height ~3.0):** three normalized lines, same-day start = 100:
  - target fund reinvested NAV (solid blue `#4C78A8`)
  - benchmark fund, e.g. 512890 (grey dashed `#9A9A9A`)
  - fund's own tracking total-return index (solid orange `#F28E2B`)
  - legend carries each line's ending return; 100 baseline dotted.
- **Bottom panel (height ~1.15, sharex):** `fund_norm − index_norm` in
  percentage points, fill blue where ≥0 and red where <0, with a zero line.
  Annotate the ending value. This is the cumulative tracking difference.

Drop the standalone tracking-diff image and the report's separate
`![跟踪偏离]` line; the bottom panel replaces it. One image per fund, not two.

Implementation: compute the **common intersection of all three series** (fund
nav ∩ benchmark nav ∩ index total-return) from the group start date, normalize
each to its own first value ×100, then `gap = fund_norm - index_norm`.

### Two data-caveats that must be footnoted

1. **Index total-return data lags fund NAV.** Eastmoney fund NAV reaches the
   latest trading day; CSI total-return CSV exports are often one day behind
   (over a weekend, 2–3 days). So a chart containing the index ends earlier than
   the fund-only ranking table, and the fund's ending % on the chart is slightly
   below the table's 总收益 column. State the index cutoff date explicitly so
   readers don't read it as an error.
2. **The bottom-panel gap starts at the group comparison start**, whereas a
   separate tracking-error summary table often computes cumulative excess over
   the fund's full history. The two numbers legitimately differ (especially for
   cross-market/FX funds like 3070HK). Annualized tracking error is unaffected;
   only the cumulative level is window-dependent. Say which window the gap uses.

See `scripts/generate_phase2_vs_benchmark_combined.py` (in the A股红利指数大比拼
project) for a runnable reference implementation.
