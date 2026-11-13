"""M18A: retrieve children, deliver bounded original sections, never invent missing text."""
from copy import deepcopy
from hashlib import sha256
import json
from rag_app.generation import select_context
from rag_app.indexing import preview_chunks
from rag_app.core import validate_locator

# cache: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# cache: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# revision: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# cache: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# cache: lpf2-18283 lpf2-19E2b
def context_profile(mode,*,max_chars=6000):
    if type(max_chars) is not int or not 1<=max_chars<=120000:raise ValueError("上下文正文预算须为1至120000字符")
    if mode not in {'baseline','parent_section'}:raise ValueError('不支持的上下文策略')
    return {'schema_version':'context-policy/1' if max_chars==6000 else 'context-policy/2','mode':mode,'algorithm_version':'m18a-original-section-v1',
            'parent_max_chars':1800,'max_chars':max_chars,'budget_unit':'body_characters',
            'grouping':'contiguous_exact_heading_path','missing_heading':'single_block',
            'overflow':'fallback_child_without_truncation','structured_chunks':'keep_existing'}

def _digest(value):
    return sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def _sections(doc_id,blocks):
    mapping={};group=[];previous=None
    for block in blocks:
        if not isinstance(block,dict) or block.get('doc_id')!=doc_id or not isinstance(block.get('text'),str):
            raise ValueError('父块原文或文档身份无效')
        loc=validate_locator(block.get('locator'));identity=loc['block_id']
        if identity in mapping:raise ValueError('解析块身份重复')
        heading=loc.get('heading_path')
        if heading is not None and (not isinstance(heading,list) or any(not isinstance(x,str) or not x.strip() for x in heading)):
            raise ValueError('标题路径格式无效')
        # A missing heading is a boundary, including between two title-free blocks.
        if not heading or heading!=previous:group=[]
        group.append(block);mapping[identity]=(block,group)
        previous=heading
    return mapping

def select_expanded(candidates,blocks_by_doc,*,final_k=5,max_chars=6000,parent_max_chars=1800):
    for value in [final_k,max_chars,parent_max_chars]:
        if type(value) is not int or value<1:raise ValueError('上下文数量与预算必须为正整数')
    if final_k>20:raise ValueError('final_k超过20')
    ids=[h.get('chunk_id') for h in candidates]
    if any(not isinstance(i,str) or not i for i in ids) or len(set(ids))!=len(ids):raise ValueError('候选身份缺失或重复')
    maps={doc:_sections(doc,blocks) for doc,blocks in blocks_by_doc.items()}
    choices=[]
    for hit in candidates:
        if not isinstance(hit.get('text'),str) or not hit['text'].strip():raise ValueError('候选正文为空')
        if hit.get('doc_id') not in maps:raise ValueError('候选文档没有绑定的原文')
        if hit.get('source_spans'):
            choices.append((hit,None,'structured_chunk'));continue
        found=maps[hit['doc_id']].get(hit.get('locator',{}).get('block_id'))
        if found is None:raise ValueError('候选原文块已丢失')
        block,section=found;r=hit.get('char_range')
        if (hit.get('locator')!=block['locator'] or not isinstance(r,list) or len(r)!=2 or
            any(type(n) is not int for n in r) or not 0<=r[0]<r[1]<=len(block['text']) or block['text'][r[0]:r[1]]!=hit['text']):
            raise ValueError('候选与原文字符区间不一致，不能补全')
        # Empty source blocks may delimit groups but contribute no made-up content.
        spans=[{'doc_id':hit['doc_id'],'locator':deepcopy(b['locator']),'char_range':[0,len(b['text'])],
                'text':b['text'],'role':'parent_context'} for b in section if b['text'].strip()]
        body='\n\n'.join(s['text'] for s in spans)
        if len(spans)==1 and body==hit['text']:
            choices.append((hit,None,'already_complete'));continue
        if len(body)>parent_max_chars:
            choices.append((hit,None,'parent_limit'));continue
        parent={'chunk_id':_digest({'version':'m18a-original-section-v1','doc_id':hit['doc_id'],'spans':spans}),
                'doc_id':hit['doc_id'],'text':body,'type':'parent_context','locator':deepcopy(hit['locator']),
                'char_range':None,'source_spans':spans,'metadata':{
                    'source_range_notice':'主定位为首个命中的子块；全部原文范围见source_spans。',
                    'parent_expansion':{'matched_child_ids':[hit['chunk_id']],'grouping':'contiguous_exact_heading_path'}}}
        choices.append((hit,parent,None))
    hits=[];excluded=[];decisions=[];selected={};used=0
    for child,parent,reason in choices:
        row={'child_id':child['chunk_id'],'parent_id':parent['chunk_id'] if parent else None}
        if parent and parent['chunk_id'] in selected:
            selected[parent['chunk_id']]['metadata']['parent_expansion']['matched_child_ids'].append(child['chunk_id'])
            decisions.append({**row,'action':'merged','reason':'parent_already_selected'});continue
        if len(hits)>=final_k:
            excluded.append({'chunk_id':child['chunk_id'],'reason':'final_k'})
            decisions.append({**row,'action':'excluded','reason':'final_k'});continue
        chosen=parent
        if parent and used+len(parent['text'])>max_chars:reason='parent_budget';chosen=None
        if chosen is None:chosen=deepcopy(child)
        if used+len(chosen['text'])>max_chars:
            excluded.append({'chunk_id':child['chunk_id'],'reason':'char_budget'})
            decisions.append({**row,'action':'excluded','reason':'char_budget'});continue
        hits.append(chosen);used+=len(chosen['text'])
        if parent and chosen is parent:selected[parent['chunk_id']]=parent
        decisions.append({**row,'action':'expanded' if parent is chosen else 'kept_child',
                          'reason':reason or 'within_budget','context_id':chosen['chunk_id']})
    return {'hits':hits,'excluded':excluded,'decisions':decisions,'text_chars':used,'max_chars':max_chars,
            'final_k':final_k,'budget_unit':'body_characters','parent_max_chars':parent_max_chars}

def select_for_pipeline(pipeline,candidates,index_profile,*,final_k=5,max_chars=6000):
    mode=pipeline.settings.context_policy
    if mode=='baseline':return select_context(candidates,final_k=final_k,max_chars=max_chars)
    context_profile(mode)
    if not candidates:return select_expanded([],{},final_k=final_k,max_chars=max_chars)
    rows=(index_profile or {}).get('documents',[])
    by_doc={r['doc_id']:r for r in rows}
    if len(by_doc)!=len(rows):raise ValueError('索引文档身份重复')
    blocks_by_doc={}
    for doc in sorted({h['doc_id'] for h in candidates}):
        snapshot=by_doc.get(doc)
        if snapshot is None:raise ValueError('候选未绑定实际索引')
        preview=preview_chunks(pipeline,doc)
        raw=(pipeline.folder(doc)/'blocks.json').read_bytes()
        if (sha256(raw).hexdigest()!=preview['blocks_sha256'] or preview['blocks_sha256']!=snapshot.get('blocks_sha256')
            or pipeline.store.get(doc)['sha256']!=snapshot.get('source_sha256')):
            raise ValueError('补全时原文已变化，请重新解析和建立独立索引')
        expected={h['chunk_id']:h for h in preview['chunks']}
        for hit in (h for h in candidates if h['doc_id']==doc):
            original=expected.get(hit['chunk_id'])
            if original is None or any(hit.get(k)!=original.get(k) for k in ['doc_id','text','type','locator','char_range','metadata','source_spans']):
                raise ValueError('候选与当前索引片段不一致，不能补全')
        blocks_by_doc[doc]=json.loads(raw)
    return select_expanded(candidates,blocks_by_doc,final_k=final_k,max_chars=max_chars)
