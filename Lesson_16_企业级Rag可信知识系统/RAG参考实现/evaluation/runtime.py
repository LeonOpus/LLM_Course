"""独立评估运行器：标签只在评分侧使用，未复核不自动判对/判错。"""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import time

# checksum: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# cache: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# generated: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# checksum: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# generated: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# generated: lpf2-18283 lpf2-19E2b
SCORING_VERSION = 'm11-v1'

def digest(value):
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest()

def _unique(rows, key):
    result = {}
    for row in rows:
        value = row.get(key)
        if value is None or value in result:
            raise ValueError(f'{key} 缺失或重复')
        result[value] = row
    return result

def safe_request(case, config, doc_ids):
    if case.get('split') != 'development' or case.get('review_status') not in {
            'source_checked_by_author', 'independently_reviewed'}:
        raise ValueError('学生运行器仅接受已核查的开发题')
    return request_fields(case,config,doc_ids)

def request_fields(case,config,doc_ids):
    """内部通用请求字段；split授权由学生/教师入口各自校验。"""
    question = case.get('question')
    if not isinstance(question, str) or not question.strip():
        raise ValueError('题干为空')
    top, final = config.get('top_k'), config.get('final_k')
    if type(top) is not int or not 1 <= top <= 50 or type(final) is not int or not 1 <= final <= min(20, top):
        raise ValueError('top_k/final_k 无效')
    if config.get('strategy') not in {'baseline', 'rerank'}:
        raise ValueError('不支持的策略')
    history = case.get('conversation_history', [])
    if not isinstance(history, list) or len(history) > 6:
        raise ValueError('历史无效')
    for message in history:
        if set(message) != {'role', 'content'} or message['role'] not in {'user', 'assistant'} or not isinstance(message['content'], str):
            raise ValueError('历史消息无效')
    return deepcopy(dict(question=question, history=history, strategy=config['strategy'],
        top_k=top, final_k=final, doc_ids=sorted(doc_ids)))

def bind_corpus(documents, corpus):
    _unique(corpus, 'id')
    expected = _unique(corpus, 'sha256')
    if not expected:
        raise ValueError('评估语料为空')
    ready = [d for d in documents if d.get('status') == 'ready']
    _unique(ready, 'doc_id')
    actual = _unique(ready, 'sha256')
    if set(expected) != set(actual):
        raise ValueError('ready 语料与登记 SHA 不一致：检查缺失或额外文件')
    return {actual[h]['doc_id']: {'document_id': expected[h]['id'], 'sha256': h}
            for h in sorted(expected)}

def _tri(value):
    if value is not None and type(value) is not bool:
        raise ValueError('判断只能为 true、false 或 null')
    return value

def _judgment(row, field):
    value = _tri(row.get(field))
    if value is not None and not str(row.get('reason', '')).strip():
        raise ValueError('确定判断必须写理由')
    return value

def _quote(quote, text):
    if not isinstance(quote, str) or not quote.strip() or quote not in text:
        raise ValueError('摘录不在对应原文中')

def _all(values):
    if False in values:
        return False
    return None if None in values else True

def _groups(case, rows, hits, binding):
    expected = _unique(case.get('evidence_groups', []), 'id')
    given = _unique(rows, 'group_id')
    if set(given) != set(expected):
        raise ValueError('证据组复核条目不完整或含未知组')
    anchors = _unique(case.get('gold_evidence', []), 'evidence_id')
    actual = _unique(hits, 'chunk_id')
    values = []
    for gid, row in given.items():
        found = _judgment(row, 'found')
        links = row.get('links', [])
        if found is True and not links:
            raise ValueError('声称召回必须提供来源映射')
        if found is not True and links:
            raise ValueError('未命中/未确认不能附上已命中映射')
        for link in links:
            eid = link.get('evidence_id')
            if eid not in expected[gid]['any_of'] or eid not in anchors:
                raise ValueError('来源证据不属于本组')
            anchor = anchors[eid]
            ids = link.get('chunk_ids', [])
            if not ids or len(set(ids)) != len(ids) or any(i not in actual for i in ids):
                raise ValueError('映射的片段不存在或重复')
            for cid in ids:
                source = binding.get(actual[cid].get('doc_id'), {})
                if source.get('document_id') != anchor['document_id'] or source.get('sha256') != anchor['source_hash']:
                    raise ValueError('来源文档或指纹不一致')
            _quote(link.get('source_quote'), anchor['evidence_text_or_fact'])
            _quote(link.get('retrieved_quote'), '\n'.join(actual[i]['text'] for i in ids))
        values.append(found)
    return None if not values or None in values else sum(values) / len(values)

def validate_review(case, record, review, binding):
    if case['case_id'] != record.get('case_id') or case['case_id'] != review.get('case_id'):
        raise ValueError('题号不一致')
    if review.get('record_sha256') != digest(record):
        raise ValueError('运行记录指纹变化，旧复核失效')
    if record.get('execution') != 'ok':
        raise ValueError('失败/未执行记录不能作为成功回答复核')
    reviewer = review.get('reviewer', {})
    if reviewer.get('kind') not in {'human', 'model_assisted'} or not reviewer.get('name'):
        raise ValueError('必须说明复核者及模式')
    response = record['response']
    answer = response['answer']
    behavior = _judgment(review.get('behavior', {}), 'correct')
    expected_status = {'answer': 'answered', 'calculate_with_evidence': 'answered',
        'refuse_insufficient_evidence': 'refused', 'ask_clarification': 'clarify'}.get(case['expected_behavior'])
    if expected_status is None:
        raise ValueError('未知预期行为')
    if response['status'] != expected_status:
        behavior = False
    points = _unique(review.get('points', []), 'id')
    expected_points = _unique(case.get('gold_answer_points', []), 'id')
    if set(points) != set(expected_points):
        raise ValueError('答案要点复核不完整')
    correctness = [behavior]
    for pid, point in points.items():
        passed = _judgment(point, 'passed')
        if passed is True:
            _quote(point.get('answer_quote'), answer)
        if expected_points[pid].get('required', True):
            correctness.append(passed)
    critical = _unique(review.get('critical_errors', []), 'index')
    errors = case.get('scoring_method', {}).get('critical_errors', [])
    if set(critical) != set(range(len(errors))):
        raise ValueError('关键错误检查不完整')
    for row in critical.values():
        present = _judgment(row, 'present')
        if present is True:
            _quote(row.get('answer_quote'), answer)
        correctness.append(None if present is None else not present)
    numeric = case.get('scoring_method', {}).get('numeric_checks', [])
    checks = _unique(review.get('numeric_checks', []), 'name')
    if set(checks) != {n['name'] for n in numeric}:
        raise ValueError('数值检查不完整')
    for expected in numeric:
        row = checks[expected['name']]
        passed = _judgment(row, 'passed')
        if passed is True:
            _quote(row.get('answer_quote'), answer)
            observed = row.get('observed')
            if type(observed) not in (int, float) or not math.isfinite(observed):
                raise ValueError('数值复核必须填写有限 observed')
            if row.get('unit') != expected['unit'] or abs(observed - expected['expected']) > expected['absolute_tolerance']:
                raise ValueError('数值或单位不符合给定容差，不能标通过')
        correctness.append(passed)
    trace = response.get('trace', {})
    recall = _groups(case, review.get('retrieval_groups', []), trace.get('candidates', []), binding)
    context_recall = _groups(case, review.get('context_groups', []), trace.get('context', []), binding)
    citations = _unique(response.get('citations', []), 'chunk_id')
    cited_review = _unique(review.get('citations', []), 'chunk_id')
    if set(citations) != set(cited_review):
        raise ValueError('引用复核必须对应全部实际引用')
    support = []
    for cid, row in cited_review.items():
        supported = _judgment(row, 'supported')
        if supported is not None:
            _quote(row.get('answer_quote'), answer)
            _quote(row.get('evidence_quote'), citations[cid]['text'])
        support.append(supported)
    precision = None if not support or None in support else sum(support) / len(support)
    complete = _judgment(review.get('citation_complete', {}), 'complete')
    correct = _all(correctness)
    # 拒答/澄清可能无正例证据：仅当复核确认该行为与内容正确时可判成功。
    citation_required = expected_status == 'answered'
    citation_ok = _all([None if precision is None else precision == 1, complete]) if citation_required else _all(support + [complete])
    return {'case_id': case['case_id'], 'reviewer_kind': reviewer['kind'],
        'answer_correct': correct, 'behavior_correct': behavior, 'retrieval_recall': recall,
        'context_recall': context_recall, 'citation_precision': precision,
        'citation_complete': complete, 'rag_success': _all([correct, citation_ok])}

def _metric(values):
    known = [v for v in values if v is not None]
    return {'value': sum(known) / len(known) if known else None,
            'n': len(known), 'pending': len(values) - len(known), 'total': len(values)}

def summarize(cases, records, reviews, binding):
    from .usage import summarize_record_usage
    cases_by_id = _unique(cases, 'case_id')
    records_by_id = _unique(records, 'case_id')
    reviews_by_id = _unique(reviews, 'case_id')
    if set(records_by_id) != set(cases_by_id) or not set(reviews_by_id) <= set(cases_by_id):
        raise ValueError('运行记录/复核题号与冻结题集不一致')
    scores = []
    for cid, case in cases_by_id.items():
        record = records_by_id[cid]
        if cid in reviews_by_id:
            score = validate_review(case, record, reviews_by_id[cid], binding)
        else:
            score = dict(case_id=cid, reviewer_kind=None, answer_correct=None, behavior_correct=None,
                retrieval_recall=None, context_recall=None, citation_precision=None, citation_complete=None, rag_success=None)
        score.update(primary_task=case.get('primary_task'), primary_source_format=case.get('primary_source_format'),
            execution=record['execution'], evidence_applicable=bool(case.get('evidence_groups')),
            citation_applicable=bool(record.get('response', {}).get('citations')))
        scores.append(score)
    metrics = {}
    for label, field in [('answer_accuracy', 'answer_correct'), ('behavior_accuracy', 'behavior_correct'),
            ('retrieval_recall', 'retrieval_recall'), ('context_recall', 'context_recall'),
            ('citation_precision', 'citation_precision'), ('citation_complete', 'citation_complete'), ('rag_success', 'rag_success')]:
        applicable = [s for s in scores if (s['evidence_applicable'] if 'recall' in field else s['citation_applicable'] if field == 'citation_precision' else True)]
        metrics[label] = _metric([s[field] for s in applicable])
        metrics[label]['not_applicable'] = len(scores) - len(applicable)
    latencies = [r['elapsed_ms'] for r in records if r.get('elapsed_ms') is not None]
    tokens = [r.get('response', {}).get('usage', {}).get('total_tokens') for r in records]
    known_tokens = [v for v in tokens if type(v) is int and v >= 0]
    rewrite_tokens=[]
    for record in records:
        detail=record.get('response',{}).get('trace',{}).get('query_rewrite',{})
        value=0 if detail.get('attempted') is False else detail.get('usage',{}).get('total_tokens')
        rewrite_tokens.append(value if type(value) is int and value>=0 else None)
    known_rewrite=[v for v in rewrite_tokens if v is not None]
    categories = {}
    for dimension in ['primary_task', 'primary_source_format']:
        categories[dimension] = {str(value): _metric([s['answer_correct'] for s in scores if s[dimension] == value])
            for value in sorted({s[dimension] for s in scores}, key=str)}
    return {'scoring_version': SCORING_VERSION, 'planned': len(cases),
        'execution_counts': dict(Counter(r['execution'] for r in records)),
        'review_status': 'provisional_model_assisted' if any(s['reviewer_kind'] == 'model_assisted' for s in scores)
            else 'human_review_complete' if all(m['pending'] == 0 for m in metrics.values()) else 'pending_review',
        'metrics': metrics, 'by_category': categories, 'scores': scores,
        'latency_ms': {'mean': sum(latencies) / len(latencies) if latencies else None, 'n': len(latencies), 'includes_failed_requests': True},
        'query_rewrite_tokens': {'known_total':sum(known_rewrite) if known_rewrite else None, 'known_n':len(known_rewrite), 'unknown_n':len(records)-len(known_rewrite), 'scope':'query_rewrite_only'},
        'tokens': {'scope':'answer_generation_only','known_total': sum(known_tokens) if known_tokens else None, 'known_n': len(known_tokens), 'unknown_n': len(tokens) - len(known_tokens)},
        'request_usage':summarize_record_usage(records),'cost': None}

def _write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')

def valid_index_profile(profile,binding):
    """核对声明结构和已绑定原件；不以此证明云服务或向量语义真实。"""
    def fingerprint(value):return isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value)
    if not isinstance(profile,dict) or profile.get('schema_version')!='rag-index-profile/1':return False
    if profile.get('strategy') not in {'baseline','table_rows','table_context','multipage_rows','multipage_context'}:return False
    if not isinstance(profile.get('collection'),str) or not profile['collection'].startswith('rag_course_'):return False
    visual=profile.get('visual_augmentation')
    if visual is not None:
        if not isinstance(visual,dict) or visual.get('schema_version')!='visual-augmentation/1' or visual.get('semantic_verified') is not False:return False
        bundles=visual.get('bundles')
        if not isinstance(bundles,list) or not bundles or type(visual.get('region_count')) is not int or visual['region_count']!=len(bundles):return False
        regions=set()
        for bundle in bundles:
            if not isinstance(bundle,dict) or not all(fingerprint(bundle.get(k)) for k in ['bundle_sha256','region_id']):return False
            if bundle.get('doc_id') not in binding or bundle['region_id'] in regions:return False
            if bundle.get('origin') not in {'fixture','configured_transport'} or bundle.get('prompt_version') not in {'visual-transcription-m19a-v1','visual-relations-m24-v2'}:return False
            if not isinstance(bundle.get('model'),str) or not bundle['model']:return False
            regions.add(bundle['region_id'])
    rows=profile.get('documents')
    if not isinstance(rows,list) or len(rows)!=len(binding):return False
    seen=set()
    for row in rows:
        if not isinstance(row,dict) or not isinstance(row.get('doc_id'),str):return False
        uid=row['doc_id']
        if uid not in binding or uid in seen or row.get('source_sha256')!=binding[uid]['sha256']:return False
        seen.add(uid)
        if not all(fingerprint(row.get(k)) for k in ['blocks_sha256','manifest_sha256']):return False
        chunking=row.get('chunking')
        if not isinstance(chunking,dict):return False
        if profile['strategy']!='baseline':
            if not fingerprint(row.get('plan_sha256')) or chunking.get('strategy')!=profile['strategy'] or chunking.get('plan_sha256')!=row['plan_sha256']:return False
            if profile['strategy'] in {'multipage_rows','multipage_context'}:
                if chunking.get('algorithm_version')!='m12c-multipage-v1':return False
                for key,value in [('plan_schema_version',2),('window',600),('overlap',100)]:
                    if type(chunking.get(key)) is not int or chunking[key]!=value:return False
                if chunking.get('preserve_tables') is not False:return False
                count=chunking.get('reviewed_table_count')
                if type(count) is not int or count<0:return False
        elif row.get('plan_sha256') is not None:return False
    return True


def valid_retrieval_profile(profile,top_k):
    if not isinstance(profile,dict) or profile.get('schema_version')!='rag-retrieval-profile/1':return False
    mode=profile.get('mode')
    if mode not in {'dense','bm25','hybrid'}:return False
    if any(type(profile.get(k)) is not int or profile[k]!=top_k for k in ['branch_top_k','output_top_k']):return False
    if profile.get('rrf_k')!=(60 if mode=='hybrid' else None):return False
    full=profile.get('full_text')
    expected={'algorithm':'milvus-bm25','analyzer':{'type':'chinese'},'field':'sparse','version':1,'bm25_k1':1.2,'bm25_b':.75,'index_algorithm':'DAAT_MAXSCORE'}
    if full is not None and full!=expected:return False
    return mode=='dense' or full==expected


def valid_query_profile(profile,top_k):
    if not isinstance(profile,dict):return False
    mode=profile.get('mode')
    if mode not in {'off','contextual'}:return False
    model=profile.get('model')
    if mode=='off' and model is not None:return False
    if mode=='contextual' and (not isinstance(model,str) or not model.strip()):return False
    expected={'schema_version':'query-rewrite-profile/1','mode':mode,'model':model,
              'prompt_version':'query-rewrite-m13b-v1','gate_version':'zh-reference-user-history-v1',
              'guard_version':'literal-entities-and-constraints-v1','fusion':'original-rewritten-rrf',
              'rrf_k':60,'top_k':top_k,'max_tokens':384,'temperature':0,'enable_thinking':False}
    return profile==expected and type(profile.get('top_k')) is int


def valid_generation_profile(profile,prompt_version):
    if not isinstance(profile,dict):return False
    mode=profile.get('mode')
    if mode not in {'baseline','evidence_ledger'}:return False
    expected={'schema_version':'generation-policy/1','mode':mode,
              'prompt_version':'rag-m10-v1' if mode=='baseline' else 'rag-m14-ledger-v1',
              'validator_version':'membership-v1' if mode=='baseline' else 'ledger-quotes-decimal-v1',
              'decimal_precision':None if mode=='baseline' else 28,'semantic_support':'not_evaluated'}
    return profile==expected and prompt_version==expected['prompt_version']


def valid_context_profile(profile):
    if not isinstance(profile,dict) or profile.get('mode') not in {'baseline','parent_section'}:return False
    version=profile.get('schema_version');budget=profile.get('max_chars')
    if version not in {'context-policy/1','context-policy/2'} or type(budget) is not int or not 1<=budget<=120000:return False
    if version=='context-policy/1' and budget!=6000:return False
    expected={'schema_version':version,'mode':profile['mode'],'algorithm_version':'m18a-original-section-v1',
        'parent_max_chars':1800,'max_chars':budget,'budget_unit':'body_characters',
        'grouping':'contiguous_exact_heading_path','missing_heading':'single_block',
        'overflow':'fallback_child_without_truncation','structured_chunks':'keep_existing'}
    return profile==expected and all(type(profile.get(k)) is int for k in ['max_chars','parent_max_chars'])


def run_suite(cases, corpus, config, output, get_documents, ask,*,project_root=None):
    return _run_suite(cases,corpus,config,output,get_documents,ask,request_builder=safe_request,project_root=project_root)

def _run_suite(cases, corpus, config, output, get_documents, ask,*,request_builder,project_root=None):
    output = Path(output)
    if output.exists():
        raise ValueError('运行目录已存在，选择新目录避免覆盖')
    cases, corpus, config = deepcopy((cases, corpus, config))
    _unique(cases, 'case_id')
    if not cases:
        raise ValueError('题集为空')
    from .reproducibility import source_snapshot
    project_root=Path(project_root) if project_root is not None else Path(__file__).resolve().parents[1]
    source_before=source_snapshot(project_root)
    documents = deepcopy(get_documents())
    binding = bind_corpus(documents, corpus)
    requests = [request_builder(c, config, list(binding)) for c in cases]
    corpus_identity = sorted([{'id': d['id'], 'sha256': d['sha256']} for d in corpus], key=lambda d: d['id'])
    manifest = {'scoring_version': SCORING_VERSION, 'created_at': datetime.now(timezone.utc).isoformat(),
        'cases_sha256': digest(cases), 'corpus_sha256': digest(corpus_identity), 'config_sha256': digest(config),
        'config': config, 'binding': binding, 'status': 'running', 'comparable': False,'source_files':source_before}
    output.mkdir(parents=True, exist_ok=False)
    _write(output / 'manifest.json', manifest)
    _write(output / 'cases.json', cases)
    _write(output / 'corpus.json', corpus)
    _write(output / 'documents-before.json', documents)
    records, consecutive_errors = [], 0
    with (output / 'records.jsonl').open('x', encoding='utf-8') as stream:
        for case, request in zip(cases, requests):
            record = {'case_id': case['case_id'], 'request': request}
            if consecutive_errors >= 3:
                record.update(execution='not_run', reason='three_consecutive_errors', elapsed_ms=None)
            else:
                started = time.perf_counter()
                try:
                    response = ask(deepcopy(request))
                    if not isinstance(response, dict) or response.get('status') not in {'answered', 'refused', 'clarify'} or not isinstance(response.get('answer'), str):
                        raise ValueError('问答响应格式无效')
                    digest(response)  # 拒绝不可序列化与 NaN；不得写入半行记录。
                    record.update(execution='ok', response=response)
                    consecutive_errors = 0
                except Exception as error:
                    record.update(execution='error', error_type=type(error).__name__, reason='request_failed_see_service_trace')
                    consecutive_errors += 1
                record['elapsed_ms'] = (time.perf_counter() - started) * 1000
            records.append(record)
            stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + '\n')
            stream.flush()
    try:
        after = deepcopy(get_documents())
        _write(output / 'documents-after.json', after)
        unchanged = bind_corpus(after, corpus) == binding and digest(after) == digest(documents)
        manifest.update(status='completed', comparable=unchanged, corpus_unchanged=unchanged)
    except Exception as error:
        manifest.update(status='completed', comparable=False, verification_error_type=type(error).__name__)
    profiles = []
    profile_missing = False
    index_profiles_valid=[]
    for record in records:
        if record['execution'] != 'ok':
            continue
        trace = record['response'].get('trace', {})
        keys = ['models', 'prompt_version', 'generation', 'context_max_chars', 'embedding']
        index_profile=trace.get('index_profile')
        valid=valid_index_profile(index_profile,binding)
        index_profiles_valid.append(valid)
        if index_profile is not None or config.get('require_index_profile'):
            keys.append('index_profile')
            if not valid:profile_missing=True
        retrieval=trace.get('retrieval_profile')
        if retrieval is not None or config.get('require_retrieval_profile'):
            keys.append('retrieval_profile')
            if not valid_retrieval_profile(retrieval,config['top_k']):profile_missing=True
        query_profile=trace.get('query_rewrite_profile')
        if query_profile is not None or config.get('require_query_profile'):
            keys.append('query_rewrite_profile')
            if not valid_query_profile(query_profile,config['top_k']):profile_missing=True
        generation_profile=trace.get('generation_profile')
        if generation_profile is not None or config.get('require_generation_profile'):
            keys.append('generation_profile')
            if not valid_generation_profile(generation_profile,trace.get('prompt_version')):profile_missing=True
        scope_profile=trace.get('source_scope_profile')
        if scope_profile is not None or config.get('require_source_scope_profile'):
            keys.append('source_scope_profile')
            if (not isinstance(scope_profile,dict) or scope_profile.get('mode') not in {'off','explicit'}
                or scope_profile!={'mode':scope_profile.get('mode'),'version':'explicit-registered-document-page-v1'}):profile_missing=True
        context_profile=trace.get('context_profile')
        if context_profile is not None or config.get('require_context_profile'):
            keys.append('context_profile')
            if not valid_context_profile(context_profile) or trace.get('context_max_chars')!=context_profile.get('max_chars'):profile_missing=True
        if any(trace.get(k) is None for k in keys):
            profile_missing = True
        profiles.append({k: trace.get(k) for k in keys})
    profile_stable = bool(profiles) and not profile_missing and len({digest(p) for p in profiles}) == 1
    manifest['observed_configuration_stable'] = profile_stable
    manifest['index_profile_verification']='recorded_stable' if profile_stable and index_profiles_valid and all(index_profiles_valid) else 'missing_invalid_or_changed' if config.get('require_index_profile') or any(index_profiles_valid) else 'not_available_legacy'
    manifest['observed_configurations'] = list({digest(p): p for p in profiles}.values())
    manifest['comparable'] = manifest['comparable'] and profile_stable
    manifest['source_unchanged']=source_snapshot(project_root)==source_before
    manifest['comparable']=manifest['comparable'] and manifest['source_unchanged']
    manifest['records_sha256'] = digest(records)
    _write(output / 'manifest.json', manifest)
    result = summarize(cases, records, [], binding)
    result['manifest'] = manifest
    _write(output / 'summary.json', result)
    return result

def compare_runs(left, right):
    for key in ['cases_sha256', 'corpus_sha256', 'scoring_version']:
        if not left['manifest'].get(key) or left['manifest'][key] != right['manifest'].get(key):
            raise ValueError(f'{key} 不一致，不能配对比较')
    if not left['manifest'].get('comparable') or not right['manifest'].get('comparable'):
        raise ValueError('运行未完成配置/语料稳定性检查')
    a, b = _unique(left['scores'], 'case_id'), _unique(right['scores'], 'case_id')
    if set(a) != set(b) or not a:
        raise ValueError('逐题得分集合不一致或为空')
    pairs = []
    for cid in a:
        before, after = a[cid]['answer_correct'], b[cid]['answer_correct']
        state = 'pending' if before is None or after is None else 'gain' if not before and after else 'regression' if before and not after else 'unchanged'
        pairs.append({'case_id': cid, 'before': before, 'after': after, 'change': state})
    known = [p for p in pairs if p['change'] != 'pending']
    return {'paired_n': len(known), 'pending': len(pairs) - len(known),
        'answer_accuracy_delta': sum(int(p['after']) - int(p['before']) for p in known) / len(known) if known else None,
        'changes': dict(Counter(p['change'] for p in pairs)), 'pairs': pairs,
        'config_before': left['manifest'].get('config'), 'config_after': right['manifest'].get('config'),
        'review_status': 'provisional_model_assisted' if any(s.get('reviewer_kind') == 'model_assisted' for s in list(a.values()) + list(b.values())) else 'human_or_pending'}
