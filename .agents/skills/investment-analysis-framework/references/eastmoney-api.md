# East Money (东方财富) API Reference

## Datacenter API Base

```
https://datacenter.eastmoney.com/securities/api/data/v1/get
```

## Report Names

| Report Name | Description | Key Fields |
|---|---|---|
| `RPT_DMSK_FN_INCOME` | Income statement (利润表) | PARENT_NETPROFIT, DEDUCT_PARENT_NETPROFIT, BASIC_EPS, TOTAL_OPERATE_INCOME |
| `RPT_DMSK_FN_BALANCE` | Balance sheet summary (资产负债表摘要) | MONETARYFUNDS, INVENTORY, FIXED_ASSET, TOTAL_ASSETS, TOTAL_LIABILITIES, DEBT_ASSET_RATIO |
| `RPT_DMSK_FN_CASHFLOW` | Cash flow statement (现金流量表) | NETCASH_OPERATE, CONSTRUCT_LONG_ASSET, NETCASH_INVEST, CCE_ADD |

## Filter Format

```
filter=(SECUCODE="600809.SH")(REPORT_DATE='2025-12-31')
```

- SECUCODE: `XXXXXX.SH` for Shanghai, `XXXXXX.SZ` for Shenzhen
- Date: **single quotes** around YYYY-MM-DD. Double quotes → "日期参数格式错误"
- In JS `fetch()`, escape as `\\'2025-12-31\\'`
- Multiple filters are concatenated without AND/OR

## Common Parameters

- `pageSize`: max 50
- `sortColumns=REPORT_DATE`, `sortTypes=-1` (descending)
- `source=HSF10`, `client=PC`

## Income Statement Fields (RPT_DMSK_FN_INCOME)

| Field | Description |
|---|---|
| PARENT_NETPROFIT | 净利润 (归母) |
| DEDUCT_PARENT_NETPROFIT | 扣非净利润 |
| BASIC_EPS | 基本每股收益 |
| TOTAL_OPERATE_INCOME | 营业总收入 |

## Balance Sheet Fields (RPT_DMSK_FN_BALANCE)

| Field | Description |
|---|---|
| MONETARYFUNDS | 货币资金 |
| INVENTORY | 存货 |
| FIXED_ASSET | 固定资产 |
| ACCOUNTS_RECE | 应收账款 |
| TOTAL_CURRENT_ASSETS | 流动资产合计 |
| TOTAL_NONCURRENT_ASSETS | 非流动资产合计 |
| TOTAL_ASSETS | 总资产 |
| ACCOUNTS_PAYABLE | 应付账款 |
| ADVANCE_RECEIVABLES | 预收款项（注意：不是合同负债；营运质量分析中的合同负债需从年报合并资产负债表/PDF附注提取） |
| TOTAL_LIABILITIES | 总负债 |
| TOTAL_EQUITY | 股东权益合计 |
| CURRENT_RATIO | 流动比率 |
| DEBT_ASSET_RATIO | 资产负债率 |

**NOT available in summary API**: 交易性金融资产, 短期借款, 长期借款, 理财产品, 其他流动资产. Detailed balance sheet API (`zcfzbAjaxNew`) is anti-crawler blocked.

## Cash Flow Fields (RPT_DMSK_FN_CASHFLOW)

| Field | Description |
|---|---|
| NETCASH_OPERATE | 经营活动现金流净额 |
| CONSTRUCT_LONG_ASSET | 购建固定资产等支付的现金 (CapEx) |
| NETCASH_INVEST | 投资活动现金流净额 |
| NETCASH_FINANCE | 筹资活动现金流净额 |
| CCE_ADD | 现金及现金等价物净增加额 |
| SALES_SERVICES | 销售商品、提供劳务收到的现金 |
| PAY_STAFF_CASH | 支付给职工的现金 |

## Calling via browser_console

```javascript
fetch('https://datacenter.eastmoney.com/securities/api/data/v1/get?reportName=RPT_DMSK_FN_CASHFLOW&columns=ALL&filter=(SECUCODE="600809.SH")(REPORT_DATE=\\'2025-12-31\\')&pageSize=1&source=HSF10&client=PC')
.then(r => r.json())
.then(d => JSON.stringify(d.result?.data?.[0], null, 2))
```

## Current Quote Page

```
https://quote.eastmoney.com/concept/shXXXXXX.html
```

Shows: 最新价, 动态市盈率, 市净率, 总市值, 52周高低, etc.

## F10 Financial Analysis Page

```
https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/Index?type=web&code=shXXXXXX
```

Detailed balance sheet, income statement, cash flow — but detailed API endpoints are anti-crawler protected.

## Known Issues

1. `zcfzbAjaxNew` (detailed balance sheet) returns HTML redirect instead of JSON
2. `RPT_F10_FN_BALANCE` report name does not exist / returns no data
3. Date filter with double quotes fails; must use single quotes: `'2025-12-31'`
4. Field `TRADING_FINANCIAL_ASSETS` does not exist in RPT_DMSK_FN_BALANCE
5. Use `columns=ALL` first to discover available fields for a given report
