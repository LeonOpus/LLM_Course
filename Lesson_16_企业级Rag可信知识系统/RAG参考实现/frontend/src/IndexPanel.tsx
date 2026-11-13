import {VisualNotice} from './VisualNotice';
import {createRequestGate} from './workspace';
import {RetrievalDebug} from './RetrievalDebug';
import {scoreLabel} from './retrievalPresentation';
import {chunkRangeLabel} from './chunkSources';
import {useEffect,useState,useRef} from 'react';
import {requestJSON} from './documents';
import type {Doc} from './documents';
import {startIndex,searchCandidates} from './retrieval';
import type {Retrieval} from './retrieval';
import {sourceLocation} from './sourceView';
interface Chunk {retrieval_ranks?:Record<string,number>;retrieval_scores?:Record<string,number>;chunk_id:string;doc_id:string;text:string;char_range:number[]|null;source_spans?:unknown[];metadata?:Record<string,unknown>;locator:Record<string,unknown>}
interface Preview {doc_id:string;chunk_count:number;chunks:Chunk[];config:{window:number;overlap:number;preserve_tables:boolean;strategy?:string};verification:string}
const describe=(error:unknown)=>error instanceof Error?error.message:'请求失败，请核对服务与配置';
export function IndexPanel({docs,refresh}:{docs:Doc[];refresh:()=>Promise<void>}){
 const previewGate=useRef(createRequestGate());
 useEffect(()=>()=>previewGate.current.dispose(),[]);
 const [id,setId]=useState(''),[preview,setPreview]=useState<Preview|null>(null),[notice,setNotice]=useState(''),[busy,setBusy]=useState('');
 const [question,setQuestion]=useState(''),[topK,setTopK]=useState('5'),[result,setResult]=useState<Retrieval|null>(null),[queryError,setQueryError]=useState('');
 const doc=docs.find(d=>d.doc_id===id);const canIndex=!!doc&&(doc.status==='parsed'||doc.status==='indexing'||(doc.status==='failed'&&doc.stage==='index'));
 useEffect(()=>{setPreview(null);setNotice('');},[id]);
 async function showChunks(){const request=previewGate.current.begin();setBusy('preview');setPreview(null);setNotice('');try{
  const value=await requestJSON(`/documents/${encodeURIComponent(id)}/chunks`,{signal:request.signal});
  if(value?.doc_id!==id||value?.verification!=='preview_only'||!Array.isArray(value?.chunks)||value.chunk_count!==value.chunks.length)throw new Error('切块预览不符合接口契约');if(request.current())setPreview(value);
 }catch(error){if(request.current())setNotice(describe(error));}finally{if(request.current())setBusy('');}}
 async function index(){setBusy('index');setNotice('');try{await startIndex(id);setNotice('入库请求已提交；处理结果以上方文档当前状态为准。');await refresh();}catch(error){setNotice(describe(error));}finally{setBusy('');}}
 async function query(){setBusy('query');setResult(null);setQueryError('');try{setResult(await searchCandidates(question,Number(topK)));}catch(error){setQueryError(describe(error));}finally{setBusy('');}}
 return <section className="index-panel" aria-labelledby="index-title"><p className="eyebrow">02 / 先查回原文，再写回答</p><h2 id="index-title">切块、入库与候选检索</h2><p>相似度不是准确率；本区域只检索候选，不生成答案。预览只在本机计算。入库请求百炼Embedding；查询时dense/hybrid请求Embedding，BM25不请求。</p><label htmlFor="index-document">选择需要入库的文档</label><select id="index-document" value={id} onChange={event=>{previewGate.current.dispose();setBusy('');setPreview(null);setId(event.target.value);}}><option value="">请选择一份已解析文档</option>{docs.map(d=><option key={d.doc_id} value={d.doc_id}>{d.name} · {d.status}</option>)}</select>{doc&&<div className="index-status"><p>文档：{doc.name} · 状态：{doc.status} · 已入库片段数：{doc.chunk_count}</p>{doc.error&&<p role="alert">{doc.error}</p>}</div>}<div className="doc-actions"><button disabled={!id||!!busy} onClick={()=>void showChunks()}>预览切块</button><button disabled={!canIndex||!!busy} onClick={()=>void index()}>{doc?.status==='indexing'?'恢复入库':'开始入库'}</button></div><p className="hint">处理中请等待列表刷新。后端重启导致中断时才恢复入库；同一进程尚在处理的请求会被拒绝。</p>{notice&&<p role="status">{notice}</p>}{preview&&<aside className="blocks"><h3>切块预览：{preview.chunk_count} 个片段</h3><p className="hint">分块策略：{preview.config.strategy??'baseline'} · 窗口{preview.config.window}字符 · 重叠{preview.config.overlap}字符 · 尚未通过预览写入数据库</p><p className="hint">输入来源标记：{[...new Set(preview.chunks.map(c=>String(c.metadata?.parser??'未声明')))].join('、')}。source_audit_docx表示本地原件结构，不是DocMind云解析。</p><details><summary>实际切块配置与计划指纹</summary><pre>{JSON.stringify(preview.config,null,2)}</pre></details>{preview.chunks.map(c=><article key={c.chunk_id}><h4>{sourceLocation(c.locator)}</h4><VisualNotice metadata={c.metadata}/><pre>{c.text}</pre><p>{chunkRangeLabel(c)}</p><details><summary>来源与片段编号</summary><pre>{JSON.stringify({chunk_id:c.chunk_id,doc_id:c.doc_id,locator:c.locator,char_range:c.char_range,source_spans:c.source_spans,metadata:c.metadata,retrieval_ranks:c.retrieval_ranks,retrieval_scores:c.retrieval_scores},null,2)}</pre></details></article>)}</aside>}<div className="retrieval-form"><h3>仅检索候选</h3><label htmlFor="candidate-question">输入你要检索的问题</label><textarea id="candidate-question" value={question} onChange={e=>setQuestion(e.target.value)} rows={3} placeholder="例如：X200 的功率是多少？"/><div className="doc-actions"><label htmlFor="candidate-top-k">top_k（最多返回几条）</label><input id="candidate-top-k" type="number" min="1" max="50" step="1" value={topK} onChange={e=>setTopK(e.target.value)}/><button disabled={!!busy} onClick={()=>void query()}>{busy==='query'?'正在检索…':'仅检索候选'}</button></div>{queryError&&<p role="alert">{queryError}</p>}{result&&<aside className="blocks"><h4>本次检索：{result.candidate_count} 个候选</h4>{result.mode==='no_documents'&&<p>当前没有可检索的已入库文档。请先完成入库并确认 ready；本次没有请求模型。</p>}{result.candidates.map(c=><article key={c.chunk_id}><h4>{sourceLocation(c.locator)}</h4><p>{scoreLabel(c.score_kind)}：{c.score}（排序分数，不是准确率）</p><VisualNotice metadata={c.metadata}/><pre>{c.text}</pre><details><summary>候选来源与字符范围</summary><pre>{JSON.stringify({doc_id:c.doc_id,chunk_id:c.chunk_id,locator:c.locator,char_range:c.char_range,source_spans:c.source_spans,metadata:c.metadata,retrieval_ranks:c.retrieval_ranks,retrieval_scores:c.retrieval_scores},null,2)}</pre></details></article>)}<RetrievalDebug profile={result.retrieval_profile} routes={result.retrieval_routes}/>{result.index_profile&&<details><summary>实际索引配置</summary><pre>{JSON.stringify(result.index_profile,null,2)}</pre></details>}{result.timing&&<details><summary>本次实际耗时</summary><pre>{JSON.stringify(result.timing,null,2)}</pre></details>}</aside>}</div></section>;
}
// cache: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
// checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
/* revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525 */
/* generated: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37 */
// cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
/* generated: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72 */
// cache: lpf2-18283 lpf2-19E2b
