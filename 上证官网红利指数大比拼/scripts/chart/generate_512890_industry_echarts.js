#!/usr/bin/env node
/**
 * 使用 ECharts 生成季度前十大行业构成图。
 * 运行前：npm install --prefix /tmp/hermes-echarts-render echarts@6.1.0
 * 运行：NODE_PATH=/tmp/hermes-echarts-render/node_modules node scripts/generate_512890_industry_echarts.js
 */

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');
const echarts = require('echarts');

const base = path.resolve(__dirname, '..');
const source = path.join(base, 'sources', 'etf-position-proxy', '512890', '512890_前十大持仓行业构成.csv');
const outputDir = path.join(base, 'charts', '512890');
const svgPath = path.join(outputDir, '季度前十大行业构成.svg');
const pngPath = path.join(outputDir, '季度前十大行业构成.png');

fs.mkdirSync(outputDir, { recursive: true });

const lines = fs.readFileSync(source, 'utf8').replace(/^\uFEFF/, '').trim().split(/\r?\n/);
const headers = lines[0].split(',');
const rows = lines.slice(1).map(line => {
  const values = line.split(',');
  return Object.fromEntries(headers.map((header, index) => [header, values[index]]));
});

const periods = [...new Set(rows.map(row => row['报告期']))].sort();
const categories = ['基建', '周期', '金融', '制造', '消费', '其他'];
const values = Object.fromEntries(categories.map(category => [category, Object.fromEntries(periods.map(period => [period, 0]))]));

for (const row of rows) {
  const industry = categories.includes(row['同花顺行业大类']) && row['同花顺行业大类'] !== '其他'
    ? row['同花顺行业大类']
    : '其他';
  values[industry][row['报告期']] += Number(row['前十大中占比(%)']);
}

const quarterLabel = period => `${period.slice(0, 4)}Q${Math.floor((Number(period.slice(4, 6)) - 1) / 3) + 1}`;
const labels = periods.map(quarterLabel);
const palette = {
  基建: '#5B84B1',
  周期: '#F28E2B',
  金融: '#8064A2',
  制造: '#63A35C',
  消费: '#E4686A',
  其他: '#9AA0A6',
};

const latestPeriod = periods[periods.length - 1];
const latestText = categories
  .filter(category => values[category][latestPeriod] > 0)
  .map(category => `${category} ${values[category][latestPeriod].toFixed(1)}%`)
  .join('   ');

const chart = echarts.init(null, null, {
  renderer: 'svg',
  ssr: true,
  width: 2400,
  height: 1100,
});

chart.setOption({
  backgroundColor: '#FFFFFF',
  animation: false,
  color: categories.map(category => palette[category]),
  textStyle: {
    fontFamily: 'PingFang SC, Hiragino Sans GB, sans-serif',
    color: '#374151',
  },
  title: {
    left: 70,
    top: 24,
    text: '季度前十大行业构成',
    subtext: '季度原始数据，曲线仅作平滑连接｜医疗、科技合并为“其他”｜非完整ETF行业权重',
    textStyle: { fontSize: 36, fontWeight: 600, color: '#111827' },
    subtextStyle: { fontSize: 21, color: '#6B7280', lineHeight: 34 },
    itemGap: 12,
  },
  legend: {
    top: 40,
    right: 70,
    itemWidth: 38,
    itemHeight: 18,
    itemGap: 30,
    textStyle: { fontSize: 21, color: '#374151' },
    data: categories,
  },
  grid: {
    left: 105,
    right: 65,
    top: 165,
    bottom: 90,
  },
  xAxis: {
    type: 'category',
    boundaryGap: false,
    data: labels,
    axisLine: { lineStyle: { color: '#C7CED8' } },
    axisTick: { show: false },
    axisLabel: {
      color: '#6B7280',
      fontSize: 19,
      margin: 18,
      showMaxLabel: true,
      hideOverlap: false,
      formatter: value => {
        if (value === labels[labels.length - 1]) return value;
        if (value === '2026Q1') return '';
        return value.endsWith('Q1') ? value : '';
      },
    },
  },
  yAxis: {
    type: 'value',
    min: 0,
    max: 100,
    interval: 20,
    name: '前十大内部占比（%）',
    nameLocation: 'middle',
    nameGap: 70,
    nameTextStyle: { color: '#4B5563', fontSize: 21 },
    axisLabel: { color: '#6B7280', fontSize: 19 },
    axisLine: { show: false },
    axisTick: { show: false },
    splitLine: { lineStyle: { color: '#E7EBF0', width: 1.2 } },
  },
  tooltip: {
    trigger: 'axis',
    valueFormatter: value => `${Number(value).toFixed(1)}%`,
  },
  graphic: [
    {
      type: 'text',
      right: 70,
      top: 132,
      style: {
        text: `最新原始值：${latestText}`,
        font: '20px PingFang SC, Hiragino Sans GB, sans-serif',
        fill: '#374151',
        backgroundColor: 'rgba(255,255,255,0.90)',
        padding: [7, 10],
      },
    },
  ],
  series: categories.map(category => ({
    name: category,
    type: 'line',
    stack: '总量',
    smooth: 0.3,
    smoothMonotone: 'x',
    symbol: 'none',
    showSymbol: false,
    lineStyle: { width: 1.5, color: palette[category] },
    areaStyle: { opacity: 0.88, color: palette[category] },
    emphasis: { focus: 'series' },
    data: periods.map(period => Number(values[category][period].toFixed(2))),
  })),
});

fs.writeFileSync(svgPath, chart.renderToSVGString(), 'utf8');
chart.dispose();

const conversion = spawnSync('rsvg-convert', ['-w', '2400', '-h', '1100', '-o', pngPath, svgPath], { encoding: 'utf8' });
if (conversion.status !== 0) {
  process.stderr.write(conversion.stderr || 'rsvg-convert failed\n');
  process.exit(conversion.status || 1);
}

console.log(JSON.stringify({ svg: svgPath, png: pngPath, periods: periods.length, categories }, null, 2));
