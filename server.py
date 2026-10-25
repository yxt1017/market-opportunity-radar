"""零外部依赖的本地浏览器版市场机会雷达（Python 3.10+）。"""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import webbrowser

from core import (FIELDS, METRICS, OPPORTUNITY_TYPES, PLATFORMS, SOURCES,
                  add_rows, analyze, connect, export_csv, import_csv,
                  read_rows, seed_demo)

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "data" / "opportunity_radar.sqlite3"
HOST = "127.0.0.1"
PORT = 8501

PAGE = r'''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>市场机会雷达 · V1</title>
<style>
:root{color-scheme:dark;--bg:#0c111b;--panel:#161d2a;--panel2:#1d2635;--border:#2b3546;--text:#e8eef7;--muted:#9aaac0;--blue:#75a7f8;--green:#50d8ad;--yellow:#e7bd68;--red:#fa8a8a}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 80% -5%,#1c3255 0,#0c111b 45%);color:var(--text);font:14px/1.6 -apple-system,BlinkMacSystemFont,"Microsoft YaHei","PingFang SC",sans-serif}
.wrap{max-width:1240px;padding:26px 24px 60px;margin:auto}.top{display:flex;justify-content:space-between;align-items:start;gap:14px;flex-wrap:wrap}.eyebrow{color:var(--blue);font-size:12px;letter-spacing:2px;font-weight:800}h1{font-size:32px;margin:5px 0 1px;letter-spacing:-1px}h2{font-size:19px;margin:6px 0 14px}p{color:var(--muted);margin:6px 0}.pill{padding:6px 12px;background:var(--panel2);color:var(--muted);border:1px solid var(--border);border-radius:100px}.toolbar,.tabs{display:flex;gap:9px;flex-wrap:wrap;align-items:center}.tabs{margin:22px 0 20px;border-bottom:1px solid var(--border);padding-bottom:14px}button,select,input,textarea{font:inherit;border:1px solid var(--border);border-radius:9px;background:var(--panel2);color:var(--text);padding:9px 12px}button{cursor:pointer;white-space:nowrap}button:hover{border-color:var(--blue)}button.active,button.primary{background:#275ab3;border-color:#3971cd;color:white}input,textarea,select{width:100%;outline:none}input:focus,textarea:focus{border-color:var(--blue)}label{color:var(--muted);display:block;margin-bottom:5px;font-size:12px}.notice{padding:13px 16px;border:1px solid #755a35;background:#2b251d;color:#f3dba5;border-radius:12px;margin:12px 0}.notice.real{background:#1b2724;border-color:#305b4d;color:#8de0be}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:18px 0}.card,.panel{background:var(--panel);border:1px solid var(--border);border-radius:15px;padding:17px}.klabel{font-size:12px;color:var(--muted)}.kval{font-size:29px;font-weight:750;letter-spacing:-.5px}.panel{margin-bottom:15px}.tableouter{overflow:auto}table{border-collapse:collapse;width:100%;white-space:nowrap}th,td{text-align:left;padding:12px 11px;border-bottom:1px solid var(--border)}th{font-size:12px;color:var(--muted);font-weight:600}td{font-size:13px}tbody tr:hover{background:rgba(150,180,240,.04)}.good{color:var(--green)}.bad{color:var(--red)}.warn{color:var(--yellow)}.muted{color:var(--muted)}.small{font-size:12px}.flex{display:flex;gap:12px;flex-wrap:wrap;align-items:center}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.cell2{grid-column:span 2}.hide{display:none!important}.chart{width:100%;height:280px;margin-top:12px;border:1px solid var(--border);border-radius:12px;background:#101824}.metricpick{max-width:700px}a{color:#90b9ff}footer{color:var(--muted);font-size:12px;margin-top:20px}.note{font-size:12px;color:var(--muted);margin:10px 0}.tag{font-size:11px;background:#283750;padding:3px 7px;border-radius:6px}.two{display:grid;grid-template-columns:1fr 1fr;gap:12px}
@media(max-width:800px){.wrap{padding:16px 12px 40px}h1{font-size:26px}.cards{grid-template-columns:repeat(2,1fr)}.grid{grid-template-columns:1fr}.cell2{grid-column:span 1}.two{grid-template-columns:1fr}.chart{height:230px}}
</style></head><body><div class="wrap">
<div class="top"><div><div class="eyebrow">MARKET OPPORTUNITY RADAR · V1</div><h1>📡 市场机会雷达</h1><p>商品机会 × 软件机会 · 原始指标可追溯 · 不伪造搜索量</p></div><div class="toolbar"><span class="pill">本机离线数据库</span><select id="mode" style="width:176px"><option value="real">真实导入数据</option><option value="demo">模拟演示数据</option></select></div></div>
<div id="banner" class="notice"></div>
<div class="tabs" id="tabs"><button data-tab="all" class="active">统一分析</button><button data-tab="商品">📦 商品机会</button><button data-tab="软件">💻 软件机会</button><button data-tab="import">📥 导入数据</button><button data-tab="quality">🔍 数据来源</button></div>
<div id="dashboard"><div class="cards" id="cards"></div><div class="panel"><div class="flex" style="justify-content:space-between"><h2 id="ranktitle">综合候选榜</h2><span class="tag">线索排序 ≠ 盈利预测</span></div><div id="ranking" class="tableouter"></div><p class="note">排序：需求线索上涨的平台数 → 可比需求指标变化中位数。不同统计口径不可合并为全网热度；本店访客不代表全平台搜索。</p></div><div class="panel"><h2>观察历史</h2><div class="two"><div><label>关键词</label><select id="keyword"></select></div><div><label>数据系列（相同来源、指标和范围才比较）</label><select id="series" class="metricpick"></select></div></div><svg id="graph" class="chart" viewBox="0 0 900 280" preserveAspectRatio="none" role="img" aria-label="观察历史趋势图"></svg><div id="chartnote" class="note"></div></div></div>
<div id="importpanel" class="hide"><div class="panel"><h2>📥 导入 CSV</h2><p>只允许上传你有权使用的数据。CSV 表头请使用模板；每行是一条带日期、来源和统计范围的原始观察。</p><div class="flex" style="margin-top:18px"><button onclick="download('/api/template','市场机会雷达_导入模板.csv')">下载格式模板</button><input id="csvfile" type="file" accept=".csv,text/csv" style="max-width:360px"><button class="primary" onclick="uploadCSV()">导入真实数据区</button></div><div id="uploadresult" class="note"></div></div>
<div class="panel"><h2>手工添加一条真实记录</h2><form id="entryform" class="grid"><div><label>观察日期</label><input name="observed_date" type="date" required></div><div><label>平台</label><select name="platform"><option>拼多多</option><option>小红书</option><option>闲鱼</option><option>淘宝/天猫</option><option>京东</option><option>抖音</option><option>1688</option><option>知乎</option><option>哔哩哔哩</option><option>其他</option></select></div><div><label>类别</label><select name="opportunity_type"><option>商品</option><option>软件</option></select></div><div><label>关键词</label><input name="keyword" required maxlength="80" placeholder="如：手机支架"></div><div><label>指标</label><select name="metric_type" id="metricselect"></select></div><div><label>原始指标数值</label><input name="metric_value" type="number" min="0" step="any" required value="0"></div><div><label>数据来源声明</label><select name="source_type" id="sourceselect"></select></div><div><label>来源名称</label><input name="source_name" required placeholder="如：我的店铺后台"></div><div><label>统计范围（须保持一致）</label><input name="source_scope" required placeholder="如：店铺A·访客"></div><div class="cell2"><label>来源链接（可不填）</label><input name="source_url" placeholder="https://..."></div><div><label>备注</label><input name="notes" placeholder="说明采样方法、口径等"></div><div><button class="primary" type="submit">保存观察记录</button></div></form><div id="addresult" class="note"></div></div></div>
<div id="qualitypanel" class="hide"><div class="panel"><h2>🔍 数据质量与原始出处</h2><p>“官方导出”“授权接口”等均为导入者声明；本工具并未验证授权文件真伪。演示数据始终隔离。</p><div class="flex" style="margin:14px 0"><button onclick="download('/api/export?mode='+encodeURIComponent(mode),'观察数据.csv')">导出当前区域全部记录</button></div><div id="qualitytable" class="tableouter"></div></div><div class="panel"><h2>解释规则</h2><p>仅在同平台、同指标、同来源、同范围的系列里，将最近7日均值与此前7日均值比较，前后各至少2个样本，且前期均值非零，才计算相对变化。</p><p>搜索指数不是搜索次数；本店访客只代表店铺范围；搜索结果数、笔记数属于供给观察；建议词排名不能换算成搜索量。</p><p>闲鱼未经授权的自动化访问受到限制，本工具不包含爬虫、账号登录、逆向接口或付费服务。</p></div></div>
<footer>V1 本地程序 · 默认只监听 127.0.0.1 · 不上传数据 · 没有任何平台的实时 API 接入或全网真实热词榜</footer></div>
<script>
const $=id=>document.getElementById(id);let mode='real',tab='all',DATA={rows:[],analysis:{candidates:[],series:[]},metrics:{},sources:{}};
const escapeHTML=v=>String(v==null?'':v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=v=>v===null||v===undefined?'不足':Number(v).toFixed(1);
const trend=v=>v===null||v===undefined?'<span class="muted">不足</span>':`<span class="${v>0?'good':v<0?'bad':'muted'}">${v>0?'+':''}${Number(v).toFixed(1)}%</span>`;
function table(headers,rows){let s='<table><thead><tr>'+headers.map(x=>'<th>'+escapeHTML(x)+'</th>').join('')+'</tr></thead><tbody>';s+=rows.map(r=>'<tr>'+r.map(v=>'<td>'+v+'</td>').join('')+'</tr>').join('');return s+'</tbody></table>';}
function curCandidates(){return DATA.analysis.candidates.filter(x=>tab==='all'||x.opportunity_type===tab)}
function render(){const isDemo=mode==='demo';$('banner').className='notice'+(isDemo?'':' real');$('banner').textContent=isDemo?'⚠️ 演示区全部词、数值和趋势均为虚构，非平台真实数据。':'✓ 真实区只显示你导入的记录；“真实区”不意味着本系统已验真。尚未接入任何实时采集。';
$('dashboard').classList.toggle('hide',tab==='import'||tab==='quality');$('importpanel').classList.toggle('hide',tab!=='import');$('qualitypanel').classList.toggle('hide',tab!=='quality');
$('tabs').querySelectorAll('button').forEach(b=>b.classList.toggle('active',b.dataset.tab===tab));
let items=curCandidates();$('cards').innerHTML=[['已记录关键词',new Set(DATA.rows.map(r=>r.keyword+'|'+r.opportunity_type)).size],['商品候选',DATA.analysis.candidates.filter(x=>x.opportunity_type==='商品').length],['软件候选',DATA.analysis.candidates.filter(x=>x.opportunity_type==='软件').length],['历史观察',DATA.rows.length]].map(([name,v])=>`<div class="card"><div class="klabel">${escapeHTML(name)}</div><div class="kval">${v}</div></div>`).join('');
$('ranktitle').textContent=tab==='all'?'综合候选榜':tab+'机会候选榜';$('ranking').innerHTML=items.length?table(['关键词','类别','来源平台','趋势判断','有效需求系列','上涨平台数','需求线索相对变化中位数'],items.map(x=>[escapeHTML(x.keyword),escapeHTML(x.opportunity_type),escapeHTML(x.platforms),escapeHTML(x.status),x.demand_sources,x.up_platforms,trend(x.median_change_pct)])):'<p>暂无数据。请先切换演示区或导入真实观察。</p>';
const choices=items.map(x=>x.keyword+'||'+x.opportunity_type);let old=$('keyword').value;$('keyword').innerHTML=items.map(x=>`<option value="${escapeHTML(x.keyword+'||'+x.opportunity_type)}">${escapeHTML(x.keyword)} · ${escapeHTML(x.opportunity_type)}</option>`).join('');if(choices.includes(old))$('keyword').value=old;renderSeries();
let quality=DATA.rows.slice().sort((a,b)=>b.observed_date.localeCompare(a.observed_date));$('qualitytable').innerHTML=quality.length?table(['日期','平台','关键词','类别','指标','原始值','来源类型声明','来源名称','统计范围'],quality.map(x=>[x.observed_date,escapeHTML(x.platform),escapeHTML(x.keyword),escapeHTML(x.opportunity_type),escapeHTML(DATA.metrics[x.metric_type]?.[0]||x.metric_type),escapeHTML(x.metric_value),escapeHTML(DATA.sources[x.source_type]||x.source_type),escapeHTML(x.source_name),escapeHTML(x.source_scope)])):'<p>暂无记录</p>';
}
function renderSeries(){const [kw,kind]=($('keyword').value||'').split('||');const points=DATA.rows.filter(x=>x.keyword===kw&&x.opportunity_type===kind);let opts=[],map={};for(const p of points){let k=[p.platform,p.metric_type,p.source_name,p.source_scope].join('|');if(!map[k]){map[k]=[];opts.push(k)}map[k].push(p)}
$('series').innerHTML=opts.map(k=>{let p=map[k][0];return `<option value="${escapeHTML(k)}">${escapeHTML(p.platform)} · ${escapeHTML(DATA.metrics[p.metric_type]?.[0]||p.metric_type)} · ${escapeHTML(p.source_name)} · ${escapeHTML(p.source_scope)}</option>`}).join('');$('series')._points=map;draw();}
function draw(){let points=($('series')._points||{})[$('series').value]||[];points=points.slice().sort((a,b)=>a.observed_date.localeCompare(b.observed_date));let svg=$('graph');if(!points.length){svg.innerHTML='';$('chartnote').textContent='没有足够的数据系列。';return}
let values=points.map(p=>Number(p.metric_value)),mn=Math.min(...values),mx=Math.max(...values);if(mx===mn){mn-=1;mx+=1}let x=i=>55+i*(810/Math.max(points.length-1,1)),y=v=>235-((v-mn)/(mx-mn))*183;
let lines=[0,.25,.5,.75,1].map(t=>{let yy=235-t*183;return `<line x1="55" x2="865" y1="${yy}" y2="${yy}" stroke="#2e3a4b" stroke-width="1"/><text x="43" y="${yy+4}" text-anchor="end" fill="#93a4bd" font-size="12">${(mn+t*(mx-mn)).toFixed(1)}</text>`}).join('');
let poly=points.map((p,i)=>`${x(i)},${y(Number(p.metric_value))}`).join(' ');let dots=points.map((p,i)=>`<circle cx="${x(i)}" cy="${y(Number(p.metric_value))}" r="3.5" fill="#79aafa"><title>${escapeHTML(p.observed_date+'：'+p.metric_value)}</title></circle>`).join('');let dateLabels=[0,Math.floor((points.length-1)/2),points.length-1].filter((x,i,a)=>a.indexOf(x)===i).map(i=>`<text x="${x(i)}" y="265" text-anchor="middle" font-size="12" fill="#93a4bd">${escapeHTML(points[i].observed_date)}</text>`).join('');svg.innerHTML=lines+`<polyline points="${poly}" fill="none" stroke="#78acff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>`+dots+dateLabels;
let p=points[0];$('chartnote').textContent=(DATA.metrics[p.metric_type]?.[1]||'')+' · 来源：'+(DATA.sources[p.source_type]||p.source_type)+' · 同范围历史观测点 '+points.length+' 个';}
async function load(){try{let r=await fetch('/api/data?mode='+mode);if(!r.ok)throw Error('HTTP '+r.status);DATA=await r.json();render()}catch(e){$('banner').textContent='读取失败：'+e.message}}
async function req(endpoint,payload){let r=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});let data=await r.json();if(!r.ok)throw Error(data.error||r.status);return data}
async function uploadCSV(){let file=$('csvfile').files[0];if(!file){$('uploadresult').textContent='请选择文件';return}if(file.size>2*1024*1024){$('uploadresult').textContent='文件不能超过2MB';return}try{let txt=await file.text(),res=await req('/api/import',{csv:txt});$('uploadresult').textContent='✅ 成功导入或更新 '+res.count+' 行；已切换真实区。';mode='real';$('mode').value=mode;await load()}catch(e){$('uploadresult').textContent='❌ '+e.message}}
$('entryform').addEventListener('submit',async e=>{e.preventDefault();const row=Object.fromEntries(new FormData(e.target));try{await req('/api/add',{row});$('addresult').textContent='✅ 保存成功（真实区）';mode='real';$('mode').value=mode;await load()}catch(err){$('addresult').textContent='❌ '+err.message}});
function download(url,name){let a=document.createElement('a');a.href=url;a.download=name;document.body.appendChild(a);a.click();a.remove()}
$('mode').onchange=e=>{mode=e.target.value;load()};$('keyword').onchange=renderSeries;$('series').onchange=draw;
$('tabs').querySelectorAll('button').forEach(b=>b.onclick=()=>{tab=b.dataset.tab;render()});
$('entryform').querySelector('[name="observed_date"]').value=new Date(Date.now()-new Date().getTimezoneOffset()*60000).toISOString().slice(0,10);
// 来源选项在请求返回后设置，保证与后端定义一致
load().then(()=>{for(let [code,v] of Object.entries(DATA.metrics))$('metricselect').insertAdjacentHTML('beforeend',`<option value="${escapeHTML(code)}">${escapeHTML(v[0])}</option>`);for(let [code,v] of Object.entries(DATA.sources))if(code!=='demo')$('sourceselect').insertAdjacentHTML('beforeend',`<option value="${escapeHTML(code)}">${escapeHTML(v)}</option>`)});
</script></body></html>'''


class AppHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # 不在控制台打印每个浏览器请求。
        return

    def _json(self, obj, status=200):
        b = json.dumps(obj, ensure_ascii=False, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _bytes(self, content, mime, *, attachment=None):
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        if attachment:
            self.send_header("Content-Disposition", 'attachment; filename="observations.csv"')
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        path = urlparse(self.path)
        if path.path == "/":
            self._bytes(PAGE.encode("utf-8"), "text/html; charset=utf-8")
            return
        if path.path == "/api/template":
            from datetime import date
            row = {k: "" for k in FIELDS}
            row.update(observed_date=date.today().isoformat(), platform="拼多多",
                       keyword="仅为格式示例_请替换", opportunity_type="商品",
                       metric_type="shop_search_visitors", metric_value=10,
                       source_type="manual_observation", source_name="我的观察",
                       source_scope="店铺A的搜索来源访客", notes="示例并非真实统计")
            self._bytes(export_csv([row]), "text/csv; charset=utf-8", attachment=True)
            return
        if path.path in ("/api/data", "/api/export"):
            mode = parse_qs(path.query).get("mode", ["real"])[0]
            if mode not in ("real", "demo"):
                self._json({"error": "非法数据区域"}, 400)
                return
            conn = connect(DB_PATH)
            try:
                rows = read_rows(conn, is_demo=(mode == "demo"))
            finally:
                conn.close()
            if path.path == "/api/export":
                self._bytes(export_csv(rows), "text/csv; charset=utf-8", attachment=True)
                return
            self._json({"rows": rows, "analysis": analyze(rows), "metrics": METRICS,
                        "sources": SOURCES, "mode": mode})
            return
        self._json({"error": "页面不存在"}, 404)

    def do_POST(self):
        path = urlparse(self.path)
        if path.path not in ("/api/add", "/api/import"):
            self._json({"error": "不支持的操作"}, 404)
            return
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            self._json({"error": "需要 JSON 请求"}, 415)
            return
        origin = self.headers.get("Origin")
        if origin and origin not in (f"http://{HOST}:{PORT}", f"http://localhost:{PORT}"):
            self._json({"error": "来源不符"}, 403)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._json({"error": "错误的文件长度"}, 400)
            return
        if length <= 0 or length > 2_700_000:
            self._json({"error": "请求为空或超过2.7MB"}, 413)
            return
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            conn = connect(DB_PATH)
            try:
                if path.path == "/api/import":
                    csvdata = payload["csv"].encode("utf-8")
                    count = import_csv(conn, csvdata)
                else:
                    count = add_rows(conn, [payload["row"]])
            finally:
                conn.close()
        except (ValueError, KeyError, TypeError, UnicodeError) as exc:
            self._json({"error": str(exc)}, 400)
            return
        self._json({"ok": True, "count": count})


def main():
    conn = connect(DB_PATH)
    try:
        seed_demo(conn)
    finally:
        conn.close()
    server = ThreadingHTTPServer((HOST, PORT), AppHandler)
    print(f"\n市场机会雷达已启动： http://{HOST}:{PORT}")
    print("仅限本机访问；不连接外部平台。按 Ctrl+C 关闭。\n")
    webbrowser.open(f"http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已关闭")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
