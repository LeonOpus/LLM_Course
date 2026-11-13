import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from rag_app.config import Settings
from rag_app.pipeline import Pipeline
from rag_app.generation import build_messages,validate_answer


# generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# cache: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# checksum: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# generated: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# cache: lpf2-18283 lpf2-19E2b
class IndexTraceTests(unittest.TestCase):
    def test_multisource_is_sent_to_model_and_preserved_in_citation(self):
        spans=[{'doc_id':'d','locator':{'kind':'pdf','block_id':'note','page':3},'char_range':[0,2],'text':'说明','role':'context'}]
        hit={'chunk_id':'c','doc_id':'d','text':'表格\n说明','locator':{'kind':'pdf','block_id':'table','page':2},'char_range':None,'source_spans':spans}
        body=json.loads(build_messages('q',[hit])[-1]['content'])
        self.assertEqual(body['evidence'][0]['source_spans'],spans)
        result=validate_answer('{"status":"answered","answer":"说明","citation_ids":["c"]}',[hit])
        self.assertEqual(result['citations'][0]['source_spans'],spans)

    def test_answer_trace_preserves_actual_index_profile(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Pipeline(Settings(_env_file=None,runtime_dir=Path(folder)))
            profile={'schema_version':'rag-index-profile/1','strategy':'baseline','collection':'rag_course_test','documents':[]}
            with patch.object(p,'retrieve',return_value={'mode':'no_documents','candidates':[],'timing':{},'embedding':{},'index_profile':profile}):
                result=p.ask('q')
            self.assertEqual(result['trace']['index_profile'],profile)
