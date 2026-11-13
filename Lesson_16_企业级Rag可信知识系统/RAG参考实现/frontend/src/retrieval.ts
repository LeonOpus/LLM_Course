import {requestJSON} from './documents.ts';
export interface Candidate {chunk_id:string;doc_id:string;text:string;score:number;score_kind?:string;rerank_score?:number;retrieval_ranks?:Record<string,number>;retrieval_scores?:Record<string,number>;locator:Record<string,unknown>;char_range?:number[]|null;source_spans?:unknown[];metadata?:Record<string,unknown>}
export interface Retrieval {mode:'live'|'no_documents';candidate_count:number;candidates:Candidate[];timing?:Record<string,number>;notice?:string;retrieval_profile?:Record<string,unknown>;retrieval_routes?:Record<string,unknown>;index_profile?:Record<string,unknown>}
export async function startIndex(id:string,fetcher:typeof fetch=fetch):Promise<void>{
 const value=await requestJSON(`/documents/${encodeURIComponent(id)}/index`,{method:'POST'},fetcher);
 if(value?.doc_id!==id||value?.accepted!==true)throw new Error('入库响应不符合任务受理契约');
}
export async function searchCandidates(question:string,top_k:number,fetcher:typeof fetch=fetch):Promise<Retrieval>{
 if(!question.trim()||question.length>2000)throw new Error('问题须为1至2000字符的非空文本');
 if(!Number.isInteger(top_k)||top_k<1||top_k>50)throw new Error('top_k须为1至50的整数');
 const value=await requestJSON('/retrieve',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:question.trim(),top_k})},fetcher,120000);
 if(!value||!['live','no_documents'].includes(value.mode)||!Array.isArray(value.candidates)||value.candidate_count!==value.candidates.length)throw new Error('检索结果不符合候选列表契约');
 return value;
}
/* generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222 */
// checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
// checksum: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
// cache: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
// cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
// cache: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
/* generated: lpf2-18283 lpf2-19E2b */
