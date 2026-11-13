from copy import deepcopy
import pytest
from rag_app.evidence_labels import label_evidence

# generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# cache: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# checksum: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# revision: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# generated: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# checksum: lpf2-18283 lpf2-19E2b
DOC={'doc_id':'source-random-17','name':'D10-告警核查.pdf','sha256':'a'*64}
HIT={'chunk_id':'chunk-1','doc_id':DOC['doc_id'],'text':'原始证据：条件不足，不能执行。','locator':{'kind':'pdf','page':2,'block_id':'b1'},'metadata':{'parser':'docmind'},'char_range':[0,20]}

def test_names_are_from_registered_documents_without_modifying_evidence():
 hits=[deepcopy(HIT)];before=deepcopy(hits)
 out=label_evidence(hits,[DOC],{DOC['doc_id']:DOC['sha256']})
 assert hits==before
 assert out[0]['metadata']['source_document']=={'name':DOC['name'],'sha256':DOC['sha256']}
 for key in ['text','chunk_id','doc_id','locator','char_range']:assert out[0][key]==HIT[key]
 assert out[0]['metadata']['parser']=='docmind'

def test_repeated_hits_keep_order_and_only_add_same_bound_source_label():
 other={**HIT,'chunk_id':'chunk-2'}
 out=label_evidence([other,HIT],[DOC],{DOC['doc_id']:DOC['sha256']})
 assert [x['chunk_id'] for x in out]==['chunk-2','chunk-1']
 assert out[0]['metadata']['source_document']==out[1]['metadata']['source_document']

@pytest.mark.parametrize('documents,bindings',[([],{}),([DOC,DOC],{DOC['doc_id']:DOC['sha256']}),([DOC],{}),([DOC],{DOC['doc_id']:'b'*64})])
def test_unbound_or_ambiguous_sources_fail(documents,bindings):
 with pytest.raises(ValueError):label_evidence([HIT],documents,bindings)

def test_existing_conflicting_source_metadata_is_not_silently_overwritten():
 hit=deepcopy(HIT);hit['metadata']['source_document']={'name':'wrong.pdf','sha256':'b'*64}
 with pytest.raises(ValueError):label_evidence([hit],[DOC],{DOC['doc_id']:DOC['sha256']})

def test_empty_evidence_does_not_invent_a_document():
 assert label_evidence([],[],{})==[]
