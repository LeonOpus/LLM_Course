import {useEffect,useRef,useState} from 'react';
import {fetchHealth} from './health';
import type {Health} from './health';
import {requestJSON} from './documents';
import {documentCounts} from './workspace';
export function Overview(){
 const [snapshot,setSnapshot]=useState<{health:Health;counts:{total:number;ready:number};at:string}|null>(null),[error,setError]=useState(''),[loading,setLoading]=useState(false);
 const active=useRef(true),busy=useRef(false);
 async function refresh(){if(busy.current)return;busy.current=true;setLoading(true);setSnapshot(null);setError('');try{const [health,docs]=await Promise.all([fetchHealth(),requestJSON('/documents')]);const counts=documentCounts(docs);if(active.current)setSnapshot({health,counts,at:new Date().toLocaleTimeString()});}catch(e){if(active.current){setSnapshot(null);setError(e instanceof Error?e.message:'读取失败');}}finally{busy.current=false;if(active.current)setLoading(false);}}
 useEffect(()=>{active.current=true;void refresh();const timer=setInterval(()=>void refresh(),15000);return()=>{active.current=false;clearInterval(timer);};},[]);
 return <><section className="page-heading"><p className="eyebrow">WORKSPACE STATUS</p><h1>环境检查</h1><p>查看当前配置和文档状态，确认实操的起点。</p></section><section className="connection"><div><h2>当前工作区</h2><p>配置存在仅表示已填写，模型权限、余额与数据库连接需实际调用验证。</p><p role="status">{loading?'正在读取实际状态…':snapshot?`后端可连接 · 最近读取 ${snapshot.at}`:'尚无可用的当前状态'}</p>{error&&<p role="alert">{error}。旧状态已清除，可重新检查。</p>}</div><button disabled={loading} onClick={()=>void refresh()}>重新检查工作区</button></section>{snapshot&&<><section className="overview-counts"><article><strong>{snapshot.counts.total}</strong><span>实际文档</span></article><article><strong>{snapshot.counts.ready}</strong><span>已入库文档</span></article><article><strong>{snapshot.health.models.dimension}</strong><span>配置的向量维度</span></article></section><section className="workspace-config"><h2>本次后端返回的配置</h2><p>生成模型：{snapshot.health.models.chat} · Embedding：{snapshot.health.models.embedding}</p><p>百炼配置：{snapshot.health.configured.bailian?'已填写':'未填写'} · DocMind配置：{snapshot.health.configured.docmind?'已填写':'未填写'} · 重排配置：{snapshot.health.configured.rerank?'已填写':'未填写'}</p><p>当前索引：<code>{snapshot.health.index_configuration.collection}</code></p><p>切块：{snapshot.health.index_configuration.chunk_strategy} · 召回：{snapshot.health.query_configuration.retrieval_mode} · 改写：{snapshot.health.query_configuration.query_rewrite} · 生成：{snapshot.health.query_configuration.generation_policy}</p><p>上下文：{snapshot.health.context_configuration.context_policy==='parent_section'?'同小节原文补全':'原始片段（基线）'}</p><details><summary>查看完整公开配置</summary><pre>{JSON.stringify(snapshot.health,null,2)}</pre></details></section></>}</>;
}
// checksum: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
// cache: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
// cache: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
// checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
// cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
// checksum: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
// cache: lpf2-18283 lpf2-19E2b
