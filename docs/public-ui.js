/* This file defines helpers; app.js owns navigation and calls them after loading. */
let publicMetric='wiki_pageviews',publicFeed=null,loadSequence=0;
function safeLink(url,label){
  try{const u=new URL(url);if(!['https:','http:'].includes(u.protocol))return '无链接';return `<a href="${escapeHTML(u.href)}" target="_blank" rel="noopener noreferrer">${escapeHTML(label)}</a>`;}catch{return '无链接';}
}
function localTime(value){return value?new Date(value).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false}):'尚无成功记录';}
async function loadPublicFeed(){
  const response=await fetch('./data/public.json',{cache:'no-store'});
  if(!response.ok)throw Error('公开数据文件读取失败（'+response.status+'）');
  const feed=await response.json();
  if(feed.schema_version===2&&Array.isArray(feed.series)&&Array.isArray(feed.receipts)){
    feed.rows=feed.series.flatMap(s=>s.points.map(([day,value,receipt])=>({...s.base,...feed.receipts[receipt],observed_date:day,metric_value:value})));
  }
  if(![1,2].includes(feed.schema_version)||!Array.isArray(feed.rows)||!Array.isArray(feed.sources)||!Number.isFinite(Date.parse(feed.generated_at)))throw Error('公开数据格式无效');
  feed.rows=feed.rows.map(r=>{
    const clean=Radar.validate(r);
    if(clean.source_type!=='public_api'||r.is_demo!==0||!['wiki_pageviews','github_stars'].includes(clean.metric_type))throw Error('公开数据含无效来源标记');
    return {...clean,api_url:r.api_url,fetched_at:r.fetched_at};
  });
  return feed;
}
function enhancePublicView(){
  const isPublic=mode==='public';
  $('public-controls').classList.toggle('hide',!isPublic);
  $('source-health').classList.toggle('hide',!isPublic);
  $('rank-note').textContent=isPublic?'固定观察清单，按同一指标的可比变化排序；不是全网热词榜或利润榜。缺失日不补零，来源失败或过期时暂停排名。':'排序：需求线索上涨的平台数 → 可比需求指标变化中位数。不同统计口径不可合并为全网热度；本店访客不代表全平台搜索。';
  if(!isPublic)return;
  $('banner').textContent='公开真实数据 · 百科阅读与开源关注信号，不代表闲鱼、小红书或拼多多搜索量、销量。';
  const feed=publicFeed;
  if(!feed){$('update-status').textContent='正在读取公开数据…';return;}
  const old=Date.now()-Date.parse(feed.generated_at)>36*3600000;
  $('update-status').textContent=`${old?'⚠ 更新已超过36小时，请检查任务':feed.status==='ok'?'✓ 本轮采集正常':'⚠ 部分来源失败，旧记录保留原日期'} · 最近采集：${localTime(feed.generated_at)}（北京时间） · ${feed.successful_sources}/${feed.total_sources} 个来源成功 · 每天11:23更新，可能延迟`;
  const items=curCandidates(),wiki=publicMetric==='wiki_pageviews';
  $('ranktitle').textContent=(tab==='all'?'综合':tab)+'公开关注候选';
  $('ranking').innerHTML=items.length?table(['关键词','类别',wiki?'近7日日均阅读':'累计Star','最新观测日',wiki?'前后7日变化':'7日净变化率',wiki?'有效观察日':'相邻日Star净变化','状态','来源'],items.map(x=>[escapeHTML(x.keyword),escapeHTML(x.opportunity_type),fmt(x.current_value),escapeHTML(x.latest_date),x.stale?'暂不排名':trend(x.median_change_pct),wiki?escapeHTML(x.coverage):x.net_change===null?'积累中':escapeHTML((x.net_change>0?'+':'')+x.net_change),escapeHTML(x.status),safeLink(x.source_url,'查看原始来源')])):'<p>当前类别没有该来源的数据。商品方向可选择「百科阅读关注」。</p>';
  $('chartnote').textContent+=' · '+(wiki?'UTC自然日，缺失日期不补零':'北京时间每日快照；累计Star不是日新增');
  $('source-health').innerHTML='<h2>每日采集状态</h2><p>百科数据由官方公开统计回填；GitHub历史从接入日起积累。以下记录显示每个观察对象的最新采集结果。</p><div class="tableouter">'+table(['观察对象','来源','状态','数据日期','最近成功（北京）','原始接口'],feed.sources.filter(s=>selectedPlatform==='all'||(selectedPlatform==='GitHub'?s.provider==='github':selectedPlatform==='维基百科'?s.provider==='wikipedia':false)).map(s=>[escapeHTML(s.keyword),escapeHTML(s.provider),escapeHTML(s.status==='ok'?'成功':'失败：'+s.error),escapeHTML(s.latest_observation||'无'),escapeHTML(localTime(s.last_success_at)),safeLink(s.api_url,'API')]))+'</div>';
}
