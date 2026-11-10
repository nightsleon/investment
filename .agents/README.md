# Investment 项目 Skills 全景说明与优化方案

本目录（`.agents/skills/`）存放本项目的全部专项技能（Skills）。本文档用平实的语言梳理当前 **19 个 Skill** 的实际功能，并给出逐项精简、合并与架构优化建议（**当前仅作为方案讨论，暂未对各 Skill 进行实质文件改动**）。

---

## 一、 现有 19 个 Skill 功能一览與逐项修改建议

按业务场景，现有的 19 个 Skill 可分为 **个股研究与财报**、**指数与基金研究**、**内容写作与改稿**、**质量校验与工具** 四大类。

### （一）个股研究与财报分析类（6 个，含新建统一主技能）

#### 0. `stock-investment-analysis`（【新建】统一 3R 个股深度投资分析报告）
* **当前规模**：主文件 145 行｜`references/` 2 个文件
* **功能简介**：将原 `investment-analysis-framework`（一手财报精算、现金头寸与图表底座）与 `3r-investment-analysis`（好生意 60 分 + 好管理层 20 分 + 好价格 20 分，固定 28 项评分与决策结构）合二为一的**新一代个股主技能**。每只股票直接输出一份兼具扎实财务核算与 3R 极速决策结构的《3R 投资分析报告》，消除维护两套 100 分制报告的内耗。
* **当前状态**：已新建落盘，待实测验收通过后，可直接替代下方的 `investment-analysis-framework` 与 `3r-investment-analysis`。

#### 1. `investment-analysis-framework`（旧版完整个股深度报告，待验收后退役）
* **当前规模**：主文件 359 行｜`references/` 33 个文件｜`scripts/` 2 个脚本
* **功能简介**：用于撰写完整的个股深度投资分析报告。采用 100 分制（好行业 20 分 + 好公司定性 20 分 + 好公司定量 40 分 + 好时机 20 分），从公司画像、能力圈与排雷开始，逐章分析商业模式、竞争格局、六年财务数据、彼得林奇现金头寸、历史估值分位与保守/中性毛估估，最后给出胜率赔率结论与证伪条件。
* **存在问题**：
  1. `references/` 堆积了 33 个文件，其中包含大量后来已独立成专门 Skill 的旧文档（如财报速览 `earnings-quick-review.md`、红利指数对比 `dividend-low-volatility-index-analysis.md`、蛋卷估值接口、平台文章改写指南，以及旧版全量备份 `legacy-skill-full-2026-06-29.md`），容易与独立 Skill 产生双口径冲突。
  2. 20 多个单家公司案例（五粮液、汾酒、福耀、珀莱雅、东阿阿胶等）与核心方法论平铺混放在一起，导致主文件末尾的路由表长达 60 多行。
  3. 内置的 `scripts/a-share-generate-charts.py` 与 `stock-earnings-line` 脚本重复。
* **修改建议【简化清理】**：
  * 删除已独立为专门 Skill 的 5 个冗余 reference 文件和 `legacy-skill-full` 历史备份；
  * 将单家公司的案例文件统一收拢到 `references/cases/` 子目录，主文件路由表精简为 8~10 个核心通用方法文件；
  * 移除重复的画图脚本，统一调用 `stock-financial-charts` 和 `stock-earnings-line`。

#### 2. `3r-investment-analysis`（个股 3R 投资分析简报）
* **当前规模**：主文件 132 行｜`references/` 2 个文件｜`scripts/` 3 个脚本
* **功能简介**：输出独立于完整报告的“3R 投资分析简报”，按好生意（Right Business 60 分）、好管理层（Right People 20 分）、好价格（Right Price 20 分）共 28 个固定子项打分，配套固定 4 张核心财务与估值图。支持脱敏证据包盲评（避免受原报告打分干扰）和全库脚本校验。
* **存在问题**：
  * 主文件把“日常单只股票写 3R 简报”和“批量回补时用 3 个隔离评估器跑 JSON 中位数、人工裁决、定点回写旧报告”的批处理工程指令混写在一起，占了近一半篇幅。日常写单篇简报时，这批工程指令属于干扰信息。
* **修改建议【简化主文件】**：
  * 将“多评估器盲评、中位数锁分与 JSON 批量回写”的细则全部移入已有的 `references/blind-evaluation-protocol.md`；
  * 主文件只保留 3R 评分表、单篇写作流程、四张图规范和基础校验，篇幅可压至 70 行左右。

#### 3. `stock-financial-speedread`（A 股/港股单期财报速览，原 `financial-report-speedread`）
* **当前规模**：主文件约 180 行｜`references/` 8 个文件/子目录｜`scripts/` 3 个脚本
* **功能简介**：在单家公司（仅限 A 股和港股）发布季报、中报或年报后，以官方财报 PDF 为唯一数据源，按“四问框架”（赚不赚钱、钱到手没、家底厚不厚、明年还能赚吗）快速拆解核心变化，配套红绿灯速判、16:9 核心业绩看板图和股价 vs 利润 TTM 归一化图，产出面向普通投资者的速览文章。
* **已优化完成**：
  * 重新顺平步骤 1~6 的正文逻辑，把港股 PDF 下载排障、扫描件 OCR 回退链下沉到 `references/pdf_acquisition_and_ocr.md`；
  * 明确与 3R 深度报告的边界，出图逻辑与 `stock-earnings-line` 脚本保持对齐共用。

#### 4. `stock-financial-charts`（个股 3R 好生意定量图表标准，原 `fundamental-quant-charts`）
* **当前规模**：主文件约 180 行｜`scripts/` 1 个脚本
* **功能简介**：为个股 3R 投资分析中「好生意（Right Business）」定量部分生成风格统一的 6 张白底标准图（4.1 ROE与杜邦、4.2 利润增速、4.3 收入结构与增量贡献、4.4 现金流覆盖、4.5 现金头寸与资产负债率、4.6 应收存货合同负债）。
* **已优化完成**：
  * 全面吸收 `stock-earnings-line` 中关于 4.2 利润拆解、4.5 营运质量、4.6 产品结构年度基本面图表的版式标准与低基数处理经验，确立本 Skill 为个股基本面定量图表的唯一事实源。

#### 5. `stock-earnings-line`（个股彼得·林奇收益线分析，原 `quarterly-stock-profit-analysis`）
* **当前规模**：主文件约 105 行｜`references/` 3 个文件｜`scripts/` 2 个脚本
* **功能简介**：基于彼得林奇“收益线”思路，拉取 A 股/港股季度（或半年度）利润数据与前复权股价，计算滚动 TTM 利润，生成“股价 vs 扣非 TTM 利润”双 Y 轴折线图、归一化对比图和单季度季节性图，服务于 3R 报告中「好价格（Right Price）」的匹配度验证。
* **已优化完成**：
  * 彻底清理重复条目、修复代码块未闭合与列表编号错乱；
  * 删除越界的第四章图表内容（归还给 `stock-financial-charts`）与现金头寸重复规则；
  * 主文件从 387 行大幅瘦身至约 105 行，精准聚焦“季度/半年度 TTM 计算 + 股价利润对比图生成”。

---

### （二）指数与基金/ETF 研究类（7 个）

#### 6. `dividend-index-analysis`（红利策略指数质量评价与横评）
* **当前规模**：主文件 216 行｜`references/` 5 个文件｜`scripts/` 1 个脚本
* **功能简介**：专门评估和横向对比红利、高股息、红利低波、红利质量等策略指数本身的质量。采用五维打分框架（规则稳健性 30% + 历史风险收益 25% + 表现稳定性 15% + 结构分散 10% + 证据可信度 20%），重点拆解选样与加权规则、验证长期全收益（TR）表现，严格排除当前估值择时和 ETF 产品层干扰。
* **存在问题**：
  * 主体框架成熟，但 `references/` 中的中证官网接口说明与 `index-performance-backtest`、`fund-etf-selection` 存在多处重复。
* **修改建议【微调简化】**：
  * 保持核心五维评价框架不变；抽离共用的中证官网数据采集说明，减少跨 Skill 重复维护。

#### 7. `index-performance-backtest`（指数 3/5/10 年全收益行情回溯）
* **当前规模**：主文件 343 行｜`references/` 1 个文件｜`scripts/` 3 个脚本
* **功能简介**：对单只或多只指数过去 3 年、5 年、10 年的全收益历史行情进行客观回溯（不评价规则优劣、不打分）。计算年化收益、波动率、最大回撤、修复时间、滚动胜率与牛熊分阶段表现，生成归一化走势图与年度收益热力图，并展示最新前十大权重与行业分布快照。
* **存在问题**：
  * 与 `index-generation-backtrace` 同属“指数全收益客观回溯（不打分）”，两边的数据源、指标定义、回溯标注规则高度重合。
* **修改建议【合并吸收 `index-generation-backtrace`】**：
  * 作为“指数历史行情回溯”的唯一主 Skill，支持两种窗口模式：**模式 A（固定 3/5/10 年窗口）** 与 **模式 B（按基日分代统一起点窗口）**。详见下一条。

#### 8. `index-generation-backtrace`（指数基日分代统一起点回溯）
* **当前规模**：主文件 135 行｜`references/` 2 个文件
* **功能简介**：按指数“基日”划分世代（如 2013 前世代、港股通世代、央企定制世代），在各组内拉齐统一起点回溯全收益表现，并提供“回测光环定量检验（发布前 vs 发布后实盘落差）”、“长短期四象限”、“波动时间结构”等深度分析视角。
* **存在问题**：
  1. **全文是一篇单次会话的复盘备忘录**：大量出现“本会话被用户连续抓错两次”、“本会话真实事故”、“2026-08 会话新增”等对话痕迹；
  2. 内容跨界混杂了“基日分代回溯”、“高回测指数规则打假”、“雪球平台改写格式”、“基金跟踪损耗拆账”四件事，与 `index-performance-backtest`、`dividend-index-analysis`、`fund-tracking-analysis` 边界交错。
* **修改建议【建议合并入 `index-performance-backtest`】**：
  * **取消独立 Skill**；
  * 将“按基日分代统一起点回溯”的方法论清洗掉会话抓错流水账后，连同很有价值的 `references/backtest-halo-and-methodology-quality.md`（回测光环与套壳检验）一起并入 `index-performance-backtest/references/`；
  * 将其中关于“基金表现 = 指数规则 + 跟踪损耗分账”的段落并入基金跟踪 Skill。

#### 9. `fund-performance-analysis`（基金分红再投净值与收益分析）
* **当前规模**：主文件 212 行｜`references/` 2 个文件
* **功能简介**：通过东方财富基金净值接口（`lsjz`）获取单位净值（DWJZ）与分红/分拆事件（FHSP），手工复算分红再投全收益净值（解决行情软件前复权失真和累计净值不含复利的问题），计算跟踪误差并以 512890 为基准进行多基金分组对比。

#### 10. `fund-tracking-analysis`（基金跟踪误差与多基金分组对比）
* **当前规模**：主文件 316 行｜`references/` 0 个文件
* **功能简介**：同样通过东方财富 `lsjz` 接口复算分红再投净值，计算跟踪误差（TE）与累计跟踪差（TD），并以 512890 为基准进行多基金分组（5 年组/3 年组/观察池）对比与可投资性校验。
* **第 9、10 项共同存在的问题**：
  1. **高度重复建设**：两个 Skill 的核心目的、数据接口、正则表达式（`DIVIDEND_RE` / `SPLIT_RE`）、递推公式、甚至反面案例（515300 东财 72% vs 雪球 52%、512890 1拆2分拆）**超过 80% 完全相同**。
  2. **内部规则互相打架**：`fund-performance-analysis` 写的是按“5 年组 / 2 年组”划分；`fund-tracking-analysis` 第 129 行写“默认按 3 年/5 年硬门槛（用户确认偏好）”，但第 246 行“陷阱 6”又写“硬卡 3 年/5 年是陷阱，应按自然断点分组”，第 312 行输出结构又写回“5 年组 / 2 年组”，同一文件前后自相矛盾。
* **第 9、10 项修改建议【强烈建议二合一】**：
  * **将 `fund-performance-analysis` 与 `fund-tracking-analysis` 合并为一个 Skill**（保留 `fund-tracking-analysis` 名称）；
  * 把 `fund-performance-analysis/references/` 下的 2 个文件（港股 ETF 复权口径校验、共同区间截图陷阱）迁入合并后的 Skill；
  * 统一分组口径为最终确认的“5 年组 / 3 年组 / 观察池”，删除自相矛盾的旧陷阱条目，篇幅控制在 180 行左右。

#### 11. `fund-etf-selection`（指数基金与 ETF 综合筛选决策）
* **当前规模**：主文件 156 行｜`references/` 10 个文件
* **功能简介**：用于回答“具体买哪只指数基金/ETF”。把“底层指数质量”和“基金产品外壳（费率、跟踪损耗、规模流动性、场内 ETF vs 场外联接/指数基金）”结合起来，给出最终可投资标的的筛选与排序建议。
* **存在问题**：
  1. 主文件为全英文编写，与项目内其他中文 Skill 风格不统一；
  2. 主文件第 76~81 行又重复写了一遍东方财富 `lsjz` 净值拆分公式；
  3. `references/` 下挂载了 10 个文件，其中 `dividend-low-volatility.md`、`dividend-index-classification.md`、`csi-index-scoring-and-ranking.md` 属于纯指数评价内容，与 `dividend-index-analysis` 重复；`fund-nav-vs-index-comparison.md` 与 `fund-tracking-analysis` 重复。
* **修改建议【简化收敛 + 统一中文】**：
  * 将主文件改为中文，明确其边界为“**从指数到具体基金产品的最后一公里筛选（费率/规模/渠道/同类外壳择优）**”；
  * 净值复算与跟踪误差计算直接引用合并后的 `fund-tracking-analysis`，纯红利指数评分文件归还给 `dividend-index-analysis`，`references/` 从 10 个精简到 4~5 个。

#### 12. `index-valuation-dashboard`（指数估值 HTML 看板生成）
* **当前规模**：主文件 287 行｜`references/` 1 个文件
* **功能简介**：运行 `indices/指数估值/generate.py`，从蛋卷基金接口拉取 11 只宽基、行业、红利及海外指数的 PE/ROE 历史数据，生成带 30/70 分位色带、区间切换按钮的 HTML 估值看板，并同步更新 `docs/` 下的 GitHub Pages 历史归档入口页。
* **存在问题**：
  1. **大量多轮 UI 调试的过渡对话记录未清理**：如第 67~70 行连续记录“入口页导航布局（本轮确认）→ 顶部压缩（本轮新增）→ 文案取舍（本轮新增）→ 极简终态（本轮最终确认）”；第 221~236 行详细介绍“把 `chart-badge` 放进 `chart-top-actions`”，紧接着第 274 行又写“旧方案已废弃：直接删掉 badge”。
  2. **内容完全重复**：第 163~182 行的 `## Pitfalls` 与第 185~215 行的 `## 踩坑记录（必读）` 把同一组问题（Python f-string 生成 JS 语法错误、annotation box 范围、Chart.js canvas 验证）一字不差地写了兩遍。
* **修改建议【大幅简化】**：
  * 删除已被废弃的 `chart-badge` 旧方案、中间态 UI 讨论过程以及重复两遍的踩坑记录，只保留最终生效的页面规范与命令，主文件可从 287 行直接精简至 **120 行以内**。

---

### （三）内容写作与语言改稿类（4 个）

#### 13. `stock-investment-article`（个股“五个选股问题”价值投资文章）
* **当前规模**：主文件约 200 行｜`references/` 1 个文件
* **功能简介**：基于已有的 3R 投资分析报告或个股投研底稿，严格围绕“五个选股问题”（能不能看懂、能不能活得久、利润能不能守得住、能不能高效复利、当前价格买得值不值）加上“增长陷阱与情景估值”，改写为面向雪球、知乎、公众号发布的严谨个股分析长文（默认输出 `_雪球知乎版.md`）。
* **存在问题**：
  * 与上游 `stock-investment-analysis` 形成体系组合，融入四大语言硬招、生意小账本翻译、巴菲特一美元原则与安全边际价格梯队。
* **修改建议【完成重命名与质地重构】**：
  * 从 `investment-article-writing` 更名为 `stock-investment-article`，优化开头模板与文风规范。

#### 14. `business-feature`（商业特稿与商战复盘写作）
* **当前规模**：主文件 104 行｜`references/` 0 个文件（按需查阅项目 `references/大V文章库/`）
* **功能简介**：**带严格显式门禁**——仅在用户明确要求写“商业特稿、特稿、商战复盘、深度商业长文”时调用。以真实微观现场或反常识数据账单破题，拆解单店/单品经济模型（UE）与管理层战略取舍的代价，撰写兼具大众可读性与商业深度的特稿。
* **存在问题**：无。篇幅精炼（104 行）、触发门禁清晰、正反例明确，是项目内 Skill 的标杆结构。
* **修改建议【保持现状】**：无需改动。

#### 15. `financial-humanizer`（财经文本去 AI 味与通俗化改稿）
* **当前规模**：主文件 151 行｜`references/` 0 个文件
* **功能简介**：独立的按需改稿工具（严禁其他写作 Skill 在后台自动嵌套调用）。在严守“三不碰”安全红线（不改财务数字与口径、不删诚实限定语、不弱化投资判断）的前提下，就地剪枝清除公文大词、段首无主语感慨、设问自答与机械排比，把晦涩的研报术语翻译为通俗的生意算账。
* **存在问题**：无。指令可执行性极高，对照示例清晰。
* **修改建议【保持现状】**：无需改动。

#### 16. `video-interview-summary`（商业与投资视频访谈双文档整理）
* **当前规模**：主文件 162 行｜`references/` 0 个文件
* **功能简介**：将 B 站、YouTube 或本地的投资人/企业家访谈音视频，通过提取现成字幕或语音转录（`yt-dlp` + Gemini Flash / Whisper），提炼为“结构化深度商业研报（含 Mermaid 导图与业务语义章节）”和“纯问答对话实录”双文档，统一按 `{人物或公司}` 归档至 `insights/访谈笔记/` 并更新全局研读清单。
* **存在问题**：无。归档路径规范、防 AI 伪深刻红线与执行脚本均已闭环。
* **修改建议【保持现状】**：无需改动。

---

### （四）质量审计与通用工具类（3 个）

#### 17. `article-output-qa`（投资文章机械校验与财报内容审计）
* **当前规模**：主文件 112 行｜`references/` 2 个文件｜`scripts/` 1 个脚本
* **功能简介**：用于投资文章发布前后的质量把关，分三块任务：一是机械校验（运行脚本检查 Markdown 表格列数错位、核对图表截止日与正文数字一致性）；二是对照原始财报 PDF 做内容审计（核查硬错、口径混用、税项/在建工程等附注遗漏）；三是按清单执行限定范围改稿。
* **存在问题**：无。主文件轻量化做得很好，复杂细则均已合理拆分到 `references/`。
* **修改建议【保持现状】**：无需改动。

#### 18. `composite-score-audit`（加权综合评分模型审计与稳健性检验）
* **当前规模**：主文件 175 行｜`references/` 4 个文件
* **功能简介**：用于检验任何“多维度加权求和打分”（如指数横评榜、基金排名榜）是否稳健，防止“谁拿第一只是人为设定的权重产物”。核心方法包括：剔除全员同分的零方差死重、合并重复计分项、细分满分封顶档位、以及跑多组权重敏感性测试。
* **存在问题**：
  1. **通用审计方法与红利指数单次项目细节混放**：前半部分“四步审计法”是极佳的通用方法论；但后半部分（第 74~94 行 30 只红利指数 A/H 拆组与负收益年扣分演进、第 111~133 行标普 Factsheet 英文核对与 PDF 单张提取）其实是红利指数项目的专项规则；
  2. 第 108~110 行与第 139~142 行关于“打分表后拆三段解释、配原始数据表”的段落完全重复。
* **修改建议【简化拆分】**：
  * 删除重复段落；
  * 将“标普编制方案与单张不一致核对”、“PDF 单张 Vision 提取”移入 `references/`（或归入 `dividend-index-analysis`）；
  * 主文件只保留通用的“加权评分四步审计 + 权重敏感性测试 + 读者呈现规范”，精简至 90 行左右。

#### 19. `jupyter-live-kernel`（Jupyter 交互式 Python 内核）
* **当前规模**：主文件 168 行｜`references/` 0 个文件
* **功能简介**：从外部开源仓库（`hamelnb`）引入的通用英文工具 Skill，用于在本地启动 JupyterLab 并保持跨步骤的 Python 变量状态。
* **存在问题**：
  * 依赖外部未安装的 `~/.agent-skills/hamelnb` 路径和旧版 Hermes Agent 的 `execute_code` 概念；且本项目所有投研计算均采用“独立 Python 脚本落盘至 `scripts/` + 生成 CSV/PNG 工件”的可复现模式，日常根本不使用该 Skill。同目录下的 `.agents/skills/DESCRIPTION.md` 也是当时遗留的无用说明文件。
* **修改建议【建议移除】**：
  * 直接移除 `jupyter-live-kernel` 目录及 `.agents/skills/DESCRIPTION.md`，减少系统每次加载可用 Skill 列表时的上下文噪音。

---

## 二、 整体架构优化总览表

若按上述建议执行优化（含以 `stock-investment-analysis` 统一替代原有两套个股报告 Skill），项目 Skill 总数将从 **19 个精简为 15 个**，消除全部功能撞车与双评分体系内耗：

| 类别 | Skill 名称 | 优化动作 | 核心调整内容 |
| :--- | :--- | :---: | :--- |
| **个股与财报** | **`stock-investment-analysis`** | **已新建（二合一）** | 统一采用 3R（60/20/20，28项指标）标准，融合一手财报核算、现金头寸精算与 4 张标准图，每只股票只出一份报告 |
| | ~~`investment-analysis-framework`~~ | **待实测后合并退役** | 核心财务精算与排雷规则已并入 `stock-investment-analysis`；待新 Skill 测试通过后归档或删除 |
| | ~~`3r-investment-analysis`~~ | **待实测后合并退役** | 28 项 3R 评分表与报告骨架已并入 `stock-investment-analysis`；待新 Skill 测试通过后归档或删除 |
| | `stock-financial-speedread` | **已简化优化** | 原 `financial-report-speedread`；顺平步骤 1~6 流程，PDF/OCR 排障移入 `references/`，与 `stock-earnings-line` 共用出图脚本 |
| | `stock-financial-charts` | **已吸收统一** | 原 `fundamental-quant-charts`；吸收越界的 4.2/4.5/4.6 画图规则，作为 3R 好生意定量图表唯一标准 |
| | `stock-earnings-line` | **已重写精简** | 原 `quarterly-stock-profit-analysis`；修复代码块与序号，剔除越界内容与重复规则，从 387 行压至 ~105 行，聚焦彼得林奇收益线 |
| **指数与基金** | `dividend-index-analysis` | **微调** | 抽离共用的中证官网接口说明，保留红利规则拆解与五维评分核心 |
| | `index-performance-backtest` | **合并保留** | 吸收 `index-generation-backtrace`，统一负责指数全收益客观回溯（支持固定 3/5/10Y 与基日分代双模式） |
| | ~~`index-generation-backtrace`~~ | **被合并** | 清洗掉单次会话抓错流水账后，作为“基日分代模式”与“回测光环检验”并入 `index-performance-backtest` |
| | `fund-tracking-analysis` | **合并保留** | 吸收 `fund-performance-analysis`，统一负责基金分红再投净值复算、跟踪误差（TE/TD）与多基金分组对比 |
| | ~~`fund-performance-analysis`~~ | **被合并** | 与 `fund-tracking-analysis` 80% 内容重复，将其 `references/` 迁入后者后移除独立目录 |
| | `fund-etf-selection` | **简化转中** | 统一为中文，聚焦“指数+基金外壳”最终选品决策，剔除与纯指数打分、净值复算重复的 5 个 reference |
| | `index-valuation-dashboard` | **大幅简化** | 删掉已废弃的旧版 badge 方案、多轮 UI 过程记录及重复两遍的 Pitfalls，从 287 行压至 ~110 行 |
| **内容与改稿** | `stock-investment-article` | **体系命名与质地重构** | 原 `investment-article-writing`，与上游 `stock-investment-analysis` 呼应；融入四大反AI硬招与安全边际价格梯队 |
| | `business-feature` | **保持现状** | 104 行标杆结构，门禁与文风规范清晰，无需改动 |
| | `financial-humanizer` | **保持现状** | 151 行独立按需改稿工具，边界与红线清晰，无需改动 |
| | `video-interview-summary` | **保持现状** | 162 行双文档转录与归档流程清晰，无需改动 |
| **审计与工具** | `article-output-qa` | **保持现状** | 112 行机械校验与财报内容审计网关，主次分明，无需改动 |
| | `composite-score-audit` | **简化** | 删除重复段落，将标普单张核对等专项规则移入 `references/`，主文件只留通用四步审计法 |
| | ~~`jupyter-live-kernel`~~ | **移除** | 外部引入的闲置工具，不符合项目脚本落盘规范，建议连同 `DESCRIPTION.md` 一并移除 |

---

## 三、 跨 Skill 共性问题与长期维护建议

在盘点全部 19 个 Skill 的过程中，发现有 4 个共性问题最影响大模型的执行稳定性，建议后续修订时作为统一准则：

1. **禁止把“单次会话的 Debug 流水账”直接追加进 `SKILL.md`**
   * **典型症状**：`index-generation-backtrace`、`index-valuation-dashboard`、`composite-score-audit` 中存在大量“本会话被用户抓错两次”、“第一版方案已废弃，本轮最终确认改为……”的过程性记录。
   * **危害**：模型读取 `SKILL.md` 时，既看到了旧错方案，又看到了新方案，极易被前面大段的旧方案代码带偏。
   * **规范**：迭代 Skill 时永远采用**状态覆盖（State Overwrite）**而非**日志追加（Log Append）**——只写最终生效的正确规则，直接删掉被推翻的旧方案。
2. **消除“同一公式/脚本在多个 Skill 中复制粘贴”**
   * **典型症状**：
     * 东方财富基金分红再投净值公式在 `fund-performance-analysis`、`fund-tracking-analysis`、`fund-etf-selection` 写了 3 遍；
     * 港股/A股季度“股价 vs 利润 TTM”画图脚本在 `stock-earnings-line` 与 `stock-financial-speedread` 共用；
     * 彼得林奇现金头寸公式统一在 `stock-investment-analysis` 维护。
   * **规范**：每个核心计算或画图逻辑只在一个主责 Skill 中定义并维护脚本，其他 Skill 通过一句话引用该脚本路径，杜绝多处改、多处漏。
3. **主文件（`SKILL.md`）严格控制在 100~200 行以内**
   * `business-feature`（104 行）、`article-output-qa`（112 行）、`financial-humanizer`（151 行）之所以触发准、执行稳，核心在于主文件只保留**触发边界 + 核心工作流 + 硬红线清单**；把特定行业案例、API 字段字典、长篇排查手册放到 `references/` 按需读取。
4. **统一语言与 Frontmatter 规范**
   * 除移除 `jupyter-live-kernel` 外，将 `fund-etf-selection`、以及部分英文 `description`（如 `composite-score-audit`、`index-performance-backtest`）统一改为精准的中文描述，并在 `description` 中明确写出“什么场景用、什么场景不用”，提升路由分流的准确率。
