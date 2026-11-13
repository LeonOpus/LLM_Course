from copy import deepcopy
from pathlib import Path
import json,tempfile,unittest
from unittest.mock import patch
import httpx
from rag_app.config import Settings
from rag_app.providers import Bailian,ProviderError
from rag_app.pipeline import Pipeline
from rag_app.answering import answer_events

# generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# cache: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# revision: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# checksum: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# generated: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# revision: lpf2-18283 lpf2-19E2b
HISTORY=[{'role':'user','content':'我问的是X200-Pro。'},{'role':'assistant','content':'请继续说明问题。'}]
Q='它在40°C最多运行多久？'
REWRITE='X200-Pro在40°C最多运行多久？'

def hit(cid='c',score=.9):return {'chunk_id':cid,'doc_id':'d','text':'原件片段','locator':{'kind':'txt','block_id':cid},'score':score,'score_kind':'cosine'}
def retrieval(query,hits=None):return {'mode':'live','question':query,'candidates':hits or [hit()], 'timing':{'embed_ms':1,'retrieve_ms':2},'embedding':{'model':'fixture'},'index_profile':{'id':'frozen'},'retrieval_profile':{'mode':'dense'},'ready_doc_ids':['d'],'retrieval_routes':{'dense':hits or [hit()],'bm25':[]}}

class RewriteProviderTests(unittest.TestCase):
 def provider(self,obj,reason='stop',capture=None):
  def handler(req):
   if capture is not None:capture.append(json.loads(req.content))
   return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps(obj,ensure_ascii=False)},'finish_reason':reason}],'usage':{'total_tokens':12}})
  return Bailian(Settings(_env_file=None,dashscope_api_key='REDACTED_SECRET'),httpx.Client(transport=httpx.MockTransport(handler)))
 def test_only_question_and_user_history_sent_no_evidence_or_labels(self):
  sent=[];r=self.provider({'action':'rewrite','query':REWRITE},capture=sent).rewrite_query(Q,HISTORY)
  body=sent[0];self.assertEqual(body['response_format'],{'type':'json_object'});self.assertFalse(body['enable_thinking'])
  data=json.loads(body['messages'][-1]['content']);self.assertEqual(set(data),{'question','user_history'})
  self.assertEqual(data['user_history'],[HISTORY[0]['content']]);self.assertEqual(r['query'],REWRITE);self.assertEqual(r['usage']['total_tokens'],12)
 def test_new_identifier_lost_numeric_or_negation_rejected(self):
  rows=[('它在4mA时读数多少？','X200-Pro在4MA时读数多少？'),(Q,'X200-Pro在40最多运行多久？'),(Q,'X300在40°C最多运行多久？'),(Q,'X200-Pro最多运行多久？'),('它不能超过40°C吗？','X200-Pro超过40°C吗？')]
  for q,new in rows:
   with self.subTest(query=q,new=new):
    with self.assertRaises(ProviderError):self.provider({'action':'rewrite','query':new}).rewrite_query(q,HISTORY)
 def test_assistant_history_not_an_authorized_new_number_source(self):
  history=[{'role':'user','content':'说一下设备'},{'role':'assistant','content':'型号为X999，功率900W'}]
  with self.assertRaises(ProviderError):self.provider({'action':'rewrite','query':'X999功率？'}).rewrite_query('它功率？',history)
 def test_keep_changed_query_extra_fields_and_cutoff_fail(self):
  for obj,reason in [({'action':'keep','query':REWRITE},'stop'),({'action':'rewrite','query':REWRITE,'answer':'secret'},'stop'),({'action':'rewrite','query':REWRITE},'length')]:
   with self.subTest(obj=obj,reason=reason):
    with self.assertRaises(ProviderError):self.provider(obj,reason).rewrite_query(Q,HISTORY)

class QueryFusionTests(unittest.TestCase):
 def test_same_source_different_inner_rrf_ranks_merge_not_conflict(self):
  from rag_app.rewriting import fuse_query_results
  a={**hit(),'score_kind':'rrf','retrieval_ranks':{'dense':1},'retrieval_scores':{'dense':.9}}
  b={**hit(score=.1),'score_kind':'rrf','retrieval_ranks':{'bm25':3},'retrieval_scores':{'bm25':4}}
  old=deepcopy((a,b));r=fuse_query_results([a],[b],10)
  self.assertEqual(r[0]['score_kind'],'query_rrf');self.assertEqual(r[0]['query_ranks'],{'original':1,'rewritten':1});self.assertAlmostEqual(r[0]['score'],2/61)
  self.assertEqual((a,b),old)
  with self.assertRaises(ValueError):fuse_query_results([a],[{**b,'text':'changed'}],10)

class RewritePipelineTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.p=Pipeline(Settings(_env_file=None,runtime_dir=Path(self.tmp.name),query_rewrite='contextual'))
  self.bp=patch('rag_app.answering.Bailian');self.provider=self.bp.start().return_value;self.addCleanup(self.bp.stop)
  self.provider.rewrite_query.return_value={'action':'rewrite','query':REWRITE,'usage':{'total_tokens':12}}
  self.provider.answer.return_value={'status':'refused','answer':'演练无足够依据','citations':[],'usage':{'total_tokens':5}}
 def test_original_and_rewrite_both_retrieved_same_filter_generation_keeps_original(self):
  with patch.object(self.p,'retrieve',side_effect=[retrieval(Q),retrieval(REWRITE,[hit('other')])]) as get:
   events=list(answer_events(self.p,Q,doc_ids=['d'],history=HISTORY,stream=False))
  self.assertEqual(events[-1]['type'],'result');self.assertEqual([c.args[0] for c in get.call_args_list],[Q,REWRITE])
  self.assertTrue(all(c.kwargs=={'top_k':10,'doc_ids':['d']} for c in get.call_args_list))
  self.assertEqual(self.provider.answer.call_args.args[0],Q);self.assertEqual(self.provider.answer.call_args.kwargs['history'],HISTORY)
  trace=events[-1]['payload']['trace'];self.assertEqual(trace['query_rewrite']['decision'],'rewritten');self.assertEqual(set(trace['query_retrievals']),{'original','rewritten'})
 def test_off_no_history_no_reference_and_empty_library_skip_cloud_rewrite(self):
  for mode,question,history,result in [('off',Q,HISTORY,retrieval(Q)),('contextual',Q,[],retrieval(Q)),('contextual','X200-Pro功率？',HISTORY,retrieval(Q)),('contextual',Q,HISTORY,{**retrieval(Q),'mode':'no_documents','candidates':[]})]:
   with self.subTest(mode=mode,history=history,question=question):
    self.provider.rewrite_query.reset_mock();self.p.settings.query_rewrite=mode
    with patch.object(self.p,'retrieve',return_value=result) as get:events=list(answer_events(self.p,question,history=history,stream=False))
    self.provider.rewrite_query.assert_not_called();get.assert_called_once();self.assertIn('query_rewrite',events[-1]['payload']['trace'])
 def test_explicit_keep_does_not_repeat_retrieval(self):
  self.provider.rewrite_query.return_value={'action':'keep','query':Q,'usage':{}}
  with patch.object(self.p,'retrieve',return_value=retrieval(Q)) as get:events=list(answer_events(self.p,Q,history=HISTORY,stream=False))
  get.assert_called_once();self.assertEqual(events[-1]['payload']['trace']['query_rewrite']['decision'],'kept_by_model')
 def test_provider_failure_is_visible_not_silent_baseline(self):
  self.provider.rewrite_query.side_effect=ProviderError('fixture rewrite failed')
  with patch.object(self.p,'retrieve',return_value=retrieval(Q)) as get:events=list(answer_events(self.p,Q,history=HISTORY,stream=False))
  self.assertEqual(events[-1]['type'],'error');self.assertEqual(events[-1]['stage'],'query_rewrite');get.assert_called_once();self.provider.answer.assert_not_called()
 def test_changed_index_between_two_retrievals_fails(self):
  other=retrieval(REWRITE);other['index_profile']={'id':'changed'}
  with patch.object(self.p,'retrieve',side_effect=[retrieval(Q),other]):events=list(answer_events(self.p,Q,history=HISTORY,stream=False))
  self.assertEqual(events[-1]['type'],'error');self.provider.answer.assert_not_called()
