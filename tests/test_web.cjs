const assert=require('node:assert/strict');
const {spawnSync}=require('node:child_process');
const path=require('node:path');
const R=require('../docs/engine.js');
const base={observed_date:'2026-01-14',platform:'拼多多',keyword:'测试词',opportunity_type:'商品',metric_type:'search_index',metric_value:10,source_type:'manual_observation',source_name:'测试来源',source_scope:'固定范围',source_url:'',notes:''};
const series=(extra={})=>Array.from({length:14},(_,i)=>({...base,observed_date:'2026-01-'+String(i+1).padStart(2,'0'),metric_value:i<7?10:15,...extra}));
let cases=[[],series(),series({metric_type:'search_result_count'}),series({metric_type:'suggestion_rank'}),[base,{...base,observed_date:'2026-01-01'}],series().map((r,i)=>({...r,metric_value:i<7?0:10})),[...series(),...series({source_name:'另一个来源',metric_value:20})],R.demoRows()];
const py=spawnSync('python',['-c','import sys,json; from core import analyze; print(json.dumps([analyze(rows) for rows in json.load(sys.stdin)],ensure_ascii=False))'],{cwd:path.resolve(__dirname,'..'),input:JSON.stringify(cases),encoding:'utf8',env:{...process.env,PYTHONIOENCODING:'utf-8'}});
assert.equal(py.status,0,py.stderr);
function approximate(actual,expected) {
  if(typeof expected==='number') assert.ok(Math.abs(actual-expected)<1e-8,`${actual} != ${expected}`);
  else if(Array.isArray(expected)){assert.equal(actual.length,expected.length);expected.forEach((v,i)=>approximate(actual[i],v));}
  else if(expected&&typeof expected==='object'){assert.deepEqual(Object.keys(actual).sort(),Object.keys(expected).sort());for(const k of Object.keys(expected))approximate(actual[k],expected[k]);}
  else assert.equal(actual,expected);
}
JSON.parse(py.stdout).forEach((expected,i)=>approximate(R.analyze(cases[i]),expected));
assert.equal(R.analyze(series()).series[0].change_pct,50);
assert.equal(R.analyze(series({metric_type:'search_result_count'})).candidates[0].rankable,false);
assert.equal(R.analyze(cases[4]).series[0].change_pct,null);
assert.equal(R.analyze(cases[5]).series[0].change_pct,null);
assert.throws(()=>R.parseCSV(R.exportCSV(R.demoRows())),/模拟数据/);
assert.throws(()=>R.validate({...base,observed_date:'2026-02-30'}),/日期/);
assert.throws(()=>R.validate({...base,metric_value:''}),/数字/);
assert.throws(()=>R.validate({...base,source_url:'javascript:alert(1)'}),/http/);
assert.throws(()=>R.validate({...base,metric_type:'suggestion_rank',metric_value:1.5}),/正整数/);
const special={...base,keyword:'逗号,引号"测试',notes:'换行\n第二行'};
assert.deepEqual(R.parseCSV(R.exportCSV([special]))[0],R.validate(special));
assert.ok(R.exportCSV([{...base,notes:'=SUM(1)'}]).includes("'=SUM(1)"));
assert.throws(()=>R.parseCSV(R.FIELDS.join(',')+'\n"unclosed'),/引号/);
assert.throws(()=>R.parseCSV(R.FIELDS.join(',')+'\n2026-01-01'),/列数/);
let saved=R.mergeRows([],series());
assert.equal(saved.length,14);
saved=R.mergeRows(saved,[{...base,metric_value:30}]);
assert.equal(saved.length,14);
assert.equal(saved.find(r=>r.observed_date==='2026-01-14').metric_value,30);
const before=JSON.stringify(saved);
assert.throws(()=>R.mergeRows(saved,[base,{...base,keyword:'invalid',source_type:'demo'}]),/模拟数据/);
assert.equal(JSON.stringify(saved),before);
console.log('PASS: 8 Python/JavaScript analysis parity cases; CSV, validation, source separation and atomic upsert checks.');
require('./test_platforms.cjs');
