import type {AnswerResult} from './answer.ts';
import {record} from './workspace.ts';
export const isRunId=(v:unknown):v is string=>typeof v==='string'&&/^[a-f0-9]{32}$/.test(v);
export function validateHits(v:unknown):void{
 if(!Array.isArray(v)||v.some(h=>!record(h)||['chunk_id','doc_id','text'].some(k=>typeof h[k]!=='string'||!(h[k] as string).trim())||!record(h.locator)||['score','rerank_score'].some(k=>h[k]!==undefined&&(typeof h[k]!=='number'||!Number.isFinite(h[k])))||(h.source_spans!==undefined&&!Array.isArray(h.source_spans))))throw new Error('候选或引用来源字段无效');
}
export function parseFinalAnswer(v:unknown):AnswerResult{
 if(!record(v)||!record(v.trace)||!record(v.timing)||!isRunId(v.run_id)||v.trace.run_id!==v.run_id||!['answered','refused','clarify'].includes(String(v.status))||typeof v.answer!=='string'||!v.answer.trim()||!['live','no_documents'].includes(String(v.trace.mode)))throw new Error('最终答案或运行记录不符合契约');
 validateHits(v.citations);validateHits(v.trace.candidates);validateHits(v.trace.context);
 if(v.trace.reranked!==undefined&&v.trace.reranked!==null)validateHits(v.trace.reranked);
 if(Object.values(v.timing).some(n=>typeof n!=='number'||!Number.isFinite(n)||n<0))throw new Error('耗时字段无效');
 if(v.ledger!==undefined&&!record(v.ledger)||v.validation!==undefined&&!record(v.validation))throw new Error('生成核验字段无效');
 return v as AnswerResult;
}
// cache: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
// cache: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
// checksum: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
// checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
// checksum: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
/* revision: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72 */
/* generated: lpf2-18283 lpf2-19E2b */
