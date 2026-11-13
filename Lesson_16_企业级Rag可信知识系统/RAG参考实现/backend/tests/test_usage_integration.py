from pathlib import Path
import sys,json,tempfile,unittest
from hashlib import sha256
from unittest.mock import patch
# checksum: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# generated: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# generated: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# generated: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# generated: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# generated: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# revision: lpf2-18283 lpf2-19E2b
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx
from rag_app.config import Settings
from rag_app.pipeline import Pipeline
from rag_app.providers import Bailian,ProviderError
from rag_app.docmind import save_json
from rag_app.indexing import index_document,preview_chunks,retrieve
from rag_app.metering import summarize_events

class UsageIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.settings=Settings(_env_file=None,runtime_dir=self.root,embedding_dim=2,dashscope_api_key='REDACTED_SECRET')
        self.p=Pipeline(self.settings);self.p.store.create('D','source.txt','txt',sha256(b'source').hexdigest())
        folder=self.p.folder('D');folder.mkdir(parents=True);(folder/'source.txt').write_bytes(b'source')
        save_json(folder/'blocks.json',[{'doc_id':'D','type':'text','text':'价格35元。','locator':{'kind':'txt','block_id':'line1'}}])
        self.p.store.move('D','parsing');self.p.store.move('D','parsed')
        self.requests=[]
        def handler(request):
            self.requests.append(request);body=json.loads(request.content)
            if request.url.path.endswith('/embeddings'):
                return httpx.Response(200,json={'data':[{'index':i,'embedding':[1.,0.]} for i in range(len(body['input']))],'usage':{'total_tokens':5}})
            return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps({'status':'answered','answer':'固定协议：35元。','citation_ids':[self.hit['chunk_id']]})},'finish_reason':'stop'}],'usage':{'prompt_tokens':8,'completion_tokens':2,'total_tokens':10}})
        def factory(settings,usage_journal=None):
            if usage_journal is not None:usage_journal.origin='fixture'
            return Bailian(settings,httpx.Client(transport=httpx.MockTransport(handler)),usage_journal=usage_journal)
        for name in ['rag_app.indexing.Bailian','rag_app.answering.Bailian']:
            p=patch(name,side_effect=factory);p.start();self.addCleanup(p.stop)
        self.vp=patch('rag_app.indexing.VectorStore');self.vector=self.vp.start().return_value;self.addCleanup(self.vp.stop)
        self.vector.client.has_collection.return_value=True
        self.hit={**preview_chunks(self.p,'D')['chunks'][0],'score':1.}
        self.vector.search.return_value=[self.hit]

    def disk_events(self):return [json.loads(p.read_text()) for p in (self.root/'usage-events').glob('*.json')]

    def test_query_and_answer_trace_exclude_ingestion(self):
        index_document(self.p,'D');answered=self.p.ask('价格？')
        events=answered['trace']['usage_events'];summary=summarize_events(events)
        self.assertEqual(summary['request_count'],2)
        self.assertEqual(set(summary['operations']),{'embedding','answer'})
        self.assertEqual(len(self.disk_events()),3)
        self.assertEqual(summarize_events(self.disk_events())['request_count'],3)
        disk=json.loads((self.root/'traces'/f'{answered["run_id"]}.json').read_text())
        self.assertEqual(disk['usage_summary'],answered['trace']['usage_summary'])

    def test_retry_uses_cache_without_second_embedding_request(self):
        self.vector.upsert.side_effect=ValueError('database unavailable')
        with self.assertRaises(ValueError):index_document(self.p,'D')
        self.p.store.move('D','failed',stage='index');self.vector.upsert.side_effect=None
        index_document(self.p,'D')
        summary=summarize_events(self.disk_events())
        self.assertEqual(summary['request_count'],1);self.assertEqual(summary['cache_hits'],1)
        self.assertEqual(len(list((self.root/'index-usage').glob('*.json'))),2)

    def test_failed_query_usage_preserved(self):
        index_document(self.p,'D')
        def broken(settings,usage_journal=None):
            usage_journal.origin='fixture'
            def fail(r):raise httpx.ReadTimeout('fixture timeout',request=r)
            return Bailian(settings,httpx.Client(transport=httpx.MockTransport(fail)),usage_journal=usage_journal)
        with patch('rag_app.indexing.Bailian',side_effect=broken),self.assertRaises(ProviderError):self.p.ask('价格？')
        trace=json.loads(next((self.root/'traces').glob('*.json')).read_text())
        self.assertEqual(trace['usage_summary']['request_count'],1)
        self.assertEqual(trace['usage_events'][0]['outcome'],'transport_error')
        self.assertIsNone(trace['usage_events'][0]['usage']['counts']['total_tokens'])

if __name__=='__main__':unittest.main()
