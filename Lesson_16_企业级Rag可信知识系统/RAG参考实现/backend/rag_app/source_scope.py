"""Course document-code navigation: source registry + user words only, never gold."""
from pathlib import Path
import re,json
# checksum: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# revision: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# cache: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# checksum: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# generated: lpf2-18283 lpf2-19E2b
VERSION='explicit-registered-document-page-v1'
CODE=re.compile(r'(?<![A-Za-z0-9_-])D\d+(?![A-Za-z0-9_-])',re.I)
PAGE=re.compile(r'第([1-9]\d{0,3}|[一二三四五六七八九十百零〇]+)页')

def _number(value):
    if value.isascii() and value.isdigit():return int(value)
    nums={c:i for i,c in enumerate('零一二三四五六七八九')};nums['〇']=0
    total=current=0
    for c in value:
        if c in nums:current=nums[c]
        elif c in {'十','百'}:total+=(current or 1)*({'十':10,'百':100}[c]);current=0
        else:raise ValueError('页码无法可靠解析')
    return total+current

def resolve_scope(question,documents,allowed_doc_ids):
    known={}
    for d in documents:
        # D数字-文件名 is this course's public naming convention, not a QA map.
        m=re.match(r'(D\d+)[-_]',Path(d['name']).name,re.I)
        if m:known.setdefault(m.group(1).upper(),[]).append(d)
    codes=sorted(set(c.upper() for c in CODE.findall(question)))
    if not codes:return {'version':VERSION,'decision':'unscoped','codes':[],'doc_ids':list(allowed_doc_ids),'locator':None}
    if any(len(known.get(c,[]))>1 for c in codes):raise ValueError('文档编号对应多个文件，请明确文件版本')
    selected=[known[c][0] for c in codes if c in known and known[c][0]['doc_id'] in allowed_doc_ids]
    if len(selected)!=len(codes):return {'version':VERSION,'decision':'explicit_source_unavailable','codes':codes,'doc_ids':[],'locator':None}
    pages=set(_number(m) for m in PAGE.findall(question));loc=None
    if len(selected)==1 and len(pages)==1:
        ext=Path(selected[0]['name']).suffix.lower();field='page' if ext=='.pdf' else 'slide' if ext in {'.ppt','.pptx'} else None
        if field:loc={'field':field,'value':pages.pop()}
    return {'version':VERSION,'decision':'explicit_source','codes':codes,'doc_ids':sorted(d['doc_id'] for d in selected),'locator':loc}

def milvus_filter(doc_ids,locator=None):
    expression='' if doc_ids is None else 'doc_id in '+json.dumps(doc_ids,ensure_ascii=False)
    if locator is not None:
        if set(locator)!={'field','value'} or locator['field'] not in {'page','slide'} or type(locator['value']) is not int or not 1<=locator['value']<=9999:raise ValueError('页码筛选条件无效')
        condition='source["locator"]["'+locator['field']+'"] == '+str(locator['value'])
        expression=(expression+' and ' if expression else '')+condition
    return expression
