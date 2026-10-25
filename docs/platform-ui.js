let selectedPlatform='all';
function showPlatforms(){
  const groups=[...new Set(RadarPlatforms.platforms.map(p=>p.group))];
  $('platform-buttons').innerHTML='<button data-platform="all" '+(selectedPlatform==='all'?'class="active" aria-pressed="true"':'aria-pressed="false"')+'>全部平台</button>'+groups.map(group=>'<div class="platform-group"><span class="small muted">'+escapeHTML(group)+'</span><div class="platform-options">'+RadarPlatforms.platforms.filter(p=>p.group===group).map(p=>`<button data-platform="${escapeHTML(p.id)}" aria-pressed="${p.id===selectedPlatform}" class="${p.id===selectedPlatform?'active':''}">${escapeHTML(p.id)}<span class="platform-state ${p.metric?'good':''}">${p.metric?'每日自动':'待接入'}</span></button>`).join('')+'</div></div>').join('');
  $('platform-buttons').querySelectorAll('button').forEach(b=>b.onclick=()=>choosePlatform(b.dataset.platform));
  const p=RadarPlatforms.platforms.find(p=>p.id===selectedPlatform);
  $('platform-detail').classList.toggle('hide',!p);
  if(p){
    $('platform-detail').innerHTML=`<h3>${escapeHTML(p.id)} · ${escapeHTML(p.purpose)}</h3><p>${escapeHTML(p.hint)}</p><p>${p.metric?'自动公开数据已接入；每日任务可能有延迟，实际结果以采集状态为准。':'自动数据尚未接入。当前可手工记录或导入有权使用的数据；无数据时不生成热度和排名。'}</p><div class="flex">${p.url?safeLink(p.url,p.metric?'查看来源网站':'打开平台 / 官方入口'):''}${!p.metric?'<button id="platform-import">导入该平台记录</button>':''}</div>`;
    const btn=$('platform-import');if(btn)btn.onclick=()=>{mode='real';$('mode').value=mode;tab='import';load();};
    const entry=$('entryform').querySelector('[name="platform"]');
    if([...entry.options].some(o=>o.value===p.id))entry.value=p.id;
    if(!p.metric&&mode==='real'){
      $('banner').textContent=p.id+' · 仅显示你的导入记录；该平台尚未接入每日自动采集。';
      if(!DATA.rows.length)$('ranking').innerHTML='<div class="empty-platform"><h3>'+escapeHTML(p.id)+'尚无真实记录</h3><p>可在「导入数据」中添加该平台的授权报表或人工观察。接入后将按本平台单独分析商品与软件机会。</p><p>每日自动更新目前覆盖 GitHub 与维基百科，未将它们的数据归入本平台。</p></div>';
    }
  }
  const scope=p?p.id:'全部平台';
  $('scope-label').textContent='当前范围：'+scope+' · '+(mode==='public'?'公开自动数据':mode==='demo'?'模拟演示（非真实）':'个人导入记录');
  if(p)$('ranktitle').textContent=p.id+' · '+(tab==='商品'?'商品机会':tab==='软件'?'软件机会':'综合候选');
  // A source is never marked connected merely because it has imported observations.
  $('platform-matrix').innerHTML='<h2>平台接入状态</h2><div class="tableouter">'+table(['平台','建议用途','自动更新','当前记录','入口'],RadarPlatforms.platforms.map(x=>[escapeHTML(x.id),escapeHTML(x.purpose),x.metric?'每日11:23（公开关注）':'待接入',selectedPlatform===x.id||selectedPlatform==='all'?DATA.rows.filter(r=>r.platform===x.id).length:'切换查看',x.url?safeLink(x.url,'打开'):'—']))+'</div><p>此表的记录数随当前数据区域变化；导入记录不等于平台已自动接入。每个平台只分析其自身的记录。</p>';
}
function choosePlatform(value){
  selectedPlatform=value;
  if(value!=='all'){
    const next=RadarPlatforms.select(value,mode);mode=next.mode;
    if(next.metric){publicMetric=next.metric;$('public-metric').value=publicMetric;}
  }
  $('mode').value=mode;load();
}
function changeDataMode(value){
  mode=value;
  if(mode==='public'){
    const p=RadarPlatforms.platforms.find(p=>p.id===selectedPlatform);
    if(p&&!p.metric)selectedPlatform='all';
    if(p?.metric){publicMetric=p.metric;$('public-metric').value=publicMetric;}
  }
  load();
}
