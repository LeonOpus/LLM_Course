"""教师专用：冻结完整开发运行，或对冻结版本运行一次60题保留集。run会调用模型。"""
from pathlib import Path
from hashlib import sha256
import argparse,json,sys
# revision: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# revision: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# generated: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# generated: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# generated: lpf2-18283 lpf2-19E2b
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tools'))
from evaluation.holdout import freeze,run_holdout,read,partition,plan_pair,validate_plan,compare_planned,write_new
from evaluation.contracts import validate_dataset
from run_evaluation import http_client

def teacher_dataset(root):
    root=Path(root);folder=root/'evaluation'
    cases=[json.loads(s) for s in (folder/'cases.jsonl').read_text(encoding='utf-8').splitlines() if s.strip()]
    registry=read(folder/'fact-family-registry.json');index=read(folder/'evidence-index.json');report=read(root/'reports/evaluation-coverage.json')
    for key,name in [('dataset_sha256','cases.jsonl'),('registry_sha256','fact-family-registry.json'),('evidence_index_sha256','evidence-index.json')]:
        if report.get(key)!=sha256((folder/name).read_bytes()).hexdigest():raise ValueError('来源核验报告过期，先重新运行教师原件检查')
    if report.get('status')!='passed_complete_dataset' or report.get('errors'):raise ValueError('教师材料核验未通过')
    errors=validate_dataset(cases,read(root/'specs/evaluation-taxonomy.json'),registry,index,True)
    if errors:raise ValueError('题集契约不满足；先检查教师材料报告，不把答案发给开发助手')
    partition(cases,registry)
    return cases,registry

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    f=sub.add_parser('freeze');f.add_argument('--development-run',required=True);f.add_argument('--reviews',required=True);f.add_argument('--reason',required=True);f.add_argument('--output',required=True)
    r=sub.add_parser('run');r.add_argument('--plan',required=True);r.add_argument('--arm',choices=['baseline','candidate'],required=True);r.add_argument('--output',required=True);r.add_argument('--base-url',default='http://127.0.0.1:8000')
    b=sub.add_parser('plan');b.add_argument('--baseline',required=True);b.add_argument('--candidate',required=True);b.add_argument('--output',required=True)
    c=sub.add_parser('compare');c.add_argument('--plan',required=True);c.add_argument('--baseline-run',required=True);c.add_argument('--candidate-run',required=True);c.add_argument('--baseline-reviews',required=True);c.add_argument('--candidate-reviews',required=True);c.add_argument('--output',required=True)
    for child in [f,r]:
        child.add_argument('--project',default=str(ROOT),help='实际待测源码根目录')
        child.add_argument('--teacher-data',default=str(ROOT),help='教师200题、登记与核验报告所在根目录；不得发给学生')
    a=p.parse_args(argv)
    try:
        if a.command=='plan':
            result=plan_pair(read(a.baseline),read(a.candidate),a.output);print(json.dumps({'status':'planned','plan_sha256':result['plan_sha256']}));return
        if a.command=='compare':
            result=compare_planned(read(a.plan),a.baseline_run,a.candidate_run,read(a.baseline_reviews),read(a.candidate_reviews));write_new(a.output,result);print(json.dumps({'paired_n':result['paired_n'],'pending':result['pending'],'quality_claim':result['quality_claim']},ensure_ascii=False));return
        cases,registry=teacher_dataset(a.teacher_data)
        if a.command=='freeze':
            result=freeze(a.project,a.development_run,read(a.reviews),cases,registry,a.output,a.reason)
            print(json.dumps({'status':'frozen','candidate_sha256':result['candidate_sha256'],'development_review_status':result['development_review_status'],'holdout_questions_exported':0},ensure_ascii=False,indent=2))
        else:
            request=http_client(a.base_url)
            result=run_holdout(validate_plan(read(a.plan))[a.arm],a.project,cases,registry,a.output,Path(a.teacher_data)/'teacher/holdout-attempts',lambda:request('/api/health'),lambda:request('/api/documents'),lambda body:request('/api/ask',body))
            print(json.dumps({'status':result['manifest']['status'],'planned':result['planned'],'execution_counts':result['execution_counts'],'comparable':result['manifest']['comparable'],'review_status':result['review_status']},ensure_ascii=False,indent=2))
    except (ValueError,OSError,KeyError,TypeError) as error:
        p.exit(1,(str(error) if isinstance(error,ValueError) else type(error).__name__+'：检查教师文件与后端状态；不打印完整响应。')+'\n')
if __name__=='__main__':main()
