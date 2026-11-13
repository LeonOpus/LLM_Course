from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from evaluation.runtime import safe_request,bind_corpus,validate_review,summarize,run_suite,compare_runs

# generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# generated: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# generated: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# cache: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# cache: lpf2-18283 lpf2-19E2b
def digest(x):return sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def case():return {'case_id':'Q001','split':'development','review_status':'source_checked_by_author','smoke':True,'question':'X100功率？','conversation_history':[],
 'primary_task':'T01','primary_source_format':'pdf','expected_behavior':'answer','scope_documents':['D01'],
 'gold_answer_points':[{'id':'p1','text':'180W','required':True}],
 'gold_evidence':[{'evidence_id':'e1','document_id':'D01','source_hash':'a'*64,'locator':{'page_number':3},'evidence_text_or_fact':'X100功率180W'}],
 'evidence_groups':[{'id':'g1','any_of':['e1']}], 'scoring_method':{'critical_errors':['错误单位']}}
def hit():return {'chunk_id':'c1','doc_id':'runtime-a','text':'X100功率180W','locator':{'kind':'pdf','page':3}}
def record():return {'case_id':'Q001','execution':'ok','elapsed_ms':30,'response':{'status':'answered','answer':'X100功率180W','citations':[hit()], 'usage':{'total_tokens':20},'trace':{'candidates':[hit()],'context':[hit()]}}}
def binding():return {'runtime-a':{'document_id':'D01','sha256':'a'*64}}
def review():
 r=record();group={'group_id':'g1','found':True,'reason':'原文内容与位置一致','links':[{'evidence_id':'e1','chunk_ids':['c1'],'source_quote':'X100功率180W','retrieved_quote':'X100功率180W'}]}
 return {'case_id':'Q001','record_sha256':digest(r),'reviewer':{'kind':'human','name':'teacher'},
 'behavior':{'correct':True,'reason':'回答问题'},'points':[{'id':'p1','passed':True,'answer_quote':'180W','reason':'功率与单位一致'}],
 'critical_errors':[{'index':0,'present':False,'reason':'未见错误单位'}], 'numeric_checks':[],
 'retrieval_groups':[group],'context_groups':[deepcopy(group)],
 'citations':[{'chunk_id':'c1','supported':True,'answer_quote':'180W','evidence_quote':'180W','reason':'支持功率'}],
 'citation_complete':{'complete':True,'reason':'唯一事实有引用'}}

class RuntimeTests(unittest.TestCase):
 def test_request_does_not_leak_answer_scope_or_taxonomy(self):
  body=safe_request(case(),{'strategy':'baseline','top_k':10,'final_k':5},['runtime-a'])
  self.assertEqual(set(body),{'question','history','strategy','top_k','final_k','doc_ids'})
  self.assertNotIn('180W',json.dumps(body));self.assertNotIn('D01',json.dumps(body))
 def test_holdout_rejected_by_student_runner(self):
  c=case();c['split']='holdout'
  with self.assertRaises(ValueError):safe_request(c,{'strategy':'baseline','top_k':10,'final_k':5},[])
 def test_bind_uses_hash_not_filename(self):
  docs=[{'doc_id':'runtime-a','sha256':'a'*64,'name':'renamed.pdf','status':'ready'}]
  self.assertEqual(bind_corpus(docs,[{'id':'D01','sha256':'a'*64}]),binding())
 def test_missing_duplicate_and_foreign_ready_documents_rejected(self):
  good={'doc_id':'runtime-a','sha256':'a'*64,'status':'ready'};corpus=[{'id':'D01','sha256':'a'*64}]
  for docs in [[],[good,{**good,'doc_id':'other'}],[good,{'doc_id':'foreign','sha256':'b'*64,'status':'ready'}]]:
   with self.assertRaises(ValueError):bind_corpus(docs,corpus)
 def test_valid_human_review(self):
  score=validate_review(case(),record(),review(),binding())
  self.assertTrue(score['answer_correct']);self.assertEqual(score['retrieval_recall'],1)
  self.assertEqual(score['citation_precision'],1)
 def test_changed_record_invalidates_review(self):
  r=record();r['response']['answer']='changed'
  with self.assertRaisesRegex(ValueError,'指纹'):validate_review(case(),r,review(),binding())
 def test_invented_quotes_or_citation_ids_rejected(self):
  for edit in ['quote','id']:
   v=review()
   if edit=='quote':v['points'][0]['answer_quote']='invented'
   else:v['citations'][0]['chunk_id']='unknown'
   with self.assertRaises(ValueError):validate_review(case(),record(),v,binding())
 def test_correct_number_with_critical_error_is_wrong(self):
  v=review();v['critical_errors'][0]={'index':0,'present':True,'reason':'单位错误','answer_quote':'180W'}
  self.assertFalse(validate_review(case(),record(),v,binding())['answer_correct'])
 def test_partial_review_is_unknown_not_zero(self):
  v=review();v['points'][0]['passed']=None
  self.assertIsNone(validate_review(case(),record(),v,binding())['answer_correct'])
 def test_citation_membership_does_not_imply_support(self):
  v=review();v['citations'][0]['supported']=False
  score=validate_review(case(),record(),v,binding())
  self.assertTrue(score['answer_correct']);self.assertEqual(score['citation_precision'],0)
  self.assertFalse(score['rag_success'])
 def test_wrong_source_hash_cannot_claim_recall(self):
  b=binding();b['runtime-a']['sha256']='b'*64
  with self.assertRaisesRegex(ValueError,'来源'):validate_review(case(),record(),review(),b)
 def test_unknown_group_is_not_counted_as_missing(self):
  v=review();v['retrieval_groups'][0]={'group_id':'g1','found':None,'reason':'尚未核对','links':[]}
  self.assertIsNone(validate_review(case(),record(),v,binding())['retrieval_recall'])
 def test_no_positive_groups_recall_not_applicable(self):
  c=case();c['evidence_groups']=[];v=review();v['retrieval_groups']=[];v['context_groups']=[]
  self.assertIsNone(validate_review(c,record(),v,binding())['retrieval_recall'])
 def test_missing_review_does_not_create_accuracy(self):
  summary=summarize([case()],[record()],[],binding())
  self.assertIsNone(summary['metrics']['answer_accuracy']['value'])
  self.assertEqual(summary['metrics']['answer_accuracy']['pending'],1)
 def test_assisted_review_marked_provisional(self):
  v=review();v['reviewer']={'kind':'model_assisted','name':'qwen-plus'}
  result=summarize([case()],[record()],[v],binding())
  self.assertEqual(result['review_status'],'provisional_model_assisted')
 def test_runner_freezes_request_and_stops_after_three_errors(self):
  with tempfile.TemporaryDirectory() as tmp:
   cases=[{**case(),'case_id':f'Q{i:03}','question':f'问题{i}'} for i in range(1,5)]
   calls=[]
   def ask(body):calls.append(body);raise RuntimeError('private message should not leak')
   result=run_suite(cases,[{'id':'D01','sha256':'a'*64}],{'strategy':'baseline','top_k':10,'final_k':5},Path(tmp)/'run',lambda:[{'doc_id':'runtime-a','sha256':'a'*64,'status':'ready'}],ask)
   self.assertEqual(len(calls),3);self.assertEqual(result['execution_counts'],{'error':3,'not_run':1})
   self.assertTrue((Path(tmp)/'run/manifest.json').exists());self.assertTrue((Path(tmp)/'run/records.jsonl').exists())
   self.assertNotIn('private message', (Path(tmp)/'run/records.jsonl').read_text())
 def test_runner_does_not_overwrite_existing_directory(self):
  with tempfile.TemporaryDirectory() as tmp:
   with self.assertRaises(ValueError):run_suite([case()],[],{},Path(tmp),lambda:[],lambda b:{})
 def test_comparison_requires_same_cases_and_corpus(self):
  a={'manifest':{'cases_sha256':'a','corpus_sha256':'x','scoring_version':'m11-v1'},'scores':[]}
  b=deepcopy(a);b['manifest']['cases_sha256']='b'
  with self.assertRaises(ValueError):compare_runs(a,b)

if __name__=='__main__':unittest.main()
