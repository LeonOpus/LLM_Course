"""已冻结运行的评分批次与人工修订；不重新执行RAG问答。"""
from collections import Counter
from copy import deepcopy
from datetime import datetime,timezone
from html import escape
from pathlib import Path
import json,re
from .runtime import digest
from .reporting import load_run,score_run
from .judging import judge_one,build_messages,_pending,revise_review,PROMPT_VERSION,JUDGE_CONFIG,judge_prompt_version
from .holdout import write_new
from backend.rag_app.metering import summarize_events

# generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# revision: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# generated: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# revision: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# generated: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# cache: lpf2-18283 lpf2-19E2b
def html_report(summary,results):
    visible={k:summary[k] for k in ['notice','scope','reviewer','reason','result_counts','recorded_judge_requests','origins','run_review_status','answer_judgments','actual_cost_cny'] if k in summary}
    rows=''.join('<tr>'+''.join('<td>'+escape(str(v))+'</td>' for v in [r['case_id'],r['status'],r.get('validation_error') or '—'])+'</tr>' for r in results)
    details=''.join('<details><summary>'+escape(r['case_id'])+' · 建议与依据</summary><pre>'+escape(json.dumps(r,ensure_ascii=False,indent=2))+'</pre></details>' for r in results)
    audit_tables=''
    for result in results:
        if isinstance(result.get('audit'),dict):
            diff_rows=''.join('<tr>'+''.join('<td>'+escape(str(value))+'</td>' for value in [change['path'],change['before'],change['after']])+'</tr>' for change in result['audit']['changes'])
            audit_tables+='<h3>修改前后</h3><div class="scroll"><table><tr><th>字段</th><th>原值</th><th>新值</th></tr>'+diff_rows+'</table></div>'
    return '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>辅助评分核查</title><style>body{max-width:1080px;margin:32px auto;padding:0 20px;font:16px/1.7 system-ui;background:#f8f5ef;color:#302b26}.notice{background:#fff0ce;padding:18px;border-left:4px solid #997048}table{width:100%;border-collapse:collapse;background:white}td,th{padding:12px;text-align:left;border-bottom:1px solid #ddd}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:white;padding:16px}details{padding:12px;background:white;margin:12px 0}.scroll{overflow-x:auto}</style><h1>先看依据，再接受评分</h1><p class="notice">模型辅助建议仍是暂评。结构校验通过不代表语义判断正确；失败和缺依据保留待确认。固定协议演练不代表真实模型评分能力。</p>'''+ '<h2>本批次</h2><pre>'+escape(json.dumps(visible,ensure_ascii=False,indent=2))+'</pre><details><summary>完整批次与配置指纹</summary><pre>'+escape(json.dumps(summary,ensure_ascii=False,indent=2))+'</pre></details><div class="scroll"><table><tr><th>题号</th><th>建议状态</th><th>待处理原因</th></tr>'+rows+'</table></div><h2>逐题复核</h2>'+audit_tables+details+'</html>'

def grade_run(run,output,provider,model,limit=5,case_ids=None,teacher_holdout=False,allow_partial=False,protocol='quotes'):
    version=judge_prompt_version(protocol)
    config=deepcopy(JUDGE_CONFIG)
    if protocol=='split':
        from .split_judging import configuration
        config=configuration()
    out=Path(output)
    if out.exists():raise ValueError('评分目录已存在，请换新批次，保留旧建议')
    if type(limit) is not int or not 1<=limit<=200:raise ValueError('评分数量须为1至200的整数')
    score_run(run,[]) # 拒绝重复题号、缺记录和非法事件后才允许发起评分。
    manifest,cases,records=load_run(run);by_id={r['case_id']:r for r in records}
    if any(c['split']=='holdout' for c in cases) and (not teacher_holdout or manifest.get('evaluation_split')!='holdout' or not manifest.get('freeze_sha256')):raise ValueError('保留集只能在教师模式评分已冻结教师运行')
    if any(c['split']=='holdout' for c in cases):
        frozen=json.loads((Path(run)/'freeze.json').read_text(encoding='utf-8'))
        fingerprint=digest({k:v for k,v in frozen.items() if k!='freeze_sha256'})
        if fingerprint!=frozen.get('freeze_sha256') or fingerprint!=manifest['freeze_sha256'] or frozen.get('holdout_sha256')!=manifest['cases_sha256'] or frozen.get('corpus_sha256')!=manifest['corpus_sha256'] or frozen.get('binding')!=manifest['binding'] or any(c['split']!='holdout' for c in cases):
            raise ValueError('保留评分的冻结文件、题集或语料绑定不一致')
    if case_ids is not None and (len(set(case_ids))!=len(case_ids) or not set(case_ids)<={c['case_id'] for c in cases}):raise ValueError('指定题号重复或不在运行中')
    selected=[c for c in cases if case_ids is None or c['case_id'] in case_ids][:limit]
    if not selected:raise ValueError('没有可评分题目')
    if any(not isinstance(c.get('case_id'),str) or not re.fullmatch(r'Q\d{3}',c['case_id']) for c in selected):raise ValueError('题号须为Q加三位数字，不允许路径字符')
    out.mkdir(parents=True,exist_ok=False)
    batch={'schema_version':'rag-judge-batch/1','created_at':datetime.now(timezone.utc).isoformat(),'run_manifest_sha256':digest(manifest),
           'records_sha256':manifest['records_sha256'],'cases_sha256':manifest['cases_sha256'],'prompt_version':version,'quote_protocol':protocol,'model':model,'judge_configuration':config,
           'selection_limit':limit,'requested_case_ids':case_ids,'unselected_count':len(cases)-len(selected),'selected_case_ids':[c['case_id'] for c in selected],'teacher_holdout':teacher_holdout,'status':'running',
           'validation_policy':'split-component-v1' if protocol=='split' else 'component-v1' if allow_partial else 'strict-v1'}
    write_new(out/'batch.json',batch);results=[];reviews=[];consecutive=0
    for c in selected:
        record=by_id[c['case_id']]
        if record['execution']!='ok':result={'case_id':c['case_id'],'status':'skipped_failed_execution','usage_events':[]}
        elif consecutive>=3:result={'case_id':c['case_id'],'status':'not_run_after_three_errors','usage_events':[],'review':_pending(c,record,model)}
        else:
            try:
                result=judge_one(provider,c,record,manifest['binding'],model,teacher_holdout,allow_partial=allow_partial,protocol=protocol)
                consecutive=0 if result['status'] in {'accepted_provisional','accepted_partial'} else consecutive+1
            except (ValueError,TypeError,KeyError) as error:
                result={'case_id':c['case_id'],'status':'invalid_input','validation_error':type(error).__name__,'usage_events':[],'review':_pending(c,record,model)};consecutive+=1
        results.append(result)
        if result.get('review') is not None:reviews.append(result['review'])
        write_new(out/(c['case_id']+'.json'),result)
    write_new(out/'reviews.json',reviews)
    usage=summarize_events([e for r in results for e in r['usage_events']]);write_new(out/'judge-usage.json',usage)
    scored,_,_=score_run(run,reviews)
    batch.update(status='completed',result_counts=dict(Counter(r['status'] for r in results)),reviews_sha256=digest(reviews),
                 recorded_judge_requests=usage['request_count'],origins=usage['origins'],run_review_status=scored['review_status'],
                 answer_judgments={'known_n':scored['metrics']['answer_accuracy']['n'],'pending':scored['metrics']['answer_accuracy']['pending'],'total':len(cases)},
                 actual_cost_cny=None,scope='本批评分模型调用；与原RAG在线调用分开，不可重复相加')
    (out/'batch.json').write_text(json.dumps(batch,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (out/'review-notes.html').write_text(html_report(batch,results),encoding='utf-8')
    return batch

def revise_batch(run,suggestions,replacement_file,output,name,reason,full_review=False):
    out=Path(output)
    if out.exists():raise ValueError('人工修订输出目录已存在')
    manifest,cases,records=load_run(run)
    reviews=json.loads(Path(suggestions).read_text(encoding='utf-8'));replacement=json.loads(Path(replacement_file).read_text(encoding='utf-8'))
    score_run(run,reviews) # 验证全部输入建议绑定原记录，不能带着过期建议进入下一版。
    selected=[(i,r) for i,r in enumerate(reviews) if r['case_id']==replacement.get('case_id')]
    if len(selected)!=1:raise ValueError('替换题号没有唯一对应的建议')
    i,old=selected[0];case=next(c for c in cases if c['case_id']==old['case_id']);record=next(r for r in records if r['case_id']==old['case_id'])
    changed,audit=revise_review(old,replacement,case,record,manifest['binding'],name,reason,full_review)
    updated=deepcopy(reviews);updated[i]=changed
    out.mkdir(parents=True,exist_ok=False);write_new(out/'reviews.json',updated)
    audit.update(input_reviews_sha256=digest(reviews),output_reviews_sha256=digest(updated),case_id=old['case_id'],record_sha256=old['record_sha256'])
    write_new(out/'revision.json',audit)
    (out/'revision.html').write_text(html_report({'notice':'人工声明的核查范围，不自动证明实际人工已查证','scope':audit['scope'],'reviewer':audit['reviewer'],'reason':audit['reason']},[{'case_id':old['case_id'],'status':changed['reviewer']['kind'],'audit':audit}]),encoding='utf-8')
    return audit
