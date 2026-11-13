import {useRef,useState} from 'react';
import {filterCases,metricLabels,parseComparison,percent,hasFixtureEvidence} from './evaluation';
import type {Comparison,Change,Side} from './evaluation';
import './evaluation.css';
const labels:Record<Change,string>={gain:'变好',regression:'退步',unchanged:'不变',pending:'待复核'};
const judgment=(v:boolean|null)=>v===null?'待确认':v?'正确':'未通过';
function EvidenceSide({side,title}:{side:Side;title:string}){
 return <article><h3>{title} · {judgment(side.scores.answer_correct)}</h3><p>执行状态：{side.execution} · 耗时 {side.elapsed_ms===null?'未知':`${side.elapsed_ms.toFixed(0)} ms`}</p><pre className="eval-answer">{side.answer??'本题没有完成回答。'}</pre>
 {(['citations','trace','scores'] as const).map(k=><details key={k}><summary>{{citations:'实际引用',trace:'检索与上下文轨迹',scores:'本题各项评分'}[k]}</summary><pre>{JSON.stringify(side[k],null,2)}</pre></details>)}</article>;
}
export function EvaluationPanel(){
 const [bundle,setBundle]=useState<Comparison|null>(null),[filename,setFilename]=useState(''),[error,setError]=useState('');
 const [change,setChange]=useState(''),[task,setTask]=useState(''),[query,setQuery]=useState(''),[selected,setSelected]=useState(''),[loading,setLoading]=useState(false);
 const version=useRef(0);
 async function load(file:File|undefined){if(!file)return;const current=++version.current;setLoading(true);setBundle(null);setSelected('');setError('');setFilename('');
  try{if(file.size>20*1024*1024)throw new Error('文件超过20MB，请分批导出评估运行。');const data=parseComparison(await file.text());if(current!==version.current)return;setBundle(data);setFilename(file.name);setChange('');setTask('');setQuery('');}
  catch(e){if(current===version.current)setError(e instanceof Error?e.message:'导入失败');}finally{if(current===version.current)setLoading(false);}}
 const cases=bundle?filterCases(bundle.cases,change,task,query):[];
 const chosen=cases.find(c=>c.case_id===selected);
 const fixture=bundle&&hasFixtureEvidence(bundle);
 return <section className="evaluation-panel"><div className="page-heading"><span className="eyebrow">MEASURE BEFORE YOU OPTIMIZE</span><h1>质量评估</h1><p>先看配对样本，再看差值。展开一题，追到它的回答和证据。</p></div>
 <div className="eval-import"><div><h2>导入一次策略对比</h2><p>选择比较工具导出的 JSON。文件只在当前浏览器读取，不上传，也不调用云模型。</p></div><label className="primary file-button">{loading?'读取中…':'选择比较文件'}<input type="file" accept=".json,application/json" onChange={e=>{void load(e.target.files?.[0]);e.target.value='';}}/></label></div>
 {error&&<p role="alert" className="error">{error}</p>}
 {!bundle&&!loading&&<div className="empty"><h2>还没有导入比较结果</h2><p>先完成两次运行与逐题复核，再按课程“评估对比面板”导出文件。<br/>未复核的题也可以导入，会显示为待确认。</p></div>}
 {bundle&&<><div className="eval-notice" role="status"><strong>{fixture?'固定响应演练 · 不代表真实模型效果':'导入运行记录 · 服务真实性需结合运行日志核对'}</strong><p>{filename} · {bundle.cases.length}题 · {bundle.comparison.review_status==='provisional_model_assisted'?'含模型辅助评分，仍待人工核查':'查看复核状态与分母后解释结果'}</p><p>页面检查文件结构与内部一致性，不重新读取原始运行目录。请使用课程导出工具生成文件。</p></div>
 <div className="eval-stats"><article><small>两侧均已复核</small><strong>{bundle.comparison.paired_n} / {bundle.cases.length}</strong></article><article><small>尚不能配对</small><strong>{bundle.comparison.pending}</strong></article><article><small>已配对子集正确率差值</small><strong>{bundle.comparison.answer_accuracy_delta===null?'待确认':`${bundle.comparison.answer_accuracy_delta>0?'+':''}${(bundle.comparison.answer_accuracy_delta*100).toFixed(1)} pp`}</strong><small>pp = 百分点；不代表完整题集提升</small></article></div>
 <div className="eval-table-wrap"><table className="eval-table"><caption>两次运行指标 · 每格同时显示有效分母</caption><thead><tr><th>指标</th><th>基线</th><th>对照</th></tr></thead><tbody>{Object.entries(metricLabels).map(([key,label])=><tr key={key}><th>{label}</th>{(['before','after'] as const).map(side=>{const m=bundle.runs[side].metrics[key];return <td key={side}><strong>{percent(m.value)}</strong><small>已确认 {m.n}/{m.total} · 待确认 {m.pending} · 不适用 {m.not_applicable}</small>{m.value!==null&&<div className="eval-bar" aria-hidden="true"><i style={{width:`${m.value*100}%`}}/></div>}</td>;})}</tr>)}</tbody></table></div>
 <details className="eval-config"><summary>两侧配置、执行状态、耗时与用量</summary><div className="eval-sides">{(['before','after'] as const).map(side=><article key={side}><h3>{side==='before'?'基线':'对照'}</h3><pre>{JSON.stringify(bundle.runs[side],null,2)}</pre></article>)}</div><p>tokens仅含最终生成用量；request_usage按实际事件分列查询Embedding、改写、重排和生成，两份统计有重叠，不能相加。缺失事件、失败请求与入库须另查全局账本。cost为null表示未知，不能当作免费。配置同时改变多项时，不能把差值归因于单个策略。</p></details>
 <h2>逐题追踪</h2><div className="eval-filters"><label>变化<select value={change} onChange={e=>{setChange(e.target.value);setSelected('');}}><option value="">全部</option>{Object.entries(labels).map(([k,v])=><option value={k} key={k}>{v}（{bundle.comparison.changes[k]??0}）</option>)}</select></label><label>主任务<select value={task} onChange={e=>{setTask(e.target.value);setSelected('');}}><option value="">全部分类</option>{[...new Set(bundle.cases.map(c=>c.primary_task))].sort().map(k=><option key={k}>{k}</option>)}</select></label><label>查找问题<input value={query} placeholder="输入题号或问题关键词" onChange={e=>{setQuery(e.target.value);setSelected('');}}/></label></div>
 <p aria-live="polite">当前显示 {cases.length} / {bundle.cases.length} 题；筛选不改变上方总体指标。</p><div className="eval-cases">{cases.map(c=><button key={c.case_id} className={selected===c.case_id?'selected':''} onClick={()=>setSelected(selected===c.case_id?'':c.case_id)} aria-expanded={selected===c.case_id}><span className={'eval-change '+c.change}>{labels[c.change]}</span><span><strong>{c.case_id} · {c.question}</strong><small>{c.primary_task} · {c.primary_source_format} · {judgment(c.before.scores.answer_correct)} → {judgment(c.after.scores.answer_correct)}</small></span></button>)}</div>
 {chosen&&<section className="eval-detail"><h2>{chosen.case_id} · 两侧原始回答</h2><p>{chosen.question}</p><div className="eval-sides"><EvidenceSide side={chosen.before} title="基线"/><EvidenceSide side={chosen.after} title="对照"/></div></section>}
 <details className="eval-config"><summary>如何解释本报告的边界</summary><ul>{bundle.limitations.map((text,i)=><li key={i}>{text}</li>)}</ul></details></>}
 </section>;
}
/* generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222 */
/* revision: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368 */
/* generated: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525 */
/* generated: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37 */
// cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
/* generated: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72 */
/* revision: lpf2-18283 lpf2-19E2b */
