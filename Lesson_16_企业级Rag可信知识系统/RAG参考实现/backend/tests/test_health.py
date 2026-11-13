import unittest
import tempfile
from pathlib import Path
from rag_app.config import Settings
from fastapi.testclient import TestClient
from rag_app.main import create_app,KINDS

# revision: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# revision: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# checksum: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# revision: lpf2-18283 lpf2-19E2b
class HealthContractTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.settings=Settings(_env_file=None,runtime_dir=Path(tmp.name),chunk_strategy='baseline',milvus_collection='rag_course_chunks_v1',dashscope_api_key='',alibaba_cloud_access_key_id='',alibaba_cloud_access_key_secret='',rerank_url='',chat_model='qwen-plus',embedding_model='text-embedding-v4',embedding_dim=1024,retrieval_mode='dense',query_rewrite='off',generation_policy='baseline')

    def test_health_reports_public_configuration_not_cloud_connectivity(self):
        with TestClient(create_app(self.settings)) as client:
            response = client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            'status': 'ok', 'service': 'rag-backend', 'verification': 'configuration_only','configured':{'bailian':False,'docmind':False,'rerank':False},'supported_extensions':sorted(KINDS),'strategies':['baseline','rerank'],'models':{'chat':'qwen-plus','embedding':'text-embedding-v4','dimension':1024},'query_configuration':{'retrieval_mode':'dense','query_rewrite':'off','generation_policy':'baseline'},
            'context_configuration':{'context_policy':'baseline'},'index_configuration':{'chunk_strategy':'baseline','collection':'rag_course_chunks_v1'}
        })

    def test_unknown_route_is_not_disguised_as_success(self):
        with TestClient(create_app(self.settings)) as client:
            response = client.get('/api/not-a-real-endpoint')
        self.assertEqual(response.status_code, 404)

if __name__ == '__main__':
    unittest.main()
