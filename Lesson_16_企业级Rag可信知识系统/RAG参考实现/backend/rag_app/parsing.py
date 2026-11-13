"""保留来源语义的格式适配。DocMind pageNum 的基准由适配器显式声明。"""
import csv
from html import escape
from hashlib import sha256
from rag_app.core import validate_locator

# checksum: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# cache: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# revision: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# checksum: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# revision: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# checksum: lpf2-18283 lpf2-19E2b
def table_html(layout):
    cells=layout.get('cells',[])
    if not cells: return layout.get('markdownContent') or layout.get('text') or ''
    rows={}; occupied=set()
    for cell in cells:
        coords=[cell.get(k) for k in ('ysc','yec','xsc','xec')]
        if any(type(v) is not int or v<0 for v in coords): raise ValueError('表格单元格缺少合法行列坐标')
        y0,y1,x0,x1=coords
        if y1<y0 or x1<x0: raise ValueError('表格单元格范围颠倒')
        for y in range(y0,y1+1):
            for x in range(x0,x1+1):
                if (y,x) in occupied: raise ValueError('表格单元格范围重叠')
                occupied.add((y,x))
        text=' '.join(str(v.get('text') or v.get('markdownContent') or '') for v in cell.get('layouts',[]))
        if not text: text=str(cell.get('text',''))
        rows.setdefault(y0,[]).append((x0,f'<td rowspan="{y1-y0+1}" colspan="{x1-x0+1}">{escape(text)}</td>'))
    return '<table>\n'+'\n'.join('<tr>'+''.join(cell for _,cell in sorted(rows[y]))+'</tr>' for y in sorted(rows))+'\n</table>'

def normalize_layouts(doc_id,kind,layouts,page_base=0):
    if type(page_base) is not int or page_base not in (0,1): raise ValueError('page_base 必须显式为 0 或 1')
    out=[];seen=set(); headings=[]
    for n,layout in enumerate(layouts):
        uid=str(layout.get('uniqueId') or f'layout-{n:06d}')
        if uid in seen: raise ValueError('DocMind 返回重复块 ID，检查结果分页')
        seen.add(uid)
        block_type=layout.get('type','text')
        origin='docmind_layout'
        table_metadata={}
        if block_type=='table':
            try:text=table_html(layout)
            except ValueError as error:
                fallback=layout.get('markdownContent')
                if not isinstance(fallback,str) or not fallback.strip():raise
                text=fallback
                table_metadata={'table_representation':'provider_markdown_fallback',
                    'table_structure_validated':False,'table_structure_issue':str(error)}
        else:text=layout.get('markdownContent') or layout.get('text') or ''
        if not str(text).strip() and layout.get('llmResult'):
            text=layout['llmResult'];origin='docmind_llm'
        if not str(text).strip(): continue
        locator={'kind':kind,'block_id':uid}
        raw_page=layout.get('pageNum')
        if kind in ('pdf','pptx'):
            if type(raw_page) is not int or raw_page<page_base: raise ValueError('解析结果缺少合法页号，不能默认成第一页')
            locator['page' if kind=='pdf' else 'slide']=raw_page-page_base+1
            locator['raw_page_num']=raw_page
            locator['raw_page_base']=page_base
        # pos 原样留存，未得到页面尺寸与坐标系前不得冒充 PDF points。
        if layout.get('pos') is not None:
            locator['raw_position']=layout['pos']; locator['coordinate_system']='docmind_raw_unverified'
        if block_type=='title':
            level=layout.get('level',0)
            if type(level) is int and 0<=level<=8:
                headings=headings[:level]+[str(text).strip().lstrip('#').strip()]
        if headings: locator['heading_path']=headings.copy()
        validate_locator(locator)
        out.append({'doc_id':doc_id,'text':str(text),'type':'table' if block_type=='table' else block_type,
                    'locator':locator,'metadata':{'parser':'docmind','text_origin':origin,
                    'raw_layout_index':layout.get('index',n),'locator_precision':
                    'page' if kind=='pdf' else 'slide' if kind=='pptx' else 'block',
                    'content_sha256':sha256(str(text).encode()).hexdigest(),**table_metadata}})
    return out

def read_csv_blocks(doc_id,path):
    blocks=[]
    with open(path,encoding='utf-8-sig',newline='') as f:
        reader=csv.reader(f)
        headers=next(reader,None)
        if not headers or any(not h.strip() for h in headers) or len(set(headers))!=len(headers):
            raise ValueError('CSV 必须有非空且不重复的表头')
        end=reader.line_num
        for index,row in enumerate(reader,1):
            start=end+1;end=reader.line_num
            if not row: continue
            if len(row)!=len(headers): raise ValueError(f'CSV 第 {start} 行字段数不等于表头数')
            locator={'kind':'csv','block_id':f'record-{index}','line_start':start,'line_end':end,'record_index':index}
            blocks.append({'doc_id':doc_id,'type':'table','text':'\n'.join(f'{k}: {v}' for k,v in zip(headers,row)),
                           'locator':locator,'metadata':{'parser':'native_csv','text_origin':'source','columns':headers}})
    return blocks
