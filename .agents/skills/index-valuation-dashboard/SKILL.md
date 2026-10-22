---
name: index-valuation-dashboard
description: 生成指数估值看板 HTML（蛋卷基金数据，含PE/ROE近10年走势图）
trigger: 用户要求生成/更新指数估值看板，或定时任务触发
tools: terminal
---

# 指数估值看板生成器

## 概述
从蛋卷基金 API 抓取 11 个指数的估值快照 + PE/ROE 历史数据，生成带图表的 HTML 看板。

## 执行步骤

1. 运行生成脚本（自动拉数据 + 生成 HTML + Pages 入口页）：
   ```
   python3 indices/指数估值/generate.py
   ```

2. 本地归档输出文件路径格式：
   ```
   indices/指数估值/指数估值看板_YYYY-MM-DD.html
   ```
   数据日期来自蛋卷 API 返回的 `ts` 字段推算，不是生成日期。

3. GitHub Pages 发布目录会同步生成：
   ```
   docs/index.html
   docs/index-valuation/指数估值看板_YYYY-MM-DD.html
   docs/index-valuation-manifest.json
   ```

4. 生成完成后，优先告知用户：
   - 本地归档 HTML 路径
   - Pages 入口页 `docs/index.html` 路径

## 覆盖指数列表
A股宽基: 沪深300(SH000300)、中证1000(SH000852)、科创50(SH000688)
A股行业: 中证白酒(SZ399997)、中证医疗(SZ399989)、主要消费(SH000932)
A股红利: 红利成长LV(CSI931157)、红利低波(CSIH30269)
港股: 恒生科技(HKHSTECH)
美股: 标普500(SP500)、纳指100(NDX)

如需增减指数，编辑 `generate.py` 中的 `INDICES` 列表。

## 页面功能
- 汇总估值表（按类别排序）
- PE百分位 ≥80% 标红，≤20% 标绿；股息率 ≥5% 标绿（含等于）
- PE值和PE百分位同步标红/标绿（两个单元格颜色一致）
- 点击表格行跳转到详情卡片（平滑滚动）
- 每个指数含 PE/ROE 近10年走势图
  - PE图: 30分位以下绿色色带、70分位以上红色色带（annotation box 类型）
  - 分位线加粗+实色白字标签，当前值水平虚线+标注
  - 不要再保留单独的当前PE badge；用户确认这种控件会让头部更乱、收益不高
  - PE 顶部直接用简洁标题承载关键信息：`PE走势（全部）｜91.7%分位`
  - ROE 标题只保留范围，不显示“当前值/百分位”这类信息：`ROE走势（全部）`
  - 时间区间按钮: 1年/3年/5年/全部（即时切换，无需重载），切换后要同步更新顶部标题文案，而不是只换图不换文案
  - 百分比显示必须统一格式化，避免出现 `20.200000000000003%` 这类浮点脏数据
- 文件管理: 同日期覆盖，不同日期保留（按数据日期后缀区分）
- GitHub Pages 入口页: `docs/index.html` 作为统一入口，桌面端内嵌预览，移动端直接跳转归档页
- 日期切换规则: 下拉框列出 `docs/index-valuation/` 下所有归档日期；默认打开最新一期；切换时同步更新 URL 参数 `?date=YYYY-MM-DD`
- 入口快捷导航: 支持“最新一期 / 最早一期 / 当前日期直达 / 上一期 / 下一期”
- 移动端摘要: 归档页顶部增加“低估优先看 / 高估需谨慎 / 高股息”三组摘要卡，点击可跳转到对应指数详情
- 视觉层级: 主看板页应采用白底、弱阴影、弱色带的研究/产品混合风，避免后台工具面板感；优先用 section title 明确分段（快速定位 / 三类重点 / 估值总览 / 指数详情）
- 顶部摘要: 主看板 header 不要用强烈渐变大横幅；改为克制 hero 区，直接给出一句可读摘要（低估机会数 / 高估区间数 / 高股息数 + 代表指数）和 2-3 个 pill 元信息
- 入口页风格: `docs/index.html` 应做成“研究归档首页”而不是工具面板；按钮用圆角 chip / 轻量主按钮
- 入口页导航布局（本轮确认）: 不要把“顺序翻看”做成单独 section。应把“最新一期 / 最早一期 / 当前日期直达 / 上一期 / 下一期”合并到同一个顶部“快捷入口”区域，减少 head 区高度，把更多垂直空间让给下方 iframe 浏览区
- 入口页顶部压缩（本轮新增）: 归档首页要尽量把垂直空间让给 iframe。做法是：1) 把“最新日期 / 当前选择 / 数据源”并进 head 区的小 pill，而不是单独占一行 meta；2) hero/head padding 与字号都收紧；3) iframe 高度可直接提高到类似 `calc(100vh - 170px)`；4) 若用户继续要求更紧凑，优先删除说明段落，只保留标题、信息 pill、日期控件和快捷入口
- 入口页文案取舍（本轮新增）: 当用户明确要求“浏览区域太小”时，优先删说明文字，不要保留“用于统一浏览…”、“按日期进入任一期…”这类解释性段落；只保留标题与控件，信息通过 pill 表达即可
- 入口页极简终态（本轮最终确认）: 如果用户继续要求把浏览区做大，最终优先级是：1) 把顺序翻看并入顶部快捷入口；2) 把“最新日期 / 当前选择 / 数据源”并入 head 内的小 pill；3) 删除说明段落；4) 直接删除整个 hero，让页面从“浏览与切换”开始。也就是说，archive 首页可以完全没有 hero，只保留 head + 快捷入口 + iframe
- 用户审美偏好（本轮确认）: 若用户选择“更像 Linear / Vercel”，优先继续往极简产品风收敛——黑白灰为主、蓝色只作极少量点缀、背景尽量纯白、阴影尽量弱、hover 只保留轻微边框变化/位移，不要再回到强渐变或高饱和 dashboard 风
- 详情卡排版: KPI 区优先用整齐网格（桌面端 6 列、移动端 2 列/1 列），卡片/表格/按钮统一浅边框、浅底色、圆角胶囊标记，减少高饱和蓝紫视觉噪音
- 归档同步规则: 每次生成都会把本地 `指数估值看板_*.html` 同步到 `docs/index-valuation/`，保证旧日期在 Pages 可回看

### 估值总览表格强调样式（重要）
- 不要把红/绿强调直接挂在 `td` 上做整块底色；相邻单元格（如 PE、PE百分位、股息率）会出现“贴连/重叠”的视觉，显得发黏
- 正确做法：`td` 保持中性，只在单元格内部包一个独立的小 badge / pill（例如 `metric-pill red|green`）
- badge 只包真正需要强调的值：PE、PE百分位、股息率；不要把整列背景染色
- 这样既能保留红绿提示，也能让列与列之间自然留白，更接近专业产品表格观感

## 阈值规则
- PE百分位 >= 80% 标红，<= 20% 标绿（含边界值）
- 股息率 >= 5% 标绿（含边界值）
- PE值和PE百分位同步标色

## 图表实现要点

### 分位线：动态计算，跟随时间区间
分位值（30/50/70）必须在 renderPE(yrs) 内按可见数据动态计算，不能用 API 返回的固定值。
```js
function percentile(arr, p) {
  var s = arr.slice().sort(function(a,b){return a-b});
  var i = (s.length-1)*p, lo = Math.floor(i), hi = Math.ceil(i);
  return s[lo] + (s[hi]-s[lo])*(i-lo);
}
// 在 renderPE 内：
var p30v = percentile(d.val, 0.3), p70v = percentile(d.val, 0.7);
```

### 色带：用数据实际范围，不用固定值
annotation box 的 yMin/yMax 必须基于当前可见数据范围，不能写死 0 或 9999。
```js
var dMin = Math.min.apply(null, d.val), dMax = Math.max.apply(null, d.val);
annotations['band_low'] = {type:'box', yMin:dMin*0.85, yMax:p30v, backgroundColor:'rgba(26,157,82,0.07)', borderWidth:0};
annotations['band_high'] = {type:'box', yMin:p70v, yMax:dMax*1.15, backgroundColor:'rgba(217,64,82,0.07)', borderWidth:0};
```

### PE / ROE 顶部信息：直接写进标题，不单独保留 badge
不要再额外放 `chart-badge`。
用户已确认：单独 badge 即使不遮挡按钮，也会增加头部噪音，性价比不高。
应直接把关键信息写进标题，并保持极简：
- PE：`PE走势（全部）｜91.7%分位`
- ROE：`ROE走势（全部）`
- 切换 1年/3年/5年/全部 时，标题中的“范围”必须同步更新
- 只有 PE 需要随区间同步重算并更新分位文案；ROE 不要显示“当前值/百分位”，因为这个指标在这里意义不大
这样能同时满足：
1. 不遮挡按钮
2. 不额外撑高头部
3. 用户一眼看到当前区间关键信息，无需额外读 badge

### 移动端适配（本轮已验证）
- 汇总表必须支持横向滑动：`.table-wrap { overflow-x:auto; -webkit-overflow-scrolling:touch; }`，并给 `table` 设置 `min-width`（当前用 980px）
- 归档页顶部应增加提示文案：告知移动端可左右滑动查看表格
- 归档页应先给“摘要卡”，再给大表：至少输出 3 组卡片（低估优先看 / 高估需谨慎 / 高股息），每组展示 3 个指数，点击跳转到详情锚点
- 图表区在 `max-width:900px` 时改单列，badge 改为 `position:static`，避免遮挡时间按钮
- 时间区间按钮在 `max-width:640px` 时应整行均分，允许换行
- TOC 在窄屏下改成横向可滚动，而不是强行换行挤压
- `docs/index.html` 桌面端可继续内嵌 iframe；移动端（<=900px）应隐藏 iframe，改为“直接打开当前日期归档页”
- 入口页要提供快速导航：最新一期、最早一期、当前日期直达、上一期、下一期；上一期/下一期需根据当前日期动态禁用/启用

### GitHub Pages 发布
如果用户要把 HTML 放到 GitHub 上在线浏览，优先采用 Pages，而不是直接点仓库文件页。

目录约定：
```text
investment/
  docs/
    index.html
    index-valuation/
      指数估值看板_2026-06-01.html
      指数估值看板_2026-05-28.html
    index-valuation-manifest.json
```

做法：
1. 归档页仍保留原始完整 HTML。
2. `docs/index.html` 作为统一入口页，提供日期下拉框。
3. 下拉框来源于 `docs/index-valuation/` 的归档文件清单。
4. 默认打开最新日期；如果 URL 有 `?date=YYYY-MM-DD`，优先打开该日期。
5. 仓库侧开启 GitHub Pages，Source 选当前分支的 `/docs`。

好处：
- 兼顾“最新入口”与“历史归档”
- 不需要把复杂交互逻辑改造成 Markdown
- 用户可直接分享某天的固定链接

## 注意事项
- 蛋卷 API 无需登录（`pe_history` / `roe_history` 是公开接口）
- 每次请求间隔 0.25s 避免被限流
- 脚本约需 10-15 秒完成全部拉取
- 如需定时执行，用 `cronjob` 工具设置 schedule，prompt 中调用此 skill

## Pitfalls

### Chart.js canvas 内容检测
不要用 `getImageData` 检测 Chart.js 渲染的 canvas — 会返回全 0 像素（false negative）。
用 `canvas.toDataURL('image/png').length` 代替，>2000 bytes 即有内容。

### Python f-string 生成 JS 对象的陷阱
f-string 中 `{...}` 生成的 JS 属性（如 `'band_low': {...}`）如果不在赋值语句内，
会被当作裸 label 语句，导致 `SyntaxError: Unexpected token ':'`。
正确写法：`annotations['band_low']={...};`（赋值语句）。
错误写法：直接把 `'band_low': {...},` 嵌入对象字面量外部。

### annotation box 的 yMax/yMin 不要写极端值
`yMax:9999` 或 `yMin:0` 会拉伸 Y 轴，导致分位线挤在底部不可见。
必须用 `Math.min(d.val)*0.85` / `Math.max(d.val)*1.15` 等数据驱动值。

### 文件命名：只覆盖同日期，不删旧文件
输出文件名含数据日期 `指数估值看板_YYYY-MM-DD.html`，每次生成只覆盖同名文件。
- 日期字段: API 返回 `date` 仅含 `MM-DD`，需用 `ts` 字段推算完整日期

## 踩坑记录（必读）

### 1. Python f-string 生成 JS 对象字面量时的语法陷阱
在 Python f-string 中拼接 JS 代码时，如果用字符串拼接往已创建的 JS 对象中"插入"属性，拼接片段会被放置在对象外面，变成裸标签语句（`'key': {...}`），导致 `SyntaxError: Unexpected token ':'`，整个 `<script>` 块中断执行，所有图表不渲染。

**错误写法**（Python）：
```python
boxes = f"""
          'band_low': {{type:'box', yMin:0, yMax:{p30v}, ...}},"""
# 拼入 annotations 对象后，band_low 出现在对象外面
```

**正确写法**：用赋值语句
```python
band_js = f"""
        annotations['band_low']={{type:'box',yMin:0,yMax:{p30v},...}};
        annotations['band_high']={{type:'box',yMin:{p70v},yMax:9999,...}};"""
# 放在 var annotations={{}}; 之后、new Chart() 之前
```

### 2. annotation box 色带：不要用固定 yMin:0 / yMax:9999
固定 `yMin:0` 或 `yMax:9999` 会把 Y 轴拉变形，分位线全部挤在底部。必须用数据实际范围计算：

```js
// 在 renderPE 函数内，拿到过滤后的数据 d 后：
var dMin = Math.min.apply(null, d.val), dMax = Math.max.apply(null, d.val);
annotations['band_low'] = {type:'box', yMin: dMin*0.85, yMax: 30分位值, backgroundColor:'rgba(26,157,82,0.07)', borderWidth:0};
annotations['band_high'] = {type:'box', yMin: 70分位值, yMax: dMax*1.15, backgroundColor:'rgba(217,64,82,0.07)', borderWidth:0};
```

不要用自定义 `beforeDraw`/`afterDraw` 插件做色带，某些浏览器下 canvas 内容被清空。annotation box 类型稳定可靠。

### 3. Chart.js v4 canvas 验证方法
`getImageData()` 在 Chart.js v4 管理的 canvas 上可能返回全零（OffscreenCanvas 机制）。验证图表是否渲染应使用 `toDataURL('image/png')`，非空且 length > 2000 即表示有内容。

### 4. annotation label padding 格式
annotation plugin v3 的 label padding 用数字（`padding: 3`），不要用对象 `{top:2,bottom:2,...}`，某些版本不兼容。

### PE 图顶部布局（新增经验）
- 不要用 `chart-badge { position:absolute }` 直接覆盖图层右上角；它很容易挡住时间区间按钮，尤其是 PE 图右上的“全部”按钮
- 也不要把 badge 放到标题下方再靠 `min-height` 强行对齐；虽然能避免遮挡，但会把 PE 图头部撑高，导致 ROE 图顶部出现明显留白
- 正确做法：把 badge 放进顶部操作区 `chart-top-actions`，与时间按钮同排，结构建议为：
  - 左：`chart-title`
  - 右：`chart-top-actions(badge)` + `range-btns`
- 这样能同时满足 3 个目标：
  1. 不遮挡按钮
  2. PE/ROE 两图画布起点自然对齐
  3. ROE 图不会为了迁就 PE 图而多出一截空白
- 若移动端空间不足，可让 `chart-top-actions` 与 `range-btns` 换行，但仍保持 badge 属于顶部操作区，而不是压到图层上

### 5. chart-badge 遮挡按钮/撑高头部的双重问题
- `position:absolute` 的 badge 容易盖住 PE 图右上角的“全部”按钮
- 把 badge 改到标题下方虽然能避开按钮，但会把 PE 图头部撑高，导致 ROE 图顶部留白、两张图看起来不齐
- 最稳妥的做法不是继续调 `top` 数值，而是改布局：把 badge 放进 `chart-top-actions`，与时间按钮同排，标题单独放左侧

### 标题文案必须跟随时间区间动态更新
不要只在切换按钮时重绘曲线，而让标题仍停留在默认文案。

`renderPE(yrs)` 内在重算可见区间分位后，应同步更新标题节点，例如：
```js
var title=document.getElementById('pe_title_'+sc);
if(title){
  title.textContent='PE走势（'+(yrs?yrs+'年':'全部')+'）｜'+pctInRange.toFixed(1)+'%分位';
}
```

`renderROE(yrs)` 也要同步更新，但只更新范围，不带数值：
```js
var title=document.getElementById('roe_title_'+sc);
if(title){
  title.textContent='ROE走势（'+(yrs?yrs+'年':'全部')+'）';
}
```
如果要做颜色提示，也应直接改标题颜色，不要重新引入单独 badge。

### 百分比格式化必须统一
Chart.js y 轴 tick、tooltip、标题都不要直接拼原始浮点值，否则会出现 `20.200000000000003%`。
统一封装格式化函数：
```js
function fmtNum(v,digits){
  if(v===null||v===undefined||Number.isNaN(Number(v))) return '--';
  return Number(Number(v).toFixed(digits)).toString();
}
function fmtPct(v,digits){ return fmtNum(v,digits)+'%'; }
```
然后：
- y 轴 tick：`callback:function(v){ return fmtPct(v,1) }`
- tooltip：`return 'ROE: '+fmtPct(c.parsed.y,2);`
- PE 标题/文案若含百分比，也统一走这个格式化思路
- ROE 标题不再显示百分比，避免给出意义不大的区间值文案

### 旧方案已废弃：badge 放 chart-top-actions
此前“把 badge 从 absolute 挪到 chart-top-actions”只能解决遮挡问题，仍然保留了额外视觉负担。
本轮用户最终确认：直接删掉 badge，用动态标题替代，更清爽。

### 6. 阈值必须用 >= / <=（包含等于）
用户明确要求包含边界值。PE百分位 `>=80` 标红，`<=20` 标绿；股息率 `>=5` 标绿。表格中 PE 值和 PE 百分位必须同步标色（同一个 `pe_cls`）。

## 脚本架构
- `generate.py`: 单文件，无外部依赖（仅 stdlib）
- 数据层: `fetch_all()` → 快照 + PE/ROE 历史
- 渲染层: `build_html()` → CSS + 汇总表 + 详情卡片 + Chart.js 图表
- 图表JS: 每个指数一个 IIFE，内含 `renderPE(years)` / `renderROE(years)` + 按钮事件绑定
- 分位色带: annotation box 类型，绿色带(0~30分位) + 红色带(70分位~9999)
