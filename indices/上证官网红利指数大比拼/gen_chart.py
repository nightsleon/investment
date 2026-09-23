import csv, os, glob
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

data_dir = os.path.join(os.path.dirname(__file__), "sources/performance-data-30index")

top10 = {
    'H11140': '香港红利',
    '931157': 'SHS红利成长LV',
    '931446': '东证红利低波',
    '930914': '港股通高股息',
    '000151': '上国红利',
    '931233': '港股通央企红利',
    'H30269': '红利低波',
    '000015': '上证红利',
    '000825': '央企红利',
    'H30270': '红利价值',
}

series = {}
for f in glob.glob(os.path.join(data_dir, "*_全收益.csv")):
    basename = os.path.basename(f).replace("_全收益.csv", "")
    code, name = basename.split("_", 1)
    if code not in top10:
        continue
    dates, closes = [], []
    with open(f, encoding='utf-8-sig') as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            d = datetime.strptime(row['日期Date'], '%Y-%m-%d')
            if d >= datetime(2016, 8, 8):
                dates.append(d)
                closes.append(float(row['收盘Close']))
    base = closes[0]
    series[code] = (dates, [c/base*100 for c in closes])

final_vals = {code: vals[-1] for code, (_, vals) in series.items()}
sorted_codes = sorted(top10.keys(), key=lambda c: -final_vals.get(c, 0))

colors = ['#d62728','#1f77b4','#2ca02c','#ff7f0e','#9467bd','#8c564b','#e377c2','#7f7f7f','#bcbd22','#17becf']

plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'PingFang SC', 'Heiti SC']
plt.rcParams['axes.unicode_minus'] = False

fig, ax = plt.subplots(figsize=(14, 7.5))
for i, code in enumerate(sorted_codes):
    dates, vals = series[code]
    total_ret = vals[-1] - 100
    ax.plot(dates, vals, linewidth=0.8, color=colors[i], label=f'{top10[code]}（{total_ret:+.0f}%）')

ax.set_title('红利指数核心前十 全收益走势（2016.8—2026.8）', fontsize=14, pad=12)
ax.set_ylabel('全收益指数（起点=100）', fontsize=11)
ax.axhline(y=100, color='gray', linestyle='--', linewidth=0.5, alpha=0.5)
ax.grid(True, alpha=0.3)
ax.legend(loc='upper left', fontsize=9, framealpha=0.9)
ax.xaxis.set_major_locator(mdates.YearLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
ax.set_xlim(datetime(2016, 8, 8), datetime(2026, 8, 7))
plt.tight_layout()

out = os.path.join(os.path.dirname(__file__), "01_主报告/核心前十全收益走势.png")
plt.savefig(out, dpi=150, bbox_inches='tight')
print(f"Saved: {out}")
