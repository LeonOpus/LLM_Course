"""M08 source inspector adapted from the reviewed course reference, in staged steps.
This is a source audit, not a replacement for DocMind or a quality score.
"""
from copy import deepcopy
from hashlib import sha256
from html import escape
from pathlib import Path
import re
from rag_app.core import validate_locator
from rag_app.parsing import read_csv_blocks

# checksum: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# checksum: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# cache: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# revision: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# cache: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# checksum: lpf2-18283 lpf2-19E2b
def _block(doc_id,kind,uid,text,block_type='text',**locator):
    source={'kind':kind,'block_id':uid,**locator};validate_locator(source)
    return {'doc_id':doc_id,'type':block_type,'text':text,'locator':source,
            'metadata':{'parser':f'source_audit_{kind}','text_origin':'source','role':'source_audit'}}


def _docx_table(table):
    """按Word网格合并同一个XML单元格，避免合并标题被重复输出。"""
    from docx.table import Table
    records={}
    for r,row in enumerate(table.rows):
        for c,cell in enumerate(row.cells,start=row.grid_cols_before):
            record=records.setdefault(cell._tc,{'cell':cell,'coordinates':[]})
            record['coordinates'].append((r,c))
    rows={};geometry=[]
    for record in records.values():
        positions=record['coordinates'];r0=min(r for r,c in positions);r1=max(r for r,c in positions)
        c0=min(c for r,c in positions);c1=max(c for r,c in positions)
        content=[]
        for item in record['cell'].iter_inner_content():
            if isinstance(item,Table):content.append(_docx_table(item)[0])
            elif item.text:content.append(escape(item.text))
        cell_text='<br/>'.join(content)
        rows.setdefault(r0,[]).append((c0,f'<td rowspan="{r1-r0+1}" colspan="{c1-c0+1}">{cell_text}</td>'))
        geometry.append({'row_start':r0+1,'row_end':r1+1,'column_start':c0+1,'column_end':c1+1})
    return '<table>\n'+'\n'.join('<tr>'+''.join(v for c,v in sorted(rows[r]))+'</tr>' for r in sorted(rows))+'\n</table>',geometry


def _docx(doc_id,path,report):
    from docx import Document
    from docx.table import Table
    doc=Document(path);blocks=[];paragraph_index=0;table_index=0;headings=[]
    for body_index,item in enumerate(doc.iter_inner_content(),1):
        if isinstance(item,Table):
            table_index+=1;text,geometry=_docx_table(item)
            block=_block(doc_id,'docx',f'table-{table_index}',text,'table',table_index=table_index,body_index=body_index,heading_path=headings.copy())
            block['metadata']['cell_geometry']=geometry;blocks.append(block)
        else:
            paragraph_index+=1
            if not item.text.strip():continue
            match=re.fullmatch(r'Heading ([1-9])',item.style.name or '')
            if match:headings=headings[:int(match[1])-1]+[item.text.strip()]
            block=_block(doc_id,'docx',f'paragraph-{paragraph_index}',item.text,'title' if match else 'text',paragraph_index=paragraph_index,body_index=body_index,heading_path=headings.copy())
            blocks.append(block)
    report['structure']={'body_paragraphs':paragraph_index,'body_tables':table_index,'inline_images':len(doc.inline_shapes)}
    report['warnings'].append({'code':'body_structure_only','message':'原生核对读取正文段落与表格；页眉页脚、文本框、修订内容和图中文字不在此读取范围，仍需DocMind及人工核查。'})
    return blocks


def _value(value):
    if value is None:return None
    if hasattr(value,'isoformat'):return value.isoformat()
    if isinstance(value,(str,int,float,bool)):return value
    return str(value)


def _xlsx(doc_id,path,report):
    from openpyxl import load_workbook
    from openpyxl.utils import get_column_letter
    wb=load_workbook(path,data_only=False,read_only=False);cache=load_workbook(path,data_only=True,read_only=False)
    blocks=[];sheets=[];missing=[]
    try:
        for sheet in wb:
            if sheet.max_row*sheet.max_column>1000000:raise ValueError('工作表声明网格超过核对上限，请先清理无用格式或拆分副本')
            merged=[str(r) for r in sheet.merged_cells.ranges]
            sheets.append({'name':sheet.title,'visibility':sheet.sheet_state,'merged_ranges':merged,'max_row':sheet.max_row,'max_column':sheet.max_column})
            for row in sheet.iter_rows():
                cells=[];lines=[]
                for cell in row:
                    if cell.value is None:continue
                    item={'coordinate':cell.coordinate,'number_format':cell.number_format}
                    if cell.data_type=='f':
                        cached=_value(cache[sheet.title][cell.coordinate].value)
                        item.update(formula=str(cell.value),cached_value=cached,cached_value_status='missing' if cached is None else 'present_unverified')
                        if cached is None:missing.append({'sheet':sheet.title,'cell':cell.coordinate})
                        value='[公式结果未缓存]' if cached is None else f'{cached} [公式缓存，未核验新鲜度]'
                    else:
                        item['value']=_value(cell.value);value=item['value']
                    cells.append(item);lines.append(f'{cell.coordinate}: {value}')
                if not cells:continue
                row_num=row[0].row;first=min(c.column for c in row if c.value is not None);last=max(c.column for c in row if c.value is not None)
                for merged_range in sheet.merged_cells.ranges:
                    if merged_range.min_row<=row_num<=merged_range.max_row:
                        first=min(first,merged_range.min_col);last=max(last,merged_range.max_col)
                cell_range=f'{get_column_letter(first)}{row_num}:{get_column_letter(last)}{row_num}'
                block=_block(doc_id,'xlsx',f'sheet-{len(sheets)}-row-{row_num}','\n'.join(lines),'table',sheet=sheet.title,cell_range=cell_range)
                block['metadata'].update(cells=cells,sheet_visibility=sheet.sheet_state,merged_ranges=[str(r) for r in sheet.merged_cells.ranges if r.min_row<=row_num<=r.max_row])
                blocks.append(block)
        report['structure']={'sheets':sheets}
        report['warnings'].append({'code':'sheet_structure_only','message':'按原生行显示值、格式与合并范围，不将第一行猜成唯一表头；图形、图表、打印布局仍需DocMind和原件核对。公式缓存即使存在也未证明为最新。'})
        if missing:report['warnings'].append({'code':'formula_cache_missing','message':'部分公式没有缓存值，未计算、未填零。','cells':missing})
        return blocks
    finally:wb.close();cache.close()


def _text(doc_id,path,kind,report):
    lines=path.read_text(encoding='utf-8-sig').splitlines();blocks=[];headings=[];start=None;group=[];fence=None;group_type='text'
    def flush(end):
        nonlocal start,group,group_type
        if group:
            blocks.append(_block(doc_id,kind,f'lines-{start}-{end}','\n'.join(group),group_type,line_start=start,line_end=end,heading_path=headings.copy()))
        start=None;group=[];group_type='text'
    for n,line in enumerate(lines,1):
        marker=re.match(r'^\s{0,3}(`{3,}|~{3,})(.*)$',line) if kind=='md' else None
        if fence:
            group.append(line)
            if marker and marker[1][0]==fence[0] and len(marker[1])>=len(fence) and not marker[2].strip():
                fence=None;flush(n)
            continue
        if marker:
            flush(n-1);start=n;group=[line];fence=marker[1];group_type='code';continue
        heading=re.match(r'^(#{1,6})\s+(.+)$',line) if kind=='md' else None
        if heading:
            flush(n-1);headings=headings[:len(heading[1])-1]+[heading[2].rstrip('# ').strip()]
            start=n;group=[line];group_type='title';flush(n);continue
        if not line.strip():flush(n-1);continue
        if start is None:start=n
        group.append(line)
    flush(len(lines))
    report['structure']={'physical_lines':len(lines)}
    if fence:report['warnings'].append({'code':'unclosed_fence','message':'Markdown代码围栏未关闭，保留到文件结尾，没有静默丢弃。'})
    if kind=='md':report['warnings'].append({'code':'markdown_source_only','message':'保留Markdown源文本及行号；不读取外链图片，复杂HTML嵌入和视觉语义需另行核对。'})
    return blocks


def _html(doc_id,path,report):
    from lxml import html,etree
    root=html.fromstring(path.read_bytes(),parser=html.HTMLParser(encoding='utf-8',no_network=True,remove_comments=True))
    for node in root.xpath('//script|//style|//head'):node.drop_tree()
    tree=root.getroottree();blocks=[];headings=[]
    id_counts={}
    for node in root.xpath('//*[@id]'):id_counts[node.get('id')]=id_counts.get(node.get('id'),0)+1
    for node in root.iter():
        if node.tag not in {'h1','h2','h3','h4','h5','h6','p','li','table','pre','nav'}:continue
        if any(a.tag in {'table','pre','li','nav'} for a in node.iterancestors()):continue
        text_node=deepcopy(node)
        for br in text_node.xpath('.//br'):
            br.tail='\n'+(br.tail or '');br.drop_tag()
        text=text_node.text_content().strip()
        if not text:continue
        if node.tag.startswith('h'):
            level=int(node.tag[1]);headings=headings[:level-1]+[text]
        anchor=next((a.get('id') for a in [node,*node.iterancestors()] if a.get('id') and id_counts[a.get('id')]==1),None)
        locator={'xpath':tree.getpath(node),'heading_path':headings.copy()}
        if anchor:locator['html_anchor']=anchor
        if node.sourceline:locator['source_line_hint']=node.sourceline
        block_type='navigation' if node.tag=='nav' else 'table' if node.tag=='table' else 'code' if node.tag=='pre' else 'title' if node.tag.startswith('h') else 'text'
        content=etree.tostring(node,encoding='unicode',method='html',with_tail=False) if node.tag=='table' else text
        blocks.append(_block(doc_id,'html',f'element-{len(blocks)+1}',content,block_type,**locator))
    report['structure']={'structural_blocks':len(blocks)}
    report['warnings'].append({'code':'html_static_only','message':'读取静态段落、列表、表格与标题；不执行JavaScript、不访问外链，也不保证覆盖CSS生成或动态加载内容。source_line_hint只是元素起始行提示。'})
    return blocks


def _pptx(doc_id,path,report):
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE_TYPE
    prs=Presentation(path);blocks=[];unsupported=[]
    def walk(shapes,slide_number,parents=()):
        for shape in shapes:
            shape_path=(*parents,shape.shape_id)
            if shape.shape_type==MSO_SHAPE_TYPE.GROUP:walk(shape.shapes,slide_number,shape_path);continue
            locator={'slide':slide_number,'shape_id':shape.shape_id,'shape_path':list(shape_path),
                     'coordinate_system':'office_emu','position':[shape.left,shape.top,shape.width,shape.height],
                     'coordinate_scope':'group_child' if parents else 'slide'}
            if shape.has_table:
                rows=[]
                for row in shape.table.rows:
                    cells=[]
                    for cell in row.cells:
                        if cell.is_spanned:continue
                        cells.append(f'<td rowspan="{cell.span_height}" colspan="{cell.span_width}">{escape(cell.text)}</td>')
                    rows.append('<tr>'+''.join(cells)+'</tr>')
                text='<table>\n'+'\n'.join(rows)+'\n</table>';kind='table'
            elif shape.has_text_frame:text=shape.text;kind='text'
            else:
                unsupported.append({'slide':slide_number,'shape_id':shape.shape_id,'shape_type':str(shape.shape_type)});continue
            if text.strip():blocks.append(_block(doc_id,'pptx',f'slide-{slide_number}-shape-'+'.'.join(map(str,shape_path)),text,kind,**locator))
    for i,slide in enumerate(prs.slides,1):walk(slide.shapes,i)
    report['structure']={'slides':len(prs.slides),'width_emu':prs.slide_width,'height_emu':prs.slide_height,'nontext_shapes':unsupported}
    report['warnings'].append({'code':'pptx_text_shapes_only','message':'读取原生文本和表格，不把形状存储顺序当视觉阅读顺序；图片、图表、备注需DocMind或另外核查。组内坐标未变换到整页。'})
    return blocks


def inspect_source(doc_id,path):
    path=Path(path);suffix=path.suffix.lower()
    kinds={'.docx':'docx','.xlsx':'xlsx','.xlsm':'xlsx','.pptx':'pptx','.csv':'csv','.md':'md','.txt':'txt','.html':'html','.htm':'html','.pdf':'pdf','.png':'image','.jpg':'image','.jpeg':'image','.bmp':'image'}
    if suffix not in kinds:raise ValueError('该扩展名暂不支持原生结构核对，请使用DocMind并保留块级定位')
    kind=kinds[suffix];report={'doc_id':doc_id,'kind':kind,'source_sha256':sha256(path.read_bytes()).hexdigest(),'role':'source_audit','replaces_docmind':False,'blocks':[],'structure':{},'warnings':[]}
    if kind=='docx':blocks=_docx(doc_id,path,report)
    elif kind=='xlsx':blocks=_xlsx(doc_id,path,report)
    elif kind=='pptx':blocks=_pptx(doc_id,path,report)
    elif kind in {'md','txt'}:blocks=_text(doc_id,path,kind,report)
    elif kind=='html':blocks=_html(doc_id,path,report)
    elif kind=='csv':
        blocks=read_csv_blocks(doc_id,path)
        for b in blocks:b['metadata']['role']='source_audit'
        report['structure']={'records':len(blocks)}
    elif kind=='pdf':
        from pypdf import PdfReader
        pdf=PdfReader(path)
        if pdf.is_encrypted:raise ValueError('PDF已加密，请使用具有授权的未加密副本')
        report['structure']={'page_count':len(pdf.pages),'pages':[{'page':i,'width_points':float(p.mediabox.width),'height_points':float(p.mediabox.height),'rotation':p.rotation} for i,p in enumerate(pdf.pages,1)]};blocks=[]
        report['warnings'].append({'code':'docmind_required','message':'这里只读取PDF页数和尺寸，不做OCR。文字、图表与布局仍来自DocMind，并需对照原文。'})
    else:
        from PIL import Image
        with Image.open(path) as img:report['structure']={'width_pixels':img.width,'height_pixels':img.height,'format':img.format}
        blocks=[];report['warnings'].append({'code':'docmind_required','message':'这里只读取图片尺寸，不做OCR。区域坐标必须声明坐标系后才可展示。'})
    report['blocks']=blocks
    return report


def reconcile_blocks(parsed_blocks,source_report):
    """保守核对文本；唯一相等也只是候选位置，报告不修改原解析块。"""
    def normalized(text):return ' '.join(str(text).split())
    lookup={}
    for block in source_report['blocks']:
        key=normalized(block['text'])
        if key:lookup.setdefault(key,[]).append(block['locator'])
    results=[]
    for block in parsed_blocks:
        matches=lookup.get(normalized(block['text']),[])
        results.append({'parsed_block_id':block['locator']['block_id'],'status':'unique_exact' if len(matches)==1 else 'ambiguous' if matches else 'unmatched','matches':deepcopy(matches)})
    return results

