import {VisualNotice} from './VisualNotice';
import {readContextDebug} from './contextPresentation';
export function ContextDebug({trace}:{trace:unknown}){
 const data=readContextDebug(trace);
 return <section aria-label="上下文原文补全"><h3>送给模型的原文</h3><p>本次策略：{data.mode} · 正文字符预算：{data.used??'未知'} / {data.max??'未知'}</p><p>字符数不等于 Token 数；补全条件不代表答案一定正确。父块没有独立召回分数。</p>
 {data.hits.length===0?<p>本次记录尚无最终上下文。</p>:data.hits.map((h,i)=><details key={String(h.chunk_id)}><summary>上下文 {i+1} · {h.type==='parent_context'?'补全后的原文小节':'保留的片段'} · {String(h.text).length} 字符</summary><VisualNotice metadata={h.metadata}/><pre>{String(h.text)}</pre><p>文档：{String(h.doc_id??'未知')} · 片段：{String(h.chunk_id)}</p><p>全部原文范围（每段保留独立定位）</p><pre>{JSON.stringify(h.source_spans??{locator:h.locator,char_range:h.char_range},null,2)}</pre></details>)}
 {data.decisions.length>0&&<><h4>逐个候选的处理结果</h4><ul>{data.decisions.map((d,i)=><li key={i}>{d.label}<br/><code>{String(d.child_id??'未提供子块编号')}</code></li>)}</ul></>}
 </section>;
}
/* generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222 */
// cache: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
/* generated: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525 */
/* generated: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37 */
// cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
// checksum: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
// cache: lpf2-18283 lpf2-19E2b
