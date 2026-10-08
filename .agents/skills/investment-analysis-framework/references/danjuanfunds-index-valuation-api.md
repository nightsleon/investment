# 蛋卷基金指数估值 API

用于获取指数级别的 PE/PB/ROE 历史走势和百分位数据。适合做指数基金的"好时机"判断。

## API 端点

### 1. 全量指数估值快照

```
GET https://danjuanfunds.com/djapi/index_eva/dj
```

返回所有指数的当前估值：PE、PB、PE百分位、PB百分位、ROE、股息率、估值类型(low/mid/high)。

无需登录。User-Agent 必须带浏览器标识。

响应结构：
```json
{
  "data": {
    "items": [
      {
        "index_code": "SZ399997",
        "name": "中证白酒",
        "pe": 20.19,
        "pb": 3.91,
        "pe_percentile": 0.1764,
        "pb_percentile": 0.0268,
        "roe": 0.1937,
        "yeild": 0.044,        // 股息率（注意拼写）
        "eva_type": "low",      // low=低估, mid=适中, high=高估
        "pb_flag": false,       // true=用PB估值, false=用PE估值
        "peg": 1.9357
      }
    ]
  }
}
```

### 2. PE 历史走势（近10年+）

```
GET https://danjuanfunds.com/djapi/index_eva/pe_history/{index_code}?day=all
```

无需登录。返回周频PE数据 + 30/中位/70分位参考线。

响应结构：
```json
{
  "data": {
    "index_eva_pe_growths": [
      {"pe": 20.04, "ts": 1464278400000},
      ...
    ],
    "horizontal_lines": [
      {"line_name": "30分位值", "line_value": 24.19, "line_color": "#07AA31"},
      {"line_name": "中位值", "line_value": 29.69, "line_color": "#666666"},
      {"line_name": "70分位值", "line_value": 34.20, "line_color": "#F0191D"}
    ]
  }
}
```

### 3. ROE 历史走势

```
GET https://danjuanfunds.com/djapi/index_eva/roe_history/{index_code}?day=all
```

无需登录。返回周频ROE数据。

响应结构：
```json
{
  "data": {
    "index_eva_roe_growths": [
      {"roe": 0.1937, "ts": 1464278400000},
      ...
    ]
  }
}
```

## 常用指数代码

| 指数名称 | index_code | 类别 |
|---------|------------|------|
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

## 注意事项

1. **接口无需登录**，但需要带 `User-Agent` 请求头
2. **`yeild` 拼写错误**是 API 本身的问题，不是我们拼错
3. **PE数据是周频**（大约每周一个点），不是日频
4. **ROE字段名**：pe_history 里是 `pe`，roe_history 里是 `roe`（小写）
5. **估值类型映射**：`low`→低估, `mid`→适中, `high`→高估
6. **pb_flag**：`true` 表示该指数用 PB 估值更合适（如银行、地产），`false` 表示用 PE 估值
7. **detail 接口需要登录**（`/djapi/index_eva/dj/detail/{code}`），但 pe_history 和 roe_history 不需要
8. **批量请求注意限频**：建议每次请求间隔 0.3 秒以上
9. **ROE数据量可能少于PE**：部分指数ROE数据起始时间晚于PE
