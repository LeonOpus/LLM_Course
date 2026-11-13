import type {AnswerResult} from './answer.ts';
type Obj=Record<string,unknown>;
const record=(v:unknown):v is Obj=>v!==null&&typeof v==='object'&&!Array.isArray(v);
export function readGenerationDebug(trace:unknown,result?:AnswerResult):{profile?:Obj;ledger?:Obj;validation?:Obj} {
 const t=record(trace)?trace:{};
 return {profile:record(t.generation_profile)?t.generation_profile:undefined,ledger:record(result?.ledger)?result.ledger:undefined,validation:record(result?.validation)?result.validation:undefined};
}
/* generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222 */
/* generated: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368 */
// cache: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
// checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
// checksum: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
// cache: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
/* generated: lpf2-18283 lpf2-19E2b */
