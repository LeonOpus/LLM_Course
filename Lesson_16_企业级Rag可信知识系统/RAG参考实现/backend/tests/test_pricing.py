import unittest,json,sys
from pathlib import Path
from copy import deepcopy
# checksum: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# revision: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# cache: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# cache: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# checksum: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# checksum: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# checksum: lpf2-18283 lpf2-19E2b
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from rag_app.metering import UsageJournal
from rag_app.pricing import estimate,pricing_context
ROOT=Path(__file__).resolve().parents[2]

class PricingTests(unittest.TestCase):
    def setUp(self):self.card=json.loads((ROOT/'pricing/beijing-2026-09-16.json').read_text())
    def event(self,n=1000,out=100,op='answer',model='qwen-plus'):
        j=UsageJournal(origin='fixture');uid=j.begin(op,model,pricing_context=pricing_context('https://dashscope.aliyuncs.com/compatible-mode/v1',{'enable_thinking':False} if op=='answer' else {}))
        j.update(uid,outcome='response_received',usage={'prompt_tokens':n,'completion_tokens':out,'total_tokens':n+out})
        e=j.events()[0];e['started_at']='2026-09-16T12:00:00+08:00';return e
    def test_provider_records_http_and_stream_context(self):
        import httpx
        from unittest.mock import patch
        from rag_app.providers import Bailian
        from rag_app.config import Settings
        settings=Settings(_env_file=None,dashscope_api_key='fixture',bailian_base_url='https://dashscope.aliyuncs.com/compatible-mode/v1',embedding_dim=2)
        def handler(request):
            if request.url.path.endswith('/embeddings'):
                return httpx.Response(200,json={'data':[{'index':0,'embedding':[1.,0.]}],'usage':{'total_tokens':2}})
            frames=[{'choices':[{'delta':{'content':'{}'},'finish_reason':None}]},
                    {'choices':[{'delta':{},'finish_reason':'stop'}]},
                    {'choices':[],'usage':{'prompt_tokens':4,'completion_tokens':2,'total_tokens':6}}]
            return httpx.Response(200,text=''.join('data: '+json.dumps(f)+'\n\n' for f in frames)+'data: [DONE]\n\n')
        j=UsageJournal(origin='fixture')
        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            provider=Bailian(settings,client,j);provider.embed(['x'])
            with patch.object(provider,'_validate_generated',return_value={'status':'answered'}):
                list(provider.answer_stream('q',[{'chunk_id':'c','text':'x'}]))
        events=j.events();self.assertEqual(len(events),2)
        self.assertEqual(events[0]['pricing_context']['enable_thinking'],None)
        self.assertEqual(events[1]['pricing_context']['enable_thinking'],False)
        self.assertEqual(events[1]['outcome'],'stream_completed')
        self.assertTrue(all(e['pricing_context']['endpoint_host']=='dashscope.aliyuncs.com' for e in events))

    def test_decimal_and_duplicate(self):
        e=self.event();v=estimate([e,e],self.card)
        self.assertEqual(v['estimated_total_cny'],'0.001');self.assertEqual(v['request_count'],1);self.assertIsNone(v['actual_cost_cny'])
    def test_tiers_are_per_request_not_marginal(self):
        self.assertEqual(estimate([self.event(128000,100)],self.card)['estimated_total_cny'],'0.1026')
        self.assertEqual(estimate([self.event(128001,100)],self.card)['estimated_total_cny'],'0.3092024')
        self.assertEqual(estimate([self.event(256001,100)],self.card)['estimated_total_cny'],'1.2336048')
        self.assertEqual(estimate([self.event(100000,0),self.event(100000,0)],self.card)['estimated_total_cny'],'0.16')
    def test_unknown_not_zero_and_partial(self):
        e=self.event();del e['pricing_context'];v=estimate([self.event(),e],self.card)
        self.assertIsNone(v['estimated_total_cny']);self.assertEqual(v['priced_subtotal_cny'],'0.001');self.assertEqual(v['unknown_request_count'],1)
    def test_empty_and_cache_only(self):
        j=UsageJournal();j.record_cache('text-embedding-v4',3)
        for events in ([],j.events()):self.assertIsNone(estimate(events,self.card)['estimated_total_cny'])
    def test_time_window_inclusive_exclusive(self):
        for t,known in [('2026-09-15T16:00:00Z',True),('2026-09-16T15:59:59Z',True),('2026-09-16T16:00:00Z',False),('2026-09-16',False)]:
            with self.subTest(t=t):
                e=self.event();e['started_at']=t;self.assertEqual(estimate([e],self.card)['unknown_request_count'],0 if known else 1)
    def test_host_mode_thinking_and_model(self):
        for host in ['dashscope-intl.aliyuncs.com','dashscope.aliyuncs.com.evil.test','x.cn-beijing.maas.aliyuncs.com.evil.test']:
            e=self.event();e['pricing_context']['endpoint_host']=host;self.assertIsNone(estimate([e],self.card)['estimated_total_cny'])
        for field,value in [('invocation','batch'),('enable_thinking',True)]:
            e=self.event();e['pricing_context'][field]=value;self.assertIsNone(estimate([e],self.card)['estimated_total_cny'])
        self.assertIsNone(estimate([self.event(model='qwen-plus-new')],self.card)['estimated_total_cny'])
    def test_input_only_and_workspace_host(self):
        e=self.event(20,0,'rerank','gte-rerank-v2');e['pricing_context']['endpoint_host']='ws-123.cn-beijing.maas.aliyuncs.com'
        e['usage']['counts']['input_tokens']=None;e['usage']['counts']['output_tokens']=None
        self.assertEqual(estimate([e],self.card)['estimated_total_cny'],'0.000016')
        e=self.event(20,0,'embedding','text-embedding-v4');self.assertEqual(estimate([e],self.card)['estimated_total_cny'],'0.00001')
    def test_failures_and_inconsistent_usage(self):
        for outcome in ['transport_error','http_error','stream_incomplete','request_started','invalid_json']:
            e=self.event();e['outcome']=outcome;self.assertIsNone(estimate([e],self.card)['estimated_total_cny'])
        e=self.event();e['usage']['counts']['total_tokens']=9999;self.assertIsNone(estimate([e],self.card)['estimated_total_cny'])
        e=self.event();e['usage']['counts']['input_tokens']=None;self.assertIsNone(estimate([e],self.card)['estimated_total_cny'])
    def test_conflicting_event_and_overlapping_rules_rejected(self):
        e=self.event();other=deepcopy(e);other['model']='other'
        with self.assertRaises(ValueError):estimate([e,other],self.card)
        self.card['rules'].append(deepcopy(self.card['rules'][0]))
        with self.assertRaises(ValueError):estimate([e],self.card)
    def test_invalid_price_rejected_even_empty(self):
        for value in ['NaN','Infinity','-1',0.8]:
            card=deepcopy(self.card);card['rules'][0]['tiers'][0]['input_per_million']=value
            with self.assertRaises(ValueError):estimate([],card)
    def test_endpoint_context_has_no_credentials_path_or_query(self):
        context=pricing_context('https://name:secret@dashscope.aliyuncs.com/private?api_key=secret',{'enable_thinking':False})
        self.assertEqual(context,{'endpoint_host':'dashscope.aliyuncs.com','invocation':'realtime','enable_thinking':False})
        self.assertNotIn('secret',json.dumps(context))
    def test_cached_tokens_standard_rate_is_explicit_not_discount(self):
        e=self.event();e['usage']['counts']['cached_input_tokens']=900
        v=estimate([e],self.card);self.assertEqual(v['estimated_total_cny'],'0.001');self.assertEqual(v['basis'],'standard_list_price_without_discounts')

if __name__=='__main__':unittest.main()
