const record=(v:unknown):v is Record<string,unknown>=>v!==null&&typeof v==='object'&&!Array.isArray(v);
export function scoreLabel(value:unknown):string {
 return value==='query_rrf'?'查询RRF融合分':value==='cosine'?'余弦相似度':value==='bm25'?'BM25分':value==='rrf'?'RRF融合分':'未标记类型的分数';
}
export function readRetrievalDebug(value:unknown):{profile?:Record<string,unknown>;routes?:Record<string,unknown>} {
 const t=record(value)?value:{};
 return {profile:record(t.retrieval_profile)?t.retrieval_profile:undefined,routes:record(t.retrieval_routes)?t.retrieval_routes:undefined};
}
/* revision: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222 */
/* revision: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368 */
/* generated: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525 */
// checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
// cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
// cache: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
/* revision: lpf2-18283 lpf2-19E2b */
