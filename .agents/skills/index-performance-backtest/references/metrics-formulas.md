# 指标计算公式与口径细则

主 skill 是执行控制器；需要确认公式细节、口径选择或复核计算结果时加载本参考。

## 一、收益类指标

### 累计全收益

```
累计全收益 = 期末点位 / 期初点位 - 1
```

最直观的终值比较，但受区间长度影响，不同年限不能直接比。

### 精确年化收益（CAGR）

```
CAGR = (期末点位 / 期初点位) ^ (365.2425 / 实际天数) - 1
```

- 按实际日历天数计算，不按整数年近似。
- 365.2425 是格里高利历平均年长（含闰年修正）。
- 不要把 10.08 年按整 10 年算。

### 年度收益

每个自然年最后一个交易日点位：

```
年度收益_y = 年末点位_y / 上年末点位_(y-1) - 1
```

- 首尾不完整年度不进入"完整年度胜率"，可单列展示。
- 完整年度 = 该年度在回溯区间内有完整的12个月交易日。

## 二、风险类指标

### 年化波动率

日频：

```
日收益率 r_t = ln(P_t / P_{t-1})
日频年化波动 = std(r_t, ddof=1) × √252
```

月频：

```
月末收益率 r_m = P_m / P_{m-1} - 1
月频年化波动 = std(r_m, ddof=1) × √12
```

- 对数收益率和简单收益率长期差异很小，但必须统一选择一种。
- √252 对应约252个交易日/年，√12 对应12个月。
- 跨指数比较必须统一频率（日频或月频）和样本区间。
- 隐含假设：每日收益独立同分布。实际有波动率聚集现象，年化只是近似。

### 最大回撤

```
回撤_t = 点位_t / 截至t的历史最高点 - 1
最大回撤 = min(回撤_t)  # 全区间最小值（负数）
```

记录：
- 回撤高点日期：回撤最低点之前的历史最高点日期；
- 回撤低点日期：回撤最深处日期；
- 修复日期：低点之后首次回到前高点的日期；
- 未修复时写"区间末尚未修复"，不留空。

### 回撤修复时间

```
修复天数 = 修复日期 - 回撤低点日期
```

- 修复时间决定了投资者能不能拿得住。
- 长期未修复的回撤对持有体验影响极大。

## 三、风险收益效率

### 收益/波动

```
收益/波动 = CAGR / 年化波动率
```

- 直观效率指标，不是夏普比率。
- 只有没有无风险利率调整时，才能用这个简化形式。

### 夏普比率

```
夏普比率 = (CAGR - 无风险利率) / 年化波动率
```

- 必须统一无风险利率（如用同期一年期国债收益率）。
- 必须统一数据频率。
- 没有统一无风险利率时，只能叫"收益/波动"，不能叫夏普。

## 四、稳定性指标

### 完整年度胜率

```
胜率 = 完整年度正收益次数 / 完整年度总数
```

- 只统计完整年度，排除首尾残年。
- 3年区间可能只有2-3个完整年度，样本量小，胜率参考价值有限。

### 最差年度

```
最差年度 = min(年度收益_y)
```

最差一年什么表现，反映极端情况下的下行风险。

### 滚动收益

取月末点位计算：

```
滚动N年年化 = (当前月末点位 / N年前对应月末点位) ^ (1/N) - 1
```

至少报告：
- 样本数（滚动窗口数量）；
- 正收益占比；
- 中位数；
- 最小值；
- 最大值。

关键提醒：相邻月度滚动窗口高度重叠。

- 滚动5年窗口：相邻窗口共享59个月（60个月中只差1个月）；
- 滚动3年窗口：相邻窗口共享35个月；
- 不能把多个滚动窗口当成多次独立检验。

稳定性评分权重：完整年度 > 滚动3年 > 滚动5年。

## 五、分阶段收益

根据区间内实际市场阶段选取代表性时段：

```
阶段收益 = 阶段末点位 / 阶段初点位 - 1
```

选取原则：
- 结合区间内实际发生的事件，不强套固定模板；
- 每个阶段应有明确的市场环境标签（如"单边下跌""快速反弹""震荡"）；
- 3年区间可能只覆盖1-2个阶段，不强求五段全填；
- 10年区间可以选4-5个阶段做更细致的拆解。

## 六、数据口径对照

| 回报类型 | 分红处理 | 用途 |
|---|---|---|
| Price Return | 不计现金分红再投资 | 仅看价格变动，辅助参考 |
| Total Return (TR) / 全收益 | 通常按税前现金分红再投资 | 长期主比较基准 |
| Net Total Return (NTR) / 净收益 | 按指数规则假设扣税后再投资 | 与TR口径不可混用 |

- 即使都标为NTR，不同指数公司的税率假设也可能不同。
- 小于约1个百分点的差异，在口径无法完全对齐时不要写成显著优势。
- 跨指数比较必须统一币种、日期和回报类型。

## 七、计算脚本核心逻辑

```python
import numpy as np
import pandas as pd

def annualized_return(start_value, end_value, start_date, end_date):
    """精确年化收益，按实际日历天数"""
    return (end_value / start_value) ** (365.2425 / (end_date - start_date).days) - 1

def max_drawdown(series):
    """最大回撤，返回(回撤值, 高点日, 低点日, 修复日)"""
    running_max = series.cummax()
    drawdown = series / running_max - 1
    trough = drawdown.idxmin()
    peak = series.loc[:trough].idxmax()
    recovered = series.loc[trough:][series.loc[trough:] >= series.loc[peak]]
    recovery = recovered.index[0] if len(recovered) else None
    return float(drawdown.loc[trough]), peak, trough, recovery

def annual_volatility_daily(series):
    """日频年化波动率"""
    daily_returns = series.pct_change().dropna()
    return daily_returns.std(ddof=1) * np.sqrt(252)

def annual_volatility_monthly(series):
    """月频年化波动率"""
    monthly = series.resample("ME").last()
    monthly_returns = monthly.pct_change().dropna()
    return monthly_returns.std(ddof=1) * np.sqrt(12)

def rolling_annualized(series, years):
    """滚动N年年化收益"""
    monthly = series.resample("ME").last()
    rolling = (monthly / monthly.shift(12 * years)) ** (1 / years) - 1
    return rolling.dropna()

def annual_returns(series):
    """年度收益，首尾残年需另行排除"""
    year_end = series.resample("YE").last()
    return year_end.pct_change()
```
