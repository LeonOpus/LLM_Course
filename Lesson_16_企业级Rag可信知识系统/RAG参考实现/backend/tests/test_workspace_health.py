import unittest,tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from rag_app.config import Settings
from rag_app.main import create_app,KINDS

# generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# revision: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# checksum: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# checksum: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# generated: lpf2-18283 lpf2-19E2b
class WorkspaceHealthTests(unittest.TestCase):
    def test_full_configuration_contract_and_no_secret_values(self):
        with tempfile.TemporaryDirectory() as folder:
            settings=Settings(_env_file=None,runtime_dir=Path(folder),dashscope_api_key='REDACTED_SECRET',
                alibaba_cloud_access_key_id='',alibaba_cloud_access_key_secret='',rerank_url='',
                chat_model='qwen-plus',embedding_model='text-embedding-v4',embedding_dim=1024,
                chunk_strategy='baseline',milvus_collection='ui_test',retrieval_mode='hybrid',
                query_rewrite='contextual',generation_policy='evidence_ledger')
            with TestClient(create_app(settings)) as client:response=client.get('/api/health')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json(),{'status':'ok','service':'rag-backend','configured':{'bailian':True,'docmind':False,'rerank':False},
            'verification':'configuration_only','supported_extensions':sorted(KINDS),'strategies':['baseline','rerank'],
            'context_configuration':{'context_policy':'baseline'},'index_configuration':{'chunk_strategy':'baseline','collection':'ui_test'},
            'query_configuration':{'retrieval_mode':'hybrid','query_rewrite':'contextual','generation_policy':'evidence_ledger'},
            'models':{'chat':'qwen-plus','embedding':'text-embedding-v4','dimension':1024}})
        self.assertNotIn('fixture-private-key',response.text)
    def test_configuration_presence_does_not_claim_service_connectivity(self):
        with tempfile.TemporaryDirectory() as folder:
            settings=Settings(_env_file=None,runtime_dir=Path(folder),dashscope_api_key='',
                alibaba_cloud_access_key_id='',alibaba_cloud_access_key_secret='',milvus_uri='http://127.0.0.1:1')
            with TestClient(create_app(settings)) as client:data=client.get('/api/health').json()
        self.assertEqual(data['configured']['bailian'],False)
        self.assertEqual(data['verification'],'configuration_only')
        self.assertEqual(data['service'],'rag-backend')

if __name__=='__main__':unittest.main()
