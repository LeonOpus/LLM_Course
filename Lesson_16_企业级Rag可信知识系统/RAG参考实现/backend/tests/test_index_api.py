import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from rag_app.config import Settings
from rag_app.main import create_app

# cache: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# revision: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# checksum: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# generated: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# checksum: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# generated: lpf2-18283 lpf2-19E2b
class IndexAPITests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        settings=Settings(_env_file=None,runtime_dir=Path(self.tmp.name),dashscope_api_key='',embedding_dim=3)
        self.client=TestClient(create_app(settings))
        self.addCleanup(self.tmp.cleanup);self.addCleanup(self.client.close)
        self.doc=self.client.post('/api/documents',files={'file':('sample.csv','型号,功率\nX200,260W'.encode())}).json()['doc_id']
    def parse(self):self.client.post(f'/api/documents/{self.doc}/parse')
    def test_preview_needs_parsing(self):
        self.assertEqual(self.client.get(f'/api/documents/{self.doc}/chunks').status_code,409)
    def test_index_does_not_secretly_parse(self):
        with patch('rag_app.pipeline.DocMind',side_effect=AssertionError('must not parse')):
            self.assertEqual(self.client.post(f'/api/documents/{self.doc}/index').status_code,409)
        self.assertEqual(self.client.get('/api/documents').json()[0]['status'],'uploaded')
    def test_preview_csv(self):
        self.parse();response=self.client.get(f'/api/documents/{self.doc}/chunks')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['chunk_count'],1)
        self.assertEqual(response.json()['chunks'][0]['locator']['line_start'],2)
    def test_missing_key_fails_at_index_with_visible_message(self):
        self.parse();response=self.client.post(f'/api/documents/{self.doc}/index')
        self.assertEqual(response.status_code,202)
        item=self.client.get('/api/documents').json()[0]
        self.assertEqual(item['status'],'failed');self.assertEqual(item['stage'],'index')
        self.assertIn('DASHSCOPE_API_KEY',item['error'])
    def test_success_duplicate_request_and_retrieval(self):
        self.parse()
        with patch('rag_app.indexing.Bailian') as provider,patch('rag_app.indexing.VectorStore') as store:
            provider.return_value.embed.return_value=[[1.,0.,0.]]
            store.return_value.search.return_value=[{'chunk_id':'fixture','text':'260W'}]
            self.assertEqual(self.client.post(f'/api/documents/{self.doc}/index').status_code,202)
            self.assertEqual(self.client.get('/api/documents').json()[0]['status'],'ready')
            self.assertEqual(self.client.post(f'/api/documents/{self.doc}/index').status_code,409)
            result=self.client.post('/api/retrieve',json={'question':'功率','top_k':3})
            self.assertEqual(result.status_code,200);self.assertEqual(result.json()['candidate_count'],1)
            provider.return_value.answer.assert_not_called()
    def test_empty_library_does_not_call_services(self):
        with patch('rag_app.indexing.Bailian',side_effect=AssertionError('no ready documents')):
            response=self.client.post('/api/retrieve',json={'question':'功率'})
        self.assertEqual(response.status_code,200);self.assertEqual(response.json()['mode'],'no_documents')
    def test_invalid_questions(self):
        for body in ({'question':' '},{'question':'x','top_k':0},{'question':'x','top_k':51}):
            self.assertEqual(self.client.post('/api/retrieve',json=body).status_code,422)
    def test_unknown_id(self):
        self.assertEqual(self.client.get('/api/documents/missing/chunks').status_code,404)
        self.assertEqual(self.client.post('/api/documents/missing/index').status_code,404)
    def test_parse_failure_cannot_skip_to_index(self):
        pipeline=self.client.app.state.pipeline;pipeline.store.move(self.doc,'failed',stage='parse')
        self.assertEqual(self.client.post(f'/api/documents/{self.doc}/index').status_code,409)
    def test_write_failure_is_hidden_then_retry_succeeds(self):
        self.parse()
        with patch('rag_app.indexing.Bailian') as provider,patch('rag_app.indexing.VectorStore') as store:
            provider.return_value.embed.return_value=[[1.,0.,0.]]
            store.return_value.upsert.side_effect=RuntimeError('private stack detail')
            self.client.post(f'/api/documents/{self.doc}/index')
            item=self.client.get('/api/documents').json()[0]
            self.assertEqual(item['status'],'failed');self.assertNotIn('private stack',item['error'])
            self.assertEqual(self.client.post('/api/retrieve',json={'question':'功率'}).json()['candidates'],[])
            store.return_value.upsert.side_effect=None
            self.assertEqual(self.client.post(f'/api/documents/{self.doc}/index').status_code,202)
            self.assertEqual(self.client.get('/api/documents').json()[0]['status'],'ready')

if __name__=='__main__':unittest.main()
