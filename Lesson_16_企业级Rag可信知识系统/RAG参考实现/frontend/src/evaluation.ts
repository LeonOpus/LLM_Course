export type Change='gain'|'regression'|'unchanged'|'pending';
export type Metric={value:number|null;n:number;total:number;pending:number;not_applicable:number};
export type Run={planned:number;config:Record<string,unknown>;metrics:Record<string,Metric>;execution_counts:Record<string,number>;review_status:string;latency_ms:unknown;tokens:unknown;query_rewrite_tokens?:unknown;request_usage?:unknown;cost:unknown;observed_configurations:unknown;fingerprints:unknown};
export type Side={execution:string;answer:string|null;elapsed_ms:number|null;status:string|null;citations:unknown[];trace:Record<string,unknown>;scores:{answer_correct:boolean|null;[key:string]:unknown}};
export type EvalCase={case_id:string;question:string;primary_task:string;primary_source_format:string;change:Change;before:Side;after:Side};
export type Comparison={schema_version:string;verification:string;runs:{before:Run;after:Run};comparison:{paired_n:number;pending:number;answer_accuracy_delta:number|null;review_status:string;changes:Record<string,number>};cases:EvalCase[];limitations:string[]};
export const metricLabels:Record<string,string>={answer_accuracy:'回答正确率',behavior_accuracy:'行为正确率',retrieval_recall:'候选证据组召回',context_recall:'上下文证据组召回',citation_precision:'引用支持率',citation_complete:'引用完整率',rag_success:'完整RAG成功率'};
const object=(v:unknown):v is Record<string,unknown>=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const count=(v:unknown)=>typeof v==='number'&&Number.isSafeInteger(v)&&v>=0;
const score=(v:unknown)=>v===null||typeof v==='boolean';
function fail(message:string):never{throw new Error('比较文件无效：'+message);}
export function parseComparison(text:string):Comparison{
 if(text.length>20*1024*1024)fail('文件超过20MB');
 let raw:unknown;try{raw=JSON.parse(text);}catch{fail('不是合法JSON，请选择导出工具生成的文件');}
 if(!object(raw)||raw.schema_version!=='rag-comparison-view/1')fail('不支持的版本');
 if(raw.verification!=='recomputed_from_frozen_records'||!object(raw.runs)||!object(raw.comparison)||!Array.isArray(raw.cases)||!raw.cases.length)fail('缺少运行、配对或逐题记录');
 const ids=new Set<string>();let known=0,delta=0;
 const changes:Record<Change,number>={gain:0,regression:0,unchanged:0,pending:0};
 for(const c of raw.cases){
  if(!object(c)||typeof c.case_id!=='string'||ids.has(c.case_id))fail('题号缺失或重复');ids.add(c.case_id);
  if(typeof c.question!=='string'||typeof c.primary_task!=='string'||typeof c.primary_source_format!=='string')fail('题目分类不完整');
  for(const name of ['before','after']){
   const s=c[name];if(!object(s)||!object(s.scores)||!score(s.scores.answer_correct)||!object(s.trace)||!Array.isArray(s.citations)||!(s.answer===null||typeof s.answer==='string')||!['ok','error','not_run'].includes(String(s.execution)))fail('逐题运行记录不完整');
   if(s.execution!=='ok'&&s.scores.answer_correct!==null)fail('执行失败或未运行的题目不能有已确认得分');
   if(s.elapsed_ms!==null&&(typeof s.elapsed_ms!=='number'||!Number.isFinite(s.elapsed_ms)||s.elapsed_ms<0))fail('耗时须为非负数或null');
  }
  const a=(c.before as Side).scores.answer_correct,b=(c.after as Side).scores.answer_correct;
  const state:Change=a===null||b===null?'pending':!a&&b?'gain':a&&!b?'regression':'unchanged';
  if(c.change!==state)fail('题目变化与得分矛盾');changes[state]++;
  if(state!=='pending'){known++;delta+=Number(b)-Number(a);}
 }
 const comparison=raw.comparison;
 if(comparison.paired_n!==known||comparison.pending!==raw.cases.length-known||!object(comparison.changes))fail('配对数量不一致');
 for(const k of Object.keys(changes) as Change[])if((comparison.changes[k]??0)!==changes[k])fail('变化汇总不一致');
 const expected=known?delta/known:null;
 if(expected===null?comparison.answer_accuracy_delta!==null:typeof comparison.answer_accuracy_delta!=='number'||Math.abs(comparison.answer_accuracy_delta-expected)>1e-10)fail('配对差值不一致');
 for(const name of ['before','after']){
  const r=raw.runs[name];if(!object(r)||r.planned!==raw.cases.length||!object(r.config)||!object(r.metrics)||!object(r.execution_counts)||typeof r.review_status!=='string')fail('运行数量或信息不完整');
  if(Object.values(r.execution_counts).some(n=>!count(n))||Object.values(r.execution_counts).reduce<number>((a,b)=>a+(b as number),0)!==r.planned)fail('执行数量不一致');
  const sides=raw.cases.map(c=>(c as EvalCase)[name as 'before'|'after']);
  const executions:Record<string,number>={ok:0,error:0,not_run:0};
  for(const side of sides)executions[side.execution]++;
  if(Object.entries(r.execution_counts).some(([key,n])=>!(key in executions)||n!==executions[key])||Object.entries(executions).some(([key,n])=>(r.execution_counts as Record<string,unknown>)[key]!==n&&n!==0))fail('执行汇总与逐题记录不一致');
  const scores=sides.map(side=>side.scores.answer_correct).filter(value=>value!==null);
  const accuracy=r.metrics.answer_accuracy;
  const value=scores.length?scores.filter(Boolean).length/scores.length:null;
  if(!object(accuracy)||accuracy.n!==scores.length||accuracy.total!==sides.length||accuracy.pending!==sides.length-scores.length||accuracy.not_applicable!==0||(value===null?accuracy.value!==null:typeof accuracy.value!=='number'||Math.abs(accuracy.value-value)>1e-10))fail('回答正确率指标汇总与逐题评分不一致');
  for(const key of Object.keys(metricLabels)){
   const m=r.metrics[key];if(!object(m)||![m.n,m.total,m.pending,m.not_applicable].every(count))fail('指标分母不完整');
   const {n,total,pending,not_applicable}=m as Metric;
   if(n+pending!==total||total+not_applicable!==r.planned)fail('指标分母不一致');
   if(n===0?m.value!==null:typeof m.value!=='number'||!Number.isFinite(m.value)||m.value<0||m.value>1)fail('指标未知值或范围不符');
  }
 }
 if(!Array.isArray(raw.limitations)||!raw.limitations.every(s=>typeof s==='string'))fail('缺少验证边界');
 return raw as unknown as Comparison;
}
export const percent=(value:number|null)=>value===null?'待确认 / 不适用':`${(value*100).toFixed(1)}%`;
export function filterCases(cases:EvalCase[],change:string,task:string,query:string){
 const q=query.trim().toLowerCase();return cases.filter(c=>(!change||c.change===change)&&(!task||c.primary_task===task)&&(!q||`${c.case_id} ${c.question}`.toLowerCase().includes(q)));
}

function visualFixture(profile:unknown):boolean {
 if(!object(profile)||!object(profile.index_profile)||!object(profile.index_profile.visual_augmentation))return false;
 const bundles=profile.index_profile.visual_augmentation.bundles;
 return Array.isArray(bundles)&&bundles.some(b=>object(b)&&b.origin==='fixture');
}
export function hasFixtureEvidence(bundle:Comparison):boolean {
 const runMarked=[bundle.runs.before,bundle.runs.after].some(r=>{
  if(r.config.execution_origin==='protocol_fixture')return true;
  if(Array.isArray(r.observed_configurations)&&r.observed_configurations.some(visualFixture))return true;
  const u=r.request_usage;
  return object(u)&&object(u.origins)&&typeof u.origins.fixture==='number'&&u.origins.fixture>0;
 });
 return runMarked||bundle.cases.some(c=>[c.before,c.after].some(side=>{
  if(visualFixture(side.trace))return true;
  const events=side.trace.usage_events;
  return Array.isArray(events)&&events.some(e=>object(e)&&e.origin==='fixture');
 }));
}
/* generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222 */
// cache: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
/* generated: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525 */
// checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
/* generated: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc */
// cache: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
/* revision: lpf2-18283 lpf2-19E2b */
