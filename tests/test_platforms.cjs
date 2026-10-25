const assert=require('node:assert/strict');
const P=require('../docs/platforms.js'),R=require('../docs/engine.js');
const base={platform:'闲鱼',keyword:'相同关键词',opportunity_type:'商品',metric_type:'search_index',source_type:'manual_observation',source_name:'测试',source_scope:'固定范围',source_url:'',notes:''};
const rows=Array.from({length:14},(_,i)=>({...base,observed_date:'2026-01-'+String(i+1).padStart(2,'0'),metric_value:i<7?10:20}));
const mixed=[...rows,...rows.map(r=>({...r,platform:'拼多多',metric_value:500}))];
const selected=P.filter(mixed,'闲鱼');
assert.equal(selected.length,14);
assert.equal(R.analyze(selected).candidates[0].platforms,'闲鱼');
assert.equal(R.analyze(selected).candidates[0].median_change_pct,100);
assert.ok(!R.exportCSV(selected).includes('拼多多'));
assert.equal(P.filter(mixed,'京东').length,0);
assert.equal(P.filter(mixed,'all').length,28);
assert.equal(P.filter(mixed,'咸鱼').length,14);
assert.equal(R.validate({...rows[0],platform:'咸鱼'}).platform,'闲鱼');
assert.equal(R.validate({...rows[0],platform:'B站'}).platform,'哔哩哔哩');
for(const p of P.platforms){
  assert.equal(R.validate({...rows[0],platform:p.id}).platform,p.id);
  if(!p.metric)assert.equal(P.select(p.id,'public').mode,'real');
}
assert.deepEqual(P.select('GitHub','real'),{mode:'public',metric:'github_stars'});
assert.deepEqual(P.select('维基百科','demo'),{mode:'public',metric:'wiki_pageviews'});
assert.equal(P.platforms.filter(p=>p.metric).length,2);
console.log('PASS: platform-isolated analysis/export, empty states, platform aliases and honest auto-source routing.');
