"""M12A：冻结解析块上的保真对照；无云调用，不修改在线索引。"""
from copy import deepcopy
from hashlib import sha256
from html.parser import HTMLParser
import json
import re
from rag_app.core import chunk_blocks, validate_locator


# checksum: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# generated: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# checksum: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# generated: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# checksum: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# revision: lpf2-18283 lpf2-19E2b
def blocks_digest(value):
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(',', ':'), allow_nan=False).encode()).hexdigest()


class _Rows(HTMLParser):
    """严格子集，不用HTML容错解析来掩盖丢失内容；记录原始字符区间。"""
    def __init__(self, text):
        super().__init__(convert_charrefs=False)
        self.text=text;self.stack=[];self.rows=[];self.widths=[];self.tables=0
        # HTMLParser只以换行符更新行号，不能把Unicode分隔符也算成新行。
        self.offsets=[0]+[m.end() for m in re.finditer('\n',text)]
        self.row_start=None;self.width=0

    def absolute_position(self):
        line,column=self.getpos()
        return self.offsets[line-1]+column

    def handle_starttag(self, tag, attrs):
        parent=self.stack[-1] if self.stack else None
        allowed={'table':{None},'thead':{'table'},'tbody':{'table'},'tfoot':{'table'},
                 'tr':{'table','thead','tbody','tfoot'},'td':{'tr'},'th':{'tr'},'br':{'td','th'}}
        if tag not in allowed or parent not in allowed[tag]:raise ValueError('表格包含不支持的标签、嵌套或残缺结构')
        if tag=='table':
            self.tables+=1
            if self.tables!=1:raise ValueError('只接受一个完整表格')
        if len(dict(attrs))!=len(attrs):raise ValueError('表格属性重复')
        for key,value in attrs:
            if tag not in {'td','th'} or key not in {'rowspan','colspan'} or value!='1':
                raise ValueError('表格含合并单元格或未知属性；先核对结构，不自动展开')
        if tag=='tr':self.row_start=self.absolute_position();self.width=0
        if tag in {'td','th'}:self.width+=1
        if tag!='br':self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        if tag!='br':raise ValueError('不支持自闭合表格标签')
        self.handle_starttag(tag,attrs)

    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1]!=tag:raise ValueError('表格标签没有正确配对')
        if tag=='tr':
            if not self.width:raise ValueError('表格存在空行')
            end=self.text.find('>',self.absolute_position())
            if end<0:raise ValueError('表格结束标签残缺')
            self.rows.append((self.row_start,end+1));self.widths.append(self.width)
        self.stack.pop()

    def handle_data(self, data):
        if data.strip() and (not self.stack or self.stack[-1] not in {'td','th'}):
            raise ValueError('表格单元格外存在未绑定文字，不能静默丢弃')

    def handle_entityref(self, name):self.handle_data('&'+name+';')
    def handle_charref(self, name):self.handle_data('&#'+name+';')
    def handle_comment(self, data):raise ValueError('表格包含注释，需先核查')
    def handle_decl(self, decl):raise ValueError('表格包含声明，需先核查')
    def handle_pi(self, data):raise ValueError('表格包含处理指令，需先核查')
    def unknown_decl(self, data):raise ValueError('表格包含未知声明')


def table_rows(text):
    if not isinstance(text,str) or len(text)>2000000:raise ValueError('表格文本类型或长度无效')
    parser=_Rows(text)
    parser.feed(text);parser.close()
    if parser.stack or parser.tables!=1 or not parser.rows or len(set(parser.widths))!=1:
        raise ValueError('表格不完整或各行列数不一致，需核对原件')
    return parser.rows


def _key(block):return (block['doc_id'],block['locator']['block_id'])


def _validate(blocks,plan):
    if not isinstance(blocks,list) or not blocks:raise ValueError('解析块必须是非空列表')
    lookup={}
    for b in blocks:
        if (not isinstance(b,dict) or not isinstance(b.get('text'),str)
            or not isinstance(b.get('doc_id'),str) or not b['doc_id'].strip()):
            raise ValueError('解析块缺少正文或文档编号')
        validate_locator(b.get('locator'))
        key=_key(b)
        if key in lookup:raise ValueError('解析块身份重复')
        lookup[key]=b
    if (not isinstance(plan,dict) or type(plan.get('schema_version')) is not int or plan['schema_version']!=1
        or not isinstance(plan.get('review_note'),str) or not plan['review_note'].strip()
        or not isinstance(plan.get('tables'),list)):
        raise ValueError('核对计划版本、核查说明或tables无效')
    if plan.get('blocks_sha256')!=blocks_digest(blocks):raise ValueError('解析块指纹已改变，请重新核查计划')
    selected={}
    for row in plan['tables']:
        if (not isinstance(row,dict) or not isinstance(row.get('doc_id'),str)
            or not isinstance(row.get('block_id'),str)):
            raise ValueError('表格计划缺少文档或块编号')
        key=(row['doc_id'],row['block_id'])
        if key in selected:raise ValueError('表格计划重复')
        if key not in lookup or lookup[key].get('type')!='table':raise ValueError('计划表格不存在或不是表格')
        spans=table_rows(lookup[key]['text']);n=row.get('header_rows')
        if type(n) is not int or not 1<=n<len(spans):raise ValueError('header_rows须为正整数且必须剩余数据行')
        ids=row.get('context_block_ids')
        if not isinstance(ids,list) or any(not isinstance(i,str) for i in ids) or len(ids)!=len(set(ids)):
            raise ValueError('附加说明编号应为不重复的列表')
        contexts=[]
        for uid in ids:
            context=lookup.get((key[0],uid))
            if context is None or context.get('type')=='table' or not context['text'].strip():
                raise ValueError('说明必须是同文档已有非空文字块，不能引用表格或跨文档补字')
            contexts.append(context)
        selected[key]={'row':row,'spans':spans,'contexts':contexts}
    return lookup,selected


def _span(block,start,end,role):
    return {'doc_id':block['doc_id'],'locator':deepcopy(block['locator']),
            'char_range':[start,end],'text':block['text'][start:end],'role':role}


def _group(block,selection,variant,window,plan_hash):
    spans=selection['spans'];n=selection['row']['header_rows'];text=block['text']
    contexts=selection['contexts'] if variant=='P1+C1' else []
    header=[_span(block,a,b,'header') for a,b in spans[:n]]
    context=[_span(b,0,len(b['text']),'context') for b in contexts]
    def body(data):
        return '<table>\n'+'\n'.join(s['text'] for s in header+data)+'\n</table>'+''.join('\n'+s['text'] for s in context)
    groups=[];pending=[]
    for a,b in spans[n:]:
        row=_span(block,a,b,'data_row')
        if len(body([row]))>window:
            raise ValueError(f'{block["locator"]["block_id"]}：完整数据行＋表头＋说明超过{window}字符；不能截断，需单独设计并记录预算实验')
        if pending and len(body(pending+[row]))>window:groups.append(pending);pending=[]
        pending.append(row)
    if pending:groups.append(pending)
    chunks=[]
    for data in groups:
        sources=header+data+context;content=body(data)
        identity={'strategy':variant,'window':window,'plan_sha256':plan_hash,'text':content,'source_spans':sources}
        chunks.append({'chunk_id':blocks_digest(identity)[:32],'doc_id':block['doc_id'],
                       'type':'table','text':content,'locator':deepcopy(block['locator']),
                       'char_range':None,'source_spans':sources,
                       'metadata':{**deepcopy(block.get('metadata',{})),
                           'transformation':variant,'plan_sha256':plan_hash,
                           'source_range_notice':'拼接片段；主locator仅指主体表格，各段实际出处见source_spans'}})
    return chunks


def _coverage(block,selection,chunks):
    key=_key(block);spans=selection['spans'];header=selection['row']['header_rows']
    def contains(chunk,source_key,interval):
        if chunk.get('source_spans') is not None:
            ranges=[s['char_range'] for s in chunk['source_spans']
                    if (s['doc_id'],s['locator']['block_id'])==source_key]
        else:ranges=[chunk['char_range']] if _key(chunk)==source_key else []
        a,b=interval
        return any(x<=a and b<=y for x,y in ranges)
    covered=[index+header+1 for index,(a,b) in enumerate(spans[header:])
             if any(contains(c,key,(a,b)) for c in chunks)]
    with_header=[];with_context=[]
    for number,interval in enumerate(spans[header:],header+1):
        together=[c for c in chunks if contains(c,key,interval) and all(contains(c,key,s) for s in spans[:header])]
        if together:with_header.append(number)
        if any(all(contains(c,_key(b),(0,len(b['text']))) for b in selection['contexts']) for c in together):
            with_context.append(number)
    expected=list(range(header+1,len(spans)+1))
    return {'doc_id':key[0],'block_id':key[1],'data_rows':len(expected),
            'covered_complete_rows':len(covered),'missing_complete_row_numbers':[i for i in expected if i not in covered],
            'rows_with_header':len(with_header),'rows_without_header_in_same_chunk':[i for i in expected if i not in with_header],
            'rows_with_header_and_context':len(with_context) if selection['contexts'] else None,
            'unit':'原表1基行号；按来源区间核对；不是检索召回率'}


def compare_structure(blocks,plan,window=600,overlap=100):
    lookup,selected=_validate(blocks,plan)
    # 保持已有B0算法，兼做window/overlap参数校验。
    baseline=chunk_blocks(blocks,window=window,overlap=overlap)
    variants={};plan_hash=blocks_digest(plan)
    for variant in ['B0','P1','P1+C1']:
        chunks=deepcopy(baseline) if variant=='B0' else []
        if variant!='B0':
            for block in blocks:
                selection=selected.get(_key(block))
                chunks.extend(_group(block,selection,variant,window,plan_hash) if selection else
                              chunk_blocks([block],window=window,overlap=overlap))
        variants[variant]={'config':{'window':window,'overlap_for_fixed_blocks':overlap,
            'table_row_overlap':None if variant=='B0' else 0,
            'reviewed_table_strategy':'fixed' if variant=='B0' else 'repeat_header_and_whole_rows',
            'repeat_reviewed_context':variant=='P1+C1','budget_unit':'body_characters_including_markup'},
            'chunks':chunks,'chunk_count':len(chunks),'total_chars':sum(len(c['text']) for c in chunks),
            'tables':[_coverage(lookup[key],s,chunks) for key,s in selected.items()]}
    warnings=[f'{k[0]}/{k[1]} 未列入核对计划，保持B0切法' for k,b in lookup.items() if b.get('type')=='table' and k not in selected]
    return {'schema_version':'rag-structure-comparison/1','blocks_sha256':blocks_digest(blocks),
            'plan_sha256':plan_hash,'review_note':plan['review_note'],'variants':variants,'warnings':warnings,
            'limitations':['本地结构对照，没有模型调用、Milvus检索或答案准确率。',
                           '计划由作者核查；指纹只证明未变更，不证明表头或语义标注正确。',
                           '跨页关联、合并单元格、图文关系尚需专项处理；未自动修复。',
                           '完整行覆盖不等于证据被召回；重复上下文可能增加片段数、向量费和干扰。']}


def selected_structure_chunks(blocks,plan,strategy,window=600,overlap=100):
    """在线只构造选中策略；不能让未启用的上下文策略影响P1。"""
    if strategy in {'multipage_rows','multipage_context'}:
        from rag_app.multipage import multipage_chunks
        return multipage_chunks(blocks,plan,window,overlap,include_context=strategy=='multipage_context')
    mapping={'table_rows':'P1','table_context':'P1+C1'}
    if strategy not in mapping:raise ValueError('不支持的结构切块策略')
    _,selected=_validate(blocks,plan)
    chunk_blocks([],window=window,overlap=overlap)
    output=[]
    for block in blocks:
        selection=selected.get(_key(block))
        output.extend(_group(block,selection,mapping[strategy],window,blocks_digest(plan)) if selection else
                      chunk_blocks([block],window=window,overlap=overlap))
    return output
