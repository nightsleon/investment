---
name: custom-index-valuation
description: "评估在证券行情软件（如同花顺、东财）中无法直观查看 PE/PB 及历史百分位的非标、跨境或策略指数（如标普港股通低波红利、富时中国等）。自动化穿透官方单张 (Factsheet)、动态获取宏观无风险利率 (10Y国债) 与 AH 溢价，通过五维估值框架（税后股息率、股债利差、PB破净深度、AH比价、周期高息过滤）输出红绿灯估值研判。"
version: 1.0.0
author: User + Hermes Agent
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [index, valuation, cross-border, smart-beta, factsheet, dividend, yield-spread]
    related_skills: [dividend-index-analysis, fund-etf-selection, index-valuation-dashboard]
---

# 非标 / 跨境指数估值与时机评估 (Custom Index Valuation)

## 概述与核心痛点

国内主流炒股与基金软件（如同花顺、东方财富、天天基金）的估值系统主要覆盖中证与国证系列指数。一旦遇到**跨境指数（标普/富时/MSCI）、港股特定策略指数或定制 Smart Beta 指数**（例如“标普港股通低波红利指数”），证券 App 通常**只显示二级市场行情点位，完全不提供成分股加权的 PE、PB、股息率及历史百分位走势**，导致投资者陷入估值盲区。

本 Skill 专门解决**“在证券 App 中无法直观获取估值”**的指数研究需求，建立了一套无需依赖付费商业数据终端的**自动化事实抓取、宏观对冲计算与五维估值研判体系**。

---

## 核心架构与三层工作流

```
[指数代码/单张链接]
       │
       ▼
1. 事实数据采集层 (Ingestion)
   ├── 官方单张抓取引擎: scripts/fetch_factsheet.py
   │   └── 依托 Chrome + Finder 原生桥接，绕过 Akamai 403 拦截，拉取官方 Factsheet PDF
   │   └── PyMuPDF 结构化提取: 截至日期、PE(TTM)、预测PE、PB、税前毛股息率、前十大持仓
   └── 宏观基准接口 (无需鉴权):
       ├── 东方财富国债数据中心: 自动拉取中国 10 年期国债收益率 (当前 1.59%)
       └── 腾讯证券行情接口: 自动拉取恒生 AH 股溢价指数 (当前 134 点)
       │
       ▼
2. 非对称五维估值计算层 (Algorithm)
   ├── 维度 1: 真实到手收益率 (港股通扣除 20% 红利税后的 Net DY)
   ├── 维度 2: 国内真实股债利差 (Net DY - 10Y CGB，决定下行托底防守)
   ├── 维度 3: 海外定价股美债利差 (Gross DY - 10Y UST，决定外资进攻弹性)
   ├── 维度 4: 账面资产打折度 (PB 破净深度与 ROE 匹配)
   ├── 维度 5: AH 股同股同权价差比 (AH 溢价折让) 与周期假高息过滤
       │
       ▼
3. 决策研判交付层 (Decision)
   └── 自动输出标准四档评级 (极度低估 🟢 / 合理偏低 🟡🟢 / 估值合理 🟡 / 估值偏高 🔴)
```

---

## 五维估值打分体系与标准标尺（取长补短统一版）

针对缺乏历史估值百分位的指数，采用“绝对现金流硬门槛 + 中美双利差锚定”：

| 维度 | 核心指标 | 🟢 绿灯（极度低估/黄金坑） | 🟡🟢 黄绿（合理中枢/稳健防守）<br>*(当前所处状态)* | 🟡 纯黄（估值合理/正常中枢） | 🔴 红灯（估值偏高/防守观望） |
|---|---|---|---|---|---|
| **1. 真实股息** | 税后净股息率 (Net DY) | **≥ 5.6%**（毛息 ≥ 7.0%） | **4.0% ~ 5.6%**（毛息 5.0%~7.0%） | 3.8% ~ 4.4% | **< 3.8%**（毛息 < 4.8%） |
| **2. 国内利差** | Net DY - 中债10Y (托底) | **≥ 300 BP** (≥ 3.00%) | **≥ 280 BP**（当前 306 BP 极强托底） | 180 ~ 280 BP | **< 150 BP** (< 1.50%) |
| **3. 美债利差** | Gross DY - 美债10Y (弹性) | **≥ 250 BP** (海内外共振) | **< 200 BP**（当前 152 BP 弹性受限） | 100 ~ 180 BP | **< 0 BP** (倒挂) |
| **4. 资产折价** | 市净率 (PB) | **≤ 0.55**（打折 ≥ 45%） | **≤ 0.65**（当前 0.57 深度破净） | 0.65 ~ 0.80 | **≥ 0.80** |
| **5. AH 折价** | 恒生 AH 溢价指数 | **≥ 140 点**（折让 ≥ 28%） | **125 ~ 135 点**（当前 134 点中性常态） | 120 ~ 125 点 | **< 120 点** |

* **评级与实操决策矩阵**：
  * **🟢 绿灯（极度低估 · 海内外共振）**：税后息 ≥ 5.6% 且 美债利差 ≥ 250 BP 且 PB ≤ 0.55。大额分批建仓，历史级赔率；
  * **🟡🟢 黄绿（合理中枢 · 稳健收息防守区）**：**税后息 4.0%~5.6% 且 国内利差 ≥ 280 BP 且 PB ≤ 0.65，但美债利差 < 200 BP**。当前 4.66% 净息、306BP 中债利差、152BP 美债利差精确落在此档。**商业本质：下有极强托底防守，上有离岸估值压制；适合稳健定投收息打底仓，不追高搏暴利**；
  * **🟡 纯黄（估值合理 · 正常中枢）**：处于历史适中中枢，保持常规节奏定投并执行分红再投资；
  * **🔴 红灯（估值偏高 · 吸引力减弱）**：净股息 < 3.8% 或 美债利差倒挂，建议暂停定投、逢高止盈分流。

---

## 工具脚本与命令行调用

技能内置了两个可独立、可组合执行的脚本工具（位于 `scripts/`）：

### 1. 官方单张抓取与解析器 (`fetch_factsheet.py`)
用于从标普等官方网站下载最新 PDF 月报并解析为 JSON。

```bash
# 自动抓取标普港股通低波红利 NTR 单张（摩根 513630 跟踪标的）
.venv/bin/python .agents/skills/custom-index-valuation/scripts/fetch_factsheet.py --index SPAHLVCP_NTR

# 自动抓取 TR 全收益单张
.venv/bin/python .agents/skills/custom-index-valuation/scripts/fetch_factsheet.py --index SPAHLVCP_TR

# 自定义任意标普单张直链
.venv/bin/python .agents/skills/custom-index-valuation/scripts/fetch_factsheet.py --url "<S&P_FACTSHEET_URL>"

# 离线解析已下载的 PDF
.venv/bin/python .agents/skills/custom-index-valuation/scripts/fetch_factsheet.py --pdf-path "indices/sources/index-factsheets/...pdf"
```

### 2. 估值计算与红绿灯判级器 (`evaluate_valuation.py`)
自动调取最新宏观国债与行情，秒级完成五维模型计算与红绿灯输出。

```bash
# 直接读取已解析的 Factsheet JSON 文件进行全自动评估
.venv/bin/python .agents/skills/custom-index-valuation/scripts/evaluate_valuation.py \
  --metrics-json indices/sources/index-factsheets/fs-sp-access-hong-kong-low-volatility-high-dividend-index-cny-ntr_metrics.json

# 手动指定核心指标直接快速测算（适用于其他非标指数）
.venv/bin/python .agents/skills/custom-index-valuation/scripts/evaluate_valuation.py \
  --gross-dy 5.82 --pb 0.57 --pe 8.90 --index-name "富时中国高股息指数"
```

---

## 支撑方法论与事实底座

在输出研究报告与决策时，统一引用以下权威事实源：
1. **官方单张归档**：`indices/sources/index-factsheets/`（月度更新）
2. **标普官方方法论白皮书**：[《驾驭香港市场的股息率》(Navigating Dividend Yield in the Hong Kong Market)](https://www.spglobal.com/spdji/zh/documents/education/education-navigating-divided-yield-in-the-hong-kong-market-zh.pdf)（提供 5.5%~6.5% 历史股息中枢依据）
3. **标普官方编制方案**：[`indices/sources/index-methodologies/methodology-sp-low-volatility-high-dividend-indices-chinese.pdf`](file:///Users/pidan-l/Documents/investment/indices/sources/index-methodologies/methodology-sp-low-volatility-high-dividend-indices-chinese.pdf)
4. **完整评估指南底稿**：[`references/标普港股通低波红利指数估值高低判断指南.md`](file:///Users/pidan-l/Documents/investment/references/标普港股通低波红利指数估值高低判断指南.md)
