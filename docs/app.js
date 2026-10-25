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
const choices=items.map(x=>JSON.stringify([x.keyword,x.opportunity_type]));let old=$('keyword').value;$('keyword').innerHTML=items.map(x=>`<option value="${escapeHTML(JSON.stringify([x.keyword,x.opportunity_type]))}">${escapeHTML(x.keyword)} · ${escapeHTML(x.opportunity_type)}</option>`).join('');if(choices.includes(old))$('keyword').value=old;renderSeries();
let quality=DATA.rows.slice().sort((a,b)=>b.observed_date.localeCompare(a.observed_date));$('qualitytable').innerHTML=quality.length?table(['日期','平台','关键词','类别','指标','原始值','来源类型声明','来源名称','统计范围'],quality.map(x=>[x.observed_date,escapeHTML(x.platform),escapeHTML(x.keyword),escapeHTML(x.opportunity_type),escapeHTML(DATA.metrics[x.metric_type]?.[0]||x.metric_type),escapeHTML(x.metric_value),escapeHTML(DATA.sources[x.source_type]||x.source_type),escapeHTML(x.source_name),escapeHTML(x.source_scope)])):'<p>暂无记录</p>';
}
function renderSeries(){const [kw,kind]=JSON.parse($('keyword').value||'[]');const points=DATA.rows.filter(x=>x.keyword===kw&&x.opportunity_type===kind);let opts=[],map=Object.create(null);for(const p of points){let k=JSON.stringify([p.platform,p.metric_type,p.source_type,p.source_name,p.source_scope]);if(!map[k]){map[k]=[];opts.push(k)}map[k].push(p)}
$('series').innerHTML=opts.map(k=>{let p=map[k][0];return `<option value="${escapeHTML(k)}">${escapeHTML(p.platform)} · ${escapeHTML(DATA.metrics[p.metric_type]?.[0]||p.metric_type)} · ${escapeHTML(p.source_name)} · ${escapeHTML(p.source_scope)}</option>`}).join('');$('series')._points=map;draw();}
function draw(){let points=($('series')._points||{})[$('series').value]||[];points=points.slice().sort((a,b)=>a.observed_date.localeCompare(b.observed_date));let svg=$('graph');if(!points.length){svg.innerHTML='';$('chartnote').textContent='没有足够的数据系列。';return}
let values=points.map(p=>Number(p.metric_value)),mn=Math.min(...values),mx=Math.max(...values);if(mx===mn){mn-=1;mx+=1}let firstDay=Date.parse(points[0].observed_date),span=Math.max(86400000,Date.parse(points.at(-1).observed_date)-firstDay);let x=i=>55+(Date.parse(points[i].observed_date)-firstDay)*810/span,y=v=>235-((v-mn)/(mx-mn))*183;
let lines=[0,.25,.5,.75,1].map(t=>{let yy=235-t*183;return `<line x1="55" x2="865" y1="${yy}" y2="${yy}" stroke="#2e3a4b" stroke-width="1"/><text x="43" y="${yy+4}" text-anchor="end" fill="#93a4bd" font-size="12">${(mn+t*(mx-mn)).toFixed(1)}</text>`}).join('');
let poly=points.map((p,i)=>`${x(i)},${y(Number(p.metric_value))}`).join(' ');let dots=points.map((p,i)=>`<circle cx="${x(i)}" cy="${y(Number(p.metric_value))}" r="3.5" fill="#79aafa"><title>${escapeHTML(p.observed_date+'：'+p.metric_value)}</title></circle>`).join('');let dateLabels=[0,Math.floor((points.length-1)/2),points.length-1].filter((x,i,a)=>a.indexOf(x)===i).map(i=>`<text x="${x(i)}" y="265" text-anchor="middle" font-size="12" fill="#93a4bd">${escapeHTML(points[i].observed_date)}</text>`).join('');svg.innerHTML=lines+`<polyline points="${poly}" fill="none" stroke="#78acff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>`+dots+dateLabels;
let p=points[0];$('chartnote').textContent=(DATA.metrics[p.metric_type]?.[1]||'')+' · 来源：'+(DATA.sources[p.source_type]||p.source_type)+' · 同范围历史观测点 '+points.length+' 个';}
const STORAGE_KEY='market-opportunity-radar-v1:observations';
function readSaved(){
  let raw; try { raw=localStorage.getItem(STORAGE_KEY); } catch { throw Error('浏览器禁止本地存储，请允许此站点使用存储后重试'); }
  if(!raw)return [];
  const rows=JSON.parse(raw);if(!Array.isArray(rows))throw Error('本地记录格式无效');
  return rows.map(r=>Radar.validate(r));
}
async function load(){try{
  const rows=mode==='demo'?Radar.demoRows():readSaved();
  DATA={rows,analysis:Radar.analyze(rows),metrics:Radar.METRICS,sources:Radar.SOURCES,mode};render();
}catch(e){DATA={rows:[],analysis:{candidates:[],series:[]},metrics:Radar.METRICS,sources:Radar.SOURCES};render();$('banner').textContent='读取失败：'+e.message;}}
async function req(endpoint,payload){
  const incoming=endpoint==='/api/import'?Radar.parseCSV(payload.csv):[Radar.validate(payload.row)];
  const merged=Radar.mergeRows(readSaved(),incoming);
  try{localStorage.setItem(STORAGE_KEY,JSON.stringify(merged));}catch{throw Error('浏览器存储不可用或空间不足，未保存；请先导出备份。');}
  return {count:incoming.length};
}
async function uploadCSV(){let file=$('csvfile').files[0];if(!file){$('uploadresult').textContent='请选择文件';return}if(file.size>2*1024*1024){$('uploadresult').textContent='文件不能超过2MB';return}try{let txt=await file.text(),res=await req('/api/import',{csv:txt});$('uploadresult').textContent='✅ 成功导入或更新 '+res.count+' 行；已切换真实区。';mode='real';$('mode').value=mode;await load()}catch(e){$('uploadresult').textContent='❌ '+e.message}}
$('entryform').addEventListener('submit',async e=>{e.preventDefault();const row=Object.fromEntries(new FormData(e.target));try{await req('/api/add',{row});$('addresult').textContent='✅ 保存成功（真实区）';mode='real';$('mode').value=mode;await load()}catch(err){$('addresult').textContent='❌ '+err.message}});
function download(url,name){
  const text=url.startsWith('/api/template')?'\uFEFF'+Radar.FIELDS.join(',')+'\r\n':Radar.exportCSV(DATA.rows);
  if(!url.startsWith('/api/template'))name=mode==='demo'?'模拟数据_非真实平台数据.csv':'我的观察记录.csv';
  const objectUrl=URL.createObjectURL(new Blob([text],{type:'text/csv;charset=utf-8'}));
  const a=document.createElement('a');a.href=objectUrl;a.download=name;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(objectUrl),1000);
}
$('mode').onchange=e=>{mode=e.target.value;load()};$('keyword').onchange=renderSeries;$('series').onchange=draw;
$('tabs').querySelectorAll('button').forEach(b=>b.onclick=()=>{tab=b.dataset.tab;render()});
$('entryform').querySelector('[name="observed_date"]').value=Radar.today();
// 来源选项在请求返回后设置，保证与后端定义一致
load().then(()=>{for(let [code,v] of Object.entries(DATA.metrics))$('metricselect').insertAdjacentHTML('beforeend',`<option value="${escapeHTML(code)}">${escapeHTML(v[0])}</option>`);for(let [code,v] of Object.entries(DATA.sources))if(code!=='demo')$('sourceselect').insertAdjacentHTML('beforeend',`<option value="${escapeHTML(code)}">${escapeHTML(v)}</option>`)});
