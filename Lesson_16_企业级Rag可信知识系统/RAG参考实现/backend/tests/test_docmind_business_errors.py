import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from rag_app.config import Settings
from rag_app.docmind import DocMind
from rag_app.providers import ProviderError


# generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# generated: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# cache: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# cache: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# revision: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# generated: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# revision: lpf2-18283 lpf2-19E2b
def setup(tmp_path):
    source = tmp_path/'source.pdf'
    source.write_bytes(b'fixture')
    sdk=Mock()
    sdk.submit_doc_parser_job_advance.return_value=SimpleNamespace(body={'Code':'200','Data':{'Id':'fixture-job'}})
    sdk.query_doc_parser_status.return_value=SimpleNamespace(body={'Code':'200','Data':{'Status':'Success'}})
    sdk.get_doc_parser_result.return_value=SimpleNamespace(body={'Code':'200','Data':json.dumps({'layouts':[{'text':'fixture'}]})})
    parser=DocMind(Settings(_env_file=None,alibaba_cloud_access_key_id='fixture',alibaba_cloud_access_key_secret='fixture'),sdk)
    return source,sdk,parser,tmp_path/'cache'


def test_submit_permission_rejection_is_not_unknown_submission(tmp_path):
    source,sdk,parser,cache=setup(tmp_path)
    sdk.submit_doc_parser_job_advance.return_value=SimpleNamespace(body={'Code':'NoPermission','Message':'private-provider-message'})
    with pytest.raises(ProviderError,match='NoPermission') as caught:
        parser.parse(source,cache)
    assert 'private-provider-message' not in str(caught.value)
    assert not (cache/'submission-uncertain.json').exists()
    sdk.query_doc_parser_status.assert_not_called()
    assert json.loads((cache/'submit-error.json').read_text())['code']=='NoPermission'


@pytest.mark.parametrize('phase',['query','result'])
def test_permission_failure_keeps_saved_job_for_resume(tmp_path,phase):
    source,sdk,parser,cache=setup(tmp_path)
    method=sdk.query_doc_parser_status if phase=='query' else sdk.get_doc_parser_result
    good=method.return_value
    method.return_value=SimpleNamespace(body={'Code':'NoPermission'})
    with pytest.raises(ProviderError,match='NoPermission'):
        parser.parse(source,cache)
    assert json.loads((cache/'job.json').read_text())['job_id']=='fixture-job'
    method.return_value=good
    assert parser.parse(source,cache)==[{'text':'fixture'}]
    assert sdk.submit_doc_parser_job_advance.call_count==1


def test_submission_response_saved_before_missing_job_is_flagged(tmp_path):
    source,sdk,parser,cache=setup(tmp_path)
    sdk.submit_doc_parser_job_advance.return_value=SimpleNamespace(body={'Code':'200','Data':{}})
    with pytest.raises(ProviderError):parser.parse(source,cache)
    assert (cache/'submission-response.json').exists()
    assert (cache/'submission-uncertain.json').exists()
