export function visualNotice(metadata:unknown):string|null{
 if(metadata===null||typeof metadata!=='object'||Array.isArray(metadata))return null;
 const m=metadata as Record<string,unknown>;
 if(m.text_origin!=='vision_model_unverified')return null;
 return `视觉模型转写 · 未经语义核验。请对照原图核对方向、单位与条件；模型：${typeof m.vision_model==='string'?m.vision_model:'未记录'}${m.origin==='fixture'?'。固定响应演练，不能作为真实识图成绩':''}`;
}

export function tableNotice(metadata:unknown):string|null{
 if(metadata===null||typeof metadata!=='object'||Array.isArray(metadata))return null;
 const m=metadata as Record<string,unknown>;
 if(m.table_representation!=='provider_markdown_fallback')return null;
 return '表格坐标异常：当前使用 DocMind 返回的 Markdown 降级内容，行列关系尚未核验。请打开原件核对表头、数值和适用条件。';
}
// checksum: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
/* generated: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368 */
/* revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525 */
// checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
/* revision: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc */
/* generated: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72 */
// cache: lpf2-18283 lpf2-19E2b
