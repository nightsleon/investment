# A股红利类指数大比拼

对A股市场主流红利类指数进行系统性横向对比的研究项目，覆盖收益、风险、持仓结构、编制规则四个维度。

## 快速入口

| 文档 | 说明 |
|---|---|
| [01_主报告/A股红利类指数大比拼_十指数.md](01_主报告/A股红利类指数大比拼_十指数.md) | 完整版主报告：十只指数横向对比，含收益/风险/持仓/规则/综合评分 |
| [01_主报告/A股红利类指数大比拼.md](01_主报告/A股红利类指数大比拼.md) | 初版（五指数精简版） |
| [02_单基金深度/](02_单基金深度/) | 单只ETF持仓变迁深度分析（4篇） |

## 覆盖指数

- **中证系列**：中证红利、中证红利低波动、中证红利低波动100、中证红利质量、中证全指红利质量、上证红利、沪港深红利成长低波动
- **标普系列**：标普中国A股大盘红利低波50、标普中国A股红利机会
- **深证系列**：深证红利（ETF净值代理）

## 目录结构

```
A股红利指数大比拼/
├── 00_研究草案/          # 写作prompt、草稿
├── 01_主报告/            # 指数横向对比主报告
├── 02_单基金深度/        # 单只ETF持仓变迁分析
├── charts/
│   ├── summary/          # 多指数汇总对比图
│   └── etf/              # 单ETF独立图表（按代码分子目录）
├── scripts/
│   ├── collect/          # 数据采集脚本（跟踪差、持仓、基本面）
│   ├── chart/            # 图表生成脚本（走势、热力图、行业构成）
│   └── score/            # 评分复算脚本（指标、V4评分）
└── sources/              # 原始数据与官网资料归档
    ├── index-methodologies/  # 指数编制方案PDF
    ├── index-factsheets/     # 指数单张（PDF + png/子目录存导出图）
    ├── performance-data/     # 全收益行情CSV、指标复算结果、评分表
    ├── etf-history-price/    # ETF历史净值、前复权价格、跟踪差
    └── etf-position-proxy/   # ETF前十大持仓历史（作为指数结构代理）
```

## 数据口径

- 比较区间：2016-06-30 至 2026-07-31
- 基准：各指数人民币全收益序列（分红再投资）
- 深证红利因无公开全收益数据，使用 159905 复权净值代理
- 统一复算脚本：`scripts/score/recalculate_index_metrics.py`
- 详细口径见 [sources/README.md](sources/README.md)

## 复跑说明

```bash
# 1. 复算收益/风险/稳定性指标 → 输出到 sources/performance-data/
python scripts/score/recalculate_index_metrics.py

# 2. 生成V4综合评分
python scripts/score/v4_score_rebuild.py

# 3. 生成汇总图表
python scripts/chart/generate_5index_trend_chart.py
python scripts/chart/generate_6index_heatmap.py
```
