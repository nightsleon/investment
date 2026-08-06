# 官网资料归档说明

本目录以指数公司官网资料为主；ETF代理数据单独归档并明确限制，按资料用途分类：

- `index-methodologies/`：指数编制方案
- `index-factsheets/`：当前指数单张；旧快照移入 `archive/`
- `performance-data/`：官网原始 XLS、官网接口数据整理的 CSV，以及统一复算指标
- `etf-position-proxy/`：跟踪ETF披露的历史前十大持仓，仅作为指数结构的代理线索
- `etf-hisotry-price/`：ETF行情元数据、前复权价格、持仓阶段收益回撤，以及复权净值对全收益指数的跟踪差复算（目录沿用现有拼写）

## 中证指数资料

| 主指数 | 全收益指数 | 编制方案 | 指数单张 | 行情接口 |
|---|---|---|---|---|
| 中证红利低波动（H30269） | H20269 | [官网 PDF](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/H30269_Index_Methodology_cn.pdf) | [官网 PDF](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/H30269factsheet.pdf) | `https://www.csindex.com.cn/csindex-home/perf/index-perf?indexCode=H20269&startDate=20160630&endDate=20260731` |
| 中证红利（000922） | H00922 | [官网 PDF](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/000922_Index_Methodology_cn.pdf) | [官网 PDF](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/000922factsheet.pdf) | `https://www.csindex.com.cn/csindex-home/perf/index-perf?indexCode=H00922&startDate=20160630&endDate=20260731` |
| 中证红利低波动100（930955） | H20955 | [官网 PDF](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/20231208180204-930955_Index_Methodology_cn.pdf) | [官网 PDF](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/930955factsheet.pdf) | `https://www.csindex.com.cn/csindex-home/perf/index-perf?indexCode=H20955&startDate=20160630&endDate=20260731` |
| 中证全指红利质量（932315） | 932315CNY010 | 本地归档 `932315_中证全指红利质量_编制方案.pdf` | 本地归档 `932315_中证全指红利质量_指数单张.pdf` | `https://www.csindex.com.cn/csindex-home/perf/index-perf?indexCode=932315CNY010&startDate=20160630&endDate=20260731` |
| 中证红利质量（931468） | 921468 | 本地归档 `931468_中证红利质量_编制方案.pdf` | 本地归档 `931468_中证红利质量_指数单张.pdf` | `https://www.csindex.com.cn/csindex-home/perf/index-perf?indexCode=921468&startDate=20160630&endDate=20260731` |
| 上证红利（000015） | H00015 | 本地归档 `000015_上证红利_编制方案.pdf` | 本地归档 `000015_上证红利_指数单张.pdf` | `https://www.csindex.com.cn/csindex-home/perf/index-perf?indexCode=H00015&startDate=20160630&endDate=20260731` |
| 中证沪港深红利成长低波动（931157） | H21157 | 本地归档 `931157_沪港深红利成长低波动_编制方案.pdf` | 本地归档 `931157_沪港深红利成长低波动_指数单张.pdf` | `https://www.csindex.com.cn/csindex-home/perf/index-perf?indexCode=H21157&startDate=20160630&endDate=20260731` |

## 标普道琼斯指数资料

标普官网对 `curl` 和自动化浏览器返回 HTTP 403 `Security Controls Triggered`，但通过本机真实 Chrome 会话可以正常下载。当前目录已保存2026-07-31官网指数单张和近十年原始 XLS；此前使用的 Wayback Machine 历史单张已移入 `index-factsheets/archive/`，不再作为文章风险数据来源。

| 指数 | 编制方案 | 指数单张 | 说明 |
|---|---|---|---|
| 标普中国A股大盘红利低波50 | [标普官网编制方案](https://www.spglobal.com/spdji/en/documents/methodologies/methodology-sp-low-volatility-high-dividend-indices.pdf) | [标普官网当前单张](https://www.spglobal.com/spdji/zh/idsenhancedfactsheet/file.pdf?calcFrequency=M&force_download=true&hostIdentifier=48190c8c-42c4-46af-8d1a-0cd5db894797&languageId=142&indexId=92372169) | 当前单张截至2026-07-31；近十年原始XLS共2450个交易日，2,819.95→7,543.97 |
| 标普中国A股红利机会 | [标普官网编制方案](https://www.spglobal.com/spdji/en/documents/methodologies/methodology-sp-dividend-opportunities.pdf) | [标普官网当前单张](https://www.spglobal.com/spdji/zh/idsenhancedfactsheet/file.pdf?calcFrequency=M&force_download=true&hostIdentifier=48190c8c-42c4-46af-8d1a-0cd5db894797&languageId=142&indexId=5625463) | 当前单张截至2026-07-31；近十年原始XLS共2450个交易日，12,105.41→29,089.90 |

## 国证指数与深证红利代理数据

- 深证红利（399324）编制方案已归档为 `index-methodologies/399324_深证红利_编制方案.pdf`；指数简介、基日和发布日期来自 `https://www.cnindex.com.cn/index-intro?indexcode=399324`。
- 国证官网公开的399324日行情为价格指数，不包含现金分红再投资；官方接口未找到可核实的全收益序列，因此没有按代码规律猜测全收益代码。
- `399324_深证红利_价格指数_2016-06-30_2026-07-31.csv` 仅作官方行情核对，不进入全收益主比较。
- 深证红利绩效暂用跟踪该指数的红利ETF工银（159905）复权单位净值代理。原始净值归档于 `etf-hisotry-price/159905_历史净值_东方财富_2010-11-05_2026-08-05.json`，统一比较序列为 `399324_深证红利_159905复权净值代理_2016-06-30_2026-07-31.csv`。
- ETF代理已经扣除基金费用，并受跟踪误差影响，不等于官方税前全收益指数；文章只用它判断大致风险收益位置，不把细小差异写成指数精确差距。

## 数据口径

- 数据区间：2016-06-30至2026-07-31。九只指数使用官方人民币全收益序列；深证红利ETF代理为2459个净值日。沪港深红利成长低波动因包含香港市场，共2572个交易日，其余序列交易日数以各自官网实际返回为准。
- 前九只指数CSV保存人民币全收益指数收盘点位，即假设现金分红再投资；两只标普CSV由官网原始XLS无损整理而来，原始XLS同时保留。深证红利单列为ETF复权净值代理。
- 年化收益按实际日历天数计算；日频年化波动率按日收益率标准差乘以 `√252`，月频年化波动率按月末收益率标准差乘以 `√12`；最大回撤按日度全收益点位计算。
- 七只中证指数单张的数据日为2026-06-30；文章中的十年区间终点另取官网日度行情2026-07-31。
- 两只标普指数单张的数据日为2026-07-31，近十年XLS与单张同日下载。Prompt 中红利机会的 `yearFlag=oneYearFlag` 已改为 `tenYearFlag` 后下载。
- `scripts/recalculate_index_metrics.py` 统一生成 `复算指标_2016-06-30_2026-07-31.csv`、`稳定性指标_2016-06-30_2026-07-31.csv` 和 `年度收益_2017_2025.csv`；三个文件均覆盖十个比较对象并保留数据口径字段。
- `综合评分_十指数.csv` 保存十只指数的规则子项、四个一级维度和总分；`综合评分_八指数.csv` 保留为上一版存档。
