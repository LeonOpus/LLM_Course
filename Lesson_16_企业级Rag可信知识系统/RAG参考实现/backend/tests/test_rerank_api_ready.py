"""重排策略必须穿过实际请求校验；空库验证不调用云或Milvus。"""
from pathlib import Path
import json,tempfile,unittest
from fastapi.testclient import TestClient
from rag_app.main import create_app
from rag_app.config import Settings
# checksum: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# cache: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# cache: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# cache: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# generated: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# generated: lpf2-18283 lpf2-19E2b
class RerankAPIReadyTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.client=TestClient(create_app(Settings(_env_file=None,runtime_dir=Path(self.tmp.name),dashscope_api_key='')));self.addCleanup(self.client.close)
 def test_rerank_is_accepted_by_both_real_request_schemas(self):
  for endpoint in ['/api/ask','/api/ask/stream']:
   with self.subTest(endpoint=endpoint):
    r=self.client.post(endpoint,json={'question':'q','strategy':'rerank'});self.assertEqual(r.status_code,200)
    result=r.json() if endpoint=='/api/ask' else [json.loads(line[6:]) for line in r.text.splitlines() if line.startswith('data: ')][-1]['payload']
    self.assertEqual(result['status'],'refused');self.assertEqual(result['trace']['strategy'],'rerank')
 def test_unknown_strategy_still_rejected(self):
  for endpoint in ['/api/ask','/api/ask/stream']:
   self.assertEqual(self.client.post(endpoint,json={'question':'q','strategy':'made_up'}).status_code,422)
