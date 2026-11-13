from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import tempfile
import pytest
from rag_app.config import Settings
from rag_app.answering import answer_events
from rag_app.context import context_profile
from evaluation.runtime import valid_context_profile

# generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# cache: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# generated: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# generated: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# cache: lpf2-18283 lpf2-19E2b
@pytest.mark.parametrize("budget,count,size",[(6000,12,500),(30000,15,500),(30000,15,2000)])
def test_actual_generation_receives_configured_budget(budget,count,size):
    with tempfile.TemporaryDirectory() as d:
        settings=Settings(_env_file=None,runtime_dir=Path(d),context_max_chars=budget,source_scope="off")
        hits=[{"chunk_id":str(i),"doc_id":"d","text":"字"*size,"locator":{}} for i in range(30)]
        retrieval={"mode":"dense","candidates":hits,"embedding":{},"timing":{},"source_scope":{"decision":"off"}}
        pipe=SimpleNamespace(settings=settings,retrieve=lambda *a,**k:retrieval)
        with patch("rag_app.answering.Bailian") as provider:
            provider.return_value.answer.return_value={"status":"answered","answer":"test","citations":[]}
            events=list(answer_events(pipe,"q",top_k=30,final_k=15,stream=False))
            result=next(e["payload"] for e in events if e["type"]=="result");trace=result["trace"]
            assert len(provider.return_value.answer.call_args.args[1])==count
            assert len(trace["context"])==count
            assert trace["context_max_chars"]==trace["context_profile"]["max_chars"]==trace["selection"]["max_chars"]==budget
            assert valid_context_profile(trace["context_profile"])

@pytest.mark.parametrize("bad",[True,0,-1,120001])
def test_invalid_budget_rejected(bad):
    with pytest.raises(ValueError):Settings(_env_file=None,context_max_chars=bad)

def test_profile_version_preserves_old_contract():
    old=context_profile("baseline")
    assert old["schema_version"]=="context-policy/1" and old["max_chars"]==6000
    assert not valid_context_profile({**old,"max_chars":30000})
    new=context_profile("baseline",max_chars=30000)
    assert new["schema_version"]=="context-policy/2" and valid_context_profile(new)
    assert not valid_context_profile({**new,"max_chars":True})

def test_new_default_is_30000():
    assert Settings(_env_file=None).context_max_chars==30000

def test_env_file_configures_budget():
    with tempfile.TemporaryDirectory() as d:
        f=Path(d)/".env"
        f.write_text("CONTEXT_MAX_CHARS=30000\nSOURCE_SCOPE=off\n")
        assert Settings(_env_file=f).context_max_chars==30000
