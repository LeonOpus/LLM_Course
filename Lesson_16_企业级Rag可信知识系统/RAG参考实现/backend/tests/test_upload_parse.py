"""本地契约测试：全部临时目录、空凭证，不调用云服务。"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from rag_app.config import Settings
from rag_app.main import create_app

# cache: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# generated: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# checksum: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# revision: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# revision: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# checksum: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# cache: lpf2-18283 lpf2-19E2b
class UploadParseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.settings=Settings(_env_file=None,runtime_dir=Path(self.tmp.name),dashscope_api_key='',alibaba_cloud_access_key_id='',alibaba_cloud_access_key_secret='')
        self.client=TestClient(create_app(self.settings))
    def tearDown(self): self.client.close();self.tmp.cleanup()
    def upload(self,name='example.csv',data='型号,功率\nX200,260W'.encode()):
        return self.client.post('/api/documents',files={'file':(name,data)})
    def test_upload_is_not_parse_success(self):
        response=self.upload();self.assertEqual(response.status_code,201)
        doc=response.json();self.assertEqual(doc['status'],'uploaded')
        self.assertEqual(self.client.get(f"/api/documents/{doc['doc_id']}/blocks").status_code,409)
    def test_csv_parse_stops_at_parsed(self):
        doc_id=self.upload().json()['doc_id']
        self.assertEqual(self.client.post(f'/api/documents/{doc_id}/parse').status_code,202)
        doc=self.client.get('/api/documents').json()[0]
        self.assertEqual(doc['status'],'parsed');self.assertEqual(doc['chunk_count'],0)
        self.assertEqual(doc['block_count'],1);self.assertIsNone(doc['error'])
        block=self.client.get(f'/api/documents/{doc_id}/blocks').json()[0]
        self.assertIn('260W',block['text']);self.assertEqual(block['locator']['line_start'],2)
    def test_duplicate_parse_rejected(self):
        doc_id=self.upload().json()['doc_id'];self.client.post(f'/api/documents/{doc_id}/parse')
        self.assertEqual(self.client.post(f'/api/documents/{doc_id}/parse').status_code,409)
    def test_pdf_missing_key_fails_honestly(self):
        doc_id=self.upload('example.pdf',b'fixture').json()['doc_id']
        self.assertEqual(self.client.post(f'/api/documents/{doc_id}/parse').status_code,202)
        doc=self.client.get('/api/documents').json()[0]
        self.assertEqual(doc['status'],'failed');self.assertIn('DocMind AccessKey',doc['error'])
    def test_pdf_fixed_adapter_result_becomes_block(self):
        doc_id=self.upload('example.pdf',b'fixture').json()['doc_id']
        with patch('rag_app.pipeline.DocMind') as adapter:
            adapter.return_value.parse.return_value=[{'uniqueId':'b1','pageNum':0,'text':'固定测试文本'}]
            self.assertEqual(self.client.post(f'/api/documents/{doc_id}/parse').status_code,202)
            adapter.return_value.parse.assert_called_once()
        block=self.client.get(f'/api/documents/{doc_id}/blocks').json()[0]
        self.assertEqual(block['text'],'固定测试文本');self.assertEqual(block['locator']['page'],1)
        self.assertEqual(self.client.get('/api/documents').json()[0]['status'],'parsed')
    def test_empty_upload_rejected(self): self.assertEqual(self.upload('x.pdf',b'').status_code,400)
    def test_executable_rejected(self):
        self.assertEqual(self.upload('x.exe',b'bad').status_code,415)
        self.assertEqual(self.client.get('/api/documents').json(),[])
    def test_unknown_parse_404(self): self.assertEqual(self.client.post('/api/documents/missing/parse').status_code,404)
    def test_source_is_same_bytes(self):
        raw='型号,功率\nX200,260W'.encode();doc_id=self.upload('x.csv',raw).json()['doc_id']
        self.assertEqual(self.client.get(f'/api/documents/{doc_id}/source').content,raw)
    def test_status_persists_after_new_app(self):
        doc_id=self.upload().json()['doc_id'];self.client.post(f'/api/documents/{doc_id}/parse')
        with TestClient(create_app(self.settings)) as second:
            self.assertEqual(second.get('/api/documents').json()[0]['status'],'parsed')
    def test_busy_document_rejects_second_request(self):
        doc_id=self.upload().json()['doc_id'];self.client.app.state.pipeline.reserve(doc_id,operation='parse')
        self.assertEqual(self.client.post(f'/api/documents/{doc_id}/parse').status_code,409)
    def test_invalid_csv_fails_with_no_blocks(self):
        doc_id=self.upload('x.csv','型号,功率\nX200'.encode()).json()['doc_id']
        self.client.post(f'/api/documents/{doc_id}/parse')
        self.assertEqual(self.client.get('/api/documents').json()[0]['status'],'failed')
        self.assertEqual(self.client.get(f'/api/documents/{doc_id}/blocks').status_code,409)
