import json
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from rag_app.config import Settings
from rag_app.pipeline import Pipeline
from rag_app.indexing import index_document, retrieve
from rag_app.experiments import prepare_experiment
from rag_app.docmind import save_json
from hashlib import sha256


# cache: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# revision: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# generated: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# generated: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# checksum: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# revision: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# revision: lpf2-18283 lpf2-19E2b
def hit(cid,score,text=None):
    return {'chunk_id':cid,'doc_id':'d','text':text or cid,'locator':{'kind':'txt','block_id':cid},'score':score}

class FusionTests(unittest.TestCase):
    def fuse(self,*args,**kwargs):
        from rag_app.hybrid import fuse_rrf
        return fuse_rrf(*args,**kwargs)
    def test_two_routes_use_ranks_not_incompatible_raw_scores(self):
        result=self.fuse([hit('a',.99),hit('b',.8)],[hit('b',100),hit('c',90)],3)
        self.assertEqual([h['chunk_id'] for h in result],['b','a','c'])
        self.assertAlmostEqual(result[0]['score'],1/62+1/61)
        self.assertEqual(result[0]['retrieval_ranks'],{'dense':2,'bm25':1})
        self.assertEqual(result[0]['retrieval_scores'],{'dense':.8,'bm25':100})
        self.assertEqual(result[0]['locator']['block_id'],'b')
    def test_limits_and_ties_are_deterministic_without_mutating_hits(self):
        dense=[hit('z',.9)];bm25=[hit('a',8)];before=deepcopy((dense,bm25))
        self.assertEqual(self.fuse(dense,bm25,1)[0]['chunk_id'],'a')
        self.assertEqual((dense,bm25),before)
        self.assertEqual(self.fuse([],[],3),[])
    def test_duplicate_branch_and_conflicting_sources_are_errors(self):
        for dense,sparse in [([hit('a',1),hit('a',.8)],[]),([hit('a',1)],[hit('a',8,'different')])]:
            with self.assertRaises(ValueError):self.fuse(dense,sparse,3)

class HybridPipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        p=Pipeline(Settings(_env_file=None,runtime_dir=self.root/'source',embedding_dim=3))
        p.store.create('d','source.txt','txt',sha256(b'original').hexdigest());f=p.folder('d');f.mkdir(parents=True)
        (f/'source.txt').write_bytes(b'original');save_json(f/'blocks.json',[{'doc_id':'d','type':'text','text':'X200-Pro E102 报警','locator':{'kind':'txt','block_id':'b'}}])
        p.store.move('d','parsing');p.store.move('d','parsed');self.source=p
        self.pp=patch('rag_app.indexing.Bailian');self.provider=self.pp.start().return_value;self.addCleanup(self.pp.stop)
        self.provider.embed.side_effect=lambda texts:[[1.,0.,0.] for _ in texts]
        self.vp=patch('rag_app.indexing.VectorStore');self.vector=self.vp.start().return_value;self.addCleanup(self.vp.stop)
        self.vector.client.has_collection.return_value=False
        self.vector.ensure_collection.side_effect=lambda:setattr(self.vector.client.has_collection,'return_value',True)
        self.vector.search.return_value=[hit('dense',.9)]
        self.vector.search_bm25.return_value=[hit('lexical',8)]
    def experiment(self):
        m=prepare_experiment(self.source.settings.runtime_dir,self.root/'exp','baseline',full_text=True)
        p=Pipeline(Settings(_env_file=None,runtime_dir=self.root/'exp',embedding_dim=3,milvus_collection=m['collection'],milvus_full_text=True))
        index_document(p,'d');self.provider.embed.reset_mock();return p
    def test_bm25_does_not_embed_query_and_retains_filter(self):
        p=self.experiment();p.settings.retrieval_mode='bm25';r=retrieve(p,'E102',3,['d','unknown'])
        self.provider.embed.assert_not_called();self.vector.search.assert_not_called()
        self.vector.search_bm25.assert_called_once_with('E102',3,['d'])
        self.assertEqual(r['retrieval_profile']['mode'],'bm25')
        self.assertEqual(r['candidates'][0]['chunk_id'],'lexical')
    def test_hybrid_calls_both_routes_with_same_filter_and_limit(self):
        p=self.experiment();p.settings.retrieval_mode='hybrid';r=retrieve(p,'E102',3,['d'])
        self.vector.search.assert_called_once_with([1.,0.,0.],3,['d'])
        self.vector.search_bm25.assert_called_once_with('E102',3,['d'])
        self.assertEqual(set(r['retrieval_routes']),{'dense','bm25'})
        self.assertEqual(len(r['candidates']),2);self.assertEqual(r['retrieval_profile']['rrf_k'],60)
    def test_empty_filter_does_not_request_any_provider(self):
        p=self.experiment();p.settings.retrieval_mode='hybrid';r=retrieve(p,'E102',3,[])
        self.assertEqual(r['candidates'],[]);self.provider.embed.assert_not_called()
        self.vector.search.assert_not_called();self.vector.search_bm25.assert_not_called()
    def test_full_text_flag_is_frozen_and_legacy_cannot_silently_hybrid(self):
        p=self.experiment();p.settings.milvus_full_text=False
        with self.assertRaisesRegex(ValueError,'配置|全文'):retrieve(p,'E102')
        self.source.settings.retrieval_mode='hybrid'
        with self.assertRaisesRegex(ValueError,'全文|FULL_TEXT'):retrieve(self.source,'E102')
        self.provider.embed.assert_not_called()

if __name__=='__main__':unittest.main()

class FullTextSchemaTests(unittest.TestCase):
    def test_wrong_bm25_parameters_or_field_types_are_rejected(self):
        from unittest.mock import MagicMock
        from rag_app.vectorstore import VectorStore
        from rag_app.providers import ProviderError
        from pymilvus import FunctionType,DataType
        v=VectorStore.__new__(VectorStore);v.name='rag_course_fixture';v.client=MagicMock()
        desc={'fields':[{'name':'text','type':DataType.VARCHAR,'params':{'enable_analyzer':'true','analyzer_params':'{"type":"chinese"}'}},{'name':'sparse','type':DataType.SPARSE_FLOAT_VECTOR}],
              'functions':[{'name':'course_bm25','type':FunctionType.BM25,'input_field_names':['text'],'output_field_names':['sparse']}]}
        v.client.describe_index.return_value={'metric_type':'BM25','bm25_k1':'1.8','bm25_b':'0.75','index_type':'SPARSE_INVERTED_INDEX','inverted_index_algo':'DAAT_MAXSCORE'}
        with self.assertRaisesRegex(ProviderError,'参数'):v.verify_full_text(desc)
        v.client.describe_index.return_value['bm25_k1']='1.2';desc['fields'][1]['type']=DataType.FLOAT_VECTOR
        with self.assertRaises(ProviderError):v.verify_full_text(desc)
