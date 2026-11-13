import json
import unittest
import httpx
from rag_app.config import Settings
from rag_app.providers import Bailian,ProviderError

# cache: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# generated: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# revision: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# checksum: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# revision: lpf2-18283 lpf2-19E2b
HIT={'chunk_id':'a','doc_id':'d','text':'X200 260W','locator':{'kind':'txt','block_id':'b','line_start':1,'line_end':1}}
CONTENT=json.dumps({'status':'answered','answer':'260W','citation_ids':['a']})

class AnswerProviderTests(unittest.TestCase):
    def client(self,handler):
        return Bailian(Settings(_env_file=None,dashscope_api_key='REDACTED_SECRET'),httpx.Client(transport=httpx.MockTransport(handler)))
    def stream(self,content=CONTENT,reason='stop',done=True):
        rows=[{'choices':[{'delta':{'content':content},'finish_reason':None}]},{'choices':[{'delta':{},'finish_reason':reason}]},{'choices':[],'usage':{'prompt_tokens':8,'completion_tokens':6,'total_tokens':14}}]
        return '\n\n'.join('data: '+json.dumps(r) for r in rows)+ ('\n\ndata: [DONE]\n\n' if done else '')
    def test_request_is_actual_stream_with_usage_and_no_thinking(self):
        def handler(req):
            body=json.loads(req.content)
            self.assertTrue(body['stream']);self.assertFalse(body['enable_thinking'])
            self.assertTrue(body['stream_options']['include_usage'])
            self.assertEqual(body['response_format'],{'type':'json_object'})
            return httpx.Response(200,text=self.stream())
        events=list(self.client(handler).answer_stream('功率？',[HIT]))
        self.assertEqual(events[0]['type'],'draft')
        self.assertEqual(events[-1]['result']['citations'][0]['doc_id'],'d')
        self.assertEqual(events[-1]['result']['usage']['total_tokens'],14)
    def test_invalid_citation_never_yields_answer_event(self):
        bad=json.dumps({'status':'answered','answer':'bad','citation_ids':['invented']})
        events=[]
        with self.assertRaises(ProviderError):
            for event in self.client(lambda r:httpx.Response(200,text=self.stream(bad))).answer_stream('q',[HIT]):events.append(event)
        self.assertTrue(any(e['type']=='draft' for e in events));self.assertFalse(any(e['type']=='answer' for e in events))
    def test_stream_cutoff_is_not_success(self):
        with self.assertRaises(ProviderError):list(self.client(lambda r:httpx.Response(200,text=self.stream(done=False))).answer_stream('q',[HIT]))
    def test_stream_length_is_not_success(self):
        with self.assertRaises(ProviderError):list(self.client(lambda r:httpx.Response(200,text=self.stream(reason='length'))).answer_stream('q',[HIT]))
    def test_stream_http_error_does_not_echo_private_body(self):
        with self.assertRaises(ProviderError) as cm:list(self.client(lambda r:httpx.Response(401,text='private-token')).answer_stream('q',[HIT]))
        self.assertNotIn('private-token',str(cm.exception));self.assertIn('401',str(cm.exception))
    def test_empty_context_makes_no_cloud_request(self):
        provider=self.client(lambda r:self.fail('no evidence must not call model'))
        events=list(provider.answer_stream('q',[]))
        self.assertEqual(events[-1]['result']['status'],'refused')
    def test_nonstream_uses_same_validation_and_history(self):
        def handler(req):
            body=json.loads(req.content);self.assertFalse(body['enable_thinking'])
            self.assertEqual(body['messages'][1],{'role':'user','content':'我问X200'})
            return httpx.Response(200,json={'choices':[{'message':{'content':CONTENT},'finish_reason':'stop'}]})
        result=self.client(handler).answer('它功率？',[HIT],history=[{'role':'user','content':'我问X200'}])
        self.assertEqual(result['validation']['semantic_support'],'not_evaluated')
    def test_nonstream_length_rejected(self):
        provider=self.client(lambda r:httpx.Response(200,json={'choices':[{'message':{'content':CONTENT},'finish_reason':'length'}]}))
        with self.assertRaises(ProviderError):provider.answer('q',[HIT])

if __name__=='__main__':unittest.main()
