"""课程原文上下文演练；固定选中子块，不调用检索/DocMind/百炼，不输出质量分数。"""
from pathlib import Path
from hashlib import sha256
from html import escape
import argparse,json,sys
# revision: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# generated: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# checksum: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# revision: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# checksum: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# generated: lpf2-18283 lpf2-19E2b
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from rag_app.core import chunk_blocks
from rag_app.context import select_expanded,context_profile
from rag_app.generation import select_context

def read_materials():
    folder=ROOT/'practice/m18a/materials';proof=json.loads((folder/'provenance.json').read_text())
    raw=(folder/proof['source_file']).read_bytes();assert sha256(raw).hexdigest()==proof['source_sha256']
    data=(folder/'D31-blocks.json').read_bytes();assert sha256(data).hexdigest()==proof['blocks_sha256']
    blocks=json.loads(data);lines=raw.decode().splitlines()
    for b in blocks:
        loc=b['locator'];assert b['text']=='\n'.join(lines[loc['line_start']-1:loc['line_end']])
    return blocks,proof

def render(result):
    panels=[]
    for name in ['baseline','parent_section']:
        row=result[name];body='\n\n'.join(h['text'] for h in row['hits'])
        panels.append(f'<section><h2>{"原始片段" if name=="baseline" else "同小节原文补全"}</h2><p>{row["text_chars"]} 个正文字符 · {len(row["hits"])} 条证据</p><pre>{escape(body)}</pre></section>')
    return '''<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>M18A 原文上下文对照</title><style>body{font-family:system-ui,sans-serif;color:#172333;background:#f2f6fa;margin:0;padding:32px}main{max-width:1160px;margin:auto}h1{font-size:30px}.notice{background:#fff2d7;padding:16px;border-radius:12px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}section{background:white;padding:24px;border-radius:16px;min-width:0}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.8 system-ui}table{width:100%;border-collapse:collapse}td,th{padding:12px;border-bottom:1px solid #cdd7e2;text-align:left}details{background:white;padding:20px;margin-top:20px}@media(max-width:720px){body{padding:16px}.grid{grid-template-columns:1fr}h1{font-size:24px}}</style><main><p>第五章 · M18A · 本地原文演练</p><h1>命中了字段，还需要它旁边的解释</h1><p class="notice">固定选择 D31 的 JSON 子块；无云调用、无真实检索。这里比较证据范围，尚未测量答案准确率。</p><div class="grid">'''+''.join(panels)+f'''</div><details open><summary>观察结果与代价</summary><pre>{escape(json.dumps(result['observations'],ensure_ascii=False,indent=2))}</pre><p>字符数不是 token 数。增加的上下文是否有用，要在同一题集真实运行并评分。</p></details><details><summary>全部来源范围、子块对应关系与预算决定</summary><pre>{escape(json.dumps(result['parent_section'],ensure_ascii=False,indent=2))}</pre></details><p>长小节超限示例：保留原片段，不截断条件；已有结构化表格也保留原证据。</p></main></html>'''

def demo(output):
    output=Path(output)
    if output.exists():raise ValueError('目录已存在，请换一个输出编号')
    blocks,proof=read_materials();chunks=chunk_blocks(blocks)
    hits=[next(h for h in chunks if '"case_id": "WO-001"' in h['text'])]
    base=select_context(hits,final_k=1,max_chars=6000)
    expanded=select_expanded(hits,{'D31':blocks},final_k=1,max_chars=6000)
    before='\n'.join(h['text'] for h in base['hits']);after='\n'.join(h['text'] for h in expanded['hits'])
    phrase='不足以证明用户从未提交附件'
    assert phrase not in before and phrase in after
    result={'scope':'original_material_fixed_child_context_demonstration','source':proof,'selected_child_ids':[h['chunk_id'] for h in hits],
            'baseline':base,'parent_section':expanded,'profiles':{m:context_profile(m) for m in ['baseline','parent_section']},
            'observations':{'空列表解释_补全前':phrase in before,'空列表解释_补全后':phrase in after,
                            '增加正文字符数':expanded['text_chars']-base['text_chars'],'新增云请求':0,
                            '答案准确率变化':None,'召回率变化':None,'实际token变化':None},
            'docmind_called':False,'bailian_called':False,'retrieval_called':False,'semantic_quality_measured':False}
    output.mkdir(parents=True);(output/'comparison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    (output/'comparison.html').write_text(render(result),encoding='utf-8')
    return {'output':str(output),'source_lines_verified':len(blocks),'before_chars':base['text_chars'],'after_chars':expanded['text_chars'],'cloud_calls':0}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    args=parser.parse_args()
    try:print(json.dumps(demo(args.output),ensure_ascii=False,indent=2))
    except (ValueError,OSError) as error:parser.exit(1,str(error)+'\n')
