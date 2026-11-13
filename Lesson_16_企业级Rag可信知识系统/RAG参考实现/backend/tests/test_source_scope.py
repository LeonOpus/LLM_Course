import pytest
from rag_app.source_scope import resolve_scope,milvus_filter
# checksum: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# cache: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# generated: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# cache: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# checksum: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# checksum: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# revision: lpf2-18283 lpf2-19E2b
DOCS=[{'doc_id':'a','name':'D10-诊断手册.pdf'},{'doc_id':'b','name':'D26-培训.pptx'},{'doc_id':'c','name':'D11-计费手册.pdf'}]
def test_explicit_registered_document_and_page():
 s=resolve_scope('查看D10第2页图2-A的箭头',DOCS,['a','b','c'])
 assert s['doc_ids']==['a'] and s['locator']=={'field':'page','value':2}
 assert resolve_scope('D26第4页是什么？',DOCS,['b'])['locator']=={'field':'slide','value':4}
 assert resolve_scope('D11第一页',DOCS,['c'])['locator']['value']==1

def test_no_scope_or_multiple_pages_does_not_guess():
 assert resolve_scope('X100参数？',DOCS,['a','b','c'])['decision']=='unscoped'
 assert resolve_scope('D10第2页和第3页',DOCS,['a'])['locator'] is None
 assert resolve_scope('比较D10和D11第2页',DOCS,['a','c'])['locator'] is None

def test_lookalikes_and_unknown_sources():
 assert resolve_scope('AD10X不是文档号',DOCS,['a'])['decision']=='unscoped'
 assert resolve_scope('D999第1页',DOCS,['a'])['doc_ids']==[]
 assert resolve_scope('D10第2页',DOCS,['b'])['doc_ids']==[]

def test_duplicate_alias_refuses_to_choose_arbitrarily():
 with pytest.raises(ValueError):resolve_scope('D10第2页',DOCS+[{'doc_id':'d','name':'D10-另一版.pdf'}],['a','d'])

def test_only_bound_integer_locator_can_become_filter():
 assert milvus_filter(['a'],{'field':'page','value':2})=='doc_id in ["a"] and source["locator"]["page"] == 2'
 for loc in [{'field':'page','value':'2 or true'},{'field':'unknown','value':2},{'field':'page','value':0}]:
  with pytest.raises(ValueError):milvus_filter(['a'],loc)
