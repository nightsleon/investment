# 蛋卷基金指数估值 API

Base URL: `https://danjuanfunds.com/djapi/index_eva`

## 端点

### 1. 估值快照
```
GET /dj
```
返回所有指数的当前估值（PE/PB/百分位/ROE/股息率/估值等级）。
- `data.items[]` — 每个指数一个对象
- `date` 字段格式 `MM-DD`（不含年份），用 `ts` 字段推算完整日期
- `eva_type`: `low`(低估) / `mid`(适中) / `high`(高估)

### 2. PE 历史
```
GET /pe_history/{index_code}?day=all
```
- `data.index_eva_pe_growths[]` — `{pe, ts}` 数组，ts 为毫秒时间戳
- `data.horizontal_lines[]` — 分位参考线 `{line_name, line_value, line_color, line_type}`
  - line_name: "30分位值", "中位值", "70分位值"

### 3. ROE 历史
```
GET /roe_history/{index_code}?day=all
```
- `data.index_eva_roe_growths[]` — `{roe, ts}` 数组，roe 为小数（0.19 = 19%）

## 指数代码

| 名称 | 代码 | 类别 |
|------|------|------|
| 沪深300 | SH000300 | A股宽基 |
| 中证1000 | SH000852 | A股宽基 |
| 科创50 | SH000688 | A股宽基 |
| 中证白酒 | SZ399997 | A股行业 |
| 中证医疗 | SZ399989 | A股行业 |
| 主要消费 | SH000932 | A股行业 |
| 红利成长LV | CSI931157 | A股红利 |
| 红利低波 | CSIH30269 | A股红利 |
| 恒生科技 | HKHSTECH | 港股 |
| 标普500 | SP500 | 美股 |
| 纳指100 | NDX | 美股 |

## 注意
- 无需登录认证（公开接口）
- 请求间隔建议 >= 0.25s
- `date` 字段只有 MM-DD，需用 `ts` 毫秒时间戳推算完整日期
