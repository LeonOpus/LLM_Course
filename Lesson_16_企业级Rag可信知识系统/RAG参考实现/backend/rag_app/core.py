"""不依赖云服务的业务逻辑。字符区间为左闭右开，来源页码从 1 开始。"""
from copy import deepcopy
from hashlib import sha256
import math

# revision: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# cache: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# cache: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# checksum: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# revision: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# revision: lpf2-18283 lpf2-19E2b
KINDS = {'pdf','docx','xlsx','pptx','image','html','md','txt','csv'}

def _positive_int(value):
    return type(value) is int and value >= 1

def validate_locator(locator):
    if not isinstance(locator, dict):
        raise ValueError('来源定位必须是字典')
    kind=locator.get('kind')
    if kind not in KINDS or not isinstance(locator.get('block_id'),str) or not locator['block_id'].strip():
        raise ValueError('来源类型不支持或 block_id 为空')
    if kind=='pdf' and not _positive_int(locator.get('page')):
        raise ValueError('PDF 页码必须是从 1 开始的整数')
    if kind!='pdf' and locator.get('page') is not None:
        raise ValueError('非 PDF 来源不能伪造 PDF 页码')
    if kind=='pptx' and not _positive_int(locator.get('slide')):
        raise ValueError('PPT 页号必须是从 1 开始的整数')
    if locator.get('cell_range') and not locator.get('sheet'):
        raise ValueError('单元格定位必须同时提供工作表')
    if 'line_start' in locator or 'line_end' in locator:
        start,end=locator.get('line_start'),locator.get('line_end')
        if not _positive_int(start) or not _positive_int(end) or end<start:
            raise ValueError('文本行范围必须从 1 开始且结束不小于开始')
    return deepcopy(locator)

def transition(current, target):
    allowed={'uploaded':{'parsing','failed'},'parsing':{'parsed','failed'},
             'parsed':{'indexing','failed'},'indexing':{'ready','failed'},
             'failed':{'parsing','indexing'},'ready':set()}
    if target not in allowed.get(current,set()):
        raise ValueError(f'不允许状态跳转：{current} → {target}')
    return target

def chunk_blocks(blocks, window=600, overlap=100, preserve_tables=False, table_limit=12000):
    if type(window) is not int or window<=0 or type(overlap) is not int or not 0<=overlap<window:
        raise ValueError('切块窗口必须为正整数，且 0 <= overlap < window')
    if type(table_limit) is not int or table_limit<=0:
        raise ValueError('表格长度上限必须为正整数')
    chunks=[]
    for block in blocks:
        locator=validate_locator(block['locator'])
        text=block['text']
        if not isinstance(text,str): raise ValueError('解析块正文必须是字符串')
        if not text.strip(): continue
        size=window
        if preserve_tables and block.get('type')=='table':
            if len(text)>table_limit: raise ValueError('表格超过上限：请先按行分组并保留表头，不能截断')
            size=len(text)
        start=0
        while start<len(text):
            end=min(start+size,len(text))
            body=text[start:end]
            identity=f"{block['doc_id']}\0{locator['block_id']}\0{start}\0{end}\0{body}"
            chunks.append({'chunk_id':sha256(identity.encode()).hexdigest()[:32],
                           'doc_id':block['doc_id'],'text':body,'type':block.get('type','paragraph'),
                           'locator':deepcopy(locator),'char_range':[start,end],
                           'metadata':deepcopy(block.get('metadata',{}))})
            if end==len(text): break
            start=end-overlap
    return chunks


def apply_rerank(candidates, results):
    seen=set();out=[]
    for row in results:
        i=row.get('index');score=row.get('relevance_score')
        if type(i) is not int or not 0<=i<len(candidates) or i in seen:
            raise ValueError('重排返回了重复或越界的候选索引')
        if type(score) not in (float,int) or not math.isfinite(score):
            raise ValueError('重排分数不是有限数值')
        seen.add(i)
        out.append({**deepcopy(candidates[i]),'rerank_score':float(score)})
    return out

