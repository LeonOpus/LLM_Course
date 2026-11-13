import json
from copy import deepcopy
import httpx,pytest
from evaluation.tests.test_runtime import case,record,binding
from evaluation.tests.test_judging import proposal
from evaluation.split_judging import answer_input,citation_input,evidence_input,decode_evidence,decode_citations,judge_split
from rag_app.providers import Bailian
from rag_app.config import Settings
from rag_app.metering import UsageJournal

# cache: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# generated: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# revision: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# revision: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# revision: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# checksum: lpf2-18283 lpf2-19E2b
def provider(handler):
 return Bailian(Settings(_env_file=None,dashscope_api_key='fixture'),httpx.Client(transport=httpx.MockTransport(handler)),UsageJournal(origin='fixture'))
def completion(value):
 return httpx.Response(200,json={'model':'fixture-model','choices':[{'message':{'content':json.dumps(value,ensure_ascii=False)},'finish_reason':'stop'}]})

def test_inputs_separate_gold_from_citation_and_trace_from_answer():
 c,r,b=case(),record(),binding();a=answer_input(c,r);ci=citation_input(c,r)
 assert 'trace' not in json.dumps(a) and 'retrieved_candidates' not in a
 assert set(ci)=={'component','question','conversation_history','answer_catalog','citations','output_template'}
 assert 'gold_answer_points' not in json.dumps(ci) and 'gold_evidence' not in ci
 assert ci['answer_catalog']['A0']==r['response']['answer']

def test_evidence_mapping_uses_exact_ids_and_text():
 c,r,b=case(),record(),binding();g=c['evidence_groups'][0];p=evidence_input(c,r,b,g,'candidates')
 raw={'found':True,'links':[{'evidence_index':0,'chunk_indices':[0]}],'reason':'fixture'}
 v=decode_evidence(raw,p,g)
 assert v['links'][0]['evidence_id']==c['gold_evidence'][0]['evidence_id']
 assert v['links'][0]['retrieved_quote']==r['response']['trace']['candidates'][0]['text']
 for bad in [True,-1,99]:
  wrong=deepcopy(raw);wrong['links'][0]['chunk_indices']=[bad]
  with pytest.raises(ValueError):decode_evidence(wrong,p,g)

def test_citation_mapping_is_index_bound_and_unknown_answer_rejected():
 c,r=case(),record();p=citation_input(c,r)
 raw={'citations':[{'index':0,'supported':True,'answer_ref':'A0','reason':'fixture'}],'citation_complete':{'complete':True,'reason':'fixture'}}
 v=decode_citations(raw,p,r)
 assert v['citations'][0]['chunk_id']==r['response']['citations'][0]['chunk_id']
 assert v['citations'][0]['evidence_quote']==r['response']['citations'][0]['text']
 raw['citations'][0]['answer_ref']='A999'
 with pytest.raises(ValueError):decode_citations(raw,p,r)

def test_split_round_trip_preserves_source_and_caches_only_exact_evidence_inputs():
 c,r,b=case(),record(),binding();before=deepcopy(r);calls=[]
 def handler(req):
  body=json.loads(req.content);p=json.loads(body['messages'][1]['content']);calls.append(p['component'])
  assert body['enable_thinking'] is True
  if p['component']=='answer':
   v={k:proposal()[k] for k in ['behavior','points','critical_errors','numeric_checks']}
   for row in v['points']:row['answer_quote']='A0'
   return completion(v)
  if p['component']=='evidence':return completion({'found':True,'links':[{'evidence_index':0,'chunk_indices':[0]}],'reason':'fixture'})
  return completion({'citations':[{'index':0,'supported':True,'answer_ref':'A0','reason':'fixture'}],'citation_complete':{'complete':True,'reason':'fixture'}})
 result=judge_split(provider(handler),c,r,b,'fixture-model')
 assert r==before and result['status']=='accepted_provisional'
 assert result['review']['reviewer']['kind']=='model_assisted'
 assert calls==['answer','evidence','citation']
 assert len(result['usage_events'])==3
 assert len([s for s in result['steps'] if s['status']=='reused_exact_input'])==1
 r2=deepcopy(r);r2['response']['trace']['context'][0]['text']+=' additional context'
 calls.clear();judge_split(provider(handler),c,r2,b,'fixture-model')
 assert calls==['answer','evidence','evidence','citation']

def test_connection_failure_stops_this_case_and_does_not_mark_correct():
 def handler(req):raise httpx.ConnectError('fixture',request=req)
 result=judge_split(provider(handler),case(),record(),binding(),'fixture-model')
 assert result['status']=='request_error' and len(result['usage_events'])==1
 assert result['review']['points'][0]['passed'] is None

def test_holdout_rejected_before_request_without_teacher_mode():
 c=case();c['split']='holdout'
 with pytest.raises(ValueError):judge_split(None,c,record(),binding(),'fixture-model')

def test_incomplete_binding_remains_unknown_instead_of_false():
 calls=[]
 def handler(req):
  p=json.loads(json.loads(req.content)['messages'][1]['content']);calls.append(p['component'])
  if p['component']=='answer':
   v={k:proposal()[k] for k in ['behavior','points','critical_errors','numeric_checks']}
   for row in v['points']:row['answer_quote']='A0'
   return completion(v)
  if p['component']=='evidence':return completion({'found':False,'links':[],'reason':'empty'})
  return completion({'citations':[{'index':0,'supported':True,'answer_ref':'A0','reason':'fixture'}],'citation_complete':{'complete':True,'reason':'fixture'}})
 result=judge_split(provider(handler),case(),record(),{},'fixture-model')
 assert result['review']['retrieval_groups'][0]['found'] is None
 assert result['review']['context_groups'][0]['found'] is None
 assert 'evidence' not in calls

def test_cross_original_mapping_rejected_even_if_both_sources_are_in_group():
 c,r,b=case(),record(),binding();p=evidence_input(c,r,b,c['evidence_groups'][0],'candidates')
 p['actual_candidates'][0]['source_hash']='b'*64
 with pytest.raises(ValueError):decode_evidence({'found':True,'links':[{'evidence_index':0,'chunk_indices':[0]}],'reason':'wrong original'},p,c['evidence_groups'][0])

def test_deterministic_absence_cannot_hide_model_request_failure():
 def handler(req):raise httpx.ConnectError('fixture',request=req)
 b={'runtime-a':{'document_id':'D99','sha256':'b'*64}}
 result=judge_split(provider(handler),case(),record(),b,'fixture-model')
 assert result['review']['retrieval_groups'][0]['found'] is False
 assert result['status']=='request_error'

def test_batch_uses_split_config_and_counts_only_actual_requests(tmp_path):
 from tools.demo_judge import setup_run
 from evaluation.judge_batch import grade_run
 from evaluation.split_judging import VERSION,configuration
 setup_run(tmp_path/'run',fail_last=False)
 def handler(req):
  p=json.loads(json.loads(req.content)['messages'][1]['content'])
  if p['component']=='answer':
   v=p['review_template'];v['behavior'].update(correct=True,reason='回答行为符合要求')
   v['points'][0].update(passed=False,answer_quote='A0',reason='室外结论错误')
   v['critical_errors'][0].update(present=True,answer_quote='A0',reason='声称可在室外使用')
   return completion(v)
  if p['component']=='evidence':return completion({'found':True,'links':[{'evidence_index':0,'chunk_indices':[0]}],'reason':'候选确有室内限制'})
  return completion({'citations':[{'index':0,'supported':False,'answer_ref':'A0','reason':'引用与回答相反'}],'citation_complete':{'complete':False,'reason':'结论无支持'}})
 batch=grade_run(tmp_path/'run',tmp_path/'grade',provider(handler),'fixture-model',limit=1,protocol='split')
 assert batch['prompt_version']==VERSION and batch['judge_configuration']==configuration()
 assert batch['recorded_judge_requests']==3
 assert batch['answer_judgments']['known_n']==1
 assert batch['result_counts']=={'accepted_provisional':1}
 assert batch['validation_policy']=='split-component-v1'

def test_batch_three_transport_failures_stop_fourth_case_even_with_absence_proofs(tmp_path):
 from tools.demo_judge import setup_run
 from evaluation.judge_batch import grade_run
 from evaluation.runtime import digest
 setup_run(tmp_path/'run',fail_last=False)
 # All retrieved fragments are from a different original, so source-absence
 # proofs remain known even if every model request fails.
 path=tmp_path/'run/cases.json';cases=json.loads(path.read_text())
 for c in cases:
  c['gold_evidence'][0]['document_id']='D-OTHER';c['gold_evidence'][0]['source_hash']='b'*64
 path.write_text(json.dumps(cases))
 path=tmp_path/'run/manifest.json';manifest=json.loads(path.read_text());manifest['cases_sha256']=digest(cases);path.write_text(json.dumps(manifest))
 calls=[]
 def handler(req):
  calls.append(1);raise httpx.ConnectError('fixture',request=req)
 batch=grade_run(tmp_path/'run',tmp_path/'grade',provider(handler),'fixture-model',limit=4,protocol='split')
 assert calls==[1,1,1]
 assert batch['result_counts']=={'request_error':3,'not_run_after_three_errors':1}
 assert batch['recorded_judge_requests']==3
 assert batch['answer_judgments']['pending']==4

def test_split_batch_checks_holdout_freeze_before_any_model_request(tmp_path):
 from tools.demo_holdout import demo
 from evaluation.judge_batch import grade_run
 demo(tmp_path/'protocol');run=tmp_path/'protocol/holdout'
 freeze=run/'freeze.json';data=json.loads(freeze.read_text());data['holdout_sha256']='0'*64;freeze.write_text(json.dumps(data))
 def handler(req):raise AssertionError('Invalid freeze must never reach cloud')
 with pytest.raises(ValueError):
  grade_run(run,tmp_path/'grade',provider(handler),'fixture-model',limit=1,teacher_holdout=True,protocol='split')
 assert not (tmp_path/'grade').exists()

def test_evidence_and_citation_keep_history_and_actual_source_locator():
 c,r,b=case(),record(),binding()
 c['conversation_history']=[{'role':'user','content':'前面说的是X100型号'}]
 ci=citation_input(c,r)
 ei=evidence_input(c,r,b,c['evidence_groups'][0],'candidates')
 assert ci['conversation_history']==c['conversation_history']
 assert ei['conversation_history']==c['conversation_history']
 assert ci['citations'][0]['locator']==r['response']['citations'][0]['locator']
 assert ci['citations'][0]['doc_id']==r['response']['citations'][0]['doc_id']
 ci['citations'][0]['locator']['page']=999
 assert r['response']['citations'][0]['locator']['page']==3

def test_clause_catalog_preserves_exact_text_for_multi_claim_sentence():
 from evaluation.split_judging import answer_catalog
 r=record();r['response']['answer']='型号X100，功率180W，容量2L。'
 values=list(answer_catalog(r).values())
 assert '功率180W，' in values
 assert all(v in r['response']['answer'] for v in values)
