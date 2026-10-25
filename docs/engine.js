/* Browser analysis engine. No network requests or platform data collectors. */
(function(root) {
  'use strict';
  const FIELDS = ['observed_date','platform','keyword','opportunity_type','metric_type','metric_value','source_type','source_name','source_scope','source_url','notes'];
  const METRICS = {
    wiki_pageviews:['百科每日阅读次数','公开关注信号；不是搜索量或购买需求','同条目同范围比较'],
    github_stars:['GitHub累计Star数','开源项目关注；不是用户数或付费需求','需积累历史快照'],
    search_index:['平台搜索指数','需求线索（相对指数）','越高越强'],
    platform_searches:['平台披露的搜索次数','需求线索（仅限明确授权数据）','越高越强'],
    shop_search_visitors:['本店搜索来源访问量','局部需求线索（仅本店）','越高越强'],
    search_result_count:['观察到的搜索结果数','供给观察（不是需求）','越高不代表需求越强'],
    content_count:['观察到的相关内容数','内容供给观察（不是需求）','越高不代表需求越强'],
    suggestion_rank:['搜索建议词位置','曝光位置观察（不是搜索量）','数字越小位置越靠前']
  };
  const SOURCES = {public_api:'公开API记录（手动导入时仅为来源声明）',official_export:'用户声明：官方后台导出（未经系统验证）',authorized_api:'用户声明：授权接口（未经系统验证）',manual_observation:'人工观察记录',third_party_estimate:'第三方提供/估算（待核验）',demo:'模拟演示，非真实平台数据'};
  const DEMAND = new Set(['search_index','platform_searches','shop_search_visitors']);
  const DAY = 86400000;
  const dateNumber = s => Date.parse(s+'T00:00:00Z')/DAY;
  const dateString = n => new Date(n*DAY).toISOString().slice(0,10);
  const today = () => new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
  const mean = a => a.length ? a.reduce((s,v)=>s+v,0)/a.length : null;
  const median = a => { a = a.slice().sort((x,y)=>x-y); const n=a.length; return n ? (a[Math.floor((n-1)/2)]+a[Math.floor(n/2)])/2 : null; };
  const key = (r,fields) => JSON.stringify(fields.map(f=>r[f]));
  const SERIES_FIELDS = ['platform','keyword','opportunity_type','metric_type','source_type','source_name','source_scope'];
  function validate(row, isDemo=false) {
    const r=Object.fromEntries(FIELDS.map(f=>[f,String(row[f]??'').trim()]));
    r.platform = ({"咸鱼": "闲鱼", "淘宝": "淘宝/天猫", "天猫": "淘宝/天猫", "淘宝天猫": "淘宝/天猫", "B站": "哔哩哔哩", "b站": "哔哩哔哩", "bilibili": "哔哩哔哩"})[r.platform] || r.platform;
    if (!/^\d{4}-\d{2}-\d{2}$/.test(r.observed_date) || !Number.isFinite(dateNumber(r.observed_date)) || dateString(dateNumber(r.observed_date))!==r.observed_date) throw Error('观察日期必须是有效的 YYYY-MM-DD');
    if(dateNumber(r.observed_date)>dateNumber(today())+1) throw Error('观察日期不能在未来超过一天');
    if(!["拼多多", "小红书", "闲鱼", "淘宝/天猫", "京东", "抖音", "1688", "知乎", "哔哩哔哩", "其他", "维基百科", "GitHub"].includes(r.platform)) throw Error('平台名称不支持，请使用页面平台列表中的名称');
    if(!r.keyword || [...r.keyword].length>80) throw Error('关键词必须是1至80个字符');
    if(!['商品','软件'].includes(r.opportunity_type)) throw Error('类别必须是商品或软件');
    if(!Object.hasOwn(METRICS,r.metric_type)) throw Error('未知的指标类型');
    if(!/^[+]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i.test(r.metric_value)) throw Error('指标值必须是非负数字');
    const value=Number(r.metric_value);
    if(!Number.isFinite(value)||value<0||value>1e15) throw Error('指标值必须是合理的非负有限数');
    if(r.metric_type==='suggestion_rank' && (!Number.isInteger(value)||value<1)) throw Error('建议词位置必须为正整数');
    if(!Object.hasOwn(SOURCES,r.source_type)) throw Error('未知的来源类型');
    if(r.source_type==='demo'&&!isDemo) throw Error('模拟数据不得导入真实数据区');
    if(!r.source_name||!r.source_scope) throw Error('来源名称和统计范围必填');
    if([...r.source_name].length>120||[...r.source_scope].length>160) throw Error('来源名称或范围过长');
    if(r.source_url) { try { const u=new URL(r.source_url); if(!['http:','https:'].includes(u.protocol)) throw Error(); } catch { throw Error('来源链接必须是有效的 http(s) 地址或留空'); } }
    if([...r.notes].length>600) throw Error('备注不能超过600字符');
    return {...r,metric_value:value,is_demo:Number(isDemo)};
  }
  function analyze(rows) {
    if(!rows.length) return {asof:null,series:[],candidates:[]};
    const asof=rows.reduce((s,r)=>r.observed_date>s?r.observed_date:s,''), end=dateNumber(asof);
    const groups=new Map();
    for(const r of rows) { const k=key(r,SERIES_FIELDS); if(!groups.has(k)) groups.set(k,[]); groups.get(k).push(r); }
    const series=[];
    for(const points of groups.values()) {
      const r=points[0], days=new Map(points.map(p=>[p.observed_date,Number(p.metric_value)]));
      const before=[],after=[];
      for(const [d,v] of days) { const n=dateNumber(d); if(n>=end-13&&n<end-6) before.push(v); if(n>=end-6&&n<=end) after.push(v); }
      const valid=before.length>=2&&after.length>=2&&mean(before)>0;
      const change=valid?(r.metric_type==='suggestion_rank'?1-mean(after)/mean(before):mean(after)/mean(before)-1)*100:null;
      series.push({...Object.fromEntries(SERIES_FIELDS.map(f=>[f,r[f]])),metric_name:METRICS[r.metric_type][0],metric_description:METRICS[r.metric_type][1],current_value:mean(after),previous_value:mean(before),current_n:after.length,previous_n:before.length,change_pct:change,valid,latest_date:[...days.keys()].sort().at(-1),is_demand:DEMAND.has(r.metric_type),is_demo:r.source_type==='demo'});
    }
    const grouped=new Map();
    for(const s of series) { const k=key(s,['keyword','opportunity_type']); if(!grouped.has(k)) grouped.set(k,[]); grouped.get(k).push(s); }
    const candidates=[];
    for(const elements of grouped.values()) {
      const demand=elements.filter(v=>v.valid&&v.is_demand), change=median(demand.map(v=>v.change_pct));
      candidates.push({keyword:elements[0].keyword,opportunity_type:elements[0].opportunity_type,platforms:[...new Set(elements.map(v=>v.platform))].sort().join(', '),up_platforms:new Set(demand.filter(v=>v.change_pct>0).map(v=>v.platform)).size,median_change_pct:change,demand_sources:demand.length,sources:[...new Set(elements.map(v=>v.platform+'·'+v.metric_name))].sort().join(', '),status:demand.length?(change>0?'需求指标上行（仅样本内）':'需求指标未上行'):elements.some(v=>v.valid)?'仅有供给/位置线索':'样本不足',rankable:!!demand.length});
    }
    candidates.sort((a,b)=>Number(b.rankable)-Number(a.rankable)||b.up_platforms-a.up_platforms||(b.median_change_pct??-1e6)-(a.median_change_pct??-1e6)||(a.keyword<b.keyword?-1:a.keyword>b.keyword?1:0));
    return {asof,series,candidates};
  }
  function demoRows() {
    const configs=[['小红书','AI简历优化','软件','search_index',45,.58],['小红书','图片批量处理','软件','search_index',62,.26],['小红书','自学英语打卡','软件','search_index',70,-.05],['拼多多','磁吸手机支架','商品','shop_search_visitors',26,.65],['拼多多','透明手机壳','商品','shop_search_visitors',34,.21],['拼多多','桌面理线器','商品','shop_search_visitors',18,.34],['闲鱼','二手电脑升级','软件','search_result_count',90,.20],['闲鱼','桌面收纳盒','商品','search_result_count',70,.38]];
    const rows=[],end=dateNumber(today())-1;
    for(const [platform,keyword,opportunity_type,metric_type,baseline,growth] of configs) for(let i=0;i<14;i++) rows.push({observed_date:dateString(end-13+i),platform,keyword,opportunity_type,metric_type,metric_value:Number((baseline*(1+((i%3)-1)*.035)*(i>=7?1+growth:1)).toFixed(1)),source_type:'demo',source_name:'模拟数据生成器',source_scope:platform+'的虚构观察样本',source_url:'',notes:'虚构样本；不代表任何平台实际趋势',is_demo:1});
    return rows;
  }
  function parseCSV(text) {
    if(new TextEncoder().encode(text).length>2*1024*1024) throw Error('文件不能超过2MB');
    text=text.replace(/^\uFEFF/,'');
    const records=[]; let record=[],field='',state='start';
    const finishField=()=>{record.push(field);field='';state='start';};
    const finishRow=()=>{finishField();if(record.some(x=>x!==''))records.push(record);record=[];};
    for(let i=0;i<text.length;i++) {
      const c=text[i];
      if(state==='quoted') { if(c==='"') {if(text[i+1]==='"'){field+='"';i++;}else state='closed';} else field+=c; continue; }
      if(c===',') {finishField();continue;}
      if(c==='\n'||c==='\r') {if(c==='\r'&&text[i+1]==='\n')i++;finishRow();continue;}
      if(c==='"'&&state==='start') {state='quoted';continue;}
      if(state==='closed'||c==='"') throw Error('CSV 引号格式无效');
      field+=c;state='plain';
    }
    if(state==='quoted') throw Error('CSV 有未闭合的引号');
    if(field!==''||record.length||state==='closed')finishRow();
    if(records.length<2)throw Error('CSV 需要表头和数据记录');
    const header=records.shift();
    if(new Set(header).size!==header.length)throw Error('CSV 表头重复');
    const missing=FIELDS.filter(f=>!header.includes(f)); if(missing.length)throw Error('CSV 缺少字段：'+missing.join(', '));
    if(records.length>20000)throw Error('每次最多导入20000行');
    return records.map((cells,i)=>{if(cells.length!==header.length)throw Error('第'+(i+2)+'条记录列数不符');try{return validate(Object.fromEntries(header.map((f,j)=>[f,cells[j]])));}catch(e){throw Error('第'+(i+2)+'条记录：'+e.message);}});
  }
  function exportCSV(rows) {
    const quote=v=>'"'+String(v).replace(/"/g,'""')+'"';
    return '\uFEFF'+FIELDS.join(',')+'\r\n'+rows.map(r=>FIELDS.map(f=>{let v=String(r[f]??'');if(f!=='metric_value'&&/^[=+\-@\t\r]/.test(v.trimStart()))v="'"+v;return quote(v);}).join(',')).join('\r\n');
  }
  function mergeRows(existing,incoming) {
    // Match SQLite's upsert identity; changing a source declaration updates that observation.
    const fields=['observed_date','platform','keyword','opportunity_type','metric_type','source_name','source_scope'];
    const map=new Map(existing.map(r=>[key(r,fields),r]));
    const clean=incoming.map(r=>validate(r));
    for(const r of clean)map.set(key(r,fields),r);
    return [...map.values()].sort((a,b)=>b.observed_date.localeCompare(a.observed_date));
  }
  const api={FIELDS,METRICS,SOURCES,SERIES_FIELDS,today,validate,analyze,demoRows,parseCSV,exportCSV,mergeRows};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  else root.Radar=api;
})(typeof globalThis!=='undefined'?globalThis:this);
