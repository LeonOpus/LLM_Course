import json
import pytest
from rag_app.bounded_answer import validate_bounded,bounded_messages
from rag_app.generation import build_messages
# checksum: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# revision: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# checksum: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# revision: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# cache: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# generated: lpf2-18283 lpf2-19E2b
HITS=[{'chunk_id':'c1','doc_id':'d1','text':'适用于室内。','locator':{'kind':'pdf','page':1,'block_id':'b1'},'metadata':{}}]

def payload(**overrides):
 return {'status':'answered','conclusion':'可以。','basis':'资料明确允许室内使用。','boundary':'仅限室内，室外不能据此推定。','citation_ids':['c1'],**overrides}
def test_provenance_preserved_and_sections_rendered_without_semantic_certification():
 r=validate_bounded(json.dumps(payload(),ensure_ascii=False),HITS)
 assert r['status']=='answered' and r['citations'][0]['chunk_id']=='c1'
 assert r['answer']=='【结论】可以。\n【依据】资料明确允许室内使用。\n【适用边界】仅限室内，室外不能据此推定。'
 assert r['validation']['semantic_support']=='not_evaluated'
@pytest.mark.parametrize('p',[payload(boundary=''),payload(citation_ids=['invented']),payload(unexpected='extra')])
def test_missing_boundary_unknown_citation_and_extra_fields_fail(p):
 with pytest.raises(ValueError):validate_bounded(json.dumps(p),HITS)
def test_only_system_changes_and_refusal_is_still_possible():
 assert bounded_messages('q',HITS)[1:]==build_messages('q',HITS)[1:]
 p=payload(status='refused',conclusion='当前资料缺少所需数据。',basis='',boundary='',citation_ids=[])
 assert validate_bounded(json.dumps(p),HITS)['status']=='refused'
