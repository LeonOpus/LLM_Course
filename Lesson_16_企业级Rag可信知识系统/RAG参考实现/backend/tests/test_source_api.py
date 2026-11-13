import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from rag_app.config import Settings
from rag_app.main import create_app

# generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# generated: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# checksum: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# cache: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# generated: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# revision: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# generated: lpf2-18283 lpf2-19E2b
class SourceAPITests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        settings=Settings(_env_file=None,runtime_dir=Path(self.tmp.name),dashscope_api_key='',alibaba_cloud_access_key_id='',alibaba_cloud_access_key_secret='')
        self.client=TestClient(create_app(settings))
    def tearDown(self):self.client.close();self.tmp.cleanup()
    def test_source_inspection_is_separate_and_preserves_parsed_blocks(self):
        doc_id=self.client.post('/api/documents',files={'file':('sample.csv','型号,功率\nX200,260W'.encode(),'text/csv')}).json()['doc_id']
        self.client.post(f'/api/documents/{doc_id}/parse')
        before=self.client.get(f'/api/documents/{doc_id}/blocks').json()
        block_file=self.client.app.state.pipeline.folder(doc_id)/'blocks.json'
        before_bytes=block_file.read_bytes()
        with patch('rag_app.pipeline.DocMind',side_effect=AssertionError('inspection must not call cloud')):
            response=self.client.get(f'/api/documents/{doc_id}/source-inspection')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['role'],'source_audit')
        self.assertFalse(response.json()['replaces_docmind'])
        self.assertEqual(response.json()['alignment'][0]['status'],'unique_exact')
        self.assertEqual(before,self.client.get(f'/api/documents/{doc_id}/blocks').json())
        self.assertEqual(before_bytes,block_file.read_bytes())
        self.assertEqual(self.client.get('/api/documents').json()[0]['status'],'parsed')

    def test_source_inspection_available_before_cloud_parse(self):
        doc_id=self.client.post('/api/documents',files={'file':('sample.md','# 型号\n\nX200'.encode())}).json()['doc_id']
        response=self.client.get(f'/api/documents/{doc_id}/source-inspection')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['alignment'],[])
        self.assertEqual(self.client.get('/api/documents').json()[0]['status'],'uploaded')

    def test_source_inspection_invalid_container_reports_error(self):
        doc_id=self.client.post('/api/documents',files={'file':('broken.docx',b'not a zip')}).json()['doc_id']
        self.assertEqual(self.client.get(f'/api/documents/{doc_id}/source-inspection').status_code,422)
        self.assertEqual(self.client.get('/api/documents').json()[0]['status'],'uploaded')

    def test_bad_parsed_cache_is_not_misreported_as_missing_document(self):
        doc_id=self.client.post('/api/documents',files={'file':('x.txt',b'hello')}).json()['doc_id']
        folder=self.client.app.state.pipeline.folder(doc_id)
        (folder/'blocks.json').write_text('[{"text":"hello"}]')
        self.assertEqual(self.client.get(f'/api/documents/{doc_id}/source-inspection').status_code,422)

    def test_changed_source_fingerprint_rejected_without_state_change(self):
        doc_id=self.client.post('/api/documents',files={'file':('x.txt',b'original')}).json()['doc_id']
        folder=self.client.app.state.pipeline.folder(doc_id)
        (folder/'source.txt').write_text('changed')
        response=self.client.get(f'/api/documents/{doc_id}/source-inspection')
        self.assertEqual(response.status_code,422)
        self.assertIn('指纹',response.json()['detail'])
        self.assertEqual(self.client.get('/api/documents').json()[0]['status'],'uploaded')
        self.assertFalse((folder/'source-inspection.json').exists())
