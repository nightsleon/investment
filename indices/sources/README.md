# 指数与基金公共数据底座 (Common Investment Sources)

本目录为 `indices/` 体系下的跨项目公共数据底座，为各研究专题（包括《红利ETF五周年实盘大决战》、《上证官网红利指数大比拼》、《红利低波优选》、《指数估值》等）提供唯一标准的数据事实来源（Source of Truth）。

---

## 一、 目录分类与数据资产清单

```text
indices/sources/
├── index-methodologies/       # ① 指数编制方案 PDF (42 份官方规则存档)
├── index-factsheets/          # ② 指数官方 Factsheet 单页与月报
├── fund-nav-correct/          # ③ 核心实盘日线底座：手工复算分红再投净值 (CSV/JSON)
├── performance-data/          # ④ 指数全收益历史日线 (官方 Total Return 系列)
├── performance-data-30index/  # ⑤ 30 只主流红利指数全收益日线与全指标库
├── holdings-30index/          # ⑥ 30 只红利指数历史成分股与权重明细
├── etf-position-proxy/        # ⑦ 重点 ETF 历季穿透持仓、行业暴露与盈利分红
├── excel-30index/             # ⑧ 中证官网原始导出的 30 指数历史数据 XLS/XLSX
├── track-funds/               # ⑨ 指数对应场内 ETF / 场外基金跟踪产品映射表
└── etf-history-price/         # ⑩ 场内 ETF 交易价格、折溢价与跟踪误差复算
```

---

## 二、 核心数据资产详解与数据口径

### 1. `index-methodologies/`（编制方案库）
- **定位**：判断指数“底层逻辑、选样漏斗、加权规则、行业约束”的唯一最高准则。
- **覆盖范围**：
  - 中证指数：中证红利低波动（H30269）、中证红利（000922）、红利低波100（930955）、中证红利质量（931468/932315）、300红利低波（930740）等；
  - 上证/深证：上证红利（000015）、深证红利（399324）、央企红利（000825）、国企红利（000824）等；
  - 标普道琼斯：标普中国A股大盘红利低波50、标普中国A股红利机会（官方中英文方案）；
  - 港股通及境外：香港红利（H11140）、港股通高股息（930914）、中华预期高股息（CESFHY）等。
- **使用规范**：凡涉及指数选样步骤与加权系数，必须逐字核对本目录对应 PDF，严禁依赖第三方研报或网络二手概括。

### 2. `fund-nav-correct/`（分红再投真净值底座）
- **定位**：全市场基金实盘评估的统一净值基准。
- **口径定义**：
  $$\text{财富指数}_t = \text{财富指数}_{t-1} \times \frac{\text{单位净值}_t \times \text{拆分比例}_t + \text{现金分红}_t}{\text{单位净值}_{t-1}}$$
- **字段规范**：`date,unit_nav,cumulative_nav,reinvested_nav,dividend,split_ratio,event_note`
- **严禁事项**：严禁直接采用证券行情软件的“前复权价格”或“累计净值”直接计算区间收益率，以消除除权失真与市场情绪带来的场内折溢价杂音。

### 3. `performance-data/` & `performance-data-30index/`（指数全收益序列）
- **定位**：评价指数原生策略表现及测算 ETF 跟踪误差/超额收益的法定基准。
- **口径**：人民币全收益收盘指数（Total Return，包含成分股税后分红再投资），包含中证 H 系列、标普 Total Return 系列。

### 4. `holdings-30index/` & `etf-position-proxy/`（持仓与行业穿透）
- **定位**：持仓结构与收益归因数据。
- **应用场景**：解析“为什么某年在特定市场风格下某只 ETF 大胜/大败”（例如 2024 年大盘高股息行情中 512890 凭借 53.6% 金融高权重胜出，而 515100 因单票 5% 限制及 100 只中小盘分散而落后）。

---

## 三、 配套公共工具链 (`indices/scripts/`)

为保证跨专题指标口径绝对一致，公共工具链统一置于 `indices/scripts/`：

1. **`indices/scripts/metrics/metrics.py`**：
   - 包含 CAGR、历史最大回撤及发生区间、年化下行标准差、卡玛比率、分年度收益等标准量化函数；
   - 支持命令行直接对比任意两只基金：
     ```bash
     python3 indices/scripts/metrics/metrics.py 512890 515100
     ```

2. **`indices/scripts/collect/collect_fund_nav_correct.py`**：
   - 通用采集接口，从东方财富抓取指定基金完整历史净值与分红拆分事件，自动复算并增量写入 `fund-nav-correct/`：
     ```bash
     python3 indices/scripts/collect/collect_fund_nav_correct.py <代码> <名称>
     ```

---

## 四、 架构与数据访问规范

为保证数据资产的绝对纯洁与单一真实来源（Single Source of Truth），本项目采取严格的物理分层架构：
1. **统一公共底座**：所有权威原始数据（中证/标普编制方案 PDF、指数 Factsheet、全收益行情日线、手工复算分红再投净值 CSV、跟踪映射字典 JSON 等）全量存放于本公共目录 `indices/sources/`，不设立任何软链接（symlink）；
2. **子专题轻量穿透**：各子专题目录（如 `01_红利低波优选`、`02_上证官网红利指数大比拼`、`红利ETF五周年实盘大决战` 等）只保留专属的研究报告、专属图表、私有佐证素材及输出结果；
3. **路径调用约定**：
   - Markdown 文档通过相对路径向上穿透引用公共底座（例如 `../../../sources/index-methodologies/...`）；
   - Python 脚本统一通过 `BASE.parent.parent / "sources"` 或项目根穿透锚定，保证随时随地可独立复现。
