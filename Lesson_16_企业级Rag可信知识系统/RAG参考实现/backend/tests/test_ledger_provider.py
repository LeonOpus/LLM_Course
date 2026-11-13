import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import httpx
from rag_app.providers import Bailian, ProviderError
from rag_app.config import Settings
from rag_app.generation import validate_answer
from rag_app.pipeline import Pipeline
from rag_app.answering import answer_events
from test_evidence_ledger import HITS, QUESTION, payload

# generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# generated: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# generated: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# revision: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# generated: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# cache: lpf2-18283 lpf2-19E2b
class LedgerProviderTests(unittest.TestCase):
    def provider(self, obj=None, stream=False):
        self.requests=[];content=json.dumps(payload() if obj is None else obj,ensure_ascii=False)
        def handler(request):
            self.requests.append(json.loads(request.content))
            if stream:
                rows=[{'choices':[{'delta':{'content':content[:20]},'finish_reason':None}]},
                      {'choices':[{'delta':{'content':content[20:]},'finish_reason':'stop'}]},
                      {'choices':[],'usage':{'total_tokens':33}}]
                body='\n\n'.join('data: '+json.dumps(row,ensure_ascii=False) for row in rows)+'\n\ndata: [DONE]\n\n'
                return httpx.Response(200,text=body)
            return httpx.Response(200,json={'choices':[{'message':{'content':content},'finish_reason':'stop'}],'usage':{'total_tokens':33}})
        client=httpx.Client(transport=httpx.MockTransport(handler));self.addCleanup(client.close)
        return Bailian(Settings(_env_file=None,generation_policy='evidence_ledger',dashscope_api_key='REDACTED_SECRET'),client)
    def test_nonstream_real_adapter_recomputes_and_requests_ledger(self):
        provider=self.provider();result=provider.answer(QUESTION,HITS)
        self.assertEqual(result['ledger']['calculations'][0]['computed'],'100')
        self.assertEqual(result['usage']['total_tokens'],33)
        self.assertIn('calculations',self.requests[0]['messages'][0]['content'])
    def test_stream_same_validated_result_and_unverified_drafts(self):
        events=list(self.provider(stream=True).answer_stream(QUESTION,HITS))
        self.assertEqual(events[-1]['result']['ledger']['calculations'][0]['computed'],'100')
        self.assertEqual([e['type'] for e in events],['draft','draft','answer'])
    def test_bad_quote_no_silent_baseline_fallback(self):
        obj=payload();obj['claims'][0]['evidence'][0]={'citation_id':'c1','quote':'原文不存在'}
        for stream in [False,True]:
            provider=self.provider(obj,stream)
            with self.subTest(stream=stream),self.assertRaises(ProviderError):
                if stream:list(provider.answer_stream(QUESTION,HITS))
                else:provider.answer(QUESTION,HITS)
            self.assertEqual(len(self.requests),1)
    def test_no_context_no_request(self):
        provider=self.provider();result=provider.answer(QUESTION,[])
        self.assertEqual(result['status'],'refused');self.assertEqual(self.requests,[])
    def test_trace_uses_actual_generation_policy(self):
        provider=self.provider()
        with tempfile.TemporaryDirectory() as folder:
            pipe=Pipeline(Settings(_env_file=None,generation_policy='evidence_ledger',runtime_dir=Path(folder)))
            retrieval={'mode':'live','candidates':HITS,'timing':{},'embedding':{'model':'fixture','dimension':1024}}
            with patch.object(pipe,'retrieve',return_value=retrieval),patch('rag_app.answering.Bailian',return_value=provider):
                events=list(answer_events(pipe,QUESTION,stream=False))
            trace=events[-1]['payload']['trace']
            self.assertEqual(trace['generation_profile']['mode'],'evidence_ledger')
            self.assertEqual(trace['prompt_version'],'rag-m14-ledger-v1')
            saved=json.loads(next((Path(folder)/'traces').glob('*.json')).read_text())
            self.assertEqual(saved['result']['ledger']['calculations'][0]['computed'],'100')
    def test_old_membership_check_is_not_semantic_check(self):
        obj={'status':'answered','answer':'永久免费。','citation_ids':['c1']}
        result=validate_answer(json.dumps(obj),HITS)
        self.assertEqual(result['validation']['citation_membership'],'passed')
        self.assertEqual(result['validation']['semantic_support'],'not_evaluated')
    def test_nonstream_failure_keeps_unvalidated_output_for_diagnosis(self):
        obj=payload();obj['claims'][0]['evidence']=[{'citation_id':'c1','quote':'原文不存在'}]
        provider=self.provider(obj)
        with tempfile.TemporaryDirectory() as folder:
            pipe=Pipeline(Settings(_env_file=None,generation_policy='evidence_ledger',runtime_dir=Path(folder)))
            retrieval={'mode':'live','candidates':HITS,'timing':{},'embedding':{'model':'fixture','dimension':1024}}
            with patch.object(pipe,'retrieve',return_value=retrieval),patch('rag_app.answering.Bailian',return_value=provider):
                events=list(answer_events(pipe,QUESTION,stream=False))
            self.assertEqual(events[-1]['type'],'error')
            saved=json.loads(next((Path(folder)/'traces').glob('*.json')).read_text())
            self.assertEqual(json.loads(saved['raw_model_output']),obj)
            self.assertEqual(saved['raw_model_output_status'],'unvalidated')
            self.assertNotIn('result',saved)
            self.assertNotIn('Authorization',json.dumps(saved))

if __name__=='__main__':unittest.main()
