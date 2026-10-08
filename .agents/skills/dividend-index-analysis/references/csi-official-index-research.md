# 中证指数官方资料核验与数据接口

用于只允许引用中证指数有限公司官方来源的指数研究。接口和页面可能调整；每次使用时都应实际请求并核对返回字段、日期与文件类型。

## 1. 资料入口

- 指数详情页：`https://www.csindex.com.cn/#/indices/family/detail?indexCode={PRICE_CODE}`
- 基础信息：`https://www.csindex.com.cn/csindex-home/indexInfo/index-basic-info/{CODE}`
- 资料清单：`https://www.csindex.com.cn/csindex-home/indexInfo/index-details-data?fileLang=2&indexCode={PRICE_CODE}`
- 衍生指数：`https://www.csindex.com.cn/csindex-home/perf/get-derivative-index?indexCode={PRICE_CODE}`

从详情页或资料清单取得编制方案、指数单张、样本权重和样本列表的官方 URL。不要根据文件命名规律自行拼接后直接引用；下载后核验 HTTP 状态、Content-Type、文件头和正文日期。资料清单中列出的附件也可能暂时不可用或返回占位内容。

## 2. 编制规则提取顺序

按下列链条摘录现行方案原文：

`样本空间 → 市值/流动性过滤 → 分红与盈利约束 → 质量/股息/低波指标 → 排序与样本数 → 加权方法 → 单股/前N大/行业上限 → 定期与临时调整`

同时记录 PDF 的版本号和年月。应明确区分“按质量得分加权”“股息率加权”和“自由流通市值加权”，不能仅凭指数名称推断。

## 3. 全收益代码与历史数据

先通过衍生指数接口确认全收益指数代码，再查其基础信息。不要猜测价格指数与全收益指数代码的对应关系。

- 历史 JSON：`https://www.csindex.com.cn/csindex-home/perf/index-perf?indexCode={TR_CODE}&startDate={YYYYMMDD}&endDate={YYYYMMDD}`
- 可用交易日：`https://www.csindex.com.cn/csindex-home/perf/index-perf-tradeDate?indexCode={TR_CODE}`
- Excel 导出：`POST https://www.csindex.com.cn/csindex-home/exportExcel/downloadindex-perf?language=CH`

Excel 请求体：

```json
[
  {
    "startDate": "20160630",
    "endDate": "20260731",
    "indexCode": "TR_CODE"
  }
]
```

验证要求：

1. JSON `code` 为 200，并核对 `indexNameCnAll`、首末 `tradeDate`、首末 `close` 和记录数。
2. Excel 响应应是工作簿内容，而不是错误 JSON 或网页。
3. 若统一比较起点早于数据起点，统一区间必须后移；若数据覆盖起点，则仍需按发布日期拆分回溯期与发布后历史。
4. 基日、历史数据起点与发布日期是三件不同的事。

## 4. 最新结构接口

- 前十大：`https://www.csindex.com.cn/csindex-home/index/weight/top10new/{PRICE_CODE}`
- 中证一级行业：`https://www.csindex.com.cn/csindex-home/index/weight/industry-weight-two-new/{PRICE_CODE}?cicsType=1`
- 样本特征：`https://www.csindex.com.cn/csindex-home/indexInfo/index-feature/{PRICE_CODE}`

引用结构时必须写明接口的 `updateDate`。若指数单张日期早于网页/API，以较新的官方结构接口回答“最新结构”，并明确单张与接口的日期差异。前十大接口通常直接给出 `top5Sum` 和 `top10Sum`，优先引用官方汇总字段而非手算。

## 5. 输出核验清单

- 只列中证指数官网及其官方 OSS 域名链接。
- 每项规则尽可能附现行方案的短原文，不用二手释义替代证据。
- 给出样本数、加权、全部明确上限、调样频率及实施日。
- 给出价格代码、全收益代码、基日/基点、发布日期。
- 给出编制方案 PDF、有效的指数单张 PDF、历史 JSON 和可选 Excel 导出接口。
- 对无效或未验证的附件明确标注，不把“资料清单存在”写成“文件可下载”。
- 最新行业与前十大统一使用同一更新日；若无法统一，分别标日期。
- 用户要求不修改文件时，仅在临时目录做下载/解析，不写入项目工作区。