import './GenerationDebug.css';
type Obj=Record<string,unknown>;
const object=(value:unknown):Obj=>value!==null&&typeof value==='object'&&!Array.isArray(value)?value as Obj:{};
const rows=(value:unknown):Obj[]=>Array.isArray(value)?value.map(object):[];
const text=(value:unknown)=>typeof value==='string'?value:'未保存';

export function GenerationDebug({profile,ledger,validation}:{profile?:Obj;ledger?:Obj;validation?:Obj}) {
 const scope=object(ledger?.applicability);
 const scopeLabels:Record<string,string>={supported:'模型认为条件已支持（仍需复核）',missing:'缺少必要条件',conflict:'存在未解决冲突'};
 const quoteList=(items:unknown)=><ul>{rows(items).map((ref,i)=><li key={i}><code>{text(ref.citation_id)}</code>：<q>{text(ref.quote)}</q></li>)}</ul>;
 return <details className="debug generation-debug"><summary>生成核验 · 结论、原文与计算</summary><div className="debug-content">
  <p>实际策略：{text(profile?.mode)}。摘录匹配和算术检查不证明语义、选数、公式或单位正确，仍需按原件复核。</p>
  {!ledger?<p>本条没有通过校验的证据账本：可能本次生成失败、使用基线、本地空库拒答或旧记录未保存。请结合上方请求状态与运行记录判断。</p>:<>
   <h3>型号、版本与条件</h3><p>模型声明：{scopeLabels[text(scope.state)]||text(scope.state)}；{text(scope.reason)}</p>{quoteList(scope.evidence)}
   <h3>逐条结论与摘录</h3>{rows(ledger.claims).length===0?<p>没有已回答的结论。</p>:rows(ledger.claims).map((claim,i)=><section key={i}><h4>结论 {i+1}</h4><p>{text(claim.text)}</p>{quoteList(claim.evidence)}</section>)}
   <h3>后端重算的计算</h3>{rows(ledger.calculations).length===0?<p>本条没有计算。</p>:rows(ledger.calculations).map((calc,i)=><section key={i}><h4>{text(calc.label)}：{text(calc.computed)} {text(calc.unit)}</h4>
    <p>Decimal 28位有效数字；显示数值通过重算，公式及单位仍需核对。</p>
    <table><thead><tr><th>输入</th><th>值与单位</th><th>来源摘录</th></tr></thead><tbody>{rows(calc.inputs).map((input,j)=><tr key={j}><td>{text(input.id)}</td><td>{text(input.value)} {text(input.unit)}</td><td>{object(input.source).kind==='question'?'用户当前问题':`证据 ${text(object(input.source).citation_id)}`} / {text(object(input.source).quote)}</td></tr>)}</tbody></table>
    <ol>{rows(calc.steps).map((step,j)=><li key={j}><code>{text(step.id)} = {text(step.op)}({Array.isArray(step.args)?step.args.map(text).join(', '):'未保存'}) = {text(step.computed)}</code></li>)}</ol>
   </section>)}
  </>}
  <p>语义支持、选数、公式和单位：仍需复核。摘录逐字匹配不表示结论正确。</p><h3>保存的校验状态</h3><pre>{JSON.stringify(validation??'未返回已通过的校验结果',null,2)}</pre>
  <details><summary>本次生成配置原始记录</summary><pre>{JSON.stringify(profile??'旧记录未保存',null,2)}</pre></details>
 </div></details>;
}
// cache: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
// cache: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
// checksum: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
/* generated: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37 */
// cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
/* generated: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72 */
// cache: lpf2-18283 lpf2-19E2b
