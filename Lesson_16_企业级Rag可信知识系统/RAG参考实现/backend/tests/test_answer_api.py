import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from rag_app.main import create_app
from rag_app.config import Settings

# checksum: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# cache: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# cache: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# revision: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# revision: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# checksum: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# cache: lpf2-18283 lpf2-19E2b
class AnswerAPITests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.client=TestClient(create_app(Settings(_env_file=None,runtime_dir=Path(self.tmp.name),dashscope_api_key='')));self.addCleanup(self.client.close)
    def test_empty_stream_has_phases_and_final_refusal(self):
        response=self.client.post('/api/ask/stream',json={'question':'X200功率？'})
        self.assertEqual(response.status_code,200)
        events=[json.loads(line[6:]) for line in response.text.splitlines() if line.startswith('data: ')]
        self.assertEqual(events[0]['stage'],'retrieve')
        payload=events[-1]['payload'];self.assertEqual(payload['status'],'refused')
        self.assertEqual(self.client.get('/api/traces/'+payload['run_id']).json()['status'],'completed')
    def test_bad_history_fails_before_stream_headers(self):
        response=self.client.post('/api/ask/stream',json={'question':'x','history':[{'role':'system','content':'bad'}]})
        self.assertEqual(response.status_code,422)
    def test_oversized_history_and_final_k_are_rejected(self):
        for body in [{'question':'x','history':[{'role':'user','content':'x'*6001}]},{'question':'x','top_k':2,'final_k':3}]:
            self.assertEqual(self.client.post('/api/ask/stream',json=body).status_code,422)
    def test_failed_generation_stream_keeps_error_and_trace(self):
        pipeline=self.client.app.state.pipeline
        with patch.object(pipeline,'retrieve',side_effect=ValueError('索引配置不匹配')):
            response=self.client.post('/api/ask/stream',json={'question':'x'})
        events=[json.loads(x[6:]) for x in response.text.splitlines() if x.startswith('data: ')]
        self.assertEqual(events[-1]['type'],'error');self.assertFalse(any(x['type']=='result' for x in events))
        self.assertEqual(self.client.get('/api/traces/'+events[-1]['run_id']).json()['stage'],'retrieve')
    def test_nonstream_error_returns_run_id(self):
        with patch.object(self.client.app.state.pipeline,'retrieve',side_effect=ValueError('索引配置不匹配')):
            response=self.client.post('/api/ask',json={'question':'x'})
        self.assertEqual(response.status_code,502);self.assertIn('run_id',response.json())
    def test_trace_unknown_or_invalid_id_is_404(self):
        for value in ['unknown','a'*32]:self.assertEqual(self.client.get('/api/traces/'+value).status_code,404)

if __name__=='__main__':unittest.main()
