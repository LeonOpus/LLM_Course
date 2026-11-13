"""M12C：显式核对计划上的跨页表格结构实验；不猜测语义，不调用云。"""
from copy import deepcopy
from html import unescape
import re
from rag_app.core import chunk_blocks
from rag_app.structure import _Rows, _validate, _span, _key, blocks_digest


# revision: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# generated: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# revision: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# revision: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# checksum: lpf2-18283 lpf2-19E2b
class _MergedRows(_Rows):
    def __init__(self,text):
        super().__init__(text)
        self.cells=[];self.current=[];self.cell_start=None;self.cell_shape=None

    def handle_starttag(self,tag,attrs):
        if tag in {'td','th'}:
            if len(attrs)!=len(dict(attrs)):raise ValueError('重复跨度属性')
            shape={'rowspan':1,'colspan':1}
            for k,v in attrs:
                if k not in shape or not isinstance(v,str) or not re.fullmatch(r'[1-9][0-9]?',v) or int(v)>64:
                    raise ValueError('不支持的跨度或属性')
                shape[k]=int(v)
            self.cell_start=self.absolute_position();self.cell_shape=shape
            super().handle_starttag(tag,[(k,'1') for k,_ in attrs])
        else:
            super().handle_starttag(tag,attrs)
            if tag=='tr':self.current=[]

    def handle_endtag(self,tag):
        if tag in {'td','th'} and self.stack and self.stack[-1]==tag:
            end=self.text.find('>',self.absolute_position())+1
            raw=self.text[self.cell_start:end]
            label=unescape(re.sub(r'<[^>]*>',' ',raw))
            self.current.append({**self.cell_shape,'label':' '.join(label.split()),'span':[self.cell_start,end]})
        super().handle_endtag(tag)
        if tag=='tr':
            self.cells.append(self.current)
            if len(self.cells)>10000:raise ValueError('表格行数超过实验上限')


def merged_table(text,header_rows):
    if not isinstance(text,str) or len(text)>2000000:raise ValueError('表格文本无效或过长')
    p=_MergedRows(text);p.feed(text);p.close()
    if p.stack or p.tables!=1 or not p.rows:raise ValueError('表格不完整')
    if type(header_rows) is not int or not 1<=header_rows<len(p.rows):raise ValueError('表头行数无效')
    grid=[{} for _ in p.rows];serial=0
    for ri,cells in enumerate(p.cells):
        col=0
        for cell in cells:
            while col in grid[ri]:col+=1
            rs,cs=cell['rowspan'],cell['colspan']
            if ri>=header_rows and (rs!=1 or cs!=1):raise ValueError('数据行合并需专项核查，不能复制展开')
            if ri<header_rows and ri+rs>header_rows:raise ValueError('表头跨度越过数据行')
            if ri+rs>len(grid) or col+cs>64:raise ValueError('跨度超出矩形边界')
            for y in range(ri,ri+rs):
                for x in range(col,col+cs):
                    if x in grid[y]:raise ValueError('合并单元格发生重叠')
                    grid[y][x]=(serial,cell['label'])
            serial+=1;col+=cs
    width=max(len(row) for row in grid)
    if not width or any(set(row)!=set(range(width)) for row in grid):raise ValueError('展开后列数不齐或存在空洞')
    paths=[]
    for col in range(width):
        path=[];previous=None
        for ri in range(header_rows):
            ident,label=grid[ri][col]
            if not label:raise ValueError('空表头需要核查，不能猜测名称')
            if ident!=previous:path.append(label)
            previous=ident
        paths.append(path)
    return {'spans':p.rows,'paths':paths,'width':width,
            'data_values':[[grid[i][c][1] for c in range(width)] for i in range(header_rows,len(grid))]}


def _review(blocks,plan):
    if (not isinstance(plan,dict) or type(plan.get('schema_version')) is not int or plan['schema_version']!=2
        or not isinstance(plan.get('groups'),list)):raise ValueError('续表计划须为版本2且groups为列表')
    lookup,_=_validate(blocks,{'schema_version':1,'review_note':plan.get('review_note'),
                             'blocks_sha256':plan.get('blocks_sha256'),'tables':[]})
    selected=set();groups=[]
    for spec in plan['groups']:
        if not isinstance(spec,dict) or not isinstance(spec.get('doc_id'),str):raise ValueError('续表文档编号无效')
        ids=spec.get('block_ids');ctx=spec.get('context_block_ids')
        for value in [ids,ctx]:
            if not isinstance(value,list) or any(not isinstance(x,str) for x in value) or len(set(value))!=len(value):
                raise ValueError('表格或说明编号须为不重复列表')
        if not ids:raise ValueError('续表块不能为空')
        group=[];last_page=0;signature=None
        for uid in ids:
            key=(spec['doc_id'],uid);b=lookup.get(key)
            if key in selected:raise ValueError('表格已属于其他续表组')
            if b is None or b.get('type')!='table' or b['locator']['kind']!='pdf':raise ValueError('续表须为同文档已有PDF表格')
            page=b['locator']['page']
            if page<=last_page:raise ValueError('续表物理页必须严格递增')
            last_page=page;parsed=merged_table(b['text'],spec.get('header_rows'))
            if signature is not None and signature!=parsed['paths']:raise ValueError('续表表头路径、单位或列顺序不一致')
            signature=parsed['paths'];group.append((b,parsed));selected.add(key)
        contexts=[]
        for uid in ctx:
            b=lookup.get((spec['doc_id'],uid))
            if b is None or b.get('type')=='table' or not b['text'].strip():raise ValueError('说明须为同文档已有非空文字块')
            contexts.append(b)
        groups.append({'tables':group,'contexts':contexts,'header_rows':spec['header_rows']})
    return lookup,selected,groups


def _assemble(group,plan_hash,window,include_context):
    n=group['header_rows'];first,parsed=group['tables'][0]
    header=[_span(first,a,b,'header') for a,b in parsed['spans'][:n]]
    contexts=[_span(b,0,len(b['text']),'context') for b in group['contexts']] if include_context else []
    rows=[_span(b,a,z,'data_row') for b,p in group['tables'] for a,z in p['spans'][n:]]
    def body(data):return '<table>\n'+'\n'.join(s['text'] for s in header+data)+'\n</table>'+''.join('\n'+s['text'] for s in contexts)
    pending=[];batches=[]
    for row in rows:
        if len(body([row]))>window:raise ValueError(f'完整表头、行与说明超过{window}字符预算；请显式设计预算实验')
        if pending and len(body(pending+[row]))>window:batches.append(pending);pending=[]
        pending.append(row)
    if pending:batches.append(pending)
    chunks=[];variant='P2+C2' if include_context else 'P2'
    for data in batches:
        sources=header+data+contexts;content=body(data)
        identity={'algorithm':'m12c-multipage-v1','variant':variant,'window':window,
                  'plan_sha256':plan_hash,'text':content,'source_spans':sources}
        chunks.append({'chunk_id':blocks_digest(identity)[:32],'doc_id':first['doc_id'],'type':'table',
                       'locator':deepcopy(data[0]['locator']),'text':content,'char_range':None,'source_spans':sources,
                       'metadata':{'transformation':variant,'plan_sha256':plan_hash,'column_paths':parsed['paths'],
                         'group_block_ids':[b['locator']['block_id'] for b,_ in group['tables']],
                         'source_range_notice':'跨页拼接；主locator仅为首个数据行，所有片段实际出处见source_spans'}})
    return chunks


def multipage_chunks(blocks,plan,window=600,overlap=100,include_context=False):
    _,selected,groups=_review(blocks,plan)
    chunk_blocks([],window=window,overlap=overlap)
    starts={_key(g['tables'][0][0]):g for g in groups};chunks=[]
    for b in blocks:
        key=_key(b)
        if key in starts:chunks.extend(_assemble(starts[key],blocks_digest(plan),window,include_context))
        elif key not in selected:chunks.extend(chunk_blocks([b],window=window,overlap=overlap))
    return chunks


def compare_multipage(blocks,plan,window=600,overlap=100):
    lookup,selected,groups=_review(blocks,plan)
    def contains(c,span):
        sources=c.get('source_spans') or [c]
        a,z=span['char_range']
        return any(_key(s)==_key(span) and s.get('char_range') is not None and
                   s['char_range'][0]<=a and z<=s['char_range'][1] for s in sources)
    variants={}
    for name,chunks in [('B0',chunk_blocks(blocks,window=window,overlap=overlap)),
                        ('P2',multipage_chunks(blocks,plan,window,overlap)),
                        ('P2+C2',multipage_chunks(blocks,plan,window,overlap,True))]:
        complete=with_header=with_context=expected=0
        for g in groups:
            n=g['header_rows'];first,fp=g['tables'][0]
            canonical=[_span(first,a,z,'header') for a,z in fp['spans'][:n]]
            contexts=[_span(b,0,len(b['text']),'context') for b in g['contexts']]
            for b,p in g['tables']:
                local=[_span(b,a,z,'header') for a,z in p['spans'][:n]]
                for a,z in p['spans'][n:]:
                    expected+=1;row=_span(b,a,z,'data_row');hits=[c for c in chunks if contains(c,row)]
                    complete+=bool(hits)
                    together=[c for c in hits if any(all(contains(c,s) for s in h) for h in [local,canonical])]
                    with_header+=bool(together)
                    if contexts:
                        with_context+=any(all(contains(c,s) for s in contexts) for c in together)
        variants[name]={'chunks':chunks,'chunk_count':len(chunks),'total_chars':sum(len(c['text']) for c in chunks),
                        'expected_rows':expected,'complete_rows':complete,'rows_with_header':with_header,
                        'rows_with_header_and_context':with_context}
    return {'schema_version':'rag-multipage-comparison/1','blocks_sha256':blocks_digest(blocks),'plan_sha256':blocks_digest(plan),
            'config':{'window':window,'overlap_for_fixed_blocks':overlap,'budget_unit':'body_characters_including_markup'},
            'cloud_calls':0,'retrieval_recall':None,'answer_accuracy':None,'variants':variants,
            'warnings':[f'{k[0]}/{k[1]} 未在计划中，保持B0' for k,b in lookup.items() if b.get('type')=='table' and k not in selected],
            'limitations':['结构覆盖不等于检索召回或答案正确。','核对计划是人工判断，指纹不认证语义。',
                           '不推断缺失表头、不纠正OCR、不展开数据合并单元格。','未选中的说明保持独立块；所选说明的适用范围需人工核查。']}
