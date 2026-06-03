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
:root{--bg:#fcfcfd;--card:#ffffff;--card-soft:#fafafa;--border:#e5e7eb;--border-strong:#d4d4d8;--text:#09090b;--text2:#52525b;--text3:#a1a1aa;--accent:#18181b;--accent-soft:#f4f4f5;--green:#15803d;--green-soft:#ecfdf5;--red:#dc2626;--red-soft:#fef2f2;--amber:#a16207;--amber-soft:#fefce8;--shadow:0 1px 2px rgba(0,0,0,.03),0 8px 24px rgba(0,0,0,.03)}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","Segoe UI",sans-serif;background:#fff;color:var(--text);line-height:1.5}
.header{padding:34px 0 20px;background:#fff}
.hero{max-width:1200px;margin:0 auto;padding:0 20px}
.hero-kicker{display:inline-flex;align-items:center;gap:8px;font-size:12px;color:var(--text2);font-weight:700;letter-spacing:.01em;margin-bottom:14px}.hero-kicker:before{content:"";width:6px;height:6px;border-radius:50%;background:var(--text)}
.hero h1{font-size:34px;font-weight:780;letter-spacing:-.04em;margin-bottom:10px}
.hero p{max-width:860px;color:var(--text2);font-size:14px;line-height:1.7}
.hero-meta{display:flex;gap:10px;flex-wrap:wrap;margin-top:18px}.hero-pill{display:inline-flex;align-items:center;height:34px;padding:0 12px;border:1px solid var(--border);border-radius:999px;background:#fff;color:var(--text2);font-size:12px}
.container{max-width:1200px;margin:0 auto;padding:20px 20px 0}
.toc{display:flex;flex-wrap:wrap;gap:8px;padding:0 0 18px}.toc a{background:#fff;border:1px solid var(--border);color:var(--text2);padding:7px 12px;border-radius:999px;text-decoration:none;font-size:12px;font-weight:600;transition:all .16s}.toc a:hover{border-color:var(--border-strong);color:var(--text)}
.mobile-summary{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:0 0 22px}.summary-block{background:#fff;border:1px solid var(--border);border-radius:20px;padding:18px;box-shadow:none}
.summary-title{font-size:15px;font-weight:720;margin-bottom:4px}.summary-sub{font-size:12px;color:var(--text3);margin-bottom:12px}
.mini-cards{display:flex;flex-direction:column;gap:10px}.mini-card{text-decoration:none;color:var(--text);background:#fff;border:1px solid #f0f0f1;border-radius:16px;padding:12px 13px;transition:transform .15s,border-color .15s}.mini-card:hover{transform:translateY(-1px);border-color:var(--border-strong)}
.mini-card-top{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:7px}.mini-name{font-size:13px;font-weight:680}.mini-tag{font-size:11px;padding:4px 8px;border-radius:999px;background:#f1f5f9;color:var(--text2)}
.mini-meta{font-size:11px;color:var(--text3);line-height:1.55}
.table-hint{color:var(--text3);font-size:12px;margin:0 0 10px}.table-wrap{background:#fff;border:1px solid var(--border);border-radius:20px;overflow-x:auto;overflow-y:hidden;-webkit-overflow-scrolling:touch;margin-bottom:28px;box-shadow:none}
table{width:100%;min-width:980px;border-collapse:separate;border-spacing:0;font-size:13px}thead{background:#fbfcff}th{padding:14px 12px;text-align:right;font-weight:650;color:var(--text3);font-size:11px;white-space:nowrap;border-bottom:1px solid #edf2f7}th:first-child,th:nth-child(2),th:nth-child(3),th:nth-child(4){text-align:left}
td{padding:14px 12px;text-align:right;border-top:1px solid #f1f5f9;white-space:nowrap}td:first-child,td:nth-child(2),td:nth-child(3),td:nth-child(4){text-align:left}
tr{cursor:pointer;transition:background .15s}tr:hover{background:#f8fbff}.idx-name{font-weight:660}.idx-code{color:var(--text3);font-size:12px}
.eva-low{color:var(--green);font-weight:600}.eva-mid{color:var(--amber);font-weight:600}.eva-high{color:var(--red);font-weight:600}
.val-red{color:var(--red);font-weight:700}.val-green{color:var(--green);font-weight:700}
.metric-pill{display:inline-flex;align-items:center;justify-content:center;min-width:56px;padding:4px 9px;border-radius:999px;font-weight:700;line-height:1.1;border:1px solid transparent}
.metric-pill.red{color:var(--red);background:var(--red-soft);border-color:#fecaca}.metric-pill.green{color:var(--green);background:var(--green-soft);border-color:#bbf7d0}
.section-title{font-size:12px;font-weight:750;color:var(--text3);letter-spacing:.08em;text-transform:uppercase;margin:24px 0 12px}
.card{background:#fff;border:1px solid var(--border);border-radius:22px;padding:24px;margin-bottom:20px;box-shadow:none;scroll-margin-top:16px}.card-head{display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:18px;flex-wrap:wrap;gap:12px}
.card-title{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.card-title h2{font-size:20px;font-weight:760;letter-spacing:-.025em}.card-code{color:var(--text3);font-size:12px;background:#f8fafc;padding:4px 9px;border-radius:999px;border:1px solid #edf2f7}.card-cat{color:var(--text2);font-size:11px;background:#f8fafc;padding:4px 10px;border-radius:999px;font-weight:600;border:1px solid #edf2f7}
.card-eva{font-size:12px;padding:6px 12px;border-radius:999px;font-weight:700;border:1px solid transparent}.card-eva.eva-low{background:var(--green-soft);border-color:#ccefd8}.card-eva.eva-mid{background:var(--amber-soft);border-color:#fde7c7}.card-eva.eva-high{background:var(--red-soft);border-color:#fecdd3}
.kpis{display:grid;grid-template-columns:repeat(6,1fr);gap:10px;margin-bottom:20px}.kpi{background:var(--card-soft);border:1px solid #f0f0f1;border-radius:16px;padding:13px 14px;min-width:0}.kpi-l{font-size:11px;color:var(--text3);margin-bottom:4px;font-weight:600}.kpi-v{font-size:20px;font-weight:740}
.charts{display:grid;grid-template-columns:1fr 1fr;gap:16px}.chart-box{background:#fff;border:1px solid #f0f0f1;border-radius:18px;padding:16px;position:relative}.chart-top{display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:12px;gap:12px;flex-wrap:wrap}.chart-title{font-size:12px;color:var(--text2);font-weight:680}
.range-btns{display:flex;gap:6px;flex-wrap:wrap}.range-btn{border:1px solid var(--border);background:#fff;color:var(--text3);padding:5px 10px;border-radius:999px;font-size:11px;cursor:pointer;font-weight:650;transition:all .15s}.range-btn:hover,.range-btn.active{background:var(--accent-soft);color:var(--text);border-color:var(--border-strong)}
.badge-val{font-size:16px;font-weight:800;line-height:1.1}.badge-sub{font-size:10px;color:var(--text3);margin-top:2px}.chart-wrap{height:260px;position:relative}.chart-wrap canvas{width:100%!important;height:100%!important}
.footer{text-align:center;padding:26px 0 36px;color:var(--text3);font-size:12px}
@media(max-width:900px){.hero{padding:0 12px}.header{padding:24px 0 14px}.hero h1{font-size:26px}.container{padding:18px 12px 0}.mobile-summary{grid-template-columns:1fr;gap:10px}.kpis{grid-template-columns:repeat(2,1fr)}.charts{grid-template-columns:1fr}.card{padding:18px}.chart-box{padding:14px}.chart-wrap{height:220px}}
@media(max-width:640px){.hero-meta{gap:8px}.toc{flex-wrap:nowrap;overflow-x:auto;padding-bottom:14px;-webkit-overflow-scrolling:touch}.toc a{flex:0 0 auto}.kpis{grid-template-columns:1fr}.chart-title{width:100%}.range-btns{width:100%}.range-btn{flex:1;justify-content:center}.footer{font-size:11px;padding:20px 0 28px}}
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
      function fmtNum(v,digits){{
        if(v===null||v===undefined||Number.isNaN(Number(v))) return '--';
        return Number(Number(v).toFixed(digits)).toString();
      }}
      function fmtPct(v,digits){{return fmtNum(v,digits)+'%';}}

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
        // 更新标题文案
        var title=document.getElementById('pe_title_{sc}');
        if(title){{
          title.textContent='PE走势（'+(yrs?yrs+'年':'全部')+'）｜'+pctInRange.toFixed(1)+'%分位';
          title.style.color=pctInRange<30?'var(--green)':pctInRange>70?'var(--red)':'var(--text2)';
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
        var title=document.getElementById('roe_title_{sc}');
        if(title){{
          title.textContent='ROE走势（'+(yrs?yrs+'年':'全部')+'）';
        }}
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
                callbacks:{{label:function(c){{return 'ROE: '+fmtPct(c.parsed.y,2);}}}}}}
            }},
            scales:{{
              x:{{ticks:{{maxTicksLimit:8,maxRotation:0,font:{{size:10}},color:'#8b949e'}}}},
              y:{{beginAtZero:false,ticks:{{color:'#8b949e',callback:function(v){{return fmtPct(v,1)}}}},grid:{{color:'#e8ecf1'}}}}
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

    def badge_value(value, cls):
        if cls == "val-red":
            return f'<span class="metric-pill red">{value}</span>'
        if cls == "val-green":
            return f'<span class="metric-pill green">{value}</span>'
        return value

    # 汇总表
    table_rows = ""
    for item in snapshot_rows:
        pe_text = badge_value(f"{item['pe']:.2f}", item["pe_cls"])
        pe_p_text = badge_value(f"{item['pe_p']}%", item["pe_cls"])
        yld_text = badge_value(f"{item['yld']}%", item["yld_cls"])
        table_rows += f'<tr onclick="document.getElementById(\'sec_{item["sc"]}\').scrollIntoView({{behavior:\'smooth\',block:\'start\'}})">' \
            f'<td class="idx-name">{item["name"]}</td><td class="idx-code">{item["code"]}</td><td>{item["cat"]}</td>' \
            f'<td class="{item["eva_cls"]}">{item["eva"]}</td><td>{pe_text}</td><td>{item["pb"]:.2f}</td>' \
            f'<td>{pe_p_text}</td><td>{item["pb_p"]}%</td><td>{item["roe"]}%</td><td>{yld_text}</td></tr>\n'

    lowest = sorted(snapshot_rows, key=lambda x: (x["pe_p"], -x["yld"]))[:3]
    highest = sorted(snapshot_rows, key=lambda x: (-x["pe_p"], x["yld"]))[:3]
    dividend = sorted(snapshot_rows, key=lambda x: (-x["yld"], x["pe_p"]))[:3]
    low_count = sum(1 for x in snapshot_rows if x["pe_p"] <= 20)
    high_count = sum(1 for x in snapshot_rows if x["pe_p"] >= 80)
    dividend_count = sum(1 for x in snapshot_rows if x["yld"] >= 5)
    lead_low = lowest[0]["name"] if lowest else "--"
    lead_high = highest[0]["name"] if highest else "--"
    lead_dividend = dividend[0]["name"] if dividend else "--"
    insight = f"当前低估机会 {low_count} 个，高估区间 {high_count} 个，高股息 {dividend_count} 个；低估代表为 {lead_low}，高估代表为 {lead_high}，股息率最高为 {lead_dividend}。"

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

        detail_cards += f"""
    <div class="card" id="sec_{sc}">
      <div class="card-head">
        <div class="card-title"><h2>{name}</h2><span class="card-code">{code}</span><span class="card-cat">{cat}</span></div>
        <span class="card-eva {eva_class_map.get(eva, '')}">{eva}</span>
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
          <div class="chart-top"><div class="chart-title" id="pe_title_{sc}">PE走势（全部）｜{cur_pe_p}%分位</div>
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
          <div class="chart-top"><div class="chart-title" id="roe_title_{sc}">ROE走势（全部）</div>
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
<div class="header"><div class="hero">
  <div class="hero-kicker">研究看板</div>
  <h1>指数估值看板</h1>
  <p>{insight}</p>
  <div class="hero-meta"><span class="hero-pill">数据日期：{data_date}</span><span class="hero-pill">生成时间：{today}</span><span class="hero-pill">口径：近10年 PE / ROE</span></div>
</div></div>
<div class="container">
  <div class="section-title">快速定位</div>
  <div class="toc">{toc}</div>
  <div class="section-title">三类重点</div>
  {mobile_summary}
  <div class="section-title">估值总览</div>
  <div class="table-hint">移动端可左右滑动查看完整表格；点击表格行可跳转到对应指数详情。</div>
  <div class="table-wrap"><table>
    <thead><tr><th>指数</th><th>代码</th><th>类别</th><th>估值</th><th>PE</th><th>PB</th><th>PE百分位</th><th>PB百分位</th><th>ROE</th><th>股息率</th></tr></thead>
    <tbody>{table_rows}</tbody>
  </table></div>
  <div class="section-title">指数详情</div>
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
    :root{{--bg:#ffffff;--card:#fff;--card-soft:#fafafa;--text:#09090b;--muted:#52525b;--line:#e5e7eb;--line-strong:#d4d4d8;--brand:#18181b;--brand-soft:#f4f4f5;--shadow:0 1px 2px rgba(0,0,0,.03),0 8px 24px rgba(0,0,0,.03);}}
    *{{box-sizing:border-box}} body{{margin:0;font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","Segoe UI",sans-serif;background:#fff;color:var(--text)}}
    .wrap{{max-width:1380px;margin:0 auto;padding:28px 24px 24px}}
    .hero{{margin-bottom:16px;padding:4px 2px 0}}
    .hero-kicker{{display:inline-flex;align-items:center;gap:8px;font-size:12px;color:var(--muted);font-weight:700;margin-bottom:14px}} .hero-kicker:before{{content:"";width:6px;height:6px;border-radius:50%;background:var(--brand)}}
    .hero h1{{font-size:34px;letter-spacing:-.04em;margin:0 0 10px}} .hero p{{margin:0;color:var(--muted);font-size:14px;line-height:1.7;max-width:900px}}
    .hero-meta{{display:flex;gap:10px;flex-wrap:wrap;margin-top:18px}} .hero-pill{{display:inline-flex;align-items:center;height:34px;padding:0 12px;border:1px solid var(--line);border-radius:999px;background:#fff;color:var(--muted);font-size:12px}}
    .panel{{background:#fff;border:1px solid var(--line);border-radius:24px;box-shadow:none;overflow:hidden}}
    .head{{padding:24px;border-bottom:1px solid var(--line);display:flex;gap:16px;align-items:flex-end;justify-content:space-between;flex-wrap:wrap;background:linear-gradient(180deg,rgba(255,255,255,1) 0%,rgba(250,252,255,1) 100%)}}
    .title h2{{font-size:22px;margin:0 0 6px;letter-spacing:-.025em}} .title p{{margin:0;color:var(--muted);font-size:13px}}
    .controls{{display:flex;gap:10px;align-items:center;flex-wrap:wrap}}
    select,button,a.btn{{height:40px;border:1px solid var(--line);border-radius:12px;background:#fff;padding:0 14px;font-size:14px;color:var(--text);text-decoration:none;display:inline-flex;align-items:center;justify-content:center;cursor:pointer;transition:all .16s}}
    select{{min-width:140px}}
    select:hover,button:hover,a.btn:hover{{border-color:var(--line-strong);transform:translateY(-1px)}}
    button.primary,a.primary{{background:var(--brand);border-color:var(--brand);color:#fff}}
    .meta{{padding:14px 24px;color:var(--muted);font-size:12px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;background:#fff}} .meta b{{color:var(--text)}}
    .section{{padding:16px 24px;border-bottom:1px solid var(--line)}}
    .section-label{{font-size:12px;font-weight:750;color:#94a3b8;letter-spacing:.08em;text-transform:uppercase;margin-bottom:12px}}
    .quick-links,.archive-nav{{display:flex;gap:10px;flex-wrap:wrap}}
    .chip{{height:36px;padding:0 14px;border:1px solid var(--line);border-radius:999px;background:#fff;color:var(--text);text-decoration:none;display:inline-flex;align-items:center;justify-content:center;font-size:13px;font-weight:600;cursor:pointer;transition:all .16s}}
    .chip:hover{{transform:translateY(-1px);border-color:var(--line-strong)}}
    .chip.primary{{background:var(--brand-soft);color:var(--brand);border-color:var(--line)}}
    .mobile-note{{display:none;padding:14px 24px;border-bottom:1px solid var(--line);background:var(--brand-soft);color:#35507a;font-size:13px;line-height:1.5}}
    .mobile-actions{{display:none;padding:16px 24px;border-bottom:1px solid var(--line);gap:10px;flex-wrap:wrap;background:#fff}}
    .mobile-actions a{{flex:1;min-width:140px}}
    iframe{{display:block;width:100%;height:calc(100vh - 220px);border:0;background:#fff}}
    @media (max-width:900px){{.wrap{{padding:12px}} .hero{{padding:2px 0 0}} .hero h1{{font-size:26px}} .head{{padding:16px;align-items:flex-start}} .title{{width:100%}} .controls{{width:100%}} select,button,a.btn{{flex:1;min-width:0}} .meta{{padding:12px 16px}} .section{{padding:14px 16px}} .mobile-note{{display:block;padding:12px 16px}} .mobile-actions{{display:flex;padding:14px 16px}} iframe{{display:none}}}}
    @media (max-width:640px){{.controls label{{width:100%}} select{{width:100%;flex:initial}} button,a.btn{{width:100%}} .mobile-actions a{{min-width:100%}} .quick-links .chip,.archive-nav .chip{{flex:1}}}}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="hero">
      <div class="hero-kicker">研究归档</div>
      <h1>指数估值看板归档</h1>
      <p>用于统一浏览每日快照与历史归档。桌面端默认内嵌最新一期，移动端直接跳转到独立页面，避免 iframe 带来的滚动与图表交互问题。</p>
      <div class="hero-meta"><span class="hero-pill">最新一期：{latest}</span><span class="hero-pill">当前默认：{selected}</span><span class="hero-pill">数据源：蛋卷基金</span></div>
    </div>
    <div class="panel">
      <div class="head">
        <div class="title">
          <h2>浏览与切换</h2>
          <p>按日期进入任一期归档，也可以直接跳到最新或最早一期。</p>
        </div>
        <div class="controls">
          <label for="dateSelect">数据日期</label>
          <select id="dateSelect">{options}</select>
          <button id="openBtn" class="primary">打开归档</button>
          <a id="newTabBtn" class="btn" target="_blank" rel="noopener">新标签打开</a>
        </div>
      </div>
      <div class="meta"><div>最新日期：<b>{latest}</b></div><div>当前选择：<b id="currentDate">{selected}</b></div></div>
      <div class="section">
        <div class="section-label">快捷入口</div>
        <div class="quick-links">
          <a id="latestBtn" class="chip primary">最新一期</a>
          <a id="oldestBtn" class="chip">最早一期</a>
          <a id="selectedLinkBtn" class="chip">当前日期直达</a>
        </div>
      </div>
      <div class="section">
        <div class="section-label">顺序翻看</div>
        <div class="archive-nav">
          <a id="prevBtn" class="chip">上一期</a>
          <a id="nextBtn" class="chip">下一期</a>
        </div>
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
