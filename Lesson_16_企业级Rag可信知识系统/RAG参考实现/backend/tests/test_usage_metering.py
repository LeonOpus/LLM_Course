from pathlib import Path
import sys,json,tempfile,unittest
# checksum: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# cache: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# cache: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# generated: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# generated: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# checksum: lpf2-18283 lpf2-19E2b
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx
from pydantic import SecretStr
from rag_app.config import Settings
from rag_app.providers import Bailian,ProviderError
from rag_app.metering import UsageJournal,normalize_usage,summarize_events

class UsageMeteringTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.settings=Settings(_env_file=None,runtime_dir=self.root,dashscope_api_key='REDACTED_SECRET',embedding_dim=2,rerank_url='https://fixture.test/rerank')
        self.journal=UsageJournal(self.root,{'phase':'test','attempt_id':'test-attempt'},origin='fixture')
    def provider(self,handler):
        return Bailian(self.settings,httpx.Client(transport=httpx.MockTransport(handler)),usage_journal=self.journal)
    def test_embed_batches_not_double_counted(self):
        def handler(request):
            rows=json.loads(request.content)['input']
            return httpx.Response(200,json={'data':[{'index':i,'embedding':[1.,0.]} for i in range(len(rows))],
                                           'usage':{'prompt_tokens':len(rows)*2,'total_tokens':len(rows)*2}})
        p=self.provider(handler);p.embed(['private-document']*11)
        events=self.journal.events();self.assertEqual(len(events),2)
        summary=summarize_events(events)
        self.assertEqual(summary['operations']['embedding']['tokens']['total_tokens']['known_total'],22)
        self.assertEqual(summary['operations']['embedding']['requests'],2)
        self.assertIsNone(summary['cost']);self.assertNotIn('private-document',json.dumps(events));self.assertNotIn('fixture-secret',json.dumps(events))
    def test_unknown_and_malformed_counts(self):
        self.assertEqual(normalize_usage(None)['counts']['total_tokens'],None)
        n=normalize_usage({'prompt_tokens':True,'completion_tokens':-1,'total_tokens':'secret'})
        self.assertTrue(all(v is None for v in n['counts'].values()))
        n=normalize_usage({'prompt_tokens':5,'input_tokens':8,'completion_tokens':2,'total_tokens':7})
        self.assertTrue(n['issues']);self.assertIsNone(n['counts']['input_tokens'])
        n=normalize_usage({'prompt_tokens':5,'completion_tokens':2,'total_tokens':99})
        self.assertIsNone(n['counts']['total_tokens'])
    def test_invalid_answer_still_has_returned_usage(self):
        p=self.provider(lambda request:httpx.Response(200,json={'choices':[{'message':{'content':'bad JSON'},'finish_reason':'stop'}],
                           'usage':{'prompt_tokens':8,'completion_tokens':2,'total_tokens':10}}))
        with self.assertRaises(ProviderError):p.answer('secret question',[{'chunk_id':'c','text':'secret text'}])
        e=self.journal.events()[0];self.assertEqual(e['usage']['counts']['total_tokens'],10)
        self.assertEqual(e['outcome'],'response_received');self.assertNotIn('secret question',json.dumps(e))
    def test_timeout_http_error_and_missing_key(self):
        def timeout(request):raise httpx.ReadTimeout('secret diagnostic',request=request)
        with self.assertRaises(ProviderError):self.provider(timeout).embed(['x'])
        with self.assertRaises(ProviderError):self.provider(lambda r:httpx.Response(429,text='secret server body')).embed(['x'])
        self.settings.dashscope_api_key=SecretStr('')
        with self.assertRaises(ProviderError):self.provider(timeout).embed(['x'])
        events=self.journal.events();self.assertEqual(len(events),2)
        self.assertEqual({e['outcome'] for e in events},{'transport_error','http_error'})
        self.assertTrue(all(e['usage']['counts']['total_tokens'] is None for e in events))
        self.assertNotIn('secret',json.dumps(events))
    def test_stream_keeps_usage_before_incomplete_end(self):
        payload={'choices':[],'usage':{'prompt_tokens':3,'completion_tokens':2,'total_tokens':5}}
        p=self.provider(lambda r:httpx.Response(200,text='data: '+json.dumps(payload)+'\n\n'))
        with self.assertRaises(ProviderError):list(p.answer_stream('q',[{'chunk_id':'c','text':'x'}]))
        e=self.journal.events()[0];self.assertEqual(e['usage']['counts']['total_tokens'],5)
        self.assertEqual(e['outcome'],'stream_incomplete')
    def test_no_evidence_no_request_event(self):
        p=self.provider(lambda r:self.fail('unexpected call'));p.embed([]);p.answer('q',[]);list(p.answer_stream('q',[]))
        self.assertEqual(self.journal.events(),[])
    def test_duplicate_event_not_billed_twice_but_conflict_rejected(self):
        p=self.provider(lambda r:httpx.Response(200,json={'data':[{'index':0,'embedding':[1.,0.]}],'usage':{'total_tokens':4}}));p.embed(['x'])
        e=self.journal.events()[0];s=summarize_events([e,e])
        self.assertEqual(s['request_count'],1)
        changed=json.loads(json.dumps(e));changed['usage']['counts']['total_tokens']=5
        with self.assertRaises(ValueError):summarize_events([e,changed])
    def test_cache_is_local_and_unknown_not_zero(self):
        self.journal.record_cache(model='text-embedding-v4',hit_count=7)
        summary=summarize_events(self.journal.events())
        self.assertEqual(summary['request_count'],0);self.assertEqual(summary['cache_hits'],7)
        self.assertEqual(summary['event_count'],1)
    def test_rerank_and_rewrite_operations(self):
        p=self.provider(lambda r:httpx.Response(200,json={'output':{'results':[{'index':0,'relevance_score':.8}]},'usage':{'total_tokens':20}}))
        p.rerank('q',[{'text':'x'}],1)
        self.assertEqual(self.journal.events()[0]['operation'],'rerank')
        p=self.provider(lambda r:httpx.Response(200,json={'choices':[{'message':{'content':'{"action":"keep","query":"q"}'},'finish_reason':'stop'}],'usage':{'prompt_tokens':4,'completion_tokens':2,'total_tokens':6}}))
        p.rewrite_query('q',[])
        self.assertEqual({e['operation'] for e in self.journal.events()},{'rerank','query_rewrite'})
    def test_cancel_stream_retains_usage_already_received(self):
        chunks=[{'choices':[],'usage':{'total_tokens':5}},{'choices':[{'delta':{'content':'draft'}}]}]
        data=''.join('data: '+json.dumps(c)+'\n\n' for c in chunks)
        p=self.provider(lambda r:httpx.Response(200,text=data));stream=p.answer_stream('q',[{'chunk_id':'c','text':'x'}])
        self.assertEqual(next(stream)['type'],'draft');stream.close()
        e=self.journal.events()[0];self.assertEqual(e['outcome'],'stream_incomplete');self.assertEqual(e['usage']['counts']['total_tokens'],5)
    def test_error_response_usage_is_preserved_without_body(self):
        p=self.provider(lambda r:httpx.Response(500,json={'error':'private details','usage':{'total_tokens':9}}))
        with self.assertRaises(ProviderError):p.embed(['x'])
        e=self.journal.events()[0];self.assertEqual(e['http_status'],500);self.assertEqual(e['usage']['counts']['total_tokens'],9)
        self.assertNotIn('private details',json.dumps(e))
    def test_separate_journals_do_not_overwrite_files(self):
        from concurrent.futures import ThreadPoolExecutor
        def worker(i):
            j=UsageJournal(self.root,{'phase':'test','attempt_id':str(i)},origin='fixture')
            e=j.begin('embedding','text-embedding-v4');j.update(e,outcome='response_received',usage={'total_tokens':1})
        with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(worker,range(12)))
        events=[json.loads(p.read_text()) for p in (self.root/'usage-events').glob('*.json')]
        self.assertEqual(len(events),12);self.assertEqual(summarize_events(events)['request_count'],12)
        self.assertFalse(list((self.root/'usage-events').glob('*.tmp')))

if __name__=='__main__':unittest.main()
