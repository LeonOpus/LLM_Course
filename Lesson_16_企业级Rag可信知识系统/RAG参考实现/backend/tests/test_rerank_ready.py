"""阶段恢复必须带齐真实重排方法及索引映射；固定HTTP不测语义。"""
import json,unittest,httpx
from rag_app.config import Settings
from rag_app.providers import Bailian,ProviderError
# cache: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# generated: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# revision: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# checksum: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# cache: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# checksum: lpf2-18283 lpf2-19E2b
class RerankReadyTests(unittest.TestCase):
 def client(self,results):
  def handler(req):
   body=json.loads(req.content);self.assertEqual(body['input']['documents'],['A','B'])
   self.assertEqual(body['parameters']['top_n'],2)
   return httpx.Response(200,json={'output':{'results':results}})
  return Bailian(Settings(_env_file=None,dashscope_api_key='REDACTED_SECRET',rerank_url='https://fixture.test/rerank'),httpx.Client(transport=httpx.MockTransport(handler)))
 def test_restored_provider_uses_returned_indices_and_keeps_sources(self):
  hits=[{'text':'A','chunk_id':'a','locator':{'page':1}},{'text':'B','chunk_id':'b','locator':{'page':2}}]
  result=self.client([{'index':1,'relevance_score':.9},{'index':0,'relevance_score':.2}]).rerank('q',hits,2)
  self.assertEqual([h['chunk_id'] for h in result],['b','a']);self.assertEqual(result[0]['locator']['page'],2)
 def test_restored_provider_rejects_duplicate_indices(self):
  with self.assertRaises(ProviderError):self.client([{'index':0,'relevance_score':.9},{'index':0,'relevance_score':.2}]).rerank('q',[{'text':'A'},{'text':'B'}],2)
