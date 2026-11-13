from copy import deepcopy
from hashlib import sha256
import json,tempfile,unittest
from pathlib import Path
import sys
# cache: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# checksum: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# checksum: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# cache: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# cache: lpf2-18283 lpf2-19E2b
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from unittest.mock import patch
from rag_app.config import Settings
from rag_app.pipeline import Pipeline
from rag_app.docmind import save_json
from rag_app.structure import blocks_digest
from rag_app.experiments import prepare_experiment
from rag_app.indexing import preview_chunks,index_document,retrieve

class MultipageIndexTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.source=self.root/'source';self.p=Pipeline(Settings(_env_file=None,runtime_dir=self.source,dashscope_api_key='',embedding_dim=3))
        self.doc='D';self.p.store.create('D','sample.pdf','pdf',sha256(b'original-pdf-fixture').hexdigest())
        folder=self.p.folder('D');folder.mkdir(parents=True);(folder/'source.pdf').write_bytes(b'original-pdf-fixture')
        header='<tr><th colspan="2">报价</th></tr><tr><th>编码</th><th>元</th></tr>'
        self.blocks=[{'doc_id':'D','type':'table','text':'<table>'+header+f'<tr><td>A{n}</td><td>35</td></tr></table>',
                      'locator':{'kind':'pdf','page':n,'block_id':f't{n}'}} for n in [1,2]]
        self.blocks.append({'doc_id':'D','type':'text','text':'批准后更换。','locator':{'kind':'pdf','page':1,'block_id':'note'}})
        self.plan={'schema_version':2,'blocks_sha256':blocks_digest(self.blocks),'review_note':'测试契约，非DocMind',
                   'groups':[{'doc_id':'D','block_ids':['t1','t2'],'header_rows':2,'context_block_ids':['note']}]}
        self.save();self.p.store.move('D','parsing');self.p.store.move('D','parsed')
        self.cloud=patch('rag_app.indexing.Bailian');self.provider=self.cloud.start().return_value;self.addCleanup(self.cloud.stop)
        self.provider.embed.side_effect=lambda texts:[[1.,0.,0.] for _ in texts]
        self.db=patch('rag_app.indexing.VectorStore');self.vector=self.db.start().return_value;self.addCleanup(self.db.stop)
        self.vector.client.has_collection.return_value=False
        self.vector.ensure_collection.side_effect=lambda:setattr(self.vector.client.has_collection,'return_value',True)

    def save(self):
        save_json(self.p.folder('D')/'blocks.json',self.blocks);save_json(self.p.folder('D')/'chunk-plan.json',self.plan)

    def prepare(self,strategy='multipage_context'):
        target=self.root/strategy;manifest=prepare_experiment(self.source,target,strategy)
        return Pipeline(Settings(_env_file=None,runtime_dir=target,chunk_strategy=strategy,milvus_collection=manifest['collection'],embedding_dim=3,dashscope_api_key=''))

    def test_actual_index_and_retrieval_profile(self):
        p=self.prepare();preview=preview_chunks(p,'D');c=preview['config']
        self.assertEqual(c['algorithm_version'],'m12c-multipage-v1');self.assertEqual(c['plan_schema_version'],2)
        self.assertEqual(c['reviewed_table_count'],2)
        index_document(p,'D')
        self.assertEqual([t for call in self.provider.embed.call_args_list for t in call.args[0]],[c['text'] for c in preview['chunks']])
        sent=self.vector.upsert.call_args.args[0];self.assertEqual(sent,preview['chunks'])
        sources=sent[0]['source_spans'];self.assertEqual({s['locator']['page'] for s in sources if s['role']=='data_row'},{1,2})
        self.vector.search.return_value=[{**sent[0],'score':1.}]
        result=retrieve(p,'A2的价格');self.assertEqual(result['candidates'][0]['source_spans'],sources)
        self.assertEqual(result['index_profile']['documents'][0]['chunking'],c)
        self.assertTrue((p.folder('D')/'chunks-multipage_context.json').exists())
        from rag_app.generation import validate_answer
        with patch('rag_app.answering.Bailian') as model:
            model.return_value.answer.side_effect=lambda question,hits,history=None:validate_answer(
                json.dumps({'status':'answered','answer':'固定协议回答，非质量评分','citation_ids':[hits[0]['chunk_id']]}),hits)
            answered=p.ask('A2的价格')
        self.assertEqual(answered['trace']['index_profile'],result['index_profile'])
        self.assertEqual(answered['citations'][0]['source_spans'],sources)
        disk=json.loads((p.settings.runtime_dir/'traces'/f'{answered["run_id"]}.json').read_text())
        self.assertEqual(disk['index_profile'],result['index_profile'])

    def test_explicit_empty_plan_keeps_baseline_and_count_zero(self):
        from rag_app.core import chunk_blocks
        self.blocks[0]['metadata']={'transformation':'P2','group_block_ids':['forged']}
        self.plan['blocks_sha256']=blocks_digest(self.blocks)
        self.plan['groups']=[];self.save();p=self.prepare();preview=preview_chunks(p,'D')
        self.assertEqual(preview['chunks'],chunk_blocks(self.blocks))
        self.assertEqual(preview['config']['reviewed_table_count'],0)

    def test_missing_plan_and_wrong_schema_fail_before_target_creation(self):
        path=self.p.folder('D')/'chunk-plan.json';path.unlink()
        with self.assertRaises(ValueError):self.prepare()
        self.assertFalse((self.root/'multipage_context').exists())
        self.plan['schema_version']=1;self.save()
        with self.assertRaises(ValueError):self.prepare()
        self.provider.embed.assert_not_called();self.vector.upsert.assert_not_called()

    def test_disabled_long_context_does_not_break_rows(self):
        self.blocks[-1]['text']='长说明'*500;self.plan['blocks_sha256']=blocks_digest(self.blocks);self.save()
        p=self.prepare('multipage_rows');self.assertTrue(preview_chunks(p,'D')['chunks'])
        with self.assertRaisesRegex(ValueError,'预算'):self.prepare('multipage_context')

    def test_changed_plan_after_prepare_is_not_reused(self):
        p=self.prepare();new=deepcopy(self.plan);new['review_note']='changed';save_json(p.folder('D')/'chunk-plan.json',new)
        with self.assertRaisesRegex(ValueError,'计划'):index_document(p,'D')
        self.provider.embed.assert_not_called();self.vector.upsert.assert_not_called()

    def test_changed_strategy_is_not_only_label_change(self):
        p=self.prepare();p.settings.chunk_strategy='multipage_rows'
        with self.assertRaisesRegex(ValueError,'配置'):preview_chunks(p,'D')

if __name__=='__main__':unittest.main()
