export function RetrievalDebug({profile,routes}:{profile?:Record<string,unknown>;routes?:Record<string,unknown>}) {
 const size=(value:unknown)=>Array.isArray(value)?String(value.length):'未保存';
 return <><h3>本次实际召回配置</h3><p>原始候选：dense {size(routes?.dense)} 条；BM25 {size(routes?.bm25)} 条。两路可能重复，融合后会去重并按候选上限截取。</p><pre>{JSON.stringify(profile??{notice:'旧记录未保存召回配置'},null,2)}</pre>{routes&&<details><summary>两路原始候选与分数（不可直接相加）</summary><pre>{JSON.stringify(routes,null,2)}</pre></details>}</>;
}
// cache: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
// cache: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
/* generated: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525 */
/* generated: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37 */
// checksum: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
/* revision: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72 */
// checksum: lpf2-18283 lpf2-19E2b
