from copy import deepcopy
import pytest
from evaluation.judging import validate_partial_proposal
from evaluation.tests.test_judging import proposal
from evaluation.tests.test_runtime import case,record,binding
from evaluation.runtime import validate_review

# generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# revision: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# revision: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# checksum: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# generated: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# checksum: lpf2-18283 lpf2-19E2b
def test_bad_quote_remains_pending_without_erasing_independent_fields():
    raw=proposal();raw['points'][0]['answer_quote']='invented'
    review,issues=validate_partial_proposal(raw,case(),record(),binding(),'test-model')
    assert review['points'][0]['passed'] is None
    assert review['behavior']['correct'] is True
    assert issues and issues[0]['path']=='points/p1'
    assert review['reviewer']['kind']=='model_assisted'
    validate_review(case(),record(),review,binding())

def test_missing_links_never_becomes_confirmed_recall():
    raw=proposal();raw['retrieval_groups'][0].pop('links')
    review,issues=validate_partial_proposal(raw,case(),record(),binding(),'test-model')
    assert review['retrieval_groups'][0]['found'] is None
    assert review['context_groups'][0]['found'] is True
    assert issues

def test_duplicate_items_reject_section_instead_of_selecting_first():
    raw=proposal();raw['points'].append(deepcopy(raw['points'][0]))
    review,issues=validate_partial_proposal(raw,case(),record(),binding(),'test-model')
    assert all(r['passed'] is None for r in review['points'])
    assert issues

def test_no_human_reviewer_injection_or_missing_top_level():
    raw=proposal();raw['reviewer']={'kind':'human'}
    with pytest.raises(ValueError):validate_partial_proposal(raw,case(),record(),binding(),'test-model')
    raw=proposal();del raw['behavior']
    with pytest.raises(ValueError):validate_partial_proposal(raw,case(),record(),binding(),'test-model')
