/* Public attention signals stay separate from market demand and demo data. */
(function(root){
  'use strict';
  const DAY=86400000, day=s=>Date.parse(s+'T00:00:00Z')/DAY;
  const mean=a=>a.length?a.reduce((s,v)=>s+v,0)/a.length:null;
  function analyze(rows,metric,today,sources=[]){
    const grouped=new Map();
    for(const r of rows.filter(r=>r.metric_type===metric)){
      const k=JSON.stringify([r.keyword,r.opportunity_type,r.platform,r.metric_type,r.source_scope]);
      if(!grouped.has(k))grouped.set(k,[]);grouped.get(k).push(r);
    }
    const candidates=[];
    for(const points of grouped.values()){
      points.sort((a,b)=>a.observed_date.localeCompare(b.observed_date));
      const p=points.at(-1),end=day(p.observed_date),days=new Map(points.map(r=>[day(r.observed_date),r.metric_value]));
      const source=sources.find(s=>s.keyword===p.keyword&&s.opportunity_type===p.opportunity_type&&s.provider===(metric==='wiki_pageviews'?'wikipedia':'github'));
      const stale=day(today)-end>(metric==='wiki_pageviews'?3:1)||source?.status==='error';
      let change=null,current=p.metric_value,previous=null,net=null,status='历史积累中',coverage='';
      if(metric==='wiki_pageviews'){
        const before=[...days].filter(([d])=>d>=end-13&&d<end-6).map(([,v])=>v),after=[...days].filter(([d])=>d>=end-6&&d<=end).map(([,v])=>v);
        current=mean(after);previous=mean(before);coverage=`${before.length}/7 → ${after.length}/7 天`;
        if(before.length>=5&&after.length>=5&&previous>0){change=(current/previous-1)*100;status=change>0?'阅读关注上升':'阅读关注未上升';}
        else status=previous===0?'前期为零，不算增幅':'可比日数不足';
      }else{
        coverage=points.length+' 天快照';
        if(days.has(end-1))net=current-days.get(end-1);
        if(days.has(end-7)&&days.get(end-7)>0){previous=days.get(end-7);change=(current/previous-1)*100;status=change>0?'Star关注上升':'Star关注未上升';}
      }
      if(stale)status='来源失败或数据过期';
      candidates.push({keyword:p.keyword,opportunity_type:p.opportunity_type,platforms:p.platform,metric_type:metric,current_value:current,previous_value:previous,median_change_pct:change,net_change:net,latest_date:p.observed_date,coverage,status,rankable:change!==null&&!stale,source_url:p.source_url,source_scope:p.source_scope,stale});
    }
    // No cross-metric composite score; insufficient history stays unranked.
    candidates.sort((a,b)=>Number(b.rankable)-Number(a.rankable)||((b.rankable?b.median_change_pct:0)-(a.rankable?a.median_change_pct:0))||a.keyword.localeCompare(b.keyword,'zh-CN'));
    return {asof:rows.length?rows.map(r=>r.observed_date).sort().at(-1):null,candidates,series:[]};
  }
  const api={analyze};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.PublicRadar=api;
})(typeof globalThis!=='undefined'?globalThis:this);
