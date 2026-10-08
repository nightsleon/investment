# CSIndex API — Index Tracking Fund Data

## Endpoint

```
GET https://www.csindex.com.cn/csindex-home/index-list/queryByIndexCode/{indexCode}
```

Returns all tracked funds/products for a given CSI index code.

**No authentication required.** Standard browser headers work:

```python
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ...",
    "Referer": "https://www.csindex.com.cn/",
    "Accept": "application/json, text/plain, */*",
}
```

## Response Format

```json
{
  "code": "200",
  "msg": "Success",
  "data": [
    {
      "productCode": "515180",
      "fundName": "易方达中证红利交易型开放式指数证券投资基金",
      "fundNameEn": "...",
      "assetClass": "股票",
      "fundType": "ETF",            // 指数基金, ETF, LOF, etc.
      "coverage": "境内",
      "indexCode": "000922",
      "indexNameCn": "中证红利",
      "aum": "179.08",              // 规模（亿元）
      "fundManager": "易方达基金管理有限公司",
      "inceptionDate": "2019-11-26",
      "exchange": "上海证券交易所"    // "-" for OTC funds
    }
  ]
}
```

## Key Fields

| Field | Description |
|---|---|
| `productCode` | Fund code (e.g. `515180` for ETF, `090010` for OTC) |
| `fundName` | Full Chinese fund name |
| `fundType` | Fund type: `ETF`, `指数基金`, `ETF联接`, `LOF` |
| `aum` | Total assets under management (亿元) |
| `inceptionDate` | Establishment date (YYYY-MM-DD) |
| `fundManager` | Fund management company |
| `exchange` | Exchange listing (or `-` for OTC/index funds) |
| `coverage` | Market coverage: `境内`, `跨市场` |

## Usage Notes

### Index Code Format

Use the index code **exactly as provided** by the index list. For CSI indices this is a numeric string (e.g. `000922`, `930955`). For other series use their prefix (e.g. `H30269`, `CESFHY`). The API handles both.

### Coverage

- Returns **all fund types** tracking the index: ETFs, ETF feeders, OTC index funds, LOFs, and even non-CN products (e.g. HK-listed ETFs tracking CSI indices).
- Cross-border indices (港股通, SHS series) correctly return HK and CN products.
- Some offshore products have non-standard `productCode` values (e.g. `3070 HK Equity`).

### Limitations

- The `aum` field updates frequency is unknown (likely quarterly from fund reports).
- The data may not include the very newest funds (launched within the last month or two).
- Does not include tracking error, fee breakdown, or performance data.

### Rate Limiting

No explicit rate limit observed, but add a 0.5s delay between requests to be safe (30 indices take ~15s).

## Complementary Data Sources

For data not available via CSIndex API (distribution history, tracking error, daily NAV, fee structure):

- **Eastmoney fund detail page**: `https://fund.eastmoney.com/pingzhongdata/{fundCode}.js` — returns NAV history, scale history, fund manager data, and sector allocation.
- **Eastmoney fund search**: `https://fundsuggest.eastmoney.com/FundSearch/api/FundSearchAPI.ashx?m=1&key={keyword}` — name/code search with basic info.
- **Fund detail page**: `https://fund.eastmoney.com/{fundCode}.html` — full HTML with fee structure, holdings, and risk metrics.

## Discovered During Development

The CSIndex SPA (single-page app) loads endpoints from `app.71baf321.js` (versioned hash). The `queryByIndexCode` endpoint was found by tracing the `indices.relativeProduct` route in the JS bundle. Other discovered endpoints:

| Path | Description |
|---|---|
| `/index-list/queryByIndexCode/{code}` | Tracking funds (this reference) |
| `/index-list/funds-tracking-index` | Paginated fund list (POST, needs filter params) |
| `/index-list/funds-filter` | Filter options |
| `/index-list/query-index-item` | Index list |
| `/exportExcel/funds-tracking-index-excel/{code}` | Excel export |

The `funds-tracking-index` POST endpoint returned empty in tests — `queryByIndexCode` is the reliable one.