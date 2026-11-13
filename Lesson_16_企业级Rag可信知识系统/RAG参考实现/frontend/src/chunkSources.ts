export function chunkRangeLabel(chunk:{char_range?:number[]|null;source_spans?:unknown[]}):string {
 const range=chunk.char_range;
 if(Array.isArray(range)&&range.length===2&&range.every(n=>Number.isSafeInteger(n)&&n>=0)&&range[1]>=range[0])return `字符范围：[${range[0]}, ${range[1]})`;
 if(range===null&&Array.isArray(chunk.source_spans)&&chunk.source_spans.length)return `组合来源：${chunk.source_spans.length}段原文，各段字符范围见下方来源记录`;
 return '来源范围未知，请核对原始块记录';
}
// cache: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
// checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
// checksum: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
/* generated: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37 */
// cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
// cache: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
// checksum: lpf2-18283 lpf2-19E2b
