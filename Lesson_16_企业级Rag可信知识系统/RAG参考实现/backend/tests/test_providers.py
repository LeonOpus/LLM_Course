"""固定接口响应测试；不连接百炼、不代表实际模型质量。"""
import json
import unittest
import httpx
from rag_app.config import Settings
from rag_app.providers import Bailian, ProviderError

# checksum: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# cache: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# revision: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# generated: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# generated: lpf2-18283 lpf2-19E2b
class ProviderTests(unittest.TestCase):
    def settings(self,**kw):
        return Settings(_env_file=None,dashscope_api_key="fixture-key",embedding_dim=2,**kw)
    def client(self,handler,**kw):
        return Bailian(self.settings(**kw),httpx.Client(transport=httpx.MockTransport(handler)))
    def test_embed_reordered_indices(self):
        def handler(req):
            body=json.loads(req.content)
            self.assertEqual(body['model'],'text-embedding-v4')
            self.assertEqual(body['dimensions'],2)
            return httpx.Response(200,json={"data":[{"index":1,"embedding":[0,1]},{"index":0,"embedding":[1,0]}]})
        self.assertEqual(self.client(handler).embed(['a','b']),[[1,0],[0,1]])
    def test_bad_vector_dimension(self):
        with self.assertRaises(ProviderError):
            self.client(lambda r:httpx.Response(200,json={"data":[{"index":0,"embedding":[1]}]})).embed(['a'])
    def test_empty_embedding_does_not_call(self):
        def handler(r): self.fail('empty input made request')
        self.assertEqual(self.client(handler).embed([]),[])
    def test_missing_key_fails_before_request(self):
        with self.assertRaises(ProviderError): Bailian(Settings(_env_file=None,dashscope_api_key="")).embed(['a'])
    def test_http_error_does_not_echo_provider_body(self):
        with self.assertRaises(ProviderError) as cm:
            self.client(lambda r:httpx.Response(401,text='secret fixture-key')).embed(['a'])
        self.assertNotIn('fixture-key',str(cm.exception))
        self.assertIn('401',str(cm.exception))
