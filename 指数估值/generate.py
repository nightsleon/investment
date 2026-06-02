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
REPO_ROOT = os.path.dirname(OUTPUT_DIR)
DOCS_DIR = os.path.join(REPO_ROOT, "docs")
DOCS_ARCHIVE_DIR = os.path.join(DOCS_DIR, "index-valuation")


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def list_archive_dates():
    if not os.path.isdir(DOCS_ARCHIVE_DIR):
        return []
    dates = []
    prefix = "指数估值看板_"
    suffix = ".html"
    for name in os.listdir(DOCS_ARCHIVE_DIR):
        if name.startswith(prefix) and name.endswith(suffix):
            dates.append(name[len(prefix):-len(suffix)])
    return sorted(set(dates), reverse=True)


def list_local_archive_files():
    prefix = "指数估值看板_"
    suffix = ".html"
    files = []
    for name in os.listdir(OUTPUT_DIR):
        if name.startswith(prefix) and name.endswith(suffix):
            files.append(name)
    return sorted(set(files), reverse=True)


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
.mobile-summary{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:0 0 18px}
.summary-block{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:14px;box-shadow:0 1px 3px rgba(0,0,0,.04)}
.summary-title{font-size:14px;font-weight:700;margin-bottom:4px}.summary-sub{font-size:11px;color:var(--text3);margin-bottom:10px}
.mini-cards{display:flex;flex-direction:column;gap:8px}.mini-card{text-decoration:none;color:var(--text);background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:10px 12px}
.mini-card-top{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:6px}.mini-name{font-size:13px;font-weight:600}.mini-tag{font-size:11px;padding:2px 8px;border-radius:999px;background:#eef2f7}
.mini-meta{font-size:11px;color:var(--text3);line-height:1.5}
.table-hint{color:var(--text3);font-size:12px;margin:-6px 0 12px}
.table-wrap{background:var(--card);border:1px solid var(--border);border-radius:12px;overflow-x:auto;overflow-y:hidden;-webkit-overflow-scrolling:touch;margin-bottom:28px;box-shadow:0 1px 3px rgba(0,0,0,.04)}
table{width:100%;min-width:980px;border-collapse:collapse;font-size:13px}thead{background:#f5f7fa}
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
.chart-top{display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:10px;gap:8px;flex-wrap:wrap}
.chart-title{font-size:12px;color:var(--text3);font-weight:600}
.range-btns{display:flex;gap:4px;flex-wrap:wrap}
.range-btn{border:1px solid var(--border);background:var(--card);color:var(--text3);padding:3px 10px;border-radius:6px;font-size:11px;cursor:pointer;font-weight:500;transition:all .15s}
.range-btn:hover,.range-btn.active{background:var(--accent);color:#fff;border-color:var(--accent)}
.chart-badge{position:absolute;top:42px;right:14px;background:var(--card);border:1px solid var(--border);border-radius:8px;padding:4px 10px;z-index:2;box-shadow:0 2px 8px rgba(0,0,0,.08)}
.badge-val{font-size:15px;font-weight:800;line-height:1.1}.badge-sub{font-size:9px;color:var(--text3);margin-top:1px}
.chart-wrap{height:260px;position:relative}.chart-wrap canvas{width:100%!important;height:100%!important}
@media(max-width:900px){.header{padding:28px 18px 22px}.header h1{font-size:22px}.container{padding:0 12px}.mobile-summary{grid-template-columns:1fr;gap:10px}.table-hint{margin:-2px 0 10px}.charts{grid-template-columns:1fr}.kpis{gap:8px}.kpi{min-width:calc(50% - 6px);padding:10px 12px;flex:none}.kpi-v{font-size:16px}.card{padding:16px}.card-head{align-items:flex-start}.card-title{width:100%}.card-eva{align-self:flex-start}.chart-box{padding:14px}.chart-badge{position:static;display:inline-block;margin-bottom:8px}.chart-wrap{height:220px}}
@media(max-width:640px){.toc{flex-wrap:nowrap;overflow-x:auto;padding:16px 0 12px;-webkit-overflow-scrolling:touch}.toc a{flex:0 0 auto}.kpi{min-width:100%}.chart-title{width:100%}.range-btns{width:100%}.range-btn{flex:1;justify-content:center;padding:6px 0}.footer{font-size:11px;padding:20px 0 28px}}
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
    eva_class_map = {"低估": "eva-low", "适中": "eva-mid", "高估": "eva-high"}

    snapshot_rows = []
    for code, cat in INDICES:
        c = snap_map.get(code, {})
        name = c.get("name", code)
        pe_p = round(c.get("pe_percentile", 0) * 100, 1)
        pb_p = round(c.get("pb_percentile", 0) * 100, 1)
        roe = round(c.get("roe", 0) * 100, 2)
        yld = round(c.get("yeild", 0) * 100, 2)
        eva = eva_map.get(c.get("eva_type", ""), "")
        sc = code.replace("-", "_")
        snapshot_rows.append({
            "code": code,
            "cat": cat,
            "name": name,
            "pe": c.get("pe", 0) or 0,
            "pb": c.get("pb", 0) or 0,
            "pe_p": pe_p,
            "pb_p": pb_p,
            "roe": roe,
            "yld": yld,
            "eva": eva,
            "sc": sc,
            "eva_cls": eva_class_map.get(eva, ""),
            "pe_cls": "val-red" if pe_p >= 80 else ("val-green" if pe_p <= 20 else ""),
            "yld_cls": "val-green" if yld >= 5 else "",
        })

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
    for item in snapshot_rows:
        table_rows += f'<tr onclick="document.getElementById(\'sec_{item["sc"]}\').scrollIntoView({{behavior:\'smooth\',block:\'start\'}})">' \
            f'<td class="idx-name">{item["name"]}</td><td class="idx-code">{item["code"]}</td><td>{item["cat"]}</td>' \
            f'<td class="{item["eva_cls"]}">{item["eva"]}</td><td class="{item["pe_cls"]}">{item["pe"]:.2f}</td><td>{item["pb"]:.2f}</td>' \
            f'<td class="{item["pe_cls"]}">{item["pe_p"]}%</td><td>{item["pb_p"]}%</td><td>{item["roe"]}%</td><td class="{item["yld_cls"]}">{item["yld"]}%</td></tr>\n'

    lowest = sorted(snapshot_rows, key=lambda x: (x["pe_p"], -x["yld"]))[:3]
    highest = sorted(snapshot_rows, key=lambda x: (-x["pe_p"], x["yld"]))[:3]
    dividend = sorted(snapshot_rows, key=lambda x: (-x["yld"], x["pe_p"]))[:3]

    def build_mobile_cards(title, items, mode):
        if mode == "low":
            desc = "PE分位越低越靠前"
        elif mode == "high":
            desc = "PE分位越高越靠前"
        else:
            desc = "股息率越高越靠前"
        cards = ""
        for item in items:
            cards += (
                f'<a class="mini-card" href="#sec_{item["sc"]}">'
                f'<div class="mini-card-top"><span class="mini-name">{item["name"]}</span><span class="mini-tag {item["eva_cls"]}">{item["eva"] or "--"}</span></div>'
                f'<div class="mini-meta">PE {item["pe"]:.2f} · PE分位 <span class="{item["pe_cls"]}">{item["pe_p"]}%</span></div>'
                f'<div class="mini-meta">股息率 <span class="{item["yld_cls"]}">{item["yld"]}%</span> · ROE {item["roe"]}%</div>'
                f'</a>'
            )
        return f'<div class="summary-block"><div class="summary-title">{title}</div><div class="summary-sub">{desc}</div><div class="mini-cards">{cards}</div></div>'

    mobile_summary = (
        '<div class="mobile-summary">'
        f'{build_mobile_cards("低估优先看", lowest, "low")}'
        f'{build_mobile_cards("高估需谨慎", highest, "high")}'
        f'{build_mobile_cards("高股息", dividend, "dividend")}'
        '</div>'
    )

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
  {mobile_summary}
  <div class="table-hint">移动端可左右滑动查看完整表格；点击表格行可跳转到对应指数详情。</div>
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


def build_index_html(archive_dates, current_date):
    options = "\n".join(
        f'<option value="{d}"{" selected" if d == current_date else ""}>{d}</option>'
        for d in archive_dates
    )
    latest = archive_dates[0] if archive_dates else current_date
    selected = current_date if current_date in archive_dates else latest
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>指数估值看板归档</title>
  <style>
    :root{{--bg:#f6f8fb;--card:#fff;--text:#1f2328;--muted:#667085;--line:#e5e7eb;--brand:#2563eb;--brand-light:#eef4ff;}}
    *{{box-sizing:border-box}} body{{margin:0;font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","Segoe UI",sans-serif;background:var(--bg);color:var(--text)}}
    .wrap{{max-width:1400px;margin:0 auto;padding:24px}}
    .panel{{background:var(--card);border:1px solid var(--line);border-radius:16px;box-shadow:0 1px 3px rgba(0,0,0,.04);overflow:hidden}}
    .head{{padding:20px 24px;border-bottom:1px solid var(--line);display:flex;gap:16px;align-items:center;justify-content:space-between;flex-wrap:wrap}}
    .title h1{{font-size:24px;margin:0 0 6px}} .title p{{margin:0;color:var(--muted);font-size:13px}}
    .controls{{display:flex;gap:10px;align-items:center;flex-wrap:wrap}}
    select,button,a.btn{{height:38px;border:1px solid var(--line);border-radius:10px;background:#fff;padding:0 12px;font-size:14px;color:var(--text);text-decoration:none;display:inline-flex;align-items:center;justify-content:center;cursor:pointer}}
    select{{min-width:140px}}
    button.primary,a.primary{{background:var(--brand);border-color:var(--brand);color:#fff}}
    .meta{{padding:10px 24px;color:var(--muted);font-size:12px;border-bottom:1px solid var(--line)}}
    .quick-links,.archive-nav{{display:flex;gap:10px;flex-wrap:wrap;padding:14px 24px;border-bottom:1px solid var(--line)}}
    .chip{{height:34px;padding:0 12px;border:1px solid var(--line);border-radius:999px;background:#fff;color:var(--text);text-decoration:none;display:inline-flex;align-items:center;justify-content:center;font-size:13px;cursor:pointer}}
    .chip.primary{{background:var(--brand-light);color:var(--brand);border-color:#cfe0ff}}
    .mobile-note{{display:none;padding:14px 24px;border-bottom:1px solid var(--line);background:var(--brand-light);color:#35507a;font-size:13px;line-height:1.5}}
    .mobile-actions{{display:none;padding:16px 24px;border-bottom:1px solid var(--line);gap:10px;flex-wrap:wrap}}
    .mobile-actions a{{flex:1;min-width:140px}}
    iframe{{display:block;width:100%;height:calc(100vh - 180px);border:0;background:#fff}}
    @media (max-width:900px){{.wrap{{padding:12px}} .head{{padding:16px;align-items:flex-start}} .title{{width:100%}} .controls{{width:100%}} select,button,a.btn{{flex:1;min-width:0}} .meta{{padding:10px 16px}} .quick-links,.archive-nav{{padding:12px 16px}} .mobile-note{{display:block;padding:12px 16px}} .mobile-actions{{display:flex;padding:14px 16px}} iframe{{display:none}}}}
    @media (max-width:640px){{.title h1{{font-size:22px}} .controls label{{width:100%}} select{{width:100%;flex:initial}} button,a.btn{{width:100%}} .mobile-actions a{{min-width:100%}} .quick-links .chip,.archive-nav .chip{{flex:1}}}}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="panel">
      <div class="head">
        <div class="title">
          <h1>指数估值看板归档</h1>
          <p>GitHub Pages 入口页。可切换历史归档日期；默认打开最新一期。</p>
        </div>
        <div class="controls">
          <label for="dateSelect">数据日期</label>
          <select id="dateSelect">{options}</select>
          <button id="openBtn" class="primary">打开归档</button>
          <a id="newTabBtn" class="btn" target="_blank" rel="noopener">新标签打开</a>
        </div>
      </div>
      <div class="meta">最新日期：{latest} · 当前选择：<span id="currentDate">{selected}</span></div>
      <div class="quick-links">
        <a id="latestBtn" class="chip primary">最新一期</a>
        <a id="oldestBtn" class="chip">最早一期</a>
        <a id="selectedLinkBtn" class="chip">当前日期直达</a>
      </div>
      <div class="archive-nav">
        <a id="prevBtn" class="chip">上一期</a>
        <a id="nextBtn" class="chip">下一期</a>
      </div>
      <div class="mobile-note">移动端不再内嵌 iframe，改为直接打开对应归档页面，滚动和图表交互会更顺手。</div>
      <div class="mobile-actions">
        <a id="mobileOpenBtn" class="btn primary">打开当前日期页面</a>
        <a id="mobileNewTabBtn" class="btn" target="_blank" rel="noopener">新标签打开</a>
      </div>
      <iframe id="viewer" title="指数估值看板"></iframe>
    </div>
  </div>
  <script>
    (function(){{
      var archiveDates = {json.dumps(archive_dates, ensure_ascii=False)};
      var latest = {json.dumps(latest, ensure_ascii=False)};
      var select = document.getElementById('dateSelect');
      var viewer = document.getElementById('viewer');
      var currentDate = document.getElementById('currentDate');
      var newTabBtn = document.getElementById('newTabBtn');
      var latestBtn = document.getElementById('latestBtn');
      var oldestBtn = document.getElementById('oldestBtn');
      var selectedLinkBtn = document.getElementById('selectedLinkBtn');
      var prevBtn = document.getElementById('prevBtn');
      var nextBtn = document.getElementById('nextBtn');
      var mobileOpenBtn = document.getElementById('mobileOpenBtn');
      var mobileNewTabBtn = document.getElementById('mobileNewTabBtn');
      function isMobile(){{
        return window.matchMedia('(max-width: 900px)').matches;
      }}
      function pathFor(date){{
        return 'index-valuation/' + encodeURIComponent('指数估值看板_' + date + '.html');
      }}
      function neighbor(date, delta){{
        var idx = archiveDates.indexOf(date);
        if(idx === -1) idx = 0;
        var nextIdx = idx + delta;
        if(nextIdx < 0 || nextIdx >= archiveDates.length) return null;
        return archiveDates[nextIdx];
      }}
      function render(date, pushState){{
        if(!date || archiveDates.indexOf(date) === -1) date = latest;
        select.value = date;
        currentDate.textContent = date;
        var path = pathFor(date);
        if(!isMobile()) viewer.src = path;
        newTabBtn.href = path;
        selectedLinkBtn.href = path;
        selectedLinkBtn.textContent = '当前日期直达 · ' + date;
        mobileOpenBtn.href = path;
        mobileNewTabBtn.href = path;
        latestBtn.href = pathFor(archiveDates[0]);
        oldestBtn.href = pathFor(archiveDates[archiveDates.length - 1]);
        var prev = neighbor(date, 1), next = neighbor(date, -1);
        if(prev){{ prevBtn.href = pathFor(prev); prevBtn.style.pointerEvents = 'auto'; prevBtn.style.opacity = '1'; prevBtn.textContent = '上一期 · ' + prev; }} else {{ prevBtn.removeAttribute('href'); prevBtn.style.pointerEvents = 'none'; prevBtn.style.opacity = '.45'; prevBtn.textContent = '上一期'; }}
        if(next){{ nextBtn.href = pathFor(next); nextBtn.style.pointerEvents = 'auto'; nextBtn.style.opacity = '1'; nextBtn.textContent = '下一期 · ' + next; }} else {{ nextBtn.removeAttribute('href'); nextBtn.style.pointerEvents = 'none'; nextBtn.style.opacity = '.45'; nextBtn.textContent = '下一期'; }}
        if(pushState){{
          var u = new URL(window.location.href);
          u.searchParams.set('date', date);
          window.history.replaceState(null, '', u.toString());
        }}
      }}
      document.getElementById('openBtn').addEventListener('click', function(){{
        render(select.value, true);
        if(isMobile()) window.location.href = pathFor(select.value);
      }});
      select.addEventListener('change', function(){{ render(select.value, true); }});
      window.addEventListener('resize', function(){{ render(select.value, false); }});
      var initial = new URL(window.location.href).searchParams.get('date') || latest;
      render(initial, false);
    }})();
  </script>
</body>
</html>"""


def write_outputs(html, data_date):
    ensure_dir(OUTPUT_DIR)
    ensure_dir(DOCS_ARCHIVE_DIR)

    filename = f"指数估值看板_{data_date}.html"
    out_path = os.path.join(OUTPUT_DIR, filename)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    # 同步本地所有历史归档到 docs/index-valuation，保证 Pages 可按日期切换
    for archive_name in list_local_archive_files():
        src = os.path.join(OUTPUT_DIR, archive_name)
        dst = os.path.join(DOCS_ARCHIVE_DIR, archive_name)
        with open(src, "r", encoding="utf-8") as rf, open(dst, "w", encoding="utf-8") as wf:
            wf.write(rf.read())

    docs_archive_path = os.path.join(DOCS_ARCHIVE_DIR, filename)
    archive_dates = list_archive_dates()
    if data_date not in archive_dates:
        archive_dates = sorted(set(archive_dates + [data_date]), reverse=True)

    ensure_dir(DOCS_DIR)
    index_html = build_index_html(archive_dates, data_date)
    index_path = os.path.join(DOCS_DIR, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_html)

    manifest_path = os.path.join(DOCS_DIR, "index-valuation-manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump({"latest": archive_dates[0] if archive_dates else data_date, "current": data_date, "archives": archive_dates}, f, ensure_ascii=False, indent=2)

    return out_path, docs_archive_path, index_path, manifest_path


def main():
    snap_map, history, data_date = fetch_all()
    html = build_html(snap_map, history, data_date)
    out_path, docs_archive_path, index_path, manifest_path = write_outputs(html, data_date)
    print(f"\n✅ 生成完成: {out_path}")
    print(f"✅ Pages 归档: {docs_archive_path}")
    print(f"✅ Pages 入口: {index_path}")
    print(f"✅ Pages 清单: {manifest_path}")
    print(f"   文件大小: {len(html):,} bytes")
    return out_path


if __name__ == "__main__":
    main()
