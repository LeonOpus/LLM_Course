from copy import deepcopy
import pytest
from rag_app.compact_context import compact_table,select_compact

# cache: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# revision: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# cache: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# checksum: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# generated: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# revision: lpf2-18283 lpf2-19E2b
def block(uid,text,kind='text',heading=None):
 return {'doc_id':'doc','type':kind,'text':text,'locator':{'kind':'pdf','page':1,'block_id':uid,**({'heading_path':heading} if heading else {})}}
def hit(b,start=0,end=None):
 end=len(b['text']) if end is None else end
 return {**deepcopy(b),'chunk_id':'child-'+b['locator']['block_id'],'text':b['text'][start:end],'char_range':[start,end],'metadata':{'parser':'docmind'}}
TABLE='<table><tr><td rowspan="1" colspan="1">型号</td><td rowspan="1" colspan="1">值</td></tr><tr><td rowspan="1" colspan="1">X100</td><td rowspan="1" colspan="1">180 W</td></tr></table>'

def test_compaction_keeps_cells_and_entities_and_rejects_unsupported_table():
 assert compact_table(TABLE)=='<table><tr><td>型号</td><td>值</td></tr><tr><td>X100</td><td>180 W</td></tr></table>'
 assert '&lt;30' in compact_table(TABLE.replace('180 W','&lt;30'))
 with pytest.raises(ValueError):compact_table(TABLE.replace('rowspan="1"','rowspan="2"'))
 with pytest.raises(ValueError):compact_table(TABLE[:-10])

def test_restore_table_with_original_spans_and_context_and_dedup():
 b=block('b',TABLE,'table',['规格']);c=block('c','仅限X100，180 W为额定功率。','text',['规格']);hs=[hit(b,20,65),hit(c)];original=deepcopy(hs)
 result=select_compact(hs,{'doc':[b,c]})
 assert hs==original and len(result['hits'])==1
 h=result['hits'][0];assert '180 W' in h['text'] and '仅限X100' in h['text']
 assert h['source_spans'][0]['text']==TABLE and h['source_spans'][0]['char_range']==[0,len(TABLE)]
 assert h['char_range'] is None and h['chunk_id']!=hs[0]['chunk_id']
 assert len(result['decisions'])==2

def test_page_and_heading_boundary_never_expand_to_unrelated_section():
 b=block('b','A','text',['一']);c=block('c','B','text',['二'])
 result=select_compact([hit(b)],{'doc':[b,c]});assert 'B' not in result['hits'][0]['text']

def test_binding_mismatch_rejected():
 b=block('b',TABLE,'table');h=hit(b);h['text']='forged'
 with pytest.raises(ValueError):select_compact([h],{'doc':[b]})

def test_budget_never_truncates_table_and_falls_back_to_child():
 b=block('b',TABLE,'table');h=hit(b,0,6)
 r=select_compact([h],{'doc':[b]},max_chars=10,parent_max_chars=10)
 assert r['hits'][0]['text']==h['text'] and r['text_chars']<=10
 assert r['decisions'][0]['reason']=='parent_limit'

def test_serialized_evidence_budget_counts_raw_provenance_too():
 b=block('b',TABLE,'table');h=hit(b,0,6)
 r=select_compact([h],{'doc':[b]},max_serialized_chars=450)
 assert r['hits']==[h] and r['decisions'][0]['reason']=='serialized_budget_fallback'

@pytest.mark.parametrize('kwargs',[{'final_k':0},{'max_chars':0},{'max_serialized_chars':0}])
def test_invalid_limits(kwargs):
 with pytest.raises(ValueError):select_compact([],{},**kwargs)
