"""固定历史时间的计价演练；不联网、不调用模型、不产生账单。"""
import argparse,json,sys
from pathlib import Path
# revision: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# revision: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# checksum: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# revision: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# generated: lpf2-18283 lpf2-19E2b
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'));sys.path.insert(0,str(ROOT/'tools'))
from rag_app.metering import UsageJournal
from rag_app.pricing import pricing_context
from report_usage import report

def demo(output):
    out=Path(output)
    if out.exists():raise ValueError('目录已存在，请换一个编号')
    j=UsageJournal(origin='fixture')
    for op,model,usage,outcome in [
        ('embedding','text-embedding-v4',{'total_tokens':2000},'response_received'),
        ('rerank','gte-rerank-v2',{'total_tokens':10000},'response_received'),
        ('query_rewrite','qwen-plus',{'prompt_tokens':500,'completion_tokens':100,'total_tokens':600},'response_received'),
        ('answer','qwen-plus',{'prompt_tokens':4000,'completion_tokens':500,'total_tokens':4500},'stream_completed'),
        ('embedding','text-embedding-v4',None,'transport_error')]:
        context=pricing_context('https://dashscope.aliyuncs.com/compatible-mode/v1',{'enable_thinking':False} if op in {'answer','query_rewrite'} else {})
        uid=j.begin(op,model,pricing_context=context);j.update(uid,outcome=outcome,usage=usage)
    j.record_cache('text-embedding-v4',2);events=j.events()
    for e in events:e['started_at']='2026-09-16T12:00:00+08:00'
    out.mkdir(parents=True);trace=out/'fixture-trace.json';trace.write_text(json.dumps({'usage_events':events},ensure_ascii=False,indent=2)+'\n')
    result=report(out/'report',trace=trace,price_card=ROOT/'pricing/beijing-2026-09-16.json')
    value=json.loads((out/'report/usage-summary.json').read_text())['cost_estimate']
    assert value['priced_subtotal_cny']=='0.0138' and value['estimated_total_cny'] is None and value['unknown_request_count']==1
    verification={'status':'passed','cloud_calls':0,'quality_metrics':None,'actual_cost_cny':None,'priced_subtotal_cny':value['priced_subtotal_cny'],'unknown_requests':1,'notice':'历史时间固定样例，不代表实际云支出或效果提升'}
    (out/'verification.json').write_text(json.dumps(verification,ensure_ascii=False,indent=2)+'\n')
    return verification
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);a=p.parse_args()
    try:print(json.dumps(demo(a.output),ensure_ascii=False,indent=2))
    except (ValueError,OSError) as e:p.exit(1,str(e)+'\n')
