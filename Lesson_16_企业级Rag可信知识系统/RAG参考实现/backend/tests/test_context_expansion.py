from copy import deepcopy
from hashlib import sha256
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from rag_app.config import Settings
from rag_app.pipeline import Pipeline
from rag_app.core import chunk_blocks
from rag_app.context import select_expanded,select_for_pipeline,context_profile

# revision: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# generated: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# revision: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# revision: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# revision: lpf2-18283 lpf2-19E2b
def block(i,text,heading='条件',doc='d'):
    return {'doc_id':doc,'text':text,'type':'paragraph','metadata':{},
        'locator':{'kind':'md','block_id':str(i),'line_start':i,'line_end':i,
                   'heading_path':[heading] if heading else []}}

class ContextTests(unittest.TestCase):
    def select(self,blocks,hits=None,**kw):
        return select_expanded(hits if hits is not None else chunk_blocks(blocks)[:1],{'d':blocks},**kw)
    def test_expands_exact_section_with_independent_identity_and_spans(self):
        blocks=[block(1,'允许申请'),block(2,'但需凭证'),block(3,'另一节','别处')]
        hit={**chunk_blocks(blocks)[0],'score':.9,'score_kind':'bm25','rerank_score':.8}
        before=deepcopy(hit);out=self.select(blocks,[hit]);parent=out['hits'][0]
        self.assertEqual(parent['text'],'允许申请\n\n但需凭证');self.assertNotEqual(parent['chunk_id'],hit['chunk_id'])
        self.assertEqual([s['text'] for s in parent['source_spans']],['允许申请','但需凭证'])
        self.assertEqual(parent['source_spans'][1]['char_range'],[0,4]);self.assertIsNone(parent['char_range'])
        for field in ['score','score_kind','rerank_score']:self.assertNotIn(field,parent)
        self.assertEqual(before,hit)
    def test_dedupes_parents_and_merges_child_ids_even_at_final_limit(self):
        blocks=[block(1,'一'),block(2,'二')];hits=chunk_blocks(blocks)
        out=self.select(blocks,hits,final_k=1)
        self.assertEqual(len(out['hits']),1)
        self.assertEqual(out['hits'][0]['metadata']['parent_expansion']['matched_child_ids'],[h['chunk_id'] for h in hits])
        self.assertEqual(out['decisions'][1]['action'],'merged')
    def test_repeated_heading_after_boundary_and_documents_do_not_merge(self):
        blocks=[block(1,'一'),block(2,'二','其他'),block(3,'三')]
        self.assertEqual(self.select(blocks)['hits'][0]['text'],'一')
        other=[block(1,'另一文件',doc='e')]
        out=select_expanded(chunk_blocks(blocks)[:1]+chunk_blocks(other),{'d':blocks,'e':other})
        self.assertEqual(len(out['hits']),2)
    def test_without_heading_only_expands_current_block(self):
        blocks=[block(1,'a'*700,None),block(2,'隐藏条件',None)]
        self.assertEqual(len(self.select(blocks)['hits'][0]['text']),700)
    def test_large_section_falls_back_without_truncating(self):
        blocks=[block(1,'a'*600),block(2,'b'*1300)];hit=chunk_blocks(blocks)[0]
        out=self.select(blocks,[hit]);self.assertEqual(out['hits'],[hit])
        self.assertEqual(out['decisions'][0]['reason'],'parent_limit')
    def test_budget_fallback_and_exclusion(self):
        blocks=[block(1,'aaa'),block(2,'bbb')];hits=chunk_blocks(blocks)
        out=self.select(blocks,hits,max_chars=4)
        self.assertEqual(out['hits'],hits[:1]);self.assertEqual(out['text_chars'],3)
        self.assertEqual(out['decisions'][0]['reason'],'parent_budget')
        self.assertEqual(out['excluded'][0]['reason'],'char_budget')
    def test_structured_chunks_keep_their_existing_provenance(self):
        blocks=[block(1,'原表')];hit={**chunk_blocks(blocks)[0],'char_range':None,'source_spans':[{'text':'原表'}]}
        out=self.select(blocks,[hit]);self.assertEqual(out['hits'],[hit])
        self.assertEqual(out['decisions'][0]['reason'],'structured_chunk')
    def test_missing_or_mismatched_raw_slice_fails(self):
        blocks=[block(1,'原文')];hit=chunk_blocks(blocks)[0]
        for change in [{'text':'伪造'},{'char_range':[0,99]},{'locator':{**hit['locator'],'line_start':2}},{'doc_id':'unknown'}]:
            with self.subTest(change=change),self.assertRaises(ValueError):self.select(blocks,[{**hit,**change}])
    def test_duplicate_ids_blocks_and_invalid_limits_rejected(self):
        blocks=[block(1,'一')];hit=chunk_blocks(blocks)[0]
        for hits,bs,kw in [([hit,hit],blocks,{}),([hit],blocks*2,{}),([hit],blocks,{'final_k':True}),([hit],blocks,{'max_chars':0})]:
            with self.subTest(kw=kw),self.assertRaises(ValueError):self.select(bs,hits,**kw)
    def test_parent_id_stable_across_matched_child_and_changes_with_source(self):
        blocks=[block(1,'一'),block(2,'二')];hits=chunk_blocks(blocks)
        a=self.select(blocks,hits[:1])['hits'][0];b=self.select(blocks,hits[1:])['hits'][0]
        self.assertEqual(a['chunk_id'],b['chunk_id'])
        altered=deepcopy(blocks);altered[1]['text']='三'
        self.assertNotEqual(a['chunk_id'],self.select(altered)['hits'][0]['chunk_id'])
    def test_live_loader_binds_candidates_to_index_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            pipeline=Pipeline(Settings(_env_file=None,runtime_dir=Path(tmp),context_policy='parent_section'))
            pipeline.store.create('d','a.md','md','a'*64);folder=pipeline.folder('d');folder.mkdir(parents=True)
            blocks=[block(1,'一'),block(2,'二')];raw=json.dumps(blocks).encode();(folder/'blocks.json').write_bytes(raw)
            preview={'blocks_sha256':sha256(raw).hexdigest(),'chunks':chunk_blocks(blocks)}
            index={'documents':[{'doc_id':'d','source_sha256':'a'*64,'blocks_sha256':preview['blocks_sha256']}]}
            with patch('rag_app.context.preview_chunks',return_value=preview):
                self.assertEqual(select_for_pipeline(pipeline,preview['chunks'][:1],index)['hits'][0]['text'],'一\n\n二')
                bad=deepcopy(preview['chunks']);bad[0]['metadata']={'forged':True}
                with self.assertRaises(ValueError):select_for_pipeline(pipeline,bad,index)
                (folder/'blocks.json').write_text('[]')
                with self.assertRaises(ValueError):select_for_pipeline(pipeline,preview['chunks'][:1],index)
    def test_baseline_keeps_legacy_hits_and_needs_no_source_access(self):
        pipeline=type('P',(),{'settings':Settings(_env_file=None)})()
        hits=[{'chunk_id':'x','text':'ok','doc_id':'d'}]
        self.assertEqual(select_for_pipeline(pipeline,hits,None)['hits'],hits)
        self.assertEqual(context_profile('baseline')['mode'],'baseline')

if __name__=='__main__':unittest.main()
