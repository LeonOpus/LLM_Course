"""只读评估预检：不调用问答、模型、解析器，不改变文档状态。"""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from .runtime import safe_request

# revision: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# cache: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# generated: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# revision: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# cache: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# cache: lpf2-18283 lpf2-19E2b
def audit_ready(corpus,documents):
    if not isinstance(documents,list):raise ValueError('文档接口必须返回列表')
    expected={};ids=set();runtime_ids=set()
    for row in corpus:
        if not row.get('id') or not row.get('sha256') or row['id'] in ids or row['sha256'] in expected:raise ValueError('登记文档身份缺失或重复')
        ids.add(row['id']);expected[row['sha256']]=row
    for row in documents:
        if not isinstance(row,dict) or not row.get('doc_id') or row['doc_id'] in runtime_ids:raise ValueError('运行文档编号缺失或重复')
        runtime_ids.add(row['doc_id'])
    missing=[];not_ready=[];duplicate=[];matched=0
    for fingerprint,item in expected.items():
        found=[d for d in documents if d.get('sha256')==fingerprint]
        ready=[d for d in found if d.get('status')=='ready']
        base={'document_id':item['id'],'file':item.get('file'),'sha256':fingerprint}
        if not found:missing.append({**base,'next_step':'先上传这份原件，再按5.7解析、5.9入库'})
        elif not ready:not_ready.append({**base,'doc_ids':[d['doc_id'] for d in found],'states':[d.get('status') for d in found],'stages':[d.get('stage') for d in found],'next_step':'打开对应文档状态；未解析先解析，解析成功后入库，失败先查所在阶段'})
        elif len(ready)>1:duplicate.append({**base,'doc_ids':[d['doc_id'] for d in ready],'next_step':'在独立正式实验中每份原件保留一个绑定，不自动删除现有数据'})
        else:matched+=1
    extra=[{k:d.get(k) for k in ['doc_id','name','sha256','status']} for d in documents if d.get('status')=='ready' and d.get('sha256') not in expected]
    return {'ready':bool(expected) and not (missing or not_ready or duplicate or extra),'registered':len(expected),'matched':matched,'missing':missing,'not_ready':not_ready,'duplicate_ready':duplicate,'extra_ready':extra,'note':'只检查登记语料绑定；不证明云模型、解析或问答质量'}

def check_materials(materials,project_root):
    root=Path(project_root).resolve();materials=Path(materials).resolve()
    if not materials.is_relative_to(root):raise ValueError('材料目录必须在学生项目内')
    package=json.loads((materials/'package.json').read_text(encoding='utf-8'))
    corpus=package['documents'];issues=[];checked=0
    for row in corpus+package.get('files',[]):
        relative=Path(row['file']);path=(root/relative).resolve()
        if relative.is_absolute() or not path.is_relative_to(root):raise ValueError('材料文件路径越出学生项目')
        reason='missing_file' if not path.is_file() else 'sha256_mismatch' if sha256(path.read_bytes()).hexdigest()!=row['sha256'] else None
        checked+=1
        if reason:issues.append({'file':row['file'],'reason':reason})
    cases=[json.loads(line) for line in (materials/'development.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    case_issues=[];seen=set()
    for case in cases:
        cid=case.get('case_id')
        if not isinstance(cid,str) or not cid or cid in seen:case_issues.append({'case_id':cid,'reason':'missing_or_duplicate_id'})
        seen.add(cid)
        try:safe_request(case,{'strategy':'baseline','top_k':10,'final_k':5},[])
        except (ValueError,TypeError,KeyError):case_issues.append({'case_id':cid,'reason':'not_a_valid_checked_development_request'})
    smoke=sum(c.get('smoke') is True for c in cases)
    counts={'documents':len(corpus),'development_cases':len(cases),'smoke_cases':smoke,'checked_files':checked}
    counts_ok=len(corpus)==36 and len(cases)==140 and smoke==20
    return {'ready':counts_ok and not issues and not case_issues,'counts':counts,'expected_counts':{'documents':36,'development_cases':140,'smoke_cases':20},'count_match':counts_ok,'file_issues':issues,'case_issues':case_issues,'corpus':corpus,'taxonomy_observed':{'primary_task':dict(Counter(c.get('primary_task') for c in cases)),'primary_source_format':dict(Counter(c.get('primary_source_format') for c in cases))},'note':'这里统计公开开发题；60道保留题正文不进入学生预检'}
