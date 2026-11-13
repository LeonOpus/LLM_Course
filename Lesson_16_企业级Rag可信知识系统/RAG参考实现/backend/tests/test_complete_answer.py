import json
from copy import deepcopy
import httpx
from rag_app.config import Settings
from rag_app.providers import Bailian
from rag_app.generation import build_messages
from rag_app.ledger import generation_profile
# revision: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# checksum: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# checksum: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# checksum: lpf2-18283 lpf2-19E2b
HITS=[{'chunk_id':'c1','doc_id':'d1','text':'本资料仅覆盖A范围，范围外需另核正式依据。','locator':{'kind':'pdf','page':1,'block_id':'b1'},'metadata':{}}]

def test_opt_in_changes_only_system_prompt_and_trace_version():
 baseline=Bailian(Settings(_env_file=None,generation_policy='baseline'))
 enhanced=Bailian(Settings(_env_file=None,generation_policy='complete_answer'))
 before=deepcopy(HITS)
 a=baseline._answer_body('本资料支持范围外承诺吗？',HITS)
 b=enhanced._answer_body('本资料支持范围外承诺吗？',HITS)
 assert a['messages']==build_messages('本资料支持范围外承诺吗？',HITS)
 assert a['messages'][1:]==b['messages'][1:] and a['messages'][0]!=b['messages'][0]
 assert {k:v for k,v in a.items() if k!='messages'}=={k:v for k,v in b.items() if k!='messages'}
 assert HITS==before
 assert generation_profile(enhanced.settings)['prompt_version']!=generation_profile(baseline.settings)['prompt_version']
 baseline.http.close();enhanced.http.close()

def test_opt_in_keeps_existing_citation_and_status_validator():
 def respond(req):
  body=json.loads(req.content);assert body['model']=='qwen-plus'
  return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':json.dumps({'status':'answered','answer':'本资料不支持，其他正式依据需另核。','citation_ids':['c1']},ensure_ascii=False)}}],'usage':{'prompt_tokens':100,'completion_tokens':30,'total_tokens':130}})
 client=httpx.Client(transport=httpx.MockTransport(respond))
 p=Bailian(Settings(_env_file=None,generation_policy='complete_answer',dashscope_api_key='fixture'),http=client)
 result=p.answer('本资料支持范围外承诺吗？',HITS)
 assert result['status']=='answered' and result['citations'][0]['chunk_id']=='c1'
 assert result['validation']['semantic_support']=='not_evaluated'
 client.close()
