# Interactive-browser download and evidence archive

Use when an official index site serves valid PDF/XLS downloads in a normal desktop browser but rejects terminal HTTP clients or automation sessions.

## Principle

A 403 from `curl`, a script, or a hosted headless browser proves only that the current access path was blocked. It does not prove the official link is invalid. If the user says the link works interactively, treat that as a workflow correction: try the host machine's real browser session before falling back to an old snapshot.

## Download workflow

1. Preserve the supplied prompt/source note; never turn it into the output article.
2. Create classified destinations first:
   - `sources/index-methodologies/`
   - `sources/index-factsheets/`
   - `sources/performance-data/`
   - `sources/index-factsheets/archive/` for superseded snapshots
3. Record the download directory's current files and modification times.
4. Open one direct official download URL in the host's real Chrome/Safari session, preferably in the background. Monitor for a newly created file while ignoring `.crdownload`, `.download`, `.part`, `.DS_Store`, and pre-existing files.
5. Verify the first file before batching the rest. If successful, download the remaining PDF/XLS files through the same session.
6. Check URL period flags. For example, a historical export containing `oneYearFlag` is not a ten-year file; use the provider's ten-year flag when the task requires ten years.
7. Copy the verified files into their classified source folders with descriptive names containing index, return type, date range, and cutoff date. Move older official snapshots into `archive/` rather than silently deleting or presenting them as current.

## Verification

Never trust the extension alone.

- PDF: validate the PDF signature/parser, page count, index identity, return type, currency, and internal cutoff date.
- XLS: validate the binary workbook format, worksheet identity, first/last rows, row count, and internal `as of` date.
- Downloaded error page: reject HTML or a security-control page saved with a `.pdf`/`.xls` suffix.
- Hash original binaries with SHA-256 for traceability.

## XLS-to-CSV and metrics

- Keep the original XLS unchanged and save CSV as a derived companion.
- Convert dates and point levels without rounding away source precision.
- Verify XLS and CSV row by row, not only by comparing endpoints.
- Compute aligned total-return CAGR, volatility, drawdown, and drawdown dates from the complete daily series.
- Keep a small derived metrics CSV that states formulas and observation counts.

For large generated CSV files, avoid reconstruction through paginated text reads: chunk boundaries can silently omit rows or introduce blanks. Generate the CSV in one pass from the original workbook, then verify exact row count, date set, values, and endpoints against the XLS.

## Reporting language

Use: “The terminal/headless access path was blocked; the host's interactive browser downloaded the current official file.”

Avoid: “The official site/link cannot be downloaded.”

If current official files are obtained, remove old-data caveats from the article and recompute affected rankings rather than only revising `sources/README.md`.