"""200条机械协议样例，仅验证140→冻结→60链路；不使用真实保留题、不联网、不衡量质量。"""
from copy import deepcopy
from pathlib import Path
import argparse,json,sys
# generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# generated: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# revision: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# checksum: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# cache: lpf2-18283 lpf2-19E2b
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from evaluation.runtime import run_suite,digest
from evaluation.reporting import load_run,review_template
from evaluation.holdout import freeze,run_holdout,write_new,plan_pair,compare_planned

def fixture():
    cases=[]
    for i in range(200):
        split='development' if i<140 else 'holdout'
        cases.append({'case_id':f'Q{i+1:03}','question':f'固定协议演练问题{i+1}：没有资料时怎么办？','conversation_history':[],
            'split':split,'smoke':i<20,'review_status':'source_checked_by_author','fact_family_id':'dev' if i<140 else 'held','related_fact_family_ids':[],
            'target_fact_ids':['d' if i<140 else 'h'],'primary_task':'fixture','primary_source_format':'fixture','expected_behavior':'refuse_insufficient_evidence',
            'gold_answer_points':[{'id':'p1','text':'说明资料不足','required':True}],'gold_evidence':[],'evidence_groups':[],
            'scoring_method':{'critical_errors':[]},'fixture_only':True})
    registry={'families':{'dev':{'split':'development'},'held':{'split':'holdout'}},'atoms':{'d':{'family_id':'dev'},'h':{'family_id':'held'}}}
    corpus=[{'id':'D-FIXTURE','sha256':'a'*64}];documents=[{'doc_id':'runtime-fixture','sha256':'a'*64,'status':'ready'}]
    profile={'models':{'chat':'qwen-plus','embedding':'text-embedding-v4','rerank':None},'prompt_version':'rag-m10-v1',
        'generation':{'temperature':0,'max_tokens':2048,'enable_thinking':False,'stream':False},'context_max_chars':6000,
        'embedding':{'model':'text-embedding-v4','dimension':1024,'base_url':'https://dashscope.aliyuncs.com/compatible-mode/v1'},
        'index_profile':{'schema_version':'rag-index-profile/1','strategy':'baseline','collection':'rag_course_fixture','documents':[{'doc_id':'runtime-fixture','source_sha256':'a'*64,'blocks_sha256':'b'*64,'manifest_sha256':'c'*64,'plan_sha256':None,'chunking':{'window':600,'overlap':100,'preserve_tables':False}}]},
        'retrieval_profile':{'schema_version':'rag-retrieval-profile/1','mode':'dense','branch_top_k':10,'output_top_k':10,'rrf_k':None,'full_text':None},
        'query_rewrite_profile':{'schema_version':'query-rewrite-profile/1','mode':'off','model':None,'prompt_version':'query-rewrite-m13b-v1','gate_version':'zh-reference-user-history-v1','guard_version':'literal-entities-and-constraints-v1','fusion':'original-rewritten-rrf','rrf_k':60,'top_k':10,'max_tokens':384,'temperature':0,'enable_thinking':False},
        'generation_profile':{'schema_version':'generation-policy/1','mode':'baseline','prompt_version':'rag-m10-v1','validator_version':'membership-v1','decimal_precision':None,'semantic_support':'not_evaluated'}}
    profile['context_profile']={'schema_version':'context-policy/1','mode':'baseline','algorithm_version':'m18a-original-section-v1','parent_max_chars':1800,'max_chars':6000,'budget_unit':'body_characters','grouping':'contiguous_exact_heading_path','missing_heading':'single_block','overflow':'fallback_child_without_truncation','structured_chunks':'keep_existing'}
    response={'status':'refused','answer':'固定协议演练：资料不足。','citations':[],'usage':{},'trace':{**deepcopy(profile),'candidates':[],'context':[]}}
    health={'models':{'chat':'qwen-plus','embedding':'text-embedding-v4','dimension':1024},'index_configuration':{'chunk_strategy':'baseline','collection':'rag_course_fixture'},'query_configuration':{'retrieval_mode':'dense','query_rewrite':'off','generation_policy':'baseline'}}
    health['context_configuration']={'context_policy':'baseline'}
    config={'strategy':'baseline','top_k':10,'final_k':5,'execution_origin':'protocol_fixture','run_label':'FIXTURE机械协议演练；不代表质量','require_index_profile':True,'require_retrieval_profile':True,'require_query_profile':True,'require_generation_profile':True,'require_context_profile':True}
    return cases,registry,corpus,documents,response,health,config

def prepare(output,project=ROOT,final_k=5):
    out=Path(output)
    if out.exists():raise ValueError('演练目录已存在，请换新编号')
    out.mkdir(parents=True)
    cases,registry,corpus,docs,response,health,config=fixture()
    config['final_k']=final_k
    run_suite(cases[:140],corpus,config,out/'development',lambda:docs,lambda body:deepcopy(response),project_root=project)
    _,_,records=load_run(out/'development');reviews=[]
    for c,r in zip(cases[:140],records):
        review=review_template(c,r);review['reviewer']={'kind':'human','name':'固定协议判定fixture，不代表真实人工质量审核'}
        review['behavior']={'correct':True,'reason':'固定拒答协议状态'};review['points'][0].update(passed=True,answer_quote='资料不足',reason='固定演练文字')
        review['citation_complete']={'complete':True,'reason':'固定拒答不要求引用'};reviews.append(review)
    write_new(out/'development-reviews.json',reviews)
    artifact=freeze(project,out/'development',reviews,cases,registry,out/'freeze.json','固定协议演练，用于检查冻结与保留集路由，不评估真实模型')
    return artifact,cases,registry,docs,response,health

def demo(output,project=ROOT):
    out=Path(output);artifact,cases,registry,docs,response,health=prepare(out,project);requests=[]
    candidate,_,_,_,_,_=prepare(out/'candidate',project,final_k=4)
    plan=plan_pair(artifact,candidate,out/'plan.json')
    result=run_holdout(artifact,project,cases,registry,out/'holdout',out/'attempts',lambda:health,lambda:docs,lambda body:(requests.append(deepcopy(body)) or deepcopy(response)))
    assert len(requests)==60 and result['manifest']['comparable']
    assert result['metrics']['answer_accuracy']['value'] is None
    assert all(set(r)=={'question','history','strategy','top_k','final_k','doc_ids'} for r in requests)
    assert all(c['split']=='holdout' for c in json.loads((out/'holdout/cases.json').read_text()))
    blocked=False
    try:run_holdout(artifact,project,cases,registry,out/'second-output',out/'attempts',lambda:health,lambda:docs,lambda body:response)
    except ValueError as error:blocked='已有正式' in str(error)
    assert blocked
    second_result=run_holdout(candidate,project,cases,registry,out/'candidate-holdout',out/'attempts',lambda:health,lambda:docs,lambda body:deepcopy(response))
    comparison=compare_planned(plan,out/'holdout',out/'candidate-holdout',[],[])
    assert comparison['pending']==60 and comparison['answer_accuracy_delta'] is None
    write_new(out/'comparison.json',comparison)
    result={'status':'passed','fixture_development':140,'fixture_holdout_per_arm':60,'arms':2,'cloud_calls':0,'real_holdout_questions_used':0,'quality_metrics':None,'labels_in_requests':False,'duplicate_run_blocked':True,'notice':'200条机械协议样例，不是课程200题，不能宣称任何质量分数'}
    write_new(out/'verification.json',result)
    (out/'protocol.html').write_text(render_protocol(result,comparison),encoding='utf-8')
    return result
def render_protocol(result,comparison):
    return f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>保留集协议演练</title><style>body{{max-width:920px;margin:30px auto;padding:0 20px;background:#f8f5ef;color:#302b26;font:17px/1.7 system-ui}}.note{{background:#fff0ce;padding:18px;border-left:4px solid #997048}}section{{background:white;padding:12px 20px;margin:14px 0}}h1{{font-size:30px}}h2{{font-size:21px}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}@media(max-width:600px){{.grid{{grid-template-columns:1fr}}}}</style><h1>先冻结，再验收</h1><p class="note">固定协议演练 · 云调用 {result['cloud_calls']} · 真实保留题使用 {result['real_holdout_questions_used']}<br>这些数字验证流程，不是模型质量成绩。</p><section><h2>① 完整开发记录</h2><p>每组 {result['fixture_development']} 条机械样例，记录配置、源码、题集与评分指纹。</p></section><section><h2>② 两个版本预先登记</h2><p>先一起登记基线和候选，再运行保留集。演练候选仅把 final_k 从 5 改为 4。</p></section><div class="grid"><section><h2>③ 基线</h2><p>{result['fixture_holdout_per_arm']} 条保留协议样例</p></section><section><h2>③ 候选</h2><p>{result['fixture_holdout_per_arm']} 条保留协议样例</p></section></div><section><h2>④ 成功运行后，还要评分</h2><p>已确认配对 {comparison['paired_n']} 题，待确认 {comparison['pending']} 题。正确率变化：未知。</p></section><section><h2>⑤ 重复运行被拦截</h2><p>换输出目录不能静默重跑同一个冻结候选。中断记录保留，需人工核查曝光范围。</p></section><p>只发送问题、历史和统一配置，保存的原始记录仍标记 holdout。完整结果见本目录 verification.json 与 comparison.json。</p></html>'''

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);a=p.parse_args()
    try:print(json.dumps(demo(a.output),ensure_ascii=False,indent=2))
    except (ValueError,OSError) as e:p.exit(1,str(e)+'\n')
