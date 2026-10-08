# 股票代码映射表

## yfinance代码格式
| 市场 | 格式 | 示例 |
|------|------|------|
| 深市A股 | {code}.SZ | 000333.SZ (美的), 002847.SZ (盐津铺子) |
| 沪市A股 | {code}.SS | 600809.SS (山西汾酒) |
| 港股 | {code}.HK | 09992.HK (泡泡玛特) |

## 东方财富API SECUCODE格式
| 市场 | 格式 | 示例 |
|------|------|------|
| 深市A股 | {code}.SZ | 000333.SZ |
| 沪市A股 | {code}.SS | 600809.SS |
| 港股 | {code}.HK | 09992.HK |

## 东方财富估值API
- 报表名：RPT_VALUEANALYSIS_DET
- 关键字段：PE_TTM, PB_MRQ, DY_RATE, CLOSE_PRICE, TRADE_DATE
- 港股同样适用，SECUCODE格式为 {code}.HK

## 注意事项
- 港股数据源：yfinance比东方财富API更稳定（东方财富港股API偶尔反爬）
- 港股估值：东方财富API可用，但push2.eastmoney.com的实时行情API可能被拦截
- 港股PE百分位：需要从RPT_VALUEANALYSIS_DET拉历史PE数据后自行计算
