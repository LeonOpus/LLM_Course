export const record=(v:unknown):v is Record<string,unknown>=>v!==null&&typeof v==='object'&&!Array.isArray(v);
export function documentCounts(value:unknown):{total:number;ready:number}{
 if(!Array.isArray(value)||value.some(d=>!record(d)||typeof d.doc_id!=='string'||!['uploaded','parsing','parsed','indexing','ready','failed'].includes(String(d.status))))throw new Error('文档列表不符合概览契约');
 return {total:value.length,ready:value.filter(d=>d.status==='ready').length};
}
export function createRequestGate(){
 let sequence=0,controller:AbortController|null=null;
 return {begin:()=>{controller?.abort();const id=++sequence;controller=new AbortController();return {signal:controller.signal,current:()=>sequence===id&&!controller?.signal.aborted};},dispose:()=>{sequence++;controller?.abort();controller=null;}};
}

export type WorkspacePage='概览'|'文档'|'知识问答'|'质量评估'|'检索调试';
export const pageHashes:Record<WorkspacePage,string>={'概览':'overview','文档':'documents','知识问答':'ask','质量评估':'evaluation','检索调试':'retrieval'};
export function pageForHash(hash:string):WorkspacePage{return (Object.entries(pageHashes).find(([,value])=>'#'+value===hash)?.[0] as WorkspacePage)||'概览';}
/* revision: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222 */
/* revision: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368 */
// checksum: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
/* generated: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37 */
/* generated: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc */
/* revision: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72 */
/* generated: lpf2-18283 lpf2-19E2b */
