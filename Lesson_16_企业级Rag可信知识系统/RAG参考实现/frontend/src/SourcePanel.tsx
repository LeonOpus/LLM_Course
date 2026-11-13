import {useState} from 'react';
import {sourceLocation} from './sourceView';
export interface SourceBlock {doc_id:string;type:string;text:string;locator:Record<string,unknown>;metadata:Record<string,unknown>}
export interface SourceReport {doc_id:string;kind:string;role:string;replaces_docmind:boolean;source_sha256:string;blocks:SourceBlock[];structure:Record<string,unknown>;warnings:{code:string;message:string}[];alignment:{parsed_block_id:string;status:string;matches:Record<string,unknown>[]}[];alignment_notice:string}
export function SourcePanel({name,report,onClose}:{name:string;report:SourceReport;onClose:()=>void}){
 const [filter,setFilter]=useState('');const normalized=filter.trim().toLocaleLowerCase();
 const visible=report.blocks.filter(block=>JSON.stringify({text:block.text,locator:block.locator,metadata:block.metadata}).toLocaleLowerCase().includes(normalized));
 return <aside className="blocks source-panel" aria-labelledby="source-title"><div className="section-heading"><div><p className="eyebrow">原件核对 / source_audit</p><h3 id="source-title">{name} · 原文件结构</h3></div><button onClick={onClose}>关闭原件核对</button></div><p>本机读取的原文件结构，用来核对来源。它没有替换 DocMind 文本，也不会把文档改成“已解析”。</p><ul className="scope-warnings">{report.warnings.map(w=><li key={w.code}>{w.message}</li>)}</ul><p>原生块共 {report.blocks.length} 个 · 当前显示 {visible.length} 个</p><label htmlFor="source-filter">查找原件文本或位置</label><input id="source-filter" type="search" value={filter} onChange={e=>setFilter(e.target.value)} placeholder="例如 B22、paragraph-5 或 型号"/><details><summary>结构信息与文件指纹</summary><pre>{JSON.stringify({source_sha256:report.source_sha256,structure:report.structure},null,2)}</pre></details><details><summary>候选来源位置：{report.alignment.length} 个解析块</summary><p>{report.alignment_notice}</p>{report.alignment.length===0?<p>尚无解析文本可对齐。原件核对成功不表示 DocMind 已经解析成功。</p>:report.alignment.map(a=><article key={a.parsed_block_id}><p>{a.parsed_block_id} · {a.status}</p><pre>{JSON.stringify(a.matches,null,2)}</pre></article>)}</details>{visible.length===0&&<p className="empty">没有匹配的原生文本块。先检查筛选词和上面的核对范围；PDF或图片仅有结构信息也可能是正常结果。</p>}{visible.map(block=><article key={String(block.locator.block_id)}><h4>{sourceLocation(block.locator)}</h4><pre>{block.text}</pre><details><summary>来源与原生字段</summary><pre>{JSON.stringify({locator:block.locator,metadata:block.metadata},null,2)}</pre></details></article>)}</aside>;
}
/* generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222 */
// cache: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
/* revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525 */
/* revision: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37 */
// cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
/* generated: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72 */
/* generated: lpf2-18283 lpf2-19E2b */
