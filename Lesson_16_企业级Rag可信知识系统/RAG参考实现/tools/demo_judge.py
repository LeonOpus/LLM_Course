"""四题固定评分协议，故意含语义错判/坏JSON/超时/原问答失败；零云调用。"""
from copy import deepcopy
from pathlib import Path
import argparse,json,sys
# generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# generated: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# generated: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# checksum: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# checksum: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# cache: lpf2-18283 lpf2-19E2b
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'backend'))
import httpx
from rag_app.config import Settings
from rag_app.providers import Bailian
from rag_app.metering import UsageJournal
from evaluation.runtime import run_suite
from evaluation.reporting import load_run,review_template,score_run
from evaluation.judge_batch import grade_run,revise_batch
from evaluation.judging import DECISIONS
from evaluation.holdout import write_new

def setup_run(folder,fail_last=True):
    c={'case_id':'Q001','split':'development','review_status':'source_checked_by_author','smoke':True,'question':'协议演练灯具能在室外使用吗？','conversation_history':[],
       'primary_task':'fixture','primary_source_format':'fixture','expected_behavior':'answer','gold_answer_points':[{'id':'p1','text':'仅限室内，不能在室外使用','required':True}],
       'gold_evidence':[{'evidence_id':'e1','document_id':'D-FIXTURE','source_hash':'a'*64,'locator':{'page_number':1},'evidence_text_or_fact':'演练灯具仅限室内使用。'}],
       'evidence_groups':[{'id':'g1','any_of':['e1']}],'scoring_method':{'critical_errors':['声称允许在室外使用']},'fixture_only':True}
    hit={'chunk_id':'fixture-c1','doc_id':'fixture-doc','text':'演练灯具仅限室内使用。','locator':{'kind':'pdf','page':1}}
    response={'status':'answered','answer':'演练灯具可在室外使用。','citations':[hit],'usage':{},'trace':{'candidates':[hit],'context':[hit],
              'models':{'chat':'fixture'},'prompt_version':'fixture','generation':{},'context_max_chars':6000,'embedding':{}}}
    cases=[{**deepcopy(c),'case_id':f'Q{i:03}','question':c['question']+f' 固定场景{i}'} for i in range(1,5)];n=[0]
    def ask(body):
        n[0]+=1
        if n[0]==4 and fail_last:raise RuntimeError('fixture RAG error')
        return deepcopy(response)
    run_suite(cases,[{'id':'D-FIXTURE','sha256':'a'*64}],{'strategy':'baseline','top_k':10,'final_k':5,'execution_origin':'protocol_fixture','run_label':'FIXTURE：灯具故意回答错误；不代表模型质量'},folder,
              lambda:[{'doc_id':'fixture-doc','sha256':'a'*64,'status':'ready'}],ask)
    return cases

def wrong_suggestion(case,record):
    value=review_template(case,record)
    value['behavior']={'correct':True,'reason':'固定错误建议：把回答当成正确'}
    value['points'][0].update(passed=True,answer_quote='室外',reason='固定错判，故意忽略室内限制')
    value['critical_errors'][0].update(present=False,reason='固定错判，故意漏掉关键错误')
    link={'evidence_id':'e1','chunk_ids':['fixture-c1'],'source_quote':'仅限室内','retrieved_quote':'仅限室内'}
    for name in ['retrieval_groups','context_groups']:value[name][0].update(found=True,reason='片段中确有室内限制',links=[deepcopy(link)])
    value['citations'][0].update(supported=True,answer_quote='室外',evidence_quote='仅限室内',reason='固定错判，摘录存在但语义相反')
    value['citation_complete']={'complete':True,'reason':'固定错误建议'}
    return {k:value[k] for k in DECISIONS}

def demo(output):
    out=Path(output)
    if out.exists():raise ValueError('输出目录已存在，请换新编号')
    out.mkdir(parents=True);cases=setup_run(out/'run');_,_,records=load_run(out/'run');proposal=wrong_suggestion(cases[0],records[0]);count=[0]
    journal=UsageJournal(out/'suggestions/usage-runtime',{'phase':'grading'},origin='fixture');settings=Settings(_env_file=None,dashscope_api_key='REDACTED_SECRET')
    def handler(request):
        count[0]+=1
        if count[0]==3:raise httpx.ReadTimeout('fixture timeout',request=request)
        content=json.dumps(proposal,ensure_ascii=False) if count[0]==1 else 'not JSON'
        return httpx.Response(200,json={'choices':[{'message':{'content':content},'finish_reason':'stop'}],'usage':{'prompt_tokens':100,'completion_tokens':10,'total_tokens':110}})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        batch=grade_run(out/'run',out/'suggestions',Bailian(settings,client,journal),'qwen-plus',limit=4)
    reviews=json.loads((out/'suggestions/reviews.json').read_text());edited=deepcopy(reviews[0])
    edited['points'][0].update(passed=False,reason='原件仅限室内，回答却允许室外')
    edited['critical_errors'][0].update(present=True,answer_quote='室外',reason='命中禁止的室外使用错误')
    edited['citations'][0].update(supported=False,reason='引用的室内限制不支持室外使用')
    edited['citation_complete'].update(complete=False,reason='关键结论没有支持性引用')
    write_new(out/'replacement-Q001.json',edited)
    revise_batch(out/'run',out/'suggestions/reviews.json',out/'replacement-Q001.json',out/'partial','协议人工声明','演练对照原文纠正语义相反判断',False)
    revise_batch(out/'run',out/'suggestions/reviews.json',out/'replacement-Q001.json',out/'full','协议人工声明','演练逐项核对整题，非真实人工质量实验',True)
    partial=json.loads((out/'partial/reviews.json').read_text());full=json.loads((out/'full/reviews.json').read_text())
    assert partial[0]['reviewer']['kind']=='model_assisted' and full[0]['reviewer']['kind']=='human'
    score,_,_=score_run(out/'run',full);assert score['scores'][0]['answer_correct'] is False
    assert batch['result_counts']=={'accepted_provisional':1,'invalid_output':1,'request_error':1,'skipped_failed_execution':1}
    assert batch['recorded_judge_requests']==3 and len(journal.events())==3
    result={'status':'passed','cloud_calls':0,'actual_holdout_questions_used':0,'mock_judge_requests':3,'known_judge_tokens':220,'unknown_usage_requests':1,
            'semantic_mistake_corrected':True,'partial_review_remains_provisional':True,'quality_metrics':None,
            'notice':'错误评分是预设协议内容，不是百炼真实输出；人工声明也是固定演练，不是独立人工审核'}
    write_new(out/'verification.json',result);return result
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);a=p.parse_args()
    try:print(json.dumps(demo(a.output),ensure_ascii=False,indent=2))
    except (ValueError,OSError) as e:p.exit(1,str(e)+'\n')
