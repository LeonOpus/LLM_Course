import {parseFinalAnswer,isRunId,validateHits} from './answerValidation.ts';
import {validateHistory} from './conversation.ts';
import type {Fetcher} from './health.ts';
export type AnswerStrategy='baseline'|'rerank';
export type Message={role:'user'|'assistant';content:string};
export type Citation={chunk_id:string;doc_id:string;text:string;locator:Record<string,unknown>;char_range?:number[]|null;source_spans?:unknown[];metadata?:Record<string,unknown>};
export type AnswerResult={status:'answered'|'refused'|'clarify';answer:string;citations:Citation[];run_id:string;timing?:Record<string,number>;usage?:Record<string,number>;ledger?:Record<string,unknown>;validation?:Record<string,string>;trace:Record<string,unknown>};
export type AnswerEvent={type:string;stage?:string;text?:string;run_id?:string;message?:string;payload?:AnswerResult;candidates?:unknown[];context?:unknown[];selection?:unknown;reranked?:unknown};
export type AnswerState={status:'idle'|'running'|'completed'|'error'|'cancelled';stage?:string;draft?:string;result?:AnswerResult;error?:string;run_id?:string;debug?:unknown};

export async function consumeAnswer(question:string,history:Message[],onEvent:(e:AnswerEvent)=>void,signal?:AbortSignal,fetcher:Fetcher=fetch,strategy:AnswerStrategy='baseline'):Promise<void>{
 if(!['baseline','rerank'].includes(strategy))throw new Error('不支持的问答策略');
 validateHistory(history);
 if(!question.trim()||Array.from(question).length>2000)throw new Error('问题须为1～2000字符');
 const response=await fetcher('/api/ask/stream',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:question.trim(),history,top_k:30,final_k:15,strategy}),signal});
 if(!response.ok){let detail='';try{const body=await response.json();detail=typeof body.detail==='string'?body.detail:'';}catch{}throw new Error(detail||`HTTP ${response.status}：问答请求失败`);}
 if(!response.headers.get('Content-Type')?.includes('text/event-stream')||!response.body)throw new Error('问答响应不是可读取的事件流');
 const reader=response.body.getReader();const decoder=new TextDecoder();let buffer='';let complete=false;let activeId:string|undefined;let draftSize=0;
 try{
  while(!complete){
   const {value,done}=await reader.read();buffer+=done?decoder.decode():decoder.decode(value,{stream:true});
   if(buffer.length>1000000)throw new Error('单个事件过大，停止读取');
   let match:RegExpExecArray|null;
   while((match=/\r?\n\r?\n/.exec(buffer))){
    const frame=buffer.slice(0,match.index);buffer=buffer.slice(match.index+match[0].length);
    const raw=frame.split(/\r?\n/).filter(l=>l.startsWith('data:')).map(l=>l.slice(5).trimStart()).join('\n');
    if(!raw)continue;
    let event:AnswerEvent;try{event=JSON.parse(raw);}catch{throw new Error('事件JSON无法解析');}
    if(!event||!['phase','context','draft','result','error'].includes(event.type))throw new Error('未知问答事件');
    if(event.type==='result')event.payload=parseFinalAnswer(event.payload);
    const current=event.type==='result'?event.payload?.run_id:event.run_id;
    if(!isRunId(current)||(activeId&&current!==activeId))throw new Error('流内运行编号缺失或不一致');activeId=current;
    if(event.type==='context'){validateHits(event.candidates);validateHits(event.context);}
    if(event.type==='draft'){if(typeof event.text!=='string')throw new Error('草稿字段无效');draftSize+=Array.from(event.text).length;if(draftSize>96000)throw new Error('草稿过长，停止读取');}
    if(event.type==='phase'&&typeof event.stage!=='string')throw new Error('阶段字段无效');
    onEvent(event);
    if(event.type==='error')throw new Error(event.message||'问答失败');
    if(event.type==='result'){complete=true;break;}
   }
   if(done)break;
  }
  if(!complete)throw new Error('事件流中断，没有通过校验的最终结果');
 }finally{await reader.cancel().catch(()=>{});reader.releaseLock();}
}

export function reduceAnswer(state:AnswerState,event:AnswerEvent):AnswerState{
 if(event.type==='start')return {status:'running',stage:'connecting',draft:''};
 if(event.type==='cancel')return {status:'cancelled',draft:state.draft,run_id:state.run_id,debug:state.debug};
 if(state.status!=='running')return state;
 const base={...state,run_id:event.run_id||event.payload?.run_id||state.run_id};
 if(event.type==='phase')return {...base,stage:event.stage};
 if(event.type==='context')return {...base,debug:{candidates:event.candidates,reranked:event.reranked,context:event.context,selection:event.selection}};
 if(event.type==='draft')return {...base,draft:(state.draft||'')+(event.text||'')};
 if(event.type==='error')return {...base,status:'error',error:event.message||'请求失败'};
 if(event.type==='result')return {...base,status:'completed',result:event.payload};
 return base;
}
/* generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222 */
/* revision: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368 */
/* generated: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525 */
// cache: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
// checksum: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
// checksum: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
/* revision: lpf2-18283 lpf2-19E2b */
