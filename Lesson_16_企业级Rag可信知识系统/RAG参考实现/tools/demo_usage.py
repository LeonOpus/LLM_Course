"""百炼固定HTTP响应计量演练；无网络、无真实密钥、无模型质量成绩。"""
import argparse,json,sys
from pathlib import Path
# cache: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# revision: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# generated: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# checksum: lpf2-18283 lpf2-19E2b
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
import httpx
from rag_app.providers import Bailian,ProviderError
from rag_app.config import Settings
from rag_app.metering import UsageJournal

def run(output):
    out=Path(output)
    if out.exists():raise ValueError('输出目录已存在，请换新编号')
    out.mkdir(parents=True,exist_ok=False)
    journal=UsageJournal(out,{'phase':'test','attempt_id':'protocol-demo'},origin='fixture')
    settings=Settings(_env_file=None,runtime_dir=out,dashscope_api_key='REDACTED_SECRET',embedding_dim=2,rerank_url='https://fixture.invalid/rerank')
    requests=[]
    def handler(request):
        requests.append(1);body=json.loads(request.content)
        if request.url.path.endswith('/embeddings'):
            return httpx.Response(200,json={'data':[{'index':i,'embedding':[1.,0.]} for i in range(len(body['input']))],
                                           'usage':{'prompt_tokens':20,'total_tokens':20}})
        if request.url.path=='/rerank':return httpx.Response(200,json={'output':{'results':[{'index':0,'relevance_score':.9}]}})
        return httpx.Response(200,json={'choices':[{'message':{'content':'invalid answer'},'finish_reason':'stop'}],
                                       'usage':{'prompt_tokens':30,'completion_tokens':10,'total_tokens':40}})
    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        p=Bailian(settings,http,usage_journal=journal);p.embed(['示例A','示例B']);journal.record_cache(settings.embedding_model,2)
        p.rerank('问题',[{'text':'示例A'}],1)
        try:p.answer('问题',[{'chunk_id':'c','text':'示例A'}])
        except ProviderError:pass
        else:raise AssertionError('故意错误回答应拒绝')
    def timeout(request):raise httpx.ReadTimeout('fixture',request=request)
    with httpx.Client(transport=httpx.MockTransport(timeout)) as http:
        try:Bailian(settings,http,usage_journal=journal).embed(['超时样例'])
        except ProviderError:pass
        else:raise AssertionError('应为超时')
    from report_usage import report
    result=report(out/'report',runtime=out)
    summary=json.loads((out/'report/usage-summary.json').read_text())
    assert summary['request_count']==4 and summary['cache_hits']==2
    assert summary['operations']['embedding']['tokens']['total_tokens']['known_total']==20
    assert summary['operations']['embedding']['tokens']['total_tokens']['unknown_n']==1
    assert summary['operations']['answer']['tokens']['total_tokens']['known_total']==40
    assert summary['operations']['rerank']['tokens']['total_tokens']['known_total'] is None
    result.update(execution_origin='protocol_fixture',cloud_calls=0,quality_score=None,events=len(journal.events()))
    (out/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);a=p.parse_args()
    try:print(json.dumps(run(a.output),ensure_ascii=False,indent=2))
    except (ValueError,OSError) as error:p.exit(1,str(error)+'\n')
