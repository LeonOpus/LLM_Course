"""教师侧冻结与保留集。仅本地审计，不提供访问控制或不可篡改保证。"""
from copy import deepcopy
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import json,re
from .runtime import digest,request_fields,_run_suite,bind_corpus,valid_index_profile,valid_retrieval_profile,valid_query_profile,valid_generation_profile,valid_context_profile
from .reporting import score_run,load_run

# revision: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# revision: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# checksum: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# revision: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# revision: lpf2-18283 lpf2-19E2b
PROFILE_KEYS=('models','prompt_version','generation','context_max_chars','embedding','index_profile','retrieval_profile','query_rewrite_profile','generation_profile','context_profile')
from .reproducibility import source_snapshot,verify_sources

def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def write_new(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f:f.write(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')

def partition(cases,registry):
    if len(cases)!=200 or len({c['case_id'] for c in cases})!=200:raise ValueError('正式题集必须为200条唯一题号')
    dev=[c for c in cases if c.get('split')=='development'];held=[c for c in cases if c.get('split')=='holdout']
    if len(dev)!=140 or len(held)!=60 or sum(c.get('smoke') is True for c in dev)!=20:raise ValueError('要求140开发、60保留及20开发冒烟')
    for c in cases:
        if c.get('review_status') not in {'source_checked_by_author','independently_reviewed'}:raise ValueError('题目尚未核查')
        if type(c.get('smoke')) is not bool or c['split']=='holdout' and c['smoke']:raise ValueError('保留题不可进入冒烟')
        families=[c['fact_family_id'],*c.get('related_fact_family_ids',[])]
        if any(registry['families'].get(f,{}).get('split')!=c['split'] for f in families):raise ValueError('事实族跨集合')
        if not c.get('target_fact_ids'):raise ValueError('题目缺少考点')
        for atom in c['target_fact_ids']:
            visited=set()
            while registry['atoms'].get(atom,{}).get('alias_of'):
                if atom in visited:raise ValueError('考点别名循环')
                visited.add(atom);atom=registry['atoms'][atom]['alias_of']
            family=registry['atoms'].get(atom,{}).get('family_id')
            if family not in families or registry['families'].get(family,{}).get('split')!=c['split']:raise ValueError('考点或别名跨集合')
    return dev,held

def teacher_request(case,config,doc_ids):
    if case.get('split')!='holdout' or case.get('review_status') not in {'source_checked_by_author','independently_reviewed'}:raise ValueError('教师入口只接受已核查保留题')
    return request_fields(case,config,doc_ids)

def guarded_ask(ask,profile,state):
    def invoke(body):
        if state.get('drift'):raise ValueError('已发现实际配置漂移，后续题不再请求模型')
        result=ask(body)
        trace=result.get('trace',{}) if isinstance(result,dict) else {}
        actual={k:trace.get(k) for k in profile}
        if digest(actual)!=digest(profile):state['drift']=True
        return result # 原响应保留，不能为了通过检查伪装成冻结配置。
    return invoke

def reserve_attempt(registry_dir,candidate,value):
    if not re.fullmatch('[a-f0-9]{64}',candidate):raise ValueError('冻结候选指纹无效')
    path=Path(registry_dir)/(candidate+'.json')
    try:write_new(path,{'status':'started','created_at':datetime.now(timezone.utc).isoformat(),**value})
    except FileExistsError:raise ValueError('该冻结候选已有正式保留集尝试；不能换输出目录重跑或删除记录。先人工核查中断原因与已曝光范围') from None
    return path

def require_live_visual_profile(profile):
    visual=profile.get('index_profile',{}).get('visual_augmentation')
    if visual and any(b.get('origin')!='configured_transport' for b in visual.get('bundles',[])):
        raise ValueError('视觉索引含固定响应fixture；只能用于本地演练，不能冻结为正式保留集候选')

def freeze(project,dev_run,reviews,cases,registry,output,selection_reason):
    dev,held=partition(cases,registry)
    if not isinstance(selection_reason,str) or len(selection_reason.strip())<10:raise ValueError('写明基于开发集选择配置的理由，至少10字')
    summary,run_cases,records=score_run(dev_run,reviews);manifest=summary['manifest']
    if digest(run_cases)!=digest(dev):raise ValueError('冻结要求完整且顺序相同的140题开发运行')
    if manifest.get('status')!='completed' or not manifest.get('comparable') or summary['execution_counts']!={'ok':140}:raise ValueError('开发运行未完整成功或配置/语料不稳定')
    if any(m['pending'] for m in summary['metrics'].values()):raise ValueError('开发评分尚未完成，不得冻结候选')
    if len(manifest.get('observed_configurations',[]))!=1:raise ValueError('缺少唯一实际配置')
    profile=manifest['observed_configurations'][0];config=manifest['config']
    if set(profile)!=set(PROFILE_KEYS) or not valid_index_profile(profile['index_profile'],manifest['binding']) or not valid_retrieval_profile(profile['retrieval_profile'],config['top_k']) or not valid_query_profile(profile['query_rewrite_profile'],config['top_k']) or not valid_generation_profile(profile['generation_profile'],profile['prompt_version']) or not valid_context_profile(profile['context_profile']):raise ValueError('实际配置契约不完整，先用当前版本重跑开发集')
    require_live_visual_profile(profile)
    corpus=read(Path(dev_run)/'corpus.json');snapshot=source_snapshot(project)
    if manifest.get('source_files')!=snapshot or manifest.get('source_unchanged') is not True:raise ValueError('开发记录缺少对应源码指纹或源码已变化，请先重跑开发集')
    docs=read(Path(dev_run)/'documents-after.json')
    if bind_corpus(docs,corpus)!=manifest['binding']:raise ValueError('开发语料绑定不一致')
    artifact={'schema_version':'rag-holdout-freeze/1','created_at':datetime.now(timezone.utc).isoformat(),
              'selection_reason':selection_reason.strip(),'dataset_sha256':digest(cases),'registry_sha256':digest(registry),
              'development_sha256':digest(dev),'holdout_sha256':digest(held),'corpus':corpus,'corpus_sha256':manifest['corpus_sha256'],
              'binding':manifest['binding'],'documents_sha256':digest(docs),'request_config':config,'observed_profile':profile,
              'source_files':snapshot,'development_records_sha256':manifest['records_sha256'],'development_reviews_sha256':digest(reviews),
              'development_review_status':summary['review_status'],'development_metrics':summary['metrics'],
              'limitations':['本地指纹可检查变化，不能证明文件从未被他人改写。','动态模型别名不能锁住服务端权重；保留请求时间与模型记录。','教师题与标签只保留教师目录，不能分发给调参学生。','冻结与协议测试不证明真实云模型效果。']}
    identity={k:artifact[k] for k in ['dataset_sha256','registry_sha256','corpus_sha256','observed_profile','source_files']}
    identity['request_config']={k:config[k] for k in ['strategy','top_k','final_k']}
    artifact['candidate_sha256']=digest(identity);artifact['freeze_sha256']=digest(artifact)
    write_new(output,artifact);return artifact

def validate_freeze(artifact,project,cases,registry):
    require_live_visual_profile(artifact.get('observed_profile',{}))
    if artifact.get('schema_version')!='rag-holdout-freeze/1':raise ValueError('冻结文件版本无效')
    raw={k:v for k,v in artifact.items() if k!='freeze_sha256'}
    if digest(raw)!=artifact.get('freeze_sha256'):raise ValueError('冻结文件指纹变化')
    dev,held=partition(cases,registry)
    if digest(cases)!=artifact['dataset_sha256'] or digest(registry)!=artifact['registry_sha256'] or digest(dev)!=artifact['development_sha256'] or digest(held)!=artifact['holdout_sha256']:raise ValueError('题集或事实族登记变化')
    verify_sources(project,artifact['source_files']);return held

def check_health(health,artifact):
    p=artifact['observed_profile'];models=health.get('models',{});q=health.get('query_configuration',{});idx=health.get('index_configuration',{})
    if health.get('context_configuration')!={'context_policy':p['context_profile']['mode']}:raise ValueError('后端上下文策略与冻结版本不一致，尚未发起问答')
    expected={'chat':p['models']['chat'],'embedding':p['models']['embedding'],'dimension':p['embedding']['dimension']}
    if models!=expected or idx!={'chunk_strategy':p['index_profile']['strategy'],'collection':p['index_profile']['collection']} or q!={'retrieval_mode':p['retrieval_profile']['mode'],'query_rewrite':p['query_rewrite_profile']['mode'],'generation_policy':p['generation_profile']['mode']}:raise ValueError('后端公开配置与冻结版本不一致，尚未发起问答')

def run_holdout(artifact,project,cases,registry,output,attempt_registry,get_health,get_documents,ask):
    output=Path(output)
    if output.exists():raise ValueError('输出目录已存在')
    held=validate_freeze(artifact,project,cases,registry);check_health(get_health(),artifact)
    documents=deepcopy(get_documents())
    if bind_corpus(documents,artifact['corpus'])!=artifact['binding'] or digest(documents)!=artifact['documents_sha256']:raise ValueError('实际语料或文档状态改变，尚未发起问答')
    ticket=reserve_attempt(attempt_registry,artifact['candidate_sha256'],{'freeze_sha256':artifact['freeze_sha256'],'output':str(output.resolve()),'planned':60})
    state={}
    try:
        config=deepcopy(artifact['request_config']);config.update(run_label='教师保留集：'+config.get('run_label','来源需核查'),require_index_profile=True,require_retrieval_profile=True,require_query_profile=True,require_generation_profile=True,require_context_profile=True)
        result=_run_suite(held,artifact['corpus'],config,output,get_documents,guarded_ask(ask,artifact['observed_profile'],state),request_builder=teacher_request,project_root=project)
        verify_sources(project,artifact['source_files'])
        manifest=result['manifest'];manifest.update(evaluation_split='holdout',freeze_sha256=artifact['freeze_sha256'],candidate_sha256=artifact['candidate_sha256'],frozen_profile_matched=not state.get('drift',False))
        manifest['comparable']=manifest['comparable'] and not state.get('drift',False)
        for filename,value in [('manifest.json',manifest),('summary.json',result)]:
            (output/filename).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
        write_new(output/'freeze.json',artifact)
        receipt={'status':'completed' if result['execution_counts']=={'ok':60} and manifest['comparable'] else 'incomplete','freeze_sha256':artifact['freeze_sha256'],'output':str(output.resolve()),'profile_drift':state.get('drift',False),'execution_counts':result['execution_counts']}
    except BaseException:
        path=output/'manifest.json'
        if path.exists():
            failed=read(path);failed.update(comparable=False,status='interrupted',evaluation_split='holdout',freeze_sha256=artifact['freeze_sha256'],frozen_verification_failed=True)
            path.write_text(json.dumps(failed,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        receipt={'status':'interrupted','freeze_sha256':artifact['freeze_sha256'],'output':str(output.resolve()),'note':'可能已发送保留题；人工核查，不自动重跑。'}
        receipt={**read(ticket),**receipt,'finished_at':datetime.now(timezone.utc).isoformat()}
        ticket.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');raise
    receipt={**read(ticket),**receipt,'finished_at':datetime.now(timezone.utc).isoformat()}
    ticket.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return result

def plan_pair(baseline,candidate,output):
    for artifact in [baseline,candidate]:
        if digest({k:v for k,v in artifact.items() if k!='freeze_sha256'})!=artifact.get('freeze_sha256'):raise ValueError('冻结文件被修改')
    for key in ['dataset_sha256','registry_sha256','holdout_sha256','development_sha256','corpus_sha256']:
        if baseline.get(key)!=candidate.get(key):raise ValueError('两组冻结的题集或语料不一致')
    if baseline['candidate_sha256']==candidate['candidate_sha256']:raise ValueError('基线和候选是同一冻结配置，无需重复消耗保留集')
    plan={'schema_version':'rag-holdout-plan/1','created_at':datetime.now(timezone.utc).isoformat(),'baseline':baseline,'candidate':candidate}
    plan['plan_sha256']=digest(plan);write_new(output,plan);return plan

def validate_plan(plan):
    if plan.get('schema_version')!='rag-holdout-plan/1' or digest({k:v for k,v in plan.items() if k!='plan_sha256'})!=plan.get('plan_sha256'):raise ValueError('保留集计划被修改')
    return plan

def compare_planned(plan,left,right,left_reviews,right_reviews):
    from .runtime import compare_runs
    plan=validate_plan(plan);a,_,_=score_run(left,left_reviews);b,_,_=score_run(right,right_reviews)
    for label,summary in [('baseline',a),('candidate',b)]:
        manifest=summary['manifest']
        try:
            planned=datetime.fromisoformat(plan['created_at']);started=datetime.fromisoformat(manifest['created_at'])
            if planned.tzinfo is None or started.tzinfo is None or planned>started:raise ValueError()
        except (ValueError,TypeError,KeyError):raise ValueError('验收计划必须早于两组运行，不能事后补登记') from None
        if manifest.get('evaluation_split')!='holdout' or manifest.get('freeze_sha256')!=plan[label]['freeze_sha256'] or manifest.get('frozen_profile_matched') is not True:raise ValueError('运行不属于预登记的冻结基线/候选，或实际配置漂移')
    comparison=compare_runs(a,b)
    comparison.update(plan_sha256=plan['plan_sha256'],scope='teacher_holdout_only',quality_claim='pending_or_provisional' if comparison['pending'] or comparison['review_status']!='human_or_pending' else 'reviewed_pair_requires_source_audit')
    return comparison
