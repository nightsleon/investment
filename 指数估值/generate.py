#!/usr/bin/env python3
"""
指数估值看板生成器 v3
数据源: 蛋卷基金 API
输出: 指数估值看板_YYYY-MM-DD.html
"""

import json
import os
import time
import urllib.request
from datetime import datetime

INDICES = [
    ("SH000300",  "A股宽基"), ("SH000852",  "A股宽基"), ("SH000688",  "A股宽基"),
    ("SZ399997",  "A股行业"), ("SZ399989",  "A股行业"), ("SH000932",  "A股行业"),
    ("CSI931157", "A股红利"), ("CSIH30269", "A股红利"),
    ("HKHSTECH",  "港股"),    ("SP500",     "美股"),    ("NDX",       "美股"),
]

API_BASE = "https://danjuanfunds.com/djapi/index_eva"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


def fetch_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    resp = urllib.request.urlopen(req, timeout=20)
    return json.loads(resp.read())


def fetch_all():
    print("[1/3] 拉取估值快照...")
    snap_raw = fetch_json(f"{API_BASE}/dj")
    snap_items = snap_raw["data"]["items"]
    snap_map = {item["index_code"]: item for item in snap_items}
    ts0 = snap_items[0]["ts"] if snap_items else 0
    data_date = datetime.fromtimestamp(ts0 / 1000).strftime("%Y-%m-%d") if ts0 else "unknown"

    history = {}
    codes = [c for c, _ in INDICES]
    total = len(codes)
    print(f"[2/3] 拉取 {total} 个指数的 PE/ROE 历史...")
    for i, code in enumerate(codes, 1):
        name = snap_map.get(code, {}).get("name", code)
        print(f"  ({i}/{total}) {name} ({code})")
        pe_data = fetch_json(f"{API_BASE}/pe_history/{code}?day=all")
        time.sleep(0.25)
        roe_data = fetch_json(f"{API_BASE}/roe_history/{code}?day=all")
        time.sleep(0.25)
        history[code] = {
            "pe": pe_data.get("data", {}).get("index_eva_pe_growths", []),
            "pe_lines": pe_data.get("data", {}).get("horizontal_lines", []),
            "roe": roe_data.get("data", {}).get("index_eva_roe_growths", []),
        }
    print("[3/3] 数据拉取完成。")
    return snap_map, history, data_date


CSS = """\
:root{--bg:#f8f9fb;--card:#fff;--border:#e8ecf1;--text:#1a1d23;--text3:#8b919e;--accent:#4a7cff;--accent-light:#eef3ff;--green:#1a9d52;--green-bg:#e8f7ef;--red:#d94052;--red-bg:#fdf0f1;--orange:#c77c14;--orange-bg:#fdf6e8}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","Segoe UI",sans-serif;background:var(--bg);color:var(--text)}
.header{background:linear-gradient(135deg,#4a7cff 0%,#6c5ce7 100%);color:#fff;padding:36px 32px 28px}
.header h1{font-size:26px;font-weight:700}.header p{opacity:.8;font-size:13px;margin-top:6px}
.container{max-width:1200px;margin:0 auto;padding:0 20px}
.toc{display:flex;flex-wrap:wrap;gap:8px;padding:20px 0 16px}
.toc a{background:var(--card);border:1px solid var(--border);color:var(--accent);padding:6px 14px;border-radius:20px;text-decoration:none;font-size:12px;font-weight:500;transition:all .2s}
.toc a:hover{background:var(--accent);color:#fff;border-color:var(--accent)}
.table-wrap{background:var(--card);border:1px solid var(--border);border-radius:12px;overflow:hidden;margin-bottom:28px;box-shadow:0 1px 3px rgba(0,0,0,.04)}
table{width:100%;border-collapse:collapse;font-size:13px}thead{background:#f5f7fa}
th{padding:12px 10px;text-align:right;font-weight:600;color:var(--text3);font-size:11px;text-transform:uppercase;letter-spacing:.5px;white-space:nowrap}
th:first-child,th:nth-child(2),th:nth-child(3),th:nth-child(4){text-align:left}
td{padding:12px 10px;text-align:right;border-top:1px solid var(--border);white-space:nowrap}
td:first-child,td:nth-child(2),td:nth-child(3),td:nth-child(4){text-align:left}
tr{cursor:pointer;transition:background .15s}tr:hover{background:var(--accent-light)}
.idx-name{font-weight:600}.idx-code{color:var(--text3);font-size:12px}
.eva-low{color:var(--green);font-weight:600}.eva-mid{color:var(--orange);font-weight:600}.eva-high{color:var(--red);font-weight:600}
.val-red{color:var(--red);font-weight:700;background:var(--red-bg);border-radius:4px;padding:2px 6px!important}
.val-green{color:var(--green);font-weight:700;background:var(--green-bg);border-radius:4px;padding:2px 6px!important}
.card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:24px;margin-bottom:20px;box-shadow:0 1px 3px rgba(0,0,0,.04);scroll-margin-top:16px}
.card-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:18px;flex-wrap:wrap;gap:10px}
.card-title{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.card-title h2{font-size:18px;font-weight:700}
.card-code{color:var(--text3);font-size:12px;background:#f0f2f5;padding:2px 8px;border-radius:6px}
.card-cat{color:var(--accent);font-size:11px;background:var(--accent-light);padding:3px 10px;border-radius:10px;font-weight:500}
.card-eva{color:#fff;font-size:12px;padding:4px 14px;border-radius:14px;font-weight:600}
.kpis{display:flex;gap:10px;margin-bottom:20px;flex-wrap:wrap}
.kpi{background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:12px 16px;min-width:110px;flex:1}
.kpi-l{font-size:11px;color:var(--text3);margin-bottom:4px;font-weight:500}.kpi-v{font-size:20px;font-weight:700}
.charts{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.chart-box{background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:16px;position:relative}
.chart-top{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px}
.chart-title{font-size:12px;color:var(--text3);font-weight:600}
.range-btns{display:flex;gap:4px}
.range-btn{border:1px solid var(--border);background:var(--card);color:var(--text3);padding:3px 10px;border-radius:6px;font-size:11px;cursor:pointer;font-weight:500;transition:all .15s}
.range-btn:hover,.range-btn.active{background:var(--accent);color:#fff;border-color:var(--accent)}
.chart-badge{position:absolute;top:42px;right:14px;background:var(--card);border:1px solid var(--border);border-radius:8px;padding:4px 10px;z-index:2;box-shadow:0 2px 8px rgba(0,0,0,.08)}
.badge-val{font-size:15px;font-weight:800;line-height:1.1}.badge-sub{font-size:9px;color:var(--text3);margin-top:1px}
.chart-wrap{height:260px;position:relative}.chart-wrap canvas{width:100%!important;height:100%!important}
@media(max-width:900px){.charts{grid-template-columns:1fr}.kpis{gap:8px}.kpi{min-width:80px;padding:10px 12px}.kpi-v{font-size:16px}}
.footer{text-align:center;padding:24px 0 32px;color:var(--text3);font-size:12px}
"""


def _chart_block(sc, pe_ts, pe_val, roe_ts, roe_val, cur_pe, cur_pe_p):
    """为一个指数生成 PE + ROE 图表的 JS 代码（分位值动态计算）"""

    return f"""
    // ===== {sc} =====
    (function(){{
      var ALL_PE_TS={pe_ts}, ALL_PE_VAL={pe_val};
      var ALL_ROE_TS={roe_ts}, ALL_ROE_VAL={roe_val};
      var curPE={cur_pe:.2f}, curPEP={cur_pe_p:.1f};

      function filterByYears(tsArr,valArr,yrs){{
        if(!yrs) return {{ts:tsArr,val:valArr}};
        var c=Date.now()-yrs*365.25*86400000,ft=[],fv=[];
        for(var i=0;i<tsArr.length;i++){{if(tsArr[i]>=c){{ft.push(tsArr[i]);fv.push(valArr[i]);}}}}
        return {{ts:ft,val:fv}};
      }}
      function fmtTs(ts){{var d=new Date(ts),m=d.getMonth()+1;return d.getFullYear()+'-'+(m<10?'0':'')+m;}}

      // 动态计算分位值
      function percentile(arr, p){{
        var s=arr.slice().sort(function(a,b){{return a-b}});
        var i=(s.length-1)*p, lo=Math.floor(i), hi=Math.ceil(i);
        return s[lo]+(s[hi]-s[lo])*(i-lo);
      }}

      var peChart=null,roeChart=null;

      function renderPE(yrs){{
        var d=filterByYears(ALL_PE_TS,ALL_PE_VAL,yrs);
        var labels=d.ts.map(fmtTs);
        // 按可见数据动态计算分位
        var p30v=percentile(d.val,0.3), p50v=percentile(d.val,0.5), p70v=percentile(d.val,0.7);
        var annotations={{}};
        var pctLines=[
          {{value:p30v,label:'30分位',color:'#07AA31'}},
          {{value:p50v,label:'中位',color:'#666666'}},
          {{value:p70v,label:'70分位',color:'#F0191D'}}
        ];
        pctLines.forEach(function(l,i){{
          annotations['ln'+i]={{
            type:'line',yMin:l.value,yMax:l.value,
            borderColor:l.color,borderWidth:1.5,borderDash:[4,3],
            label:{{display:true,content:l.label+' '+l.value.toFixed(1),position:'start',
              font:{{size:10,weight:'bold'}},backgroundColor:l.color,color:'#fff',
              padding:3,borderRadius:3}}
          }};
        }});
        // 当前值线
        annotations['cur']={{
          type:'line',yMin:curPE,yMax:curPE,
          borderColor:'rgba(80,80,80,0.5)',borderWidth:1,borderDash:[2,2],
          label:{{display:true,content:'当前 '+curPE.toFixed(1),position:'end',
            font:{{size:10}},backgroundColor:'rgba(0,0,0,0.6)',color:'#fff',
            padding:3,borderRadius:3}}
        }};
        // 计算当前PE在可见数据中的百分位
        var belowCount=0;
        for(var i=0;i<d.val.length;i++){{if(d.val[i]<curPE)belowCount++;}}
        var pctInRange=d.val.length>1?(belowCount/(d.val.length-1)*100):curPEP;
        // 更新badge
        var badge=document.getElementById('badge_{sc}');
        if(badge){{
          badge.querySelector('.badge-val').textContent=curPE.toFixed(1);
          var badgeColor=pctInRange<30?'var(--green)':pctInRange>70?'var(--red)':'var(--orange)';
          badge.querySelector('.badge-val').style.color=badgeColor;
          badge.querySelector('.badge-sub').textContent='PE · '+pctInRange.toFixed(1)+'%分位';
        }}
        // 色带
        var dMin=Math.min.apply(null,d.val), dMax=Math.max.apply(null,d.val);
        annotations['band_low']={{type:'box',yMin:dMin*0.85,yMax:p30v,backgroundColor:'rgba(26,157,82,0.07)',borderWidth:0}};
        annotations['band_high']={{type:'box',yMin:p70v,yMax:dMax*1.15,backgroundColor:'rgba(217,64,82,0.07)',borderWidth:0}};
        var ctx=document.getElementById('chart_pe_{sc}').getContext('2d');
        if(peChart)peChart.destroy();
        peChart=new Chart(ctx,{{
          type:'line',
          data:{{labels:labels,datasets:[{{
            label:'PE',data:d.val,
            borderColor:'#5B8BD4',backgroundColor:'rgba(91,139,212,0.08)',
            fill:true,pointRadius:0,pointHitRadius:6,borderWidth:2,tension:0.15
          }}]}},
          options:{{
            responsive:true,maintainAspectRatio:false,
            interaction:{{mode:'index',intersect:false}},
            plugins:{{
              legend:{{display:false}},
              annotation:{{annotations:annotations}},
              tooltip:{{backgroundColor:'rgba(0,0,0,0.8)',titleFont:{{size:11}},bodyFont:{{size:12}},
                callbacks:{{label:function(c){{return 'PE: '+c.parsed.y.toFixed(2);}}}}}}
            }},
            scales:{{
              x:{{ticks:{{maxTicksLimit:8,maxRotation:0,font:{{size:10}},color:'#8b949e'}}}},
              y:{{beginAtZero:false,ticks:{{color:'#8b949e'}},grid:{{color:'#e8ecf1'}}}}
            }}
          }}
        }});
      }}

      function renderROE(yrs){{
        var d=filterByYears(ALL_ROE_TS,ALL_ROE_VAL,yrs);
        var labels=d.ts.map(fmtTs);
        var ctx=document.getElementById('chart_roe_{sc}').getContext('2d');
        if(roeChart)roeChart.destroy();
        roeChart=new Chart(ctx,{{
          type:'line',
          data:{{labels:labels,datasets:[{{
            label:'ROE(%)',data:d.val,
            borderColor:'#C9956B',backgroundColor:'rgba(201,149,107,0.08)',
            fill:true,pointRadius:0,pointHitRadius:6,borderWidth:2,tension:0.15
          }}]}},
          options:{{
            responsive:true,maintainAspectRatio:false,
            interaction:{{mode:'index',intersect:false}},
            plugins:{{
              legend:{{display:false}},
              tooltip:{{backgroundColor:'rgba(0,0,0,0.8)',titleFont:{{size:11}},bodyFont:{{size:12}},
                callbacks:{{label:function(c){{return 'ROE: '+c.parsed.y.toFixed(2)+'%';}}}}}}
            }},
            scales:{{
              x:{{ticks:{{maxTicksLimit:8,maxRotation:0,font:{{size:10}},color:'#8b949e'}}}},
              y:{{beginAtZero:false,ticks:{{color:'#8b949e',callback:function(v){{return v+'%'}}}},grid:{{color:'#e8ecf1'}}}}
            }}
          }}
        }});
      }}

      renderPE(null);renderROE(null);

      var sec=document.getElementById('sec_{sc}');
      sec.querySelectorAll('.range-btn[data-chart="pe"]').forEach(function(btn){{
        btn.addEventListener('click',function(){{
          sec.querySelectorAll('.range-btn[data-chart="pe"]').forEach(function(b){{b.classList.remove('active')}});
          btn.classList.add('active');
          renderPE(btn.dataset.years==='all'?null:parseInt(btn.dataset.years));
        }});
      }});
      sec.querySelectorAll('.range-btn[data-chart="roe"]').forEach(function(btn){{
        btn.addEventListener('click',function(){{
          sec.querySelectorAll('.range-btn[data-chart="roe"]').forEach(function(b){{b.classList.remove('active')}});
          btn.classList.add('active');
          renderROE(btn.dataset.years==='all'?null:parseInt(btn.dataset.years));
        }});
      }});
    }})();
"""


def build_html(snap_map, history, data_date):
    today = datetime.now().strftime("%Y-%m-%d")
    eva_map = {"low": "低估", "mid": "适中", "high": "高估"}

    # 图表JS
    charts_js = ""
    for code, cat in INDICES:
        h = history[code]
        c = snap_map.get(code, {})
        cutoff = 1451606400000
        pe_recent = [p for p in h["pe"] if p["ts"] >= cutoff]
        roe_recent = [p for p in h["roe"] if p["ts"] >= cutoff]
        charts_js += _chart_block(
            code.replace("-", "_"),
            json.dumps([p["ts"] for p in pe_recent]),
            json.dumps([round(p["pe"], 2) for p in pe_recent]),
            json.dumps([p["ts"] for p in roe_recent]),
            json.dumps([round(p.get("roe", 0) * 100, 2) for p in roe_recent]),
            c.get("pe", 0) or 0,
            round(c.get("pe_percentile", 0) * 100, 1),
        )

    # 汇总表
    table_rows = ""
    for code, cat in INDICES:
        c = snap_map.get(code, {})
        name = c.get("name", code)
        pe_p = round(c.get("pe_percentile", 0) * 100, 1)
        pb_p = round(c.get("pb_percentile", 0) * 100, 1)
        roe = round(c.get("roe", 0) * 100, 2)
        yld = round(c.get("yeild", 0) * 100, 2)
        eva = eva_map.get(c.get("eva_type", ""), "")
        sc = code.replace("-", "_")
        pe_cls = "val-red" if pe_p >= 80 else ("val-green" if pe_p <= 20 else "")
        yld_cls = "val-green" if yld >= 5 else ""
        eva_cls = {"低估": "eva-low", "适中": "eva-mid", "高估": "eva-high"}.get(eva, "")
        pe = c.get("pe", 0)
        pb = c.get("pb", 0)
        table_rows += f'<tr onclick="document.getElementById(\'sec_{sc}\').scrollIntoView({{behavior:\'smooth\',block:\'start\'}})">' \
            f'<td class="idx-name">{name}</td><td class="idx-code">{code}</td><td>{cat}</td>' \
            f'<td class="{eva_cls}">{eva}</td><td class="{pe_cls}">{pe:.2f}</td><td>{pb:.2f}</td>' \
            f'<td class="{pe_cls}">{pe_p}%</td><td>{pb_p}%</td><td>{roe}%</td><td class="{yld_cls}">{yld}%</td></tr>\n'

    # TOC
    toc = "\n".join(f'    <a href="#sec_{c.replace("-","_")}">{snap_map.get(c,{}).get("name",c)}</a>' for c, _ in INDICES)

    # 详情卡片
    detail_cards = ""
    for code, cat in INDICES:
        c = snap_map.get(code, {})
        name = c.get("name", code)
        sc = code.replace("-", "_")
        cur_pe = c.get("pe", 0) or 0
        cur_pb = c.get("pb", 0)
        cur_pe_p = round(c.get("pe_percentile", 0) * 100, 1)
        cur_pb_p = round(c.get("pb_percentile", 0) * 100, 1)
        cur_roe = round(c.get("roe", 0) * 100, 2)
        cur_yld = round(c.get("yeild", 0) * 100, 2)
        eva = eva_map.get(c.get("eva_type", ""), "")
        eva_bg = {"低估": "#1a7f37", "适中": "#9a6700", "高估": "#cf222e"}.get(eva, "#333")
        pe_cls = "val-red" if cur_pe_p >= 80 else ("val-green" if cur_pe_p <= 20 else "")
        yld_cls = "val-green" if cur_yld >= 5 else ""
        badge_color = "var(--green)" if cur_pe_p < 30 else ("var(--red)" if cur_pe_p > 70 else "var(--orange)")

        detail_cards += f"""
    <div class="card" id="sec_{sc}">
      <div class="card-head">
        <div class="card-title"><h2>{name}</h2><span class="card-code">{code}</span><span class="card-cat">{cat}</span></div>
        <span class="card-eva" style="background:{eva_bg}">{eva}</span>
      </div>
      <div class="kpis">
        <div class="kpi"><div class="kpi-l">PE</div><div class="kpi-v {pe_cls}">{cur_pe:.2f}</div></div>
        <div class="kpi"><div class="kpi-l">PB</div><div class="kpi-v">{cur_pb:.2f}</div></div>
        <div class="kpi"><div class="kpi-l">PE百分位</div><div class="kpi-v {pe_cls}">{cur_pe_p}%</div></div>
        <div class="kpi"><div class="kpi-l">PB百分位</div><div class="kpi-v">{cur_pb_p}%</div></div>
        <div class="kpi"><div class="kpi-l">ROE</div><div class="kpi-v">{cur_roe}%</div></div>
        <div class="kpi"><div class="kpi-l">股息率</div><div class="kpi-v {yld_cls}">{cur_yld}%</div></div>
      </div>
      <div class="charts">
        <div class="chart-box">
          <div class="chart-badge" id="badge_{sc}"><div class="badge-val" style="color:{badge_color}">{cur_pe:.1f}</div><div class="badge-sub">PE · {cur_pe_p}%分位</div></div>
          <div class="chart-top"><div class="chart-title">PE 走势 · 近10年</div>
            <div class="range-btns">
              <button class="range-btn" data-chart="pe" data-years="1">1年</button>
              <button class="range-btn" data-chart="pe" data-years="3">3年</button>
              <button class="range-btn" data-chart="pe" data-years="5">5年</button>
              <button class="range-btn active" data-chart="pe" data-years="all">全部</button>
            </div>
          </div>
          <div class="chart-wrap"><canvas id="chart_pe_{sc}"></canvas></div>
        </div>
        <div class="chart-box">
          <div class="chart-top"><div class="chart-title">ROE 走势 · 近10年</div>
            <div class="range-btns">
              <button class="range-btn" data-chart="roe" data-years="1">1年</button>
              <button class="range-btn" data-chart="roe" data-years="3">3年</button>
              <button class="range-btn" data-chart="roe" data-years="5">5年</button>
              <button class="range-btn active" data-chart="roe" data-years="all">全部</button>
            </div>
          </div>
          <div class="chart-wrap"><canvas id="chart_roe_{sc}"></canvas></div>
        </div>
      </div>
    </div>
"""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>指数估值看板 {data_date}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3.0.1/dist/chartjs-plugin-annotation.min.js"></script>
<style>{CSS}</style>
</head>
<body>
<div class="header"><div class="container">
  <h1>📊 指数估值看板</h1>
  <p>数据来源：蛋卷基金 · 数据日期：{data_date} · 生成时间：{today} · 近10年 PE / ROE 走势</p>
</div></div>
<div class="container">
  <div class="toc">{toc}</div>
  <div class="table-wrap"><table>
    <thead><tr><th>指数</th><th>代码</th><th>类别</th><th>估值</th><th>PE</th><th>PB</th><th>PE百分位</th><th>PB百分位</th><th>ROE</th><th>股息率</th></tr></thead>
    <tbody>{table_rows}</tbody>
  </table></div>
  {detail_cards}
  <div class="footer">点击表格行跳转至指数详情 · PE百分位 ≤20% 标绿(低估) · ≥80% 标红(高估) · 股息率 ≥5% 标绿</div>
</div>
<script>
(function(){{
{charts_js}
}})();
</script>
</body>
</html>"""


def main():
    snap_map, history, data_date = fetch_all()
    html = build_html(snap_map, history, data_date)
    filename = f"指数估值看板_{data_date}.html"
    out_path = os.path.join(OUTPUT_DIR, filename)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n✅ 生成完成: {out_path}")
    print(f"   文件大小: {len(html):,} bytes")
    return out_path


if __name__ == "__main__":
    main()
