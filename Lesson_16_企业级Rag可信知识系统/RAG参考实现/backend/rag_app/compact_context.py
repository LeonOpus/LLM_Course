"""M24: restore complete sections within explicit budgets; no new source facts."""
from copy import deepcopy
import json,re
from rag_app.context import _sections,_digest
from rag_app.structure import table_rows
from rag_app.generation import build_messages
# checksum: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# cache: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# checksum: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# checksum: lpf2-18283 lpf2-19E2b
VERSION='compact-original-section-v1'

def compact_table(text):
    # Validation comes first. Merged or malformed tables are kept verbatim by
    # the caller; no inferred header, cell value or row relationship is added.
    table_rows(text)
    return re.sub(r'\s+(?:rowspan|colspan)\s*=\s*([\'"])1\1','',text,flags=re.I)

def _render(block):
    if block.get('type')=='table':
        try:return compact_table(block['text'])
        except ValueError:return block['text']
    return block['text']

def _serialized(hits):
    evidence=json.loads(build_messages('budget',hits)[-1]['content'])['evidence']
    return len(json.dumps(evidence,ensure_ascii=False))

def select_compact(candidates,blocks_by_doc,*,final_k=5,max_chars=6000,parent_max_chars=2400,max_serialized_chars=30000):
    for value in [final_k,max_chars,parent_max_chars,max_serialized_chars]:
        if type(value) is not int or value<1:raise ValueError('上下文预算必须为正整数')
    if final_k>20:raise ValueError('final_k超过20')
    ids=[h.get('chunk_id') for h in candidates]
    if any(not isinstance(i,str) or not i for i in ids) or len(ids)!=len(set(ids)):raise ValueError('候选身份缺失或重复')
    maps={doc:_sections(doc,blocks) for doc,blocks in blocks_by_doc.items()}
    hits=[];selected={};decisions=[];excluded=[];used=0
    for child in candidates:
        doc=child.get('doc_id');loc=child.get('locator',{});identity=loc.get('block_id')
        if doc not in maps or identity not in maps[doc]:raise ValueError('候选来源块未绑定')
        block,section=maps[doc][identity];reason=None;parent=None
        if child.get('source_spans'):reason='structured_chunk_kept'
        else:
            r=child.get('char_range')
            if (loc!=block['locator'] or not isinstance(r,list) or len(r)!=2 or any(type(v) is not int for v in r)
                or not 0<=r[0]<r[1]<=len(block['text']) or block['text'][r[0]:r[1]]!=child.get('text')):
                raise ValueError('候选与来源字符区间不一致')
            body='\n\n'.join(_render(b) for b in section if b['text'].strip())
            chosen=section
            if len(body)>parent_max_chars:
                chosen=[block];body=_render(block);reason='whole_block_fallback'
            if len(body)>parent_max_chars:reason='parent_limit'
            elif len(chosen)==1 and body==child['text']:reason='already_complete'
            else:
                spans=[{'doc_id':doc,'locator':deepcopy(b['locator']),'char_range':[0,len(b['text'])],
                        'text':b['text'],'role':'original_section'} for b in chosen if b['text'].strip()]
                uid=_digest({'version':VERSION,'doc_id':doc,'spans':spans})
                parent={'chunk_id':uid,'doc_id':doc,'type':'compact_parent_context','text':body,
                    'locator':deepcopy(child['locator']),'char_range':None,'source_spans':spans,
                    'metadata':{'context_transform':VERSION,'parent_expansion':{'matched_child_ids':[child['chunk_id']]},
                        'rendering':'only_remove_validated_rowspan_colspan_1; raw_source_spans_unchanged',
                        'source_range_notice':'主定位为首个命中块，完整原始范围见source_spans。'}}
        row={'child_id':child['chunk_id'],'parent_id':parent['chunk_id'] if parent else None}
        if parent and parent['chunk_id'] in selected:
            # All merged child identities are recorded in decisions, outside the prompt.
            decisions.append({**row,'action':'merged','reason':'same_parent'});continue
        if len(hits)>=final_k:
            excluded.append({'chunk_id':child['chunk_id'],'reason':'final_k'});decisions.append({**row,'action':'excluded','reason':'final_k'});continue
        chosen=parent if parent else deepcopy(child)
        if parent and used+len(parent['text'])>max_chars:chosen=deepcopy(child);reason='body_budget_fallback'
        if parent and _serialized(hits+[chosen])>max_serialized_chars:chosen=deepcopy(child);reason='serialized_budget_fallback'
        if used+len(chosen['text'])>max_chars or _serialized(hits+[chosen])>max_serialized_chars:
            excluded.append({'chunk_id':child['chunk_id'],'reason':'context_budget'});decisions.append({**row,'action':'excluded','reason':'context_budget'});continue
        hits.append(chosen);used+=len(chosen['text'])
        if chosen is parent:selected[parent['chunk_id']]=parent
        decisions.append({**row,'action':'expanded' if chosen is parent else 'kept_child','reason':reason or 'within_budget','context_id':chosen['chunk_id']})
    return {'hits':hits,'decisions':decisions,'excluded':excluded,'text_chars':used,'max_chars':max_chars,'final_k':final_k,
        'parent_max_chars':parent_max_chars,'serialized_evidence_chars':_serialized(hits),
        'max_serialized_chars':max_serialized_chars,'algorithm_version':VERSION,'budget_unit':'characters_not_tokens'}
