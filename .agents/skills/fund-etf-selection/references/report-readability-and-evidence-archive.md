# Fund-report readability and evidence archive

Use this when a fund/index comparison has grown into a research package containing a long report, a purchase recommendation, a short article, official factsheets, and screenshots.

## Readability refactor

Preserve the analytical evidence while reducing repetition.

Recommended long-report flow:

1. purchase decision card: need, recommendation, main reason, main cost;
2. underlying-index routes;
3. realized fund returns and fund-versus-index delivery gap;
4. two or three actionable purchase plans;
5. same-index wrapper selection;
6. post-purchase review indicators;
7. sources and limitations.

Practical rules:

- Define full legal fund names and codes once, then use fixed short names.
- Keep one complete recommendation section; middle sections should provide evidence rather than repeat the conclusion.
- Replace one very wide all-product table with an index-route table plus same-index wrapper tables.
- Use `fact → judgment → decision` for product-specific conclusions.
- Put ETF mechanics and methodology after the decision evidence, not before it.
- Keep a decision card in the first screen, with one default recommendation and at most two conditional alternatives.
- Before a performance table, show how each materially different index selects holdings; otherwise readers see which route won without understanding what exposure produced the result.
- Render methodology as a left-to-right chain: `universe → eligibility/quality screens → yield rank → low-volatility rank → weighting and caps`.
- Standardize each route as `selection chain + one core advantage + one core disadvantage`; quantify sector exposure in the advantage/disadvantage when concentration is decision-relevant.
- Use document-specific compression: a full chain and explicit advantage/disadvantage in an index article or deep report; a shorter chain and one “core trade-off” in a fund-buying article.
- Replace an existing methodology summary rather than appending a duplicate. Keep formulas and edge-case rules in the deep report and link to it from shorter articles.
- Index and fund datasets may have different cutoff dates. State each date beside the corresponding table; never relabel an index table with the later fund-data date.

## Do not lose delivery-gap evidence

A readability edit must not remove the fund-versus-index comparison. Preserve a compact table containing:

| Product | Fund CAGR | Matching TR/NTR index CAGR | Annualized delivery gap |
|---|---:|---:|---:|

Terminology matters:

- `fund CAGR − index CAGR` is an annualized delivery gap or annualized return-gap approximation;
- statistical tracking error is the dispersion/standard deviation of periodic active returns;
- if fund and index cutoff dates differ, label the table approximate and do not present it as precise statistical tracking error;
- when the reader explicitly asks to retain “tracking error,” retain the section but state the exact calculation and limitation beside it.

## Research-package archive

### Preserve the brief before generating output

Treat the user's research brief, source notes, and prompt as input evidence, not as an output target.

- Before rewriting any Markdown file, identify its role: prompt/brief, source note, report, or article.
- Never overwrite a prompt or research brief with the generated article, even when the user attached only one Markdown file.
- Keep separate files such as `topic-prompt.md` and `topic-article.md`, or place them under `briefs/` and `articles/`.
- If a prompt was overwritten accidentally, first save the finished article under a new output filename, then restore the original prompt byte-for-byte when recoverable from the supplied source or session record.
- Full-file replacement is appropriate only after confirming the file is an output artifact.

Prefer evidence role over file type. Create the destination folders **before downloading** so PDFs, spreadsheets, and API exports never accumulate beside the article:

```text
topic/
├── README.md
├── briefs/
├── reports/
├── articles/
├── sources/
│   ├── index-methodologies/
│   ├── index-factsheets/
│   ├── performance-data/
│   ├── index-data/          # screenshots and point-in-time tables
│   └── fund-returns/
└── archive/
```

Classification rules:

- methodology/规则 PDF → `index-methodologies/`;
- factsheet/index card → `index-factsheets/`;
- raw API, XLS, JSON, or normalized CSV time series → `performance-data/`;
- screenshots and point-in-time valuation/holdings evidence → `index-data/`;
- temporary extraction text and debugging downloads stay outside the project and are removed after verification.

Naming convention:

`code_object_content_cutoff-date.ext`

- Put index/fund code first for sorting.
- Use `YYYY-MM-DD`; do not use ambiguous forms such as `0713`.
- Do not invent a cutoff date when a screenshot does not show one.
- Keep superseded evidence in `archive/YYYY-MM/` until no current report references it.
- Add a topic README containing latest report entry points, data-cutoff notes, and a source ledger.
- In the source ledger, distinguish the document's internal data/version date from the web-archive capture date; include both when they differ.

## Official-source access fallback

When an index provider's current site triggers security controls, preserve official provenance rather than silently substituting a third-party summary. Scope the access claim precisely: `this agent/network received HTTP 403` does **not** mean the canonical link is invalid or unavailable to the user in a normal browser.

1. inspect the user's canonical current URL first and record HTTP status, content type, and whether the response is the requested PDF/XLS/JSON or an HTML error page;
2. retry with a browser session when available; if the user can download the current file normally, prefer that file over any archive snapshot;
3. distinguish endpoint types correctly: `.xls` is an Excel export, not CSV; a JSON widget endpoint is API data, not a downloadable spreadsheet; verify period flags such as `oneYearFlag` versus `tenYearFlag`;
4. identify the provider's canonical PDF URL from the official index page or archived official page;
5. query the Internet Archive CDX endpoint for successful PDF captures;
6. download the latest usable archived response with the `id_` form so the original bytes are returned;
7. verify the file signature and extract text to confirm provider, title, internal version/data date, and relevant index;
8. archive it under the normal evidence category with `存档` and the capture date in the filename;
9. record the canonical official URL, archive capture date, internal document date, and current-access limitation in `sources/README.md`;
10. never describe an older archived factsheet as current, never imply the canonical URL itself is broken based only on an environment-specific block, and do not turn manually transcribed point values into a fake "official download" file.

Archived official files are provisional evidence. Any score or comparison using an older factsheet must show its actual cutoff beside the number and explain that it is not a strict same-date comparison. Replace it and recompute as soon as the current official download becomes available.

If a newer methodology conflicts with an older factsheet, use the newer methodology for current rules, disclose the conflict, and reduce the transparency/evidence score rather than hiding it.

## Safe reorganization workflow

1. Inventory every file and classify it by role.
2. Search Markdown for all local references before moving files.
3. Read screenshots when needed to verify visible cutoff dates; do not infer missing dates from filesystem metadata.
4. Move and rename files in one explicit mapping.
5. Update the topic README, project README, report links, and source descriptions.
6. Validate every local Markdown link relative to the file containing it.
7. Search for stale old filenames after the move.
8. Confirm expected counts in each source category and run `git diff --check`.

Do not delete ambiguous duplicates during the first pass. Archive them until their role and references are confirmed.