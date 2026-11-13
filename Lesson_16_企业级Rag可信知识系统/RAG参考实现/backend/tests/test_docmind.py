"""SDK 固定响应测试，不上传文档、不消耗 DocMind 额度。"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from rag_app.config import Settings
from rag_app.docmind import DocMind
from rag_app.providers import ProviderError

# cache: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# generated: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# cache: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# generated: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# checksum: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# checksum: lpf2-18283 lpf2-19E2b
class FakeSDK:
    def __init__(self): self.submissions=0;self.offsets=[];self.fail_status=False
    def submit_doc_parser_job_advance(self,request,runtime):
        self.submissions+=1
        assert request.file_url_object.read()==b'fixture'
        return SimpleNamespace(body={'Data':{'Id':'fixture-job'}})
    def query_doc_parser_status(self,request):
        if self.fail_status: raise TimeoutError()
        return SimpleNamespace(body={'Data':{'Status':'success'}})
    def get_doc_parser_result(self,request):
        self.offsets.append(request.layout_num)
        count=100 if request.layout_num==0 else 1
        return SimpleNamespace(body={'Data':json.dumps({'layouts':[{'uniqueId':str(request.layout_num+i),'pageNum':0,'text':'fixture'} for i in range(count)]})})

class DocMindTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.dir=Path(self.tmp.name)
        self.file=self.dir/'sample.pdf';self.file.write_bytes(b'fixture')
        self.settings=Settings(_env_file=None,alibaba_cloud_access_key_id='fixture',alibaba_cloud_access_key_secret='fixture')
        self.sdk=FakeSDK();self.parser=DocMind(self.settings,self.sdk)
    def tearDown(self): self.tmp.cleanup()
    def test_pagination_and_raw_persistence(self):
        result=self.parser.parse(self.file,self.dir/'cache')
        self.assertEqual(len(result),101)
        self.assertEqual(self.sdk.offsets,[0,100])
        self.assertTrue((self.dir/'cache'/'result-000100.json').exists())
    def test_resume_does_not_resubmit(self):
        self.sdk.fail_status=True
        with self.assertRaises(ProviderError): self.parser.parse(self.file,self.dir/'cache')
        self.sdk.fail_status=False
        self.parser.parse(self.file,self.dir/'cache')
        self.assertEqual(self.sdk.submissions,1)
    def test_source_change_rejects_cached_job(self):
        self.parser.parse(self.file,self.dir/'cache')
        self.file.write_bytes(b'changed')
        with self.assertRaises(ProviderError): self.parser.parse(self.file,self.dir/'cache')
    def test_uncertain_submission_blocks_blind_retry(self):
        def fail(*a): self.sdk.submissions+=1;raise TimeoutError()
        self.sdk.submit_doc_parser_job_advance=fail
        with self.assertRaises(ProviderError): self.parser.parse(self.file,self.dir/'cache')
        with self.assertRaises(ProviderError): self.parser.parse(self.file,self.dir/'cache')
        self.assertEqual(self.sdk.submissions,1)
    def test_changed_options_do_not_reuse_old_parse(self):
        self.parser.parse(self.file,self.dir/'cache')
        with self.assertRaises(ProviderError): self.parser.parse(self.file,self.dir/'cache',enhance=True)

    def test_documented_fail_status_stops_without_sleep_or_download(self):
        self.sdk.query_doc_parser_status=lambda request: SimpleNamespace(body={'Data':{'Status':'Fail'}})
        with patch('rag_app.docmind.time.sleep',side_effect=AssertionError('terminal Fail must not poll')):
            with self.assertRaisesRegex(ProviderError,'解析失败'):
                self.parser.parse(self.file,self.dir/'cache')
        self.assertEqual(self.sdk.offsets,[])
        self.assertEqual(json.loads((self.dir/'cache'/'status.json').read_text())['Data']['Status'],'Fail')
