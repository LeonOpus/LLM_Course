"""无第三方依赖的离线报告；所有模型正文先 HTML 转义。"""
from html import escape
import json
from pathlib import Path
from .runtime import digest, summarize


# generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# cache: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# checksum: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# cache: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# cache: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# generated: lpf2-18283 lpf2-19E2b
def load_run(folder):
    folder = Path(folder)
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    cases = json.loads((folder / 'cases.json').read_text(encoding='utf-8'))
    corpus = json.loads((folder / 'corpus.json').read_text(encoding='utf-8'))
    records = [json.loads(line) for line in (folder / 'records.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    identity = sorted([{'id': d['id'], 'sha256': d['sha256']} for d in corpus], key=lambda d: d['id'])
    for label, value in [('cases', cases), ('records', records), ('corpus', identity), ('config', manifest['config'])]:
        if digest(value) != manifest.get(label + '_sha256'):
            raise ValueError(f'{label} 指纹变化，不能继续沿用本次结果')
    return manifest, cases, records


def review_template(case, record):
    if record['execution'] != 'ok':
        return None
    def groups():
        return [{'group_id': g['id'], 'found': None, 'reason': '', 'links': []} for g in case.get('evidence_groups', [])]
    return {'case_id': case['case_id'], 'record_sha256': digest(record),
        'reviewer': {'kind': 'human', 'name': '待填写'},
        'behavior': {'correct': None, 'reason': ''},
        'points': [{'id': p['id'], 'passed': None, 'answer_quote': '', 'reason': ''} for p in case.get('gold_answer_points', [])],
        'critical_errors': [{'index': i, 'present': None, 'answer_quote': '', 'reason': ''} for i, _ in enumerate(case.get('scoring_method', {}).get('critical_errors', []))],
        'numeric_checks': [{'name': n['name'], 'passed': None, 'observed': None, 'unit': '', 'answer_quote': '', 'reason': ''} for n in case.get('scoring_method', {}).get('numeric_checks', [])],
        'retrieval_groups': groups(), 'context_groups': groups(),
        'citations': [{'chunk_id': c['chunk_id'], 'supported': None, 'answer_quote': '', 'evidence_quote': '', 'reason': ''} for c in record['response'].get('citations', [])],
        'citation_complete': {'complete': None, 'reason': ''}}


def score_run(folder, reviews):
    manifest, cases, records = load_run(folder)
    result = summarize(cases, records, reviews, manifest['binding'])
    result['manifest'] = manifest
    return result, cases, records


def _json(value):
    return escape(json.dumps(value, ensure_ascii=False, indent=2))


def render_report(summary, cases, records):
    def pct(value):
        return '待复核 / 不适用' if value is None else f'{100 * value:.1f}%'
    labels = {'answer_accuracy': '回答正确率', 'behavior_accuracy': '行为正确率', 'retrieval_recall': '候选证据组召回',
        'context_recall': '上下文证据组召回', 'citation_precision': '引用支持率', 'citation_complete': '引用完整率', 'rag_success': '完整 RAG 成功率'}
    rows = ''.join(f'<tr><td>{labels[k]}</td><td>{pct(v["value"])}</td><td>{v["n"]} / {v["total"]}</td><td>{v["pending"]}</td><td>{v["not_applicable"]}</td></tr>' for k, v in summary['metrics'].items())
    lookup = {r['case_id']: r for r in records}
    scores = {s['case_id']: s for s in summary['scores']}
    details = []
    for c in cases:
        cid = c['case_id']; r = lookup[cid]
        details.append(f'<details><summary>{escape(cid)} · {escape(c["question"])}</summary><h3>本题运行与评分</h3><pre>{_json(scores[cid])}</pre><h3>实际回答和检索轨迹</h3><pre>{_json(r)}</pre><h3>评分侧标准（没有发送给待测系统）</h3><pre>{_json(c)}</pre></details>')
    return f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>RAG 评估运行报告</title><style>body{{max-width:1120px;margin:40px auto;padding:0 24px;background:#f8f5ef;color:#302b26;font:16px/1.7 system-ui,sans-serif}}h1{{font-size:32px}}h2{{margin-top:36px}}table{{border-collapse:collapse;width:100%;background:white}}th,td{{padding:12px;border-bottom:1px solid #ded6ca;text-align:left}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;padding:16px;background:#fff;border:1px solid #ded6ca;font-size:13px}}details{{margin:12px 0;padding:16px;background:#fff;border:1px solid #ded6ca}}summary{{cursor:pointer;font-weight:bold}}.note{{background:#f0e4ce;border-left:4px solid #996e3b;padding:16px}}@media(max-width:640px){{body{{padding:0 12px}}td,th{{padding:6px;font-size:12px}}}}</style>
<h1>RAG 评估运行报告</h1><p>{escape(summary.get('manifest', {}).get('config', {}).get('run_label', '运行来源未标注'))}</p><p>计划 {summary['planned']} 题 · 状态 {escape(summary['review_status'])}</p>
<div class="note">百分比只描述已复核且适用的子集。先看 n、待确认与接口错误，再看百分比。空白不是 0%；固定响应演练不代表真实模型能力。证据组召回按题宏平均。</div>
<h2>执行情况</h2><pre>{_json(summary['execution_counts'])}</pre><h2>质量指标</h2><table><thead><tr><th>指标</th><th>已复核子集</th><th>已确认 / 适用</th><th>待确认</th><th>不适用</th></tr></thead><tbody>{rows}</tbody></table>
<h2>按类型查看样本量</h2><pre>{_json(summary['by_category'])}</pre><h2>耗时与用量</h2><pre>{_json({k: summary.get(k) for k in ['latency_ms','tokens','query_rewrite_tokens','request_usage','cost']})}</pre>
<p>tokens仅含回答生成；request_usage从响应内逐次调用事件重算，可能含查询Embedding、改写、重排和生成。两份统计有重叠，不能相加。失败HTTP、旧记录、入库及DocMind计费需另查全局账本；成本未知不能写成免费。</p>
<h2>逐题核查</h2>{''.join(details)}<h2>冻结配置与可比较性</h2><pre>{_json(summary.get('manifest', {}))}</pre></html>'''
