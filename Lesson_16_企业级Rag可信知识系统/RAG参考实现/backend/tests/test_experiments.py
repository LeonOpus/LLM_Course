from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from rag_app.config import Settings
from rag_app.pipeline import Pipeline
from rag_app.docmind import save_json
from rag_app.experiments import prepare_experiment
from rag_app.indexing import index_document, preview_chunks, retrieve
from rag_app.structure import blocks_digest


# revision: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# cache: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# generated: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# revision: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# revision: lpf2-18283 lpf2-19E2b
class ExperimentTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.source=self.root/'source'
        self.p=Pipeline(Settings(_env_file=None,runtime_dir=self.source,dashscope_api_key='',embedding_dim=3))
        self.doc='fixture-doc';self.p.store.create(self.doc,'fixture.txt','txt',sha256(b'original').hexdigest())
        folder=self.p.folder(self.doc);folder.mkdir(parents=True);(folder/'source.txt').write_bytes(b'original')
        text='<table>\n<tr><td>材料</td><td>要求</td></tr>\n'+''.join('<tr><td>项目'+str(i)+'</td><td>'+('说明'*15)+'</td></tr>\n' for i in range(20))+'</table>'
        self.blocks=[{'doc_id':self.doc,'text':text,'type':'table','locator':{'kind':'txt','block_id':'t'}},
                     {'doc_id':self.doc,'text':'原件中的说明','type':'text','locator':{'kind':'txt','block_id':'n'}}]
        self.plan={'schema_version':1,'blocks_sha256':blocks_digest(self.blocks),'review_note':'协议固定样例',
                   'tables':[{'doc_id':self.doc,'block_id':'t','header_rows':1,'context_block_ids':['n']}]}
        save_json(folder/'blocks.json',self.blocks);save_json(folder/'chunk-plan.json',self.plan)
        self.p.store.move(self.doc,'parsing');self.p.store.move(self.doc,'parsed')
        self.provider_patch=patch('rag_app.indexing.Bailian');self.provider=self.provider_patch.start().return_value
        self.provider.embed.side_effect=lambda texts:[[1.,0.,0.] for _ in texts]
        self.vector_patch=patch('rag_app.indexing.VectorStore');self.vector=self.vector_patch.start().return_value
        self.vector.client.has_collection.return_value=False
        self.vector.ensure_collection.side_effect=lambda:setattr(self.vector.client.has_collection,'return_value',True)
        self.addCleanup(self.provider_patch.stop);self.addCleanup(self.vector_patch.stop)

    def experiment(self,strategy='table_rows'):
        target=self.root/'experiment';manifest=prepare_experiment(self.source,target,strategy)
        settings=Settings(_env_file=None,runtime_dir=target,chunk_strategy=strategy,
                          milvus_collection=manifest['collection'],embedding_dim=3,dashscope_api_key='')
        return Pipeline(settings)

    def test_prepare_preserves_source_but_no_old_index_or_caches(self):
        save_json(self.p.folder(self.doc)/'index-manifest.json',{'old':True})
        result=self.experiment();folder=result.folder(self.doc)
        self.assertEqual((folder/'source.txt').read_bytes(),b'original')
        self.assertEqual((folder/'blocks.json').read_bytes(),(self.p.folder(self.doc)/'blocks.json').read_bytes())
        self.assertFalse((folder/'index-manifest.json').exists())
        self.assertEqual(result.store.get(self.doc)['status'],'parsed')
        self.assertNotEqual(result.settings.milvus_collection,self.p.settings.milvus_collection)

    def test_prepare_refuses_existing_target_and_unparsed_documents(self):
        with self.assertRaises(ValueError):prepare_experiment(self.source,self.source,'baseline')
        self.p.store.create('missing','missing.txt','txt','a'*64)
        with self.assertRaises(ValueError):prepare_experiment(self.source,self.root/'new','baseline')
        self.assertFalse((self.root/'new').exists())

    def test_optimized_requires_prepared_experiment(self):
        self.p.settings.chunk_strategy='table_rows'
        with self.assertRaisesRegex(ValueError,'独立实验'):preview_chunks(self.p,self.doc)

    def test_preview_and_actual_embedding_use_selected_table_strategy(self):
        p=self.experiment();preview=preview_chunks(p,self.doc)
        self.assertEqual(preview['config']['strategy'],'table_rows')
        for c in preview['chunks']:
            if c['type']=='table':self.assertIn('<td>材料</td>',c['text']);self.assertIn('source_spans',c)
        index_document(p,self.doc)
        embedded=[t for args in self.provider.embed.call_args_list for t in args.args[0]]
        self.assertEqual(embedded,[c['text'] for c in preview['chunks']])
        manifest=json.loads((p.folder(self.doc)/'index-manifest.json').read_text())
        self.assertEqual(manifest['chunking'],preview['config'])
        self.assertTrue((p.folder(self.doc)/'chunks-table_rows.json').exists())

    def test_missing_plan_and_changed_plan_rejected_before_paid_call(self):
        p=self.experiment();path=p.folder(self.doc)/'chunk-plan.json';path.unlink()
        with self.assertRaises(ValueError):index_document(p,self.doc)
        self.provider.embed.assert_not_called()
        save_json(path,{**self.plan,'review_note':'changed'})
        with self.assertRaisesRegex(ValueError,'计划'):index_document(p,self.doc)
        self.provider.embed.assert_not_called()

    def test_changed_strategy_or_collection_rejected(self):
        for name,value in [('chunk_strategy','baseline'),('milvus_collection','rag_course_wrong')]:
            with self.subTest(name=name):
                target=self.root/name
                manifest=prepare_experiment(self.source,target,'table_rows')
                settings=Settings(_env_file=None,runtime_dir=target,chunk_strategy='table_rows',milvus_collection=manifest['collection'])
                setattr(settings,name,value);p=Pipeline(settings)
                with self.assertRaisesRegex(ValueError,'配置'):preview_chunks(p,self.doc)

    def test_changed_blocks_rejected_before_retrieval(self):
        p=self.experiment();index_document(p,self.doc);self.provider.embed.reset_mock()
        altered=deepcopy(self.blocks);altered[0]['text']+='changed';save_json(p.folder(self.doc)/'blocks.json',altered)
        with self.assertRaisesRegex(ValueError,'指纹'):retrieve(p,'q')
        self.provider.embed.assert_not_called()

    def test_retrieval_contains_frozen_index_profile(self):
        p=self.experiment();index_document(p,self.doc);self.vector.search.return_value=[]
        result=retrieve(p,'q');profile=result['index_profile']
        self.assertEqual(profile['strategy'],'table_rows');self.assertEqual(profile['collection'],p.settings.milvus_collection)
        self.assertEqual(profile['documents'][0]['doc_id'],self.doc)
        self.assertEqual(profile['documents'][0]['plan_sha256'],blocks_digest(self.plan))

    def test_existing_unowned_collection_is_never_reused(self):
        p=self.experiment();self.vector.client.has_collection.return_value=True
        with self.assertRaisesRegex(ValueError,'已存在'):index_document(p,self.doc)
        self.provider.embed.assert_not_called();self.vector.upsert.assert_not_called()

    def test_deleted_experiment_collection_is_not_an_empty_success(self):
        p=self.experiment();index_document(p,self.doc);self.provider.embed.reset_mock()
        self.vector.client.has_collection.return_value=False
        with self.assertRaisesRegex(ValueError,'collection'):retrieve(p,'q')
        self.provider.embed.assert_not_called()

    def test_collection_connection_failure_can_retry_index_stage(self):
        p=self.experiment();self.vector.ensure_collection.side_effect=ValueError('Milvus暂不可达')
        p.index_only(self.doc)
        self.assertEqual(p.store.get(self.doc)['status'],'failed')
        self.assertEqual(p.store.get(self.doc)['stage'],'index')
        self.vector.ensure_collection.side_effect=lambda:setattr(self.vector.client.has_collection,'return_value',True)
        p.reserve(self.doc,'index');p.index_only(self.doc)
        self.assertEqual(p.store.get(self.doc)['status'],'ready')

    def test_plan_with_large_disabled_context_does_not_break_p1(self):
        self.blocks[1]['text']='长说明'*300;self.plan['blocks_sha256']=blocks_digest(self.blocks)
        save_json(self.p.folder(self.doc)/'blocks.json',self.blocks);save_json(self.p.folder(self.doc)/'chunk-plan.json',self.plan)
        p=self.experiment();self.assertTrue(preview_chunks(p,self.doc)['chunks'])
        with self.assertRaisesRegex(ValueError,'完整数据行'):
            prepare_experiment(self.source,self.root/'context','table_context')
