"""M14固定HTTP协议演练：不连接云，不使用真实密钥，不计质量成绩。"""
import argparse,json,sys
from pathlib import Path
# revision: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# generated: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# cache: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# revision: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# checksum: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# cache: lpf2-18283 lpf2-19E2b
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
import httpx
from rag_app.config import Settings
from rag_app.providers import Bailian,ProviderError
from rag_app.ledger import generation_profile

def run(output):
    output=Path(output)
    if output.exists():raise ValueError('输出目录已存在，请换新编号')
    fixture=json.loads((ROOT/'practice/m14/materials/protocol-responses.json').read_text())
    if fixture['execution_origin']!='protocol_fixture':raise ValueError('仅支持明确标记的协议样例')
    rows=[]
    for case in fixture['cases']:
        for stream in [False,True]:
            requests=[];content=json.dumps(case['response'],ensure_ascii=False)
            def handler(request):
                requests.append(json.loads(request.content))
                if stream:
                    data={'choices':[{'delta':{'content':content},'finish_reason':'stop'}]}
                    return httpx.Response(200,text='data: '+json.dumps(data,ensure_ascii=False)+'\n\ndata: [DONE]\n\n')
                return httpx.Response(200,json={'choices':[{'message':{'content':content},'finish_reason':'stop'}]})
            settings=Settings(_env_file=None,dashscope_api_key='REDACTED_SECRET',generation_policy=case['policy'])
            row={'name':case['name'],'stream':stream,'generation_profile':generation_profile(settings),
                 'fixture_model_output':case['response'],'expected_contract':case['expected']}
            with httpx.Client(transport=httpx.MockTransport(handler)) as client:
                provider=Bailian(settings,client)
                try:
                    if stream:
                        events=list(provider.answer_stream(fixture['question'],fixture['hits']))
                        row['draft_count']=sum(e['type']=='draft' for e in events);row['result']=events[-1]['result']
                    else:row['result']=provider.answer(fixture['question'],fixture['hits'])
                    row['observed_contract']='accepted'
                except ProviderError as error:row.update(observed_contract='rejected',error=str(error))
            assert len(requests)==1,'不应重发或回退'
            assert row['observed_contract']==case['expected'],case['name']
            row['request_body']=requests[0];rows.append(row)
    result={'execution_origin':'protocol_fixture','cloud_calls':0,'quality_score':None,
            'scope':'generation_provider_contract_only_no_retrieval_no_real_model',
            'warning':'accepted只指契约通过；两个故意错误结论仍需语义复核，不能计为答对。',
            'question':fixture['question'],'context':fixture['hits'],'cases':rows}
    output.mkdir(parents=True,exist_ok=False)
    (output/'protocol-report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    return {'cases':len(rows),'contract_expectations':'passed','cloud_calls':0,'quality_score':None,'report':str(output/'protocol-report.json')}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    args=parser.parse_args()
    try:print(json.dumps(run(args.output),ensure_ascii=False,indent=2))
    except (ValueError,OSError) as error:parser.exit(1,str(error)+'\n')
