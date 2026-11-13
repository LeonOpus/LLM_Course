"""只读调用账本，输出用量报告；未知费用不写成零，不调用云。"""
import argparse,json,sys
from pathlib import Path
from html import escape
# checksum: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# cache: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# cache: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# generated: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# generated: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# revision: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# revision: lpf2-18283 lpf2-19E2b
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from rag_app.metering import summarize_events
from rag_app.pricing import estimate

def report(output,runtime=None,trace=None,price_card=None):
    out=Path(output)
    if out.exists():raise ValueError('输出目录已存在，请换新编号')
    if (runtime is None)==(trace is None):raise ValueError('runtime与trace必须且只能选一个')
    docmind=None
    if runtime is not None:
        root=Path(runtime)
        if not root.is_dir():raise ValueError('runtime目录不存在')
        files=sorted((root/'usage-events').glob('*.json'))
        events=[json.loads(p.read_text(encoding='utf-8')) for p in files]
        docmind={'job_cache_files':len(list((root/'documents').glob('*/docmind/job.json'))),
                 'uncertain_submission_files':len(list((root/'documents').glob('*/docmind/submission-uncertain.json'))),
                 'billable_pages':None,'cost':None,'notice':'文件数量不是提交次数或计费页数；不把轮询次数当成解析次数。'}
        scope='所选runtime中目前保存的事件；包含手工试问/重试，不等于某批评估的专属成本'
    else:
        value=json.loads(Path(trace).read_text(encoding='utf-8'));events=value.get('usage_events')
        if events is None:events=[]
        if not isinstance(events,list):raise ValueError('trace用量事件必须是列表')
        scope='单次trace中已保存事件；不含入库，旧版或缺失事件无法补算'
    summary=summarize_events(events)
    summary.update(scope=scope,docmind=docmind,record_status='recorded_events' if events else 'no_recorded_events',
                   amount_notice='人民币金额未知；未应用地域价格、梯度、缓存折扣、免费额度或实际账单。')
    cost_estimate=estimate(events,json.loads(Path(price_card).read_text(encoding='utf-8'))) if price_card else None
    summary['cost_estimate']=cost_estimate
    if cost_estimate is not None:summary['amount_notice']='已按显式价格卡估算普通实时标价；未知部分与实际扣款仍未知，未扣优惠。'
    def display(v):return '未知' if v is None else str(v)
    table=[]
    for operation,row in summary['operations'].items():
        total=row['tokens']['total_tokens']
        values=[operation,' / '.join(row['models']),str(row['requests']),display(total['known_total']),str(total['known_n']),str(total['unknown_n']),json.dumps(row['outcomes'],ensure_ascii=False)]
        table.append('<tr>'+''.join('<td>'+escape(v)+'</td>' for v in values)+'</tr>')
    content='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RAG调用用量核查</title><style>body{max-width:1160px;margin:32px auto;padding:0 20px;font:16px/1.7 system-ui;color:#302b26;background:#f8f5ef}.notice{background:#fff0ce;padding:16px;border-left:4px solid #997048}.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;background:white}td,th{padding:10px;text-align:left;border-bottom:1px solid #ded6ca}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:white;padding:16px}h1{font-size:30px}</style><h1>效果之外，还发生了哪些调用？</h1>'''
    content+='<p class="notice">费用：未知。已收到的token不等于实际账单；缺记录不表示免费。</p><p>'+escape(scope)+'</p>'
    content+='<p>记录内请求 '+str(summary['request_count'])+' 次 · 本地Embedding缓存读取命中 '+str(summary['cache_hits'])+' 项</p>'
    content+='<p>事件来源标记：'+escape(json.dumps(summary['origins'],ensure_ascii=False))+'。fixture为固定协议演练；configured_transport也需结合真实运行确认。</p>'
    content+='<div class="scroll"><table><thead><tr><th>操作</th><th>模型</th><th>已记录请求</th><th>已知总token小计</th><th>返回总token的请求</th><th>总token未知请求</th><th>服务响应状态</th></tr></thead><tbody>'+''.join(table)+'</tbody></table></div>'
    if not events:content+='<p>没有保存的用量事件。可能尚未调用，也可能使用了旧版或记录缺失，需要查看运行过程。</p>'
    if cost_estimate is not None:
        v=cost_estimate
        content+='<h2>标价估算 · 实际扣款未知</h2><p class="notice">已知标价小计：'+display(v['priced_subtotal_cny'])+' 元；所选记录全量估算：'+display(v['estimated_total_cny'])+' 元。未知请求：'+str(v['unknown_request_count'])+'。未扣免费额度与云端缓存优惠。</p>'
        content+='<p>按单次请求选档；金额不是账单。价格核查日期 '+escape(v['reviewed_on'])+'。来源：<a href="'+escape(v['source_url'],quote=True)+'">价格卡来源</a></p>'
        content+='<div class="scroll"><table><tr><th>操作</th><th>状态</th><th>规则或未知原因</th><th>标价估算（元）</th></tr>'
        for row in v['rows']:
            content+='<tr>'+''.join('<td>'+escape(display(x))+'</td>' for x in [row['operation'],row['status'],row.get('rule_id',row.get('reason')),('不适用：无新增云请求' if row['status']=='local_cache' else row['estimated_cny'])])+'</tr>'
        content+='</table></div>'
    content+='<p>response_received只表示收到响应，不表示答案正确。stream_completed只表示传输完成；可能仍未通过引用或格式校验。输入、输出、总token不能相加。</p><details><summary>分项、DocMind范围与边界</summary><pre>'+escape(json.dumps(summary,ensure_ascii=False,indent=2))+'</pre></details><details><summary>去重前事件记录</summary><pre>'+escape(json.dumps(events,ensure_ascii=False,indent=2))+'</pre></details></html>'
    out.mkdir(parents=True,exist_ok=False)
    (out/'usage-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    (out/'usage.html').write_text(content,encoding='utf-8')
    return {'status':'written','report':str(out/'usage.html'),'recorded_requests':summary['request_count'],'cost':None}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--runtime');g.add_argument('--trace');p.add_argument('--output',required=True);p.add_argument('--price-card');a=p.parse_args()
    try:print(json.dumps(report(a.output,a.runtime,a.trace,a.price_card),ensure_ascii=False,indent=2))
    except (ValueError,OSError,KeyError,TypeError) as error:p.exit(1,(str(error) if isinstance(error,ValueError) else type(error).__name__+'：检查输入路径与文件')+'\n')
