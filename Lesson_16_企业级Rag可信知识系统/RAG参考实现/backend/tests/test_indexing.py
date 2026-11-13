"""M09 行为测试：固定向量仅验证协议、状态与失败恢复，不评价语义。"""
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
from rag_app.indexing import preview_chunks, index_document, retrieve

# revision: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# cache: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# checksum: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# revision: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# checksum: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# checksum: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# cache: lpf2-18283 lpf2-19E2b
class IndexingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.settings=Settings(_env_file=None,runtime_dir=Path(self.tmp.name),embedding_dim=3,dashscope_api_key='')
        self.pipeline=Pipeline(self.settings)
        self.doc='fixture-doc'
        self.pipeline.store.create(self.doc,'fixture.txt','txt',sha256(b'original').hexdigest())
        self.folder=self.pipeline.folder(self.doc);self.folder.mkdir(parents=True)
        (self.folder/'source.txt').write_bytes(b'original')
        self.blocks=[{'doc_id':self.doc,'text':'甲'*650,'type':'text','locator':{'kind':'txt','block_id':'line1','line_start':1,'line_end':1},'metadata':{'role':'parser'}}]
        save_json(self.folder/'blocks.json',self.blocks)
        self.pipeline.store.move(self.doc,'parsing')
        self.pipeline.store.move(self.doc,'parsed')
        self.provider_patch=patch('rag_app.indexing.Bailian');self.provider=self.provider_patch.start().return_value
        self.provider.embed.side_effect=lambda texts:[[1.,0.,0.] for text in texts]
        self.vector_patch=patch('rag_app.indexing.VectorStore');self.vector=self.vector_patch.start().return_value
        self.addCleanup(self.provider_patch.stop);self.addCleanup(self.vector_patch.stop)
        self.addCleanup(self.tmp.cleanup)

    def test_preview_has_overlap_and_exact_source_without_cloud_or_state_change(self):
        before=(self.folder/'blocks.json').read_bytes()
        result=preview_chunks(self.pipeline,self.doc)
        self.assertEqual([c['char_range'] for c in result['chunks']],[[0,600],[500,650]])
        self.assertEqual(result['chunks'][1]['locator'],self.blocks[0]['locator'])
        self.assertEqual(result['chunks'][1]['text'],self.blocks[0]['text'][500:650])
        self.assertEqual(result['config'],{'window':600,'overlap':100,'preserve_tables':False})
        self.assertEqual(self.pipeline.store.get(self.doc)['status'],'parsed')
        self.assertEqual(before,(self.folder/'blocks.json').read_bytes())
        self.provider.embed.assert_not_called();self.vector.upsert.assert_not_called()

    def test_preview_ids_stable_and_metadata_not_aliased(self):
        first=preview_chunks(self.pipeline,self.doc)
        second=preview_chunks(self.pipeline,self.doc)
        self.assertEqual(first,second)
        first['chunks'][0]['locator']['line_start']=99
        self.assertEqual(second['chunks'][0]['locator']['line_start'],1)

    def test_empty_blocks_fail_before_paid_call(self):
        save_json(self.folder/'blocks.json',[])
        with self.assertRaisesRegex(ValueError,'非空'):index_document(self.pipeline,self.doc)
        self.provider.embed.assert_not_called();self.vector.upsert.assert_not_called()

    def test_whitespace_only_blocks_fail_before_paid_call(self):
        self.blocks[0]['text']='  ';save_json(self.folder/'blocks.json',self.blocks)
        with self.assertRaisesRegex(ValueError,'有效'):index_document(self.pipeline,self.doc)
        self.provider.embed.assert_not_called()

    def test_cross_document_cache_is_rejected(self):
        self.blocks[0]['doc_id']='another';save_json(self.folder/'blocks.json',self.blocks)
        with self.assertRaisesRegex(ValueError,'文档编号'):preview_chunks(self.pipeline,self.doc)

    def test_changed_original_is_rejected_before_embedding(self):
        (self.folder/'source.txt').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'指纹'):index_document(self.pipeline,self.doc)
        self.provider.embed.assert_not_called()

    def test_index_stops_at_ready_and_freezes_manifest(self):
        index_document(self.pipeline,self.doc)
        item=self.pipeline.store.get(self.doc)
        self.assertEqual(item['status'],'ready');self.assertEqual(item['chunk_count'],2)
        manifest=json.loads((self.folder/'index-manifest.json').read_text())
        self.assertEqual(manifest['embedding']['dimension'],3)
        self.assertEqual(manifest['embedding']['model'],'text-embedding-v4')
        self.assertEqual(manifest['collection'],self.settings.milvus_collection)
        rows,vectors=self.vector.upsert.call_args.args
        self.assertEqual(len(rows),2);self.assertEqual(vectors,[[1.,0.,0.]]*2)
        self.provider.answer.assert_not_called()

    def fail_and_retry(self):
        self.vector.upsert.side_effect=RuntimeError('injected write failure')
        with self.assertRaises(RuntimeError):index_document(self.pipeline,self.doc)
        self.pipeline.store.move(self.doc,'failed',stage='index')
        self.vector.upsert.side_effect=None

    def test_retry_reuses_vectors_and_stable_primary_keys(self):
        self.fail_and_retry();first=deepcopy(self.vector.upsert.call_args.args[0])
        calls=self.provider.embed.call_count
        index_document(self.pipeline,self.doc)
        self.assertEqual(self.provider.embed.call_count,calls)
        self.assertEqual(self.vector.upsert.call_args.args[0],first)
        self.assertEqual(self.pipeline.store.get(self.doc)['status'],'ready')

    def test_failed_index_not_visible_to_retrieval(self):
        self.fail_and_retry()
        result=retrieve(self.pipeline,'测试')
        self.assertEqual(result['mode'],'no_documents');self.assertEqual(result['candidates'],[])
        self.vector.search.assert_not_called()

    def test_changed_blocks_during_retry_rejected(self):
        self.fail_and_retry();self.blocks[0]['text']='新的内容';save_json(self.folder/'blocks.json',self.blocks)
        calls=self.provider.embed.call_count
        with self.assertRaisesRegex(ValueError,'冻结'):index_document(self.pipeline,self.doc)
        self.assertEqual(self.provider.embed.call_count,calls)

    def test_changed_endpoint_during_retry_rejected(self):
        self.fail_and_retry();self.settings.bailian_base_url='https://different.invalid/v1'
        with self.assertRaisesRegex(ValueError,'冻结'):index_document(self.pipeline,self.doc)

    def test_bad_cache_is_not_silently_sent_to_milvus(self):
        self.fail_and_retry()
        for p in (self.settings.runtime_dir/'embedding-cache').glob('*.json'):save_json(p,[1.,2.])
        self.vector.upsert.reset_mock()
        with self.assertRaisesRegex(ValueError,'缓存'):index_document(self.pipeline,self.doc)
        self.vector.upsert.assert_not_called()

    def test_missing_response_vector_rejected_before_any_upsert(self):
        self.provider.embed.side_effect=lambda texts:[]
        with self.assertRaisesRegex(ValueError,'数量'):index_document(self.pipeline,self.doc)
        self.vector.upsert.assert_not_called()

    def test_nonfinite_and_zero_vectors_rejected(self):
        for v in ([float('nan'),0,0],[0,0,0]):
            with self.subTest(v=v):
                self.provider.embed.side_effect=lambda texts:[v for t in texts]
                with self.assertRaises(ValueError):index_document(self.pipeline,self.doc)
                self.vector.upsert.assert_not_called()

    def test_retrieve_filters_ready_docs_and_never_generates(self):
        index_document(self.pipeline,self.doc)
        self.vector.search.return_value=[{'chunk_id':'a','text':'甲','locator':{'kind':'txt','line_start':1}}]
        result=retrieve(self.pipeline,'测试',top_k=3,doc_ids=[self.doc,'missing'])
        self.assertEqual(result['mode'],'live');self.assertEqual(result['candidate_count'],1)
        self.assertEqual(self.vector.search.call_args.args,([1.,0.,0.],3,[self.doc]))
        self.assertEqual(result['candidates'][0]['locator']['line_start'],1)
        self.provider.answer.assert_not_called();self.provider.rerank.assert_not_called()

    def test_empty_filter_makes_no_embedding_call(self):
        index_document(self.pipeline,self.doc);self.provider.embed.reset_mock()
        result=retrieve(self.pipeline,'测试',doc_ids=[])
        self.assertEqual(result['candidates'],[]);self.provider.embed.assert_not_called()

    def test_query_configuration_cannot_mix_embedding_models(self):
        index_document(self.pipeline,self.doc);self.provider.embed.reset_mock()
        self.settings.embedding_model='other-model'
        with self.assertRaisesRegex(ValueError,'配置'):retrieve(self.pipeline,'测试')
        self.provider.embed.assert_not_called()

    def test_invalid_query_rejected_before_cloud(self):
        for question,top_k in [('  ',1),('x',0),('x',51),('x',True)]:
            with self.subTest(question=question,top_k=top_k):
                with self.assertRaises(ValueError):retrieve(self.pipeline,question,top_k)
        self.provider.embed.assert_not_called()

if __name__=='__main__':unittest.main()
