const labels:Record<string,string>={disabled:'服务器关闭了查询改写',no_user_history:'没有可用于补全的用户历史',no_supported_reference:'没有触发已支持的中文指代',no_documents:'没有就绪文档',not_attempted:'尚未尝试',kept_by_model:'模型决定保留原问题',unchanged:'模型返回原问题',rewritten:'接受改写，并执行第二次检索',failed:'改写校验或请求失败，本次停止'};
function record(value:unknown):Record<string,unknown> {return value!==null&&typeof value==='object'&&!Array.isArray(value)?value as Record<string,unknown>:{};}
function shown(value:unknown):string {return typeof value==='string'||typeof value==='number'?String(value):'未保存';}
export function QueryRewriteDebug({profile,decision,retrievals}:{profile?:Record<string,unknown>;decision?:Record<string,unknown>;retrievals?:Record<string,unknown>}) {
 const original=record(retrievals?.original),rewritten=record(retrievals?.rewritten),usage=record(decision?.usage);
 return <details><summary>查询改写：决定、用量与原问题对照</summary><p>改写是检索表达，不是知识证据；词面检查通过不保证语义正确。</p>
  <dl><dt>本次服务器模式</dt><dd>{shown(profile?.mode)}</dd><dt>本次决定</dt><dd>{typeof decision?.decision==='string'?(labels[decision.decision]||decision.decision):'旧记录未保存'}</dd><dt>原问题检索词</dt><dd>{shown(original.question)}</dd><dt>第二次检索词</dt><dd>{rewritten.question?shown(rewritten.question):'未记录第二次检索'}</dd><dt>改写模型报告的Token</dt><dd>{typeof usage.total_tokens==='number'?usage.total_tokens:'未知；不能填0'}</dd></dl>
  <details><summary>展开原始改写记录与两次候选</summary><pre>{JSON.stringify({profile:profile??'旧记录未保存',decision:decision??'旧记录未保存',retrievals:retrievals??'旧记录未保存'},null,2)}</pre></details>
 </details>;
}
// cache: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
/* generated: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368 */
/* generated: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525 */
// checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
/* revision: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc */
// cache: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
/* revision: lpf2-18283 lpf2-19E2b */
