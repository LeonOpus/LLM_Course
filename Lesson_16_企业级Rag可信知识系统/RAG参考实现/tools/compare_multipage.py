"""M12C本地结构对照，无模型/向量库；输出目录必须尚不存在。"""
import argparse,json,sys
from pathlib import Path
from html import escape
# checksum: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# generated: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# generated: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# generated: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# cache: lpf2-18283 lpf2-19E2b
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from rag_app.multipage import compare_multipage

def run(blocks,plan,output,window=600,overlap=100):
    out=Path(output)
    if out.exists():raise ValueError('输出目录已存在，请换新编号')
    result=compare_multipage(json.loads(Path(blocks).read_text(encoding='utf-8')),
                             json.loads(Path(plan).read_text(encoding='utf-8')),window,overlap)
    rows=[];details=[]
    for name,v in result['variants'].items():
        rows.append('<tr>'+''.join('<td>'+str(x)+'</td>' for x in [name,v['chunk_count'],v['total_chars'],
                    v['complete_rows'],v['rows_with_header'],v['rows_with_header_and_context']])+'</tr>')
        for i,c in enumerate(v['chunks'],1):
            # 原件视为不可信文本，报告只显示转义后的HTML，不执行文档标记。
            details.append('<details><summary>'+escape(f'{name} / 片段{i} / {len(c["text"])}字 / '+json.dumps(c['locator'],ensure_ascii=False))+'</summary><pre>'+escape(c['text'])+'</pre><pre>'+escape(json.dumps(c.get('source_spans',[]),ensure_ascii=False,indent=2))+'</pre></details>')
    html='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>M12C 结构对照</title><style>body{max-width:1100px;margin:32px auto;padding:0 20px;font:16px/1.7 system-ui;color:#263548;background:#f7f8fb}h1{font-size:30px}table{border-collapse:collapse;width:100%;background:white}td,th{padding:12px;border-bottom:1px solid #d6deeb;text-align:left}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#eef2f7;padding:18px}details{margin:14px 0;background:white;padding:12px}.notice{padding:16px;background:#fff2d7}</style><h1>同一张表，换个分页后读得对吗？</h1><p class="notice">离线结构实验 · 云调用 0 次 · 不是召回率或答案准确率</p>'''
    html+='<p>固定字符预算 '+str(window)+'，普通块重叠 '+str(overlap)+'。HTML标记也计入预算。完整行共 '+str(result['variants']['B0']['expected_rows'])+'。</p><table><thead><tr><th>策略</th><th>片段数</th><th>总字符</th><th>完整行</th><th>行＋表头</th><th>行＋表头＋说明</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table>'
    html+='<p>P2：完整合并表头与续表行；P2+C2：再携带已核对的限定说明。点击片段检查原始字符区间与跨页来源。</p>'+''.join(details)+'<h2>边界</h2><ul>'+''.join('<li>'+escape(x)+'</li>' for x in result['limitations'])+'</ul></html>'
    out.mkdir(parents=True,exist_ok=False)
    (out/'comparison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (out/'comparison.html').write_text(html,encoding='utf-8')
    return {'status':'passed','report':str(out/'comparison.json'),'cloud_calls':0,
            'variants':{k:{x:y for x,y in v.items() if x!='chunks'} for k,v in result['variants'].items()}}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['blocks','plan','output']:p.add_argument('--'+name,required=True)
    p.add_argument('--window',type=int,default=600);p.add_argument('--overlap',type=int,default=100)
    a=p.parse_args()
    try:print(json.dumps(run(a.blocks,a.plan,a.output,a.window,a.overlap),ensure_ascii=False,indent=2))
    except (ValueError,OSError) as error:p.exit(1,str(error)+'\n')
