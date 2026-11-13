import type {Message,AnswerEvent} from './answer.ts';
export function validateHistory(history:Message[]):void {
 if(!Array.isArray(history)||history.length>6)throw new Error('最多发送6条历史，请清空后重新说明型号');
 if(history.some(m=>!m||!['user','assistant'].includes(m.role)||typeof m.content!=='string'||!m.content.trim()))throw new Error('历史消息格式无效');
 if(history.reduce((n,m)=>n+Array.from(m.content).length,0)>6000)throw new Error('历史合计超过6000字符，请清空历史后重新说明型号');
}
export function advanceHistory(history:Message[],question:string,event:AnswerEvent):{messages:Message[];removed:number} {
 if(event.type!=='result'||!event.payload)return {messages:history,removed:0};
 const all:Message[]=[...history,{role:'user',content:question.trim()},{role:'assistant',content:event.payload.answer}];
 return {messages:all.slice(-6),removed:Math.max(0,all.length-6)};
}
const record=(v:unknown):v is Record<string,unknown>=>v!==null&&typeof v==='object'&&!Array.isArray(v);
export function readQueryDebug(value:unknown):{profile?:Record<string,unknown>;decision?:Record<string,unknown>;retrievals?:Record<string,unknown>} {
 const t=record(value)?value:{};
 return {profile:record(t.query_rewrite_profile)?t.query_rewrite_profile:undefined,decision:record(t.query_rewrite)?t.query_rewrite:undefined,retrievals:record(t.query_retrievals)?t.query_retrievals:undefined};
}
/* revision: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222 */
// checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
// checksum: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
/* generated: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37 */
// checksum: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
/* generated: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72 */
/* generated: lpf2-18283 lpf2-19E2b */
