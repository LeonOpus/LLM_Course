type Row=Record<string,unknown>;
const object=(v:unknown):v is Row=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const finiteCount=(v:unknown)=>typeof v==='number'&&Number.isInteger(v)&&v>=0?v:null;
const reasons:Record<string,string>={within_budget:'预算内，补全同小节原文',parent_budget:'父块超出剩余预算，保留子块',parent_limit:'小节超过单块上限，保留子块',parent_already_selected:'同一父块已选中，合并命中记录',char_budget:'正文预算不足，排除该片段',final_k:'达到片段数量上限，排除该片段',already_complete:'原文已经完整，保留子块',structured_chunk:'保留已有结构化片段'};
export function readContextDebug(trace:unknown){
 const t=object(trace)?trace:{},p=object(t.context_profile)?t.context_profile:{},s=object(t.selection)?t.selection:{};
 return {mode:p.mode==='baseline'?'原始片段（基线）':p.mode==='parent_section'?'同小节原文补全':'未知',
 hits:Array.isArray(t.context)?t.context.filter((h):h is Row=>object(h)&&typeof h.text==='string'&&typeof h.chunk_id==='string'):[],
 decisions:Array.isArray(s.decisions)?s.decisions.filter(object).map(d=>({...d,child_id:typeof d.child_id==='string'?d.child_id:'未提供子块编号',label:reasons[String(d.reason)]||'未识别原因，请查看原始记录'})):[],
 used:finiteCount(s.text_chars),max:finiteCount(s.max_chars)};
}
/* generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222 */
/* generated: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368 */
/* generated: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525 */
/* revision: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37 */
// cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
/* generated: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72 */
/* generated: lpf2-18283 lpf2-19E2b */
