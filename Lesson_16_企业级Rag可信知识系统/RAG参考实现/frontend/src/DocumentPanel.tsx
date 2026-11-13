import {useEffect,useRef,useState} from 'react';
import {requestJSON,startParse} from './documents';
import type {Doc,Block} from './documents';
import {SourcePanel} from './SourcePanel';
import {IndexPanel} from './IndexPanel';
import type {SourceReport} from './SourcePanel';
const labels:Record<string,string>={uploaded:'已上传',parsing:'解析中',parsed:'已解析',failed:'处理失败',indexing:'正在入库',ready:'已入库'};
const message=(e:unknown)=>e instanceof Error?e.message:'请求失败，请检查后端';
export function DocumentPanel({view='documents'}:{view?:'documents'|'retrieval'}){
 const [docs,setDocs]=useState<Doc[]>([]),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const [busy,setBusy]=useState(''),[selected,setSelected]=useState<string|null>(null),[blocks,setBlocks]=useState<Block[]>([]);
 const [source,setSource]=useState<{name:string;report:SourceReport}|null>(null);
 const [file,setFile]=useState<File|null>(null);const input=useRef<HTMLInputElement>(null);const inFlight=useRef(false);
 async function refresh(){
  if(inFlight.current)return;inFlight.current=true;
  try{const value=await requestJSON('/documents');if(!Array.isArray(value))throw new Error('文档列表格式异常');setDocs(value);setError('');}
  catch(e){setError('刷新失败，当前列表可能已过期：'+message(e));}finally{inFlight.current=false;}
 }
 useEffect(()=>{void refresh();const timer=setInterval(()=>void refresh(),3000);return()=>clearInterval(timer);},[]);
 async function upload(){if(!file)return;setBusy('upload');setNotice('正在上传…');try{
  const form=new FormData();form.append('file',file);const doc=await requestJSON('/documents',{method:'POST',body:form});
  if(doc?.status!=='uploaded'||typeof doc.doc_id!=='string')throw new Error('上传结果不符合接口契约');
  setNotice('上传完成。请点击“仅解析”；现在还没有解析或建立索引。');setFile(null);if(input.current)input.current.value='';await refresh();
 }catch(e){setNotice(message(e));}finally{setBusy('');}}
 async function parse(doc:Doc){setBusy(doc.doc_id);try{await startParse(doc.doc_id);setNotice('任务请求已接受，请以列表后续状态为准。');await refresh();}catch(e){setNotice(message(e));}finally{setBusy('');}}
 async function inspect(doc:Doc){setSource(null);setSelected(null);setBlocks([]);setBusy(doc.doc_id);try{const value=await requestJSON(`/documents/${doc.doc_id}/blocks`);if(!Array.isArray(value))throw new Error('解析块格式异常');setBlocks(value);setSelected(doc.name);setNotice('');}catch(e){setNotice(message(e));}finally{setBusy('');}}
 async function inspectOriginal(doc:Doc){setBusy(doc.doc_id);setSource(null);setSelected(null);try{
  const value=await requestJSON(`/documents/${encodeURIComponent(doc.doc_id)}/source-inspection`);
  if(value?.role!=='source_audit'||value?.doc_id!==doc.doc_id||value?.replaces_docmind!==false||!Array.isArray(value?.blocks)||!Array.isArray(value?.warnings)||!Array.isArray(value?.alignment))throw new Error('原件核对结果不符合接口契约');
  setSource({name:doc.name,report:value});setNotice('原件结构读取完成。请核对范围与来源，文档状态保持不变。');
 }catch(e){setNotice(message(e));}finally{setBusy('');}}
 if(view==='retrieval')return <section className="retrieval-page"><div className="page-heading"><p className="eyebrow">RETRIEVAL LAB</p><h1>检索调试</h1><p>先确认资料有没有被找到，再分析答案为什么出错。</p></div>{error&&<p role="alert">{error}</p>}<IndexPanel docs={docs} refresh={refresh}/></section>;
 return <section className="documents" aria-labelledby="documents-title"><div className="section-heading"><div><p className="eyebrow">01 / 先核对资料，再开始问答</p><h2 id="documents-title">知识库</h2></div><button onClick={()=>void refresh()}>刷新列表</button></div><p>支持 PDF、Word、Excel、PPT、图片、HTML、Markdown、TXT、CSV。单文件不超过 50 MB。</p><div className="upload"><label htmlFor="document-file">选择资料</label><input id="document-file" ref={input} type="file" accept=".pdf,.docx,.doc,.xlsx,.xls,.pptx,.ppt,.png,.jpg,.jpeg,.bmp,.tif,.tiff,.html,.htm,.md,.txt,.csv" onChange={e=>setFile(e.target.files?.[0]??null)}/><button disabled={!file||!!busy} onClick={()=>void upload()}>{busy==='upload'?'正在上传…':'上传文件'}</button></div><p className="hint">CSV 在本机解析。其他格式使用 DocMind 云服务；有凭证时点击“仅解析”会提交云任务，可能产生费用。解析完成仍未建立检索索引。</p>{notice&&<p role="status">{notice}</p>}{error&&<p role="alert">{error}</p>}{docs.length===0?<p className="empty">还没有资料。先上传课程里的练习 CSV，核对一次完整流程。</p>:<ul className="doc-list">{docs.map(doc=><li key={doc.doc_id}><div className="doc-title"><h3><img className="doc-file-icon" src={'/assets/s2/repository/file/'+(doc.kind.toLowerCase()==='pdf'?'pdf':['doc','docx'].includes(doc.kind.toLowerCase())?'doc':'other')+'.svg'} alt=""/>{doc.name}</h3><span className={'state state-'+doc.status}>{labels[doc.status]??doc.status}</span></div><p>{doc.kind.toUpperCase()} · {doc.block_count} 个解析块 · {doc.chunk_count} 个检索块</p>{doc.error&&<p role="alert">{doc.error}</p>}<div className="doc-actions"><button disabled={!!busy} onClick={()=>void inspectOriginal(doc)}>核对原文件</button><a href={`/api/documents/${doc.doc_id}/source`} target="_blank" rel="noreferrer">下载原文件</a>{(doc.status==='parsed'||doc.status==='indexing'||doc.status==='ready'||(doc.status==='failed'&&doc.stage==='index'))?<button disabled={!!busy} onClick={()=>void inspect(doc)}>查看解析</button>:<button disabled={!!busy} onClick={()=>void parse(doc)}>{doc.status==='parsing'?'恢复查询':doc.status==='failed'?'重试解析':'仅解析'}</button>}</div>{doc.status==='parsing'&&<small>系统正在刷新状态。只有后端重启导致任务中断时才使用“恢复查询”；仍在运行的任务会拒绝重复请求。</small>}</li>)}</ul>}{source&&<SourcePanel key={source.report.doc_id} name={source.name} report={source.report} onClose={()=>setSource(null)}/>}{selected&&<aside className="blocks"><div className="section-heading"><h3>{selected} · 解析内容</h3><button onClick={()=>setSelected(null)}>收起解析</button></div>{blocks.map((block,i)=><article key={i}><h4>块 {i+1}</h4><pre>{block.text}</pre><p className="hint">来源定位</p><pre>{JSON.stringify(block.locator,null,2)}</pre></article>)}</aside>}<details className="knowledge-index"><summary>下一步：预览切块、入库与检索</summary><IndexPanel docs={docs} refresh={refresh}/></details></section>;
}
/* generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222 */
/* revision: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368 */
/* revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525 */
/* revision: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37 */
// checksum: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
/* revision: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72 */
/* generated: lpf2-18283 lpf2-19E2b */
