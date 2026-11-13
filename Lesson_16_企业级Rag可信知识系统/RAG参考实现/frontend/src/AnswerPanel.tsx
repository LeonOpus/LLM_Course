import {VisualNotice} from './VisualNotice';
import {ContextDebug} from './ContextDebug';
import {GenerationDebug} from './GenerationDebug';
import {readGenerationDebug} from './generationPresentation';
import {QueryRewriteDebug} from './QueryRewriteDebug';
import {advanceHistory,readQueryDebug} from './conversation';
import {RetrievalDebug} from './RetrievalDebug';
import {readRetrievalDebug} from './retrievalPresentation';
import {useEffect,useRef,useState} from 'react';
import {consumeAnswer,reduceAnswer} from './answer';
import type {AnswerState,Message,AnswerStrategy} from './answer';
import {requestJSON} from './documents';
import {sourceLocation} from './sourceView';
const stageName:Record<string,string>={query_rewrite:'补全检索问题',retrieve_rewritten:'检索改写后的问题',rerank:'重排候选',connecting:'连接后端',retrieve:'检索资料',context:'选择上下文',generate:'生成与校验',completed:'本次流程完成'};
const statusName={answered:'有引用的回答',refused:'资料不足，拒答',clarify:'需要补充条件'};

export function AnswerPanel(){
 const [question,setQuestion]=useState('');
 const [submittedQuestion,setSubmittedQuestion]=useState('');
 const [citationIndex,setCitationIndex]=useState<number|null>(null);
 const citationDialog=useRef<HTMLDialogElement>(null);
 useEffect(()=>{if(citationIndex!==null)citationDialog.current?.showModal();else citationDialog.current?.close();},[citationIndex]);
 const [strategy,setStrategy]=useState<AnswerStrategy>('baseline');
 const [state,setState]=useState<AnswerState>({status:'idle'});
 const [keepHistory,setKeepHistory]=useState(false);
 const [history,setHistory]=useState<Message[]>([]);
 const [historyNotice,setHistoryNotice]=useState('');
 const [trace,setTrace]=useState<unknown>(null);
 const [traceError,setTraceError]=useState('');
 const sequence=useRef(0),controller=useRef<AbortController|null>(null);
 useEffect(()=>()=>{sequence.current++;controller.current?.abort();},[]);
 const running=state.status==='running';
 async function loadTrace(runId:string,seq:number){
  try{const value=await requestJSON('/traces/'+encodeURIComponent(runId));if(seq===sequence.current)setTrace(value);}
  catch(error){if(seq===sequence.current)setTraceError(error instanceof Error?error.message:'读取运行记录失败');}
 }
 async function ask(){
  if(!question.trim()||running)return;
  setSubmittedQuestion(question);setCitationIndex(null);
  controller.current?.abort();const seq=++sequence.current;const request=new AbortController();controller.current=request;
  setState(prev=>reduceAnswer(prev,{type:'start'}));setTrace(null);setTraceError('');
  let timedOut=false;const timeout=setTimeout(()=>{timedOut=true;request.abort();},180000);
  try{
   await consumeAnswer(question,keepHistory?history:[],event=>{
    if(seq!==sequence.current)return;
    setState(prev=>reduceAnswer(prev,event));
    if(event.type==='result'&&event.payload){
     setTrace(event.payload.trace);
     if(keepHistory){const next=advanceHistory(history,question,event);setHistory(next.messages);setHistoryNotice(next.removed?`历史窗口已移出最早${next.removed}条消息；下一问若依赖其中型号，请重新说明。`:'');}
    }
    if(event.type==='error'&&event.run_id)void loadTrace(event.run_id,seq);
   },request.signal,undefined,strategy);
  }catch(error){
   if(seq!==sequence.current)return;
   setState(prev=>reduceAnswer(prev,{type:request.signal.aborted&&!timedOut?'cancel':'error',message:timedOut?'等待超过180秒，已停止接收；请用运行编号追查，云端计费停止时点未知':error instanceof Error?error.message:'请求失败'}));
  }finally{clearTimeout(timeout);if(seq===sequence.current)controller.current=null;}
 }
 function stop(){sequence.current++;controller.current?.abort();controller.current=null;setState(prev=>reduceAnswer(prev,{type:'cancel'}));}
 const citation=citationIndex===null?null:state.result?.citations[citationIndex];
 return <section className="answer-panel chat-layout" aria-label="知识问答">
  <div className="chat-main"><div className="chat-scroll">
   {state.status==='idle'?<div className="chat-welcome"><img className="welcome-logo" src="/assets/s2/logo.png" alt=""/><p className="eyebrow">YOUR KNOWLEDGE, CONNECTED</p><h1>你好，有什么可以帮你？</h1><p>从设备资料中查参数、找步骤、核对售后政策。<br/>答案与引用一起呈现，方便你回到原文确认。</p><div className="prompt-cards">{['X200 的功率是多少？','设备出现故障后，应该先检查什么？','不同型号的保修条件有什么区别？'].map((q,i)=><button key={q} onClick={()=>{setQuestion(q);document.getElementById('answer-question')?.focus();}}><img src={'/assets/s2/chat/'+['file.svg','search.svg','object.svg'][i]} alt=""/><span>{['查设备参数','查处理步骤','查售后政策'][i]}<small>{q}</small></span><b>↗</b></button>)}</div><a className="welcome-link" href="#documents">还没有资料？先去知识库上传 →</a></div>:<>
    <div className="question-message"><span className="user-avatar">我</span><p>{submittedQuestion}</p></div>
    <div className="assistant-message"><img className="assistant-avatar" src="/assets/s2/logo.png" alt="助手"/><div className="assistant-content"><h2>知识库助手</h2>
     <div role="status" className={'answer-status '+state.status}>{state.status==='running'?`进行中：${stageName[state.stage||'']||state.stage}；已接收草稿 ${state.draft?.length||0} 字符`:state.status==='cancelled'?'已停止接收；未确认的草稿不是正式答案，云端停止计费时点尚未确认':state.status==='error'?'本次请求失败，没有正式答案':'本次流程已完成，请核对结果与来源'}</div>
     {state.error&&<p role="alert">{state.error}</p>}
     {state.result&&<article className="answer-result"><span className="answer-kind">{statusName[state.result.status]}</span><p className="answer-text">{state.result.answer}</p>
      {state.result.trace?.mode==='no_documents'&&<p className="hint">本次为本地空库规则：没有可检索的已入库文档，没有请求百炼模型。<a href="#documents">去上传资料</a></p>}
      <div className="answer-meta"><span>{state.result.citations.length} 处引用</span><span>语义支持：{state.result.validation?.semantic_support==='not_evaluated'?'尚未评估':state.result.validation?.semantic_support||'未知'}</span></div>
      <details><summary>运行编号与模型用量</summary><p>运行编号：<code>{state.run_id}</code></p><p>最终生成 Token 用量：{state.result.usage&&Object.keys(state.result.usage).length?JSON.stringify(state.result.usage):'未知（没有返回用量，不填0）'}</p></details>
     </article>}
     {!state.result&&state.run_id&&<p className="hint">运行编号：<code>{state.run_id}</code></p>}
     {(trace||state.debug||state.run_id)&&<details className="trace-details"><summary>查看检索过程与上下文预算</summary><p className="hint">completed 只表示流程结束，不能作为回答正确的判据。未启用重排时 reranked 为 null。</p>{state.run_id&&<button onClick={()=>void loadTrace(state.run_id!,sequence.current)}>刷新本次运行记录</button>}{traceError&&<p role="alert">{traceError}</p>}<RetrievalDebug {...readRetrievalDebug(trace)}/><QueryRewriteDebug {...readQueryDebug(trace)}/><ContextDebug trace={trace}/><GenerationDebug {...readGenerationDebug(trace,state.result)}/><details><summary>完整运行记录</summary><pre>{JSON.stringify(trace||state.debug||{run_id:state.run_id},null,2)}</pre></details></details>}
     {state.draft&&<details><summary>原始 JSON 草稿（不是正式答案）</summary><pre>{state.draft}</pre></details>}
    </div></div>
   </>}
  </div>
  <div className="composer-dock"><details className="conversation-settings"><summary>对话设置<span> {keepHistory?'保留最近对话':'单轮问答'} · {strategy==='rerank'?'百炼重排':'原始排序'}</span></summary><div className="settings-body"><div className="doc-actions"><label className="check-label"><input type="checkbox" checked={keepHistory} disabled={running} onChange={e=>setKeepHistory(e.target.checked)}/>保留最近对话（最多 6 条）</label><button disabled={running} onClick={()=>{setHistory([]);setHistoryNotice('');}}>清空历史</button></div>{historyNotice&&<p role="status">{historyNotice}</p>}<details><summary>下次发送的历史（{keepHistory?history.length:0} 条）</summary><pre>{JSON.stringify(keepHistory?history:[],null,2)}</pre></details><p className="hint">历史累计超过 6000 字符时请清空。这是对话历史限制，不是服务器的 30000 字符证据预算。离开问答页会停止接收并清空本页历史。</p><label htmlFor="answer-strategy">回答前的候选排序</label><select id="answer-strategy" value={strategy} disabled={running} onChange={e=>setStrategy(e.target.value as AnswerStrategy)}><option value="baseline">保留召回顺序</option><option value="rerank">百炼重排候选</option></select><p className="hint">重排会请求百炼，可能产生费用；不会改变服务器的 dense / BM25 / hybrid 召回模式。</p></div></details>
   <form className="chat-composer" onSubmit={e=>{e.preventDefault();void ask();}}><label className="sr-only" htmlFor="answer-question">本次问答问题</label><textarea id="answer-question" rows={3} value={question} onChange={e=>setQuestion(e.target.value)} disabled={running} placeholder="向知识库提问，答案可以回到原文核对…" onKeyDown={e=>{if((e.ctrlKey||e.metaKey)&&e.key==='Enter'&&!e.nativeEvent.isComposing){e.preventDefault();void ask();}}}/><div className="composer-actions"><a href="#documents"><img src="/assets/s2/chat/select-file.svg" alt=""/>知识库资料</a><span className="keyboard-hint">Ctrl / ⌘ + Enter 发送</span>{running?<button key="stop" type="button" className="stop-button" onClick={e=>{e.preventDefault();stop();}}>停止接收</button>:<button key="send" className="send-button" disabled={!question.trim()} type="submit"><img src="/assets/s2/component/send-thunder.svg" alt=""/>发送</button>}</div></form><p className="composer-note">回答基于已入库资料生成，请核对型号、数值和适用条件。</p>
  </div></div>
  <aside className="citation-panel" aria-labelledby="citation-title"><div className="citation-heading"><h2 id="citation-title"><img src="/assets/s2/chat/file.svg" alt=""/>参考来源</h2><span>{state.result?.citations.length??0}</span></div><p className="citation-subtitle">让每个答案都有迹可循</p>
   {state.result?.citations.length?<div className="citation-list">{state.result.citations.map((c,i)=><button className="citation-card" key={c.chunk_id} onClick={()=>setCitationIndex(i)}><div><span className="citation-number">{i+1}</span><strong>{sourceLocation(c.locator)}</strong><span>↗</span></div><p>{c.text}</p><small>查看原文与来源定位</small></button>)}</div>:<div className="citation-empty"><img src="/assets/s2/chat/select-file.svg" alt=""/><h3>{running?'正在寻找相关资料':'来源会出现在这里'}</h3><p>{state.result?'本次回答没有引用。':'提问后，在这里查看引用片段，并打开原文件交叉核对。'}</p></div>}
   <p className="citation-footnote">引用编号有效，不代表语义一定正确。</p>
  </aside>
  <dialog ref={citationDialog} className="citation-dialog" onClose={()=>setCitationIndex(null)} onClick={e=>{if(e.target===e.currentTarget)setCitationIndex(null);}}>{citation&&<><div className="section-heading"><div><p className="eyebrow">SOURCE EVIDENCE</p><h2>引用 {(citationIndex??0)+1} · {sourceLocation(citation.locator)}</h2></div><button autoFocus onClick={()=>setCitationIndex(null)}>关闭</button></div><VisualNotice metadata={citation.metadata}/><pre className="source-excerpt">{citation.text}</pre><a className="source-download" href={'/api/documents/'+encodeURIComponent(citation.doc_id)+'/source'} target="_blank" rel="noreferrer">下载引用原文件 ↗</a><details><summary>来源定位与片段编号</summary><pre>{JSON.stringify({chunk_id:citation.chunk_id,doc_id:citation.doc_id,locator:citation.locator,char_range:citation.char_range,source_spans:citation.source_spans,metadata:citation.metadata},null,2)}</pre></details></>}</dialog>
 </section>;
}
/* revision: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222 */
// checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
// cache: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
// checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
// checksum: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
// cache: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
/* revision: lpf2-18283 lpf2-19E2b */
