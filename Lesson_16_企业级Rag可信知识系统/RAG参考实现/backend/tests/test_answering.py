import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from rag_app.config import Settings
from rag_app.pipeline import Pipeline
from rag_app.providers import ProviderError
from rag_app.answering import answer_events

# generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# cache: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# checksum: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# cache: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# cache: lpf2-18283 lpf2-19E2b
HIT={'chunk_id':'a','doc_id':'d','text':'X200 260W','locator':{'kind':'txt','block_id':'b','line_start':1,'line_end':1}}
ANSWER={'status':'answered','answer':'260W','citations':[HIT],'usage':{'total_tokens':9},'validation':{'semantic_support':'not_evaluated'}}

class AnsweringTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.pipeline=Pipeline(Settings(_env_file=None,runtime_dir=Path(self.tmp.name),dashscope_api_key=''))
    def retrieval(self,hits=None):return {'mode':'live','candidates':[HIT] if hits is None else hits,'timing':{'embed_ms':1,'retrieve_ms':2},'embedding':{'model':'text-embedding-v4','dimension':1024}}
    def traces(self):return [json.loads(p.read_text()) for p in Path(self.tmp.name).glob('traces/*.json')]
    def test_empty_library_refuses_without_cloud_and_keeps_trace(self):
        events=list(answer_events(self.pipeline,'X200功率？'))
        payload=events[-1]['payload']
        self.assertEqual(payload['status'],'refused');self.assertEqual(payload['trace']['mode'],'no_documents')
        self.assertEqual(self.traces()[0]['status'],'completed')
    def test_selected_context_is_exactly_what_model_receives(self):
        other={**HIT,'chunk_id':'b','text':'另一个型号'}
        with patch.object(self.pipeline,'retrieve',return_value=self.retrieval([HIT,other])) as retrieve,patch('rag_app.answering.Bailian') as provider:
            provider.return_value.answer_stream.return_value=iter([{'type':'draft','text':'{"status"'},{'type':'answer','result':ANSWER}])
            events=list(answer_events(self.pipeline,'功率？',final_k=1))
            retrieve.assert_called_once_with('功率？',top_k=10,doc_ids=None)
            self.assertEqual(provider.return_value.answer_stream.call_args.args,('功率？',[HIT]))
        trace=events[-1]['payload']['trace']
        self.assertEqual(len(trace['candidates']),2);self.assertEqual(trace['context'],[HIT])
        self.assertEqual(trace['selection']['excluded'][0]['reason'],'final_k')
        self.assertEqual(trace['status'],'completed')
    def test_failure_keeps_context_but_never_produces_result(self):
        with patch.object(self.pipeline,'retrieve',return_value=self.retrieval()),patch('rag_app.answering.Bailian') as provider:
            provider.return_value.answer_stream.side_effect=ProviderError('引用校验失败')
            events=list(answer_events(self.pipeline,'q'))
        self.assertEqual(events[-1]['type'],'error')
        trace=self.traces()[0];self.assertEqual(trace['status'],'failed');self.assertEqual(trace['context'],[HIT]);self.assertNotIn('result',trace)
    def test_retrieval_failure_is_recorded_with_stage(self):
        with patch.object(self.pipeline,'retrieve',side_effect=ValueError('查询配置不匹配')):
            events=list(answer_events(self.pipeline,'q'))
        self.assertEqual(events[-1]['stage'],'retrieve');self.assertEqual(self.traces()[0]['status'],'failed')
    def test_closing_iterator_records_cancelled_and_closes_upstream(self):
        closed=[]
        def upstream():
            try:
                yield {'type':'draft','text':'first'}
                yield {'type':'answer','result':ANSWER}
            finally:closed.append(True)
        with patch.object(self.pipeline,'retrieve',return_value=self.retrieval()),patch('rag_app.answering.Bailian') as provider:
            provider.return_value.answer_stream.return_value=upstream()
            gen=answer_events(self.pipeline,'q')
            for event in gen:
                if event['type']=='draft':break
            gen.close()
        self.assertEqual(closed,[True]);self.assertEqual(self.traces()[0]['status'],'cancelled')
    def test_nonstream_same_trace_and_validation_contract(self):
        with patch.object(self.pipeline,'retrieve',return_value=self.retrieval()),patch('rag_app.answering.Bailian') as provider:
            provider.return_value.answer.return_value=ANSWER
            events=list(answer_events(self.pipeline,'q',stream=False))
        self.assertEqual(events[-1]['type'],'result');self.assertEqual(events[-1]['payload']['answer'],'260W')
    def test_invalid_history_fails_before_retrieval(self):
        with patch.object(self.pipeline,'retrieve') as retrieve:
            with self.assertRaises(ValueError):list(answer_events(self.pipeline,'q',history=[{'role':'system','content':'bad'}]))
            retrieve.assert_not_called()
    def test_expanded_context_and_policy_reach_model_and_trace(self):
        self.pipeline.settings.context_policy='parent_section'
        parent={**HIT,'chunk_id':'parent','text':'X200 260W，仅适用于指定模式'}
        selected={'hits':[parent],'text_chars':len(parent['text']),'decisions':[{'action':'expanded'}]}
        with patch.object(self.pipeline,'retrieve',return_value=self.retrieval()),patch('rag_app.answering.select_for_pipeline',return_value=selected) as selection,patch('rag_app.answering.Bailian') as provider:
            provider.return_value.answer.return_value=ANSWER
            events=list(answer_events(self.pipeline,'q',stream=False))
            self.assertEqual(provider.return_value.answer.call_args.args,('q',[parent]))
        trace=events[-1]['payload']['trace'];self.assertEqual(trace['candidates'],[HIT])
        self.assertEqual(trace['context'],[parent]);self.assertEqual(trace['context_profile']['mode'],'parent_section')
        self.assertIn('context_ms',trace['timing'])

if __name__=='__main__':unittest.main()
