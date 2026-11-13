from copy import deepcopy
import json
import pytest
from evaluation.judge_references import reference_messages,expand_references
from evaluation.tests.test_judging import proposal
from evaluation.tests.test_runtime import case,record,binding
from evaluation.judging import validate_proposal

# generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# generated: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# cache: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# revision: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# generated: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# revision: lpf2-18283 lpf2-19E2b
def ref_proposal():
    p=proposal()
    for row in p['points']:row['answer_quote']='A0'
    for row in p['critical_errors']:row['answer_quote']=''
    for section,prefix in [('retrieval_groups','R'),('context_groups','C')]:
        for row in p[section]:
            for link in row['links']:
                link.clear();link.update(source_quote='E0',retrieved_quote=prefix+'0')
    for row in p['citations']:row.update(answer_quote='A0',evidence_quote='I0')
    return p

def test_exact_bytes_preserved_and_still_model_assisted():
    c,r,b=case(),record(),binding();raw=ref_proposal();before=deepcopy(raw)
    expanded=expand_references(raw,c,r,b)
    assert raw==before
    assert expanded['points'][0]['answer_quote']==r['response']['answer']
    assert expanded['citations'][0]['evidence_quote']==r['response']['citations'][0]['text']
    assert validate_proposal(expanded,c,r,b,'test')['reviewer']['kind']=='model_assisted'

@pytest.mark.parametrize('bad',['R0','A999','invented quote'])
def test_wrong_kind_or_unknown_answer_reference_rejected(bad):
    raw=ref_proposal();raw['points'][0]['answer_quote']=bad
    with pytest.raises(ValueError):expand_references(raw,case(),record(),binding())

def test_context_cannot_borrow_candidate_reference():
    raw=ref_proposal();raw['context_groups'][0]['links'][0]['retrieved_quote']='R0'
    with pytest.raises(ValueError):expand_references(raw,case(),record(),binding())

def test_citation_cannot_borrow_another_actual_citation():
    r=record();r['response']['citations'].append({**r['response']['citations'][0],'chunk_id':'other','text':'another'})
    raw=ref_proposal();raw['citations'][0]['evidence_quote']='I1'
    with pytest.raises(ValueError):expand_references(raw,case(),r,binding())

def test_reference_link_rejects_extra_identity_and_bad_source_binding():
    raw=ref_proposal();raw['retrieval_groups'][0]['links'][0]['evidence_id']='other'
    with pytest.raises(ValueError):expand_references(raw,case(),record(),binding())
    raw=ref_proposal();b=binding();key=next(iter(b));b[key]['sha256']='0'*64
    with pytest.raises(ValueError):validate_proposal(expand_references(raw,case(),record(),b),case(),record(),b,'test')

def test_prompt_keeps_labels_out_of_rag_and_refs_have_legal_sources():
    messages=reference_messages(case(),record(),binding());p=json.loads(messages[1]['content'])
    assert p['reference_catalog']['A0']['text']==record()['response']['answer']
    assert p['reference_catalog']['I0']['chunk_id']==record()['response']['citations'][0]['chunk_id']
    assert p['legal_source_links']['E0']['retrieval']==['R0']
    c=case();c['split']='holdout'
    with pytest.raises(ValueError):reference_messages(c,record(),binding())
    assert reference_messages(c,record(),binding(),teacher_holdout=True)

def test_exact_answer_slices_include_original_punctuation():
    r=record();r['response']['answer']='第一项：180 W；第二项。\n  保留空格。'
    p=json.loads(reference_messages(case(),r,binding())[1]['content'])
    pieces=[v['text'] for k,v in p['reference_catalog'].items() if k.startswith('A') and k!='A0']
    assert ''.join(pieces)==r['response']['answer']
    assert all(piece in r['response']['answer'] for piece in pieces)

def test_live_adapter_keeps_raw_refs_and_expanded_quote_separately():
    import httpx
    from rag_app.config import Settings
    from rag_app.providers import Bailian
    from rag_app.metering import UsageJournal
    from evaluation.judging import judge_one
    raw=json.dumps(ref_proposal(),ensure_ascii=False)
    provider=Bailian(Settings(_env_file=None,dashscope_api_key='fixture'),httpx.Client(transport=httpx.MockTransport(lambda req:httpx.Response(200,json={'choices':[{'message':{'content':raw},'finish_reason':'stop'}]}))),UsageJournal(origin='fixture'))
    result=judge_one(provider,case(),record(),binding(),'test',protocol='references')
    assert result['status']=='accepted_provisional'
    assert result['raw_output']==raw
    assert result['expanded_output']['points'][0]['answer_quote']==record()['response']['answer']
    assert result['review']['reviewer']['kind']=='model_assisted'
    assert result['review']['provenance']['quote_protocol']=='references'

def test_unknown_protocol_rejected_before_any_request():
    from evaluation.judging import judge_one
    with pytest.raises(ValueError):judge_one(None,case(),record(),binding(),'test',protocol='relax')

def test_absent_gold_document_is_provable_not_semantic_guess():
    from evaluation.judge_references import source_absence_proofs,apply_source_absence_proofs
    b=binding();b['runtime-a']={'document_id':'D99','sha256':'b'*64}
    proofs=source_absence_proofs(case(),record(),b)
    assert set(proofs)=={'retrieval_groups','context_groups'}
    assert 'g1' in proofs['retrieval_groups']
    expanded=expand_references(ref_proposal(),case(),record(),b)
    corrected,audit=apply_source_absence_proofs(expanded,case(),record(),b)
    assert corrected['retrieval_groups'][0]['found'] is False
    assert corrected['retrieval_groups'][0]['links']==[]
    assert expanded['retrieval_groups'][0]['found'] is True
    assert audit and audit[0]['model_judgment']['found'] is True
    validate_proposal(corrected,case(),record(),b,'test')

def test_present_document_or_unknown_binding_is_not_automatic_negative():
    from evaluation.judge_references import source_absence_proofs
    assert all(not p for p in source_absence_proofs(case(),record(),binding()).values())
    assert all(not p for p in source_absence_proofs(case(),record(),{}).values())


def test_reference_prompt_has_no_conflicting_literal_quote_instruction():
    messages=reference_messages(case(),record(),binding())
    system=messages[0]['content']
    assert '所有摘录必须逐字复制' not in system
    assert '逐字存在的answer_quote' not in system
    assert '引用完整率' in system and '批评' in system
    payload=json.loads(messages[1]['content'])
    assert payload['quote_field_choices']['points.answer_quote'][0]=='A0'
    assert 'I0' not in payload['quote_field_choices']['retrieval_groups.links.retrieved_quote']
