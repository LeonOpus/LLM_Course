"""M06 材料验收；仅用 Python 标准库，不调用模型，不计算 RAG 得分。"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path, PurePosixPath

# cache: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# revision: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# generated: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# revision: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# generated: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# checksum: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# checksum: lpf2-18283 lpf2-19E2b
DEFAULT_REQUIREMENTS = {
    'documents': 36,
    'formats': {'pdf': 16, 'docx': 5, 'xlsx': 4, 'pptx': 3, 'html': 2,
                'markdown': 2, 'txt': 1, 'csv': 1, 'image': 2},
    'pdf_pages_min': 180, 'pdf_pages_max': 240,
    'cases': 200, 'development': 140, 'holdout': 60, 'smoke': 20, 'variants': 6,
    'tasks': {k: {'development': d, 'holdout': h} for k, d, h in [
        ('T01', 21, 9), ('T02', 18, 7), ('T03', 21, 9), ('T04', 14, 6),
        ('T05', 14, 6), ('T06', 14, 6), ('T07', 14, 6), ('T08', 10, 5),
        ('T09', 8, 4), ('T10', 6, 2)]},
    'case_formats': {'pdf': 90, 'docx': 30, 'xlsx': 25, 'pptx': 20,
                     'html': 10, 'markdown': 10, 'txt': 5, 'csv': 5, 'image': 5},
}
EXTENSIONS = {'pdf': {'.pdf'}, 'docx': {'.docx'}, 'xlsx': {'.xlsx'},
              'pptx': {'.pptx'}, 'html': {'.html', '.htm'},
              'markdown': {'.md'}, 'txt': {'.txt'}, 'csv': {'.csv'},
              'image': {'.png', '.jpg', '.jpeg', '.webp'}}
QUESTION_FIELDS = {'case_id', 'question', 'conversation_history'}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def question_hash(row):
    return sha(json.dumps({k: row[k] for k in QUESTION_FIELDS},
                          ensure_ascii=False, sort_keys=True).encode('utf-8'))

def canonical_hash(value):
    return sha(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8'))

def make_smoke_freeze(cases):
    """Freeze reviewed teaching cases, not model results; also works on student development rows."""
    if not isinstance(cases,list) or any(not isinstance(c,dict) for c in cases):raise ValueError('题集必须为对象列表')
    ids=[c.get('case_id') for c in cases]
    if any(not isinstance(i,str) or not i for i in ids) or len(ids)!=len(set(ids)):raise ValueError('题号缺失或重复')
    if any(type(c.get('smoke')) is not bool or c.get('split') not in {'development','holdout'} for c in cases):raise ValueError('smoke或split无效')
    if any(c['smoke'] and c['split']!='development' for c in cases):raise ValueError('保留题不能进入冒烟集')
    dev=[c for c in cases if c['split']=='development'];selected=[c for c in dev if c['smoke']]
    if len(dev)!=140 or len(selected)!=20:raise ValueError('冻结要求140开发题与20冒烟题')
    fields=['primary_task','primary_source_format','expected_behavior']
    coverage={key:dict(sorted(Counter(c.get(key) for c in selected).items())) for key in fields}
    if (set(coverage['primary_task'])!=set(DEFAULT_REQUIREMENTS['tasks']) or
        set(coverage['primary_source_format'])!=set(EXTENSIONS) or
        set(coverage['expected_behavior'])!={'answer','calculate_with_evidence','refuse_insufficient_evidence','ask_clarification'}):
        raise ValueError('冒烟覆盖不足：要求10主任务、9格式、4行为')
    for c in selected:
        if not isinstance(c.get('layout_challenges'),list) or not isinstance(c.get('conversation_history'),list):raise ValueError('版式或历史类型无效')
    coverage['layout_challenges']=dict(sorted(Counter(t for c in selected for t in c['layout_challenges']).items()))
    if not {'scan','cross_page_table'}<=set(coverage['layout_challenges']):raise ValueError('冒烟版式覆盖缺扫描或跨页表')
    visual={c['primary_source_format'] for c in selected if c['primary_task']=='T04'}
    if not {'pdf','pptx','image'}<=visual:raise ValueError('视觉覆盖缺PDF/PPT/独立图片')
    coverage['with_history']=sum(bool(c['conversation_history']) and 'conversation_reference' in c.get('query_styles',[]) for c in selected)
    if not coverage['with_history']:raise ValueError('缺少有真实历史的指代题')
    if any(c.get('review_status') not in {'source_checked_by_author','independently_reviewed'} for c in selected):raise ValueError('题目尚未完成来源核查')
    frozen={'schema_version':'smoke-freeze/1','policy_version':'m06b-coverage-v1','status':'frozen_before_live_baseline',
            'case_ids':[c['case_id'] for c in selected],'development_sha256':canonical_hash(dev),
            'smoke_sha256':canonical_hash(selected),'coverage':coverage,
            'scope':'教学冒烟覆盖冻结；不代表模型质量或200题全部版式覆盖'}
    frozen['freeze_sha256']=canonical_hash(frozen)
    return frozen

def verify_smoke_freeze(cases,frozen):
    if not isinstance(frozen,dict) or frozen!=make_smoke_freeze(cases):raise ValueError('冒烟冻结与当前题干、标签、成员或覆盖不一致')
    return 'frozen_verified'

def safe_path(root, relative):
    """拒绝目录穿越、绝对路径及任意一层符号链接，包括尚未创建的目标。"""
    if not isinstance(relative, str) or '\\' in relative:
        raise ValueError('路径必须是使用 / 的相对路径')
    parts = PurePosixPath(relative)
    if parts.is_absolute() or '..' in parts.parts or not parts.parts or ':' in relative:
        raise ValueError('路径不在材料目录内：' + relative)
    current = Path(root)
    for part in parts.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError('不接受符号链接：' + relative)
    if not current.resolve().is_relative_to(Path(root).resolve()):
        raise ValueError('路径超出学生目录：' + relative)
    return current

def audit(root, requirements=None):
    root = Path(root).resolve()
    req = DEFAULT_REQUIREMENTS if requirements is None else requirements
    errors, counts = [], {}
    def fail(message):
        errors.append(message)
    def read_json(relative, lines=False):
        try:
            text = safe_path(root, relative).read_text(encoding='utf-8')
            return [json.loads(line) for line in text.splitlines() if line.strip()] if lines else json.loads(text)
        except (OSError, ValueError) as exc:
            fail(f'无法读取 {relative}：{exc}')
            return [] if lines else {}
    def verify(entry):
        try:
            p = safe_path(root, entry['file'])
            if not p.is_file():
                raise ValueError('缺少文件')
            if sha(p.read_bytes()) != entry['sha256']:
                raise ValueError('文件指纹不一致；文件被修改或材料版本不一致')
            return True
        except (OSError, ValueError, KeyError, TypeError) as exc:
            fail(f"{entry.get('file', '?')}：{exc}")
            return False
    def equal(label, actual, target):
        if actual != target:
            fail(f'{label}：实际 {actual}，要求 {target}')
    package = read_json('materials/m06/package.json')
    if not isinstance(package, dict) or package.get('schema_version') != '1.0':
        fail('材料清单缺失或 schema_version 不支持')
        package = {}
    docs, variants, files = (package.get(k, []) for k in ('documents', 'variants', 'files'))
    if not all(isinstance(x, list) and all(isinstance(y, dict) for y in x) for x in (docs, variants, files)):
        fail('documents / variants / files 必须是对象列表')
        docs, variants, files = [], [], []
    listed, doc_ids, valid_docs, valid_variants = set(), set(), [], []
    for entries, directory, accepted in ((docs, 'documents', valid_docs), (variants, 'variants', valid_variants)):
        for row in entries:
            did, name = row.get('id'), row.get('file', '')
            if not all(isinstance(row.get(k), str) for k in ('id', 'file', 'format', 'sha256')):
                fail('文档 ID、路径、格式和指纹必须是字符串'); continue
            if not did or did in doc_ids:
                fail('文档 ID 缺失或重复：' + str(did))
            doc_ids.add(did)
            if name in listed:
                fail('清单路径重复：' + name)
            listed.add(name)
            if not name.startswith(f'materials/corpus/{directory}/'):
                fail('业务文件必须位于指定目录：' + name)
            if Path(name).suffix.lower() not in EXTENSIONS.get(row.get('format'), set()):
                fail('格式标签与扩展名不符：' + name)
            if verify(row):
                accepted.append(row)
    # Documents and degradation variants are separate. Neither directory may hide labels.
    for directory in ('documents', 'variants'):
        try:
            folder = safe_path(root, 'materials/corpus/' + directory)
            if folder.exists():
                for path in folder.rglob('*'):
                    if path.is_symlink() or (path.is_file() and path.relative_to(root).as_posix() not in listed):
                        fail('业务目录中有未登记文件或链接：' + path.relative_to(root).as_posix())
        except (OSError, ValueError) as exc:
            fail(str(exc))
    verified_files = set()
    allowed_metadata = {'materials/m06/' + name for name in (
        'development.jsonl', 'smoke-questions.jsonl', 'assignment-index.json', 'taxonomy.json','smoke-freeze.json')}
    try:
        folder = safe_path(root, 'materials/m06')
        for path in folder.rglob('*'):
            rel = path.relative_to(root).as_posix()
            if path.is_symlink() or (path.is_file() and rel not in allowed_metadata | {'materials/m06/package.json'}):
                fail('M06 目录有未允许的文件或链接：' + rel)
    except (OSError, ValueError) as exc:
        fail(str(exc))
    for entry in files:
        name = entry.get('file', '')
        if not isinstance(name, str):
            fail('评估文件路径必须是字符串'); continue
        if name not in allowed_metadata:
            fail('评估清单包含越界文件：' + name)
        if name in verified_files:
            fail('评估文件路径重复：' + name)
        if verify(entry):
            verified_files.add(name)
    names = ['development.jsonl', 'smoke-questions.jsonl', 'assignment-index.json']
    for name in names:
        if 'materials/m06/' + name not in verified_files:
            fail('评估文件未登记或未通过指纹检查：' + name)
    dev = read_json('materials/m06/development.jsonl', True)
    smoke = read_json('materials/m06/smoke-questions.jsonl', True)
    assignments = read_json('materials/m06/assignment-index.json')
    if not isinstance(assignments, list):
        fail('assignment-index.json 必须是列表')
        assignments = []
    valid_assignments = []
    for row in assignments:
        if not isinstance(row, dict) or not all(k in row for k in [
            'case_id', 'split', 'smoke', 'primary_task', 'primary_source_format',
            'question_hash', 'canonical_fact_hashes', 'family_hashes']):
            fail('评估分配表字段不完整')
            continue
        if not all(isinstance(row[k], str) and row[k] for k in (
            'case_id', 'split', 'primary_task', 'primary_source_format', 'question_hash')):
            fail('评估题号、分类及指纹必须是非空字符串'); continue
        if row['split'] not in {'development', 'holdout'}:
            fail('未知 split：' + str(row['case_id']))
        if row['primary_task'] not in req['tasks'] or row['primary_source_format'] not in EXTENSIONS:
            fail('评估分类未知：' + str(row['case_id']))
        if type(row['smoke']) is not bool or (row['smoke'] and row['split'] != 'development'):
            fail('冒烟题必须属于开发集：' + str(row['case_id']))
        for key in ['canonical_fact_hashes', 'family_hashes']:
            if not isinstance(row[key], list) or not row[key] or not all(isinstance(x, str) and x for x in row[key]):
                fail('事实/事实族指纹必须为非空字符串列表：' + str(row['case_id']))
                row = {**row, key: []}
        valid_assignments.append(row)
    amap = {r['case_id']: r for r in valid_assignments}
    equal('唯一题号', len(amap), len(valid_assignments))
    for key, label in [('canonical_fact_hashes', '同一事实'), ('family_hashes', '同一事实族')]:
        splits = defaultdict(set)
        for row in valid_assignments:
            for value in row[key]:
                splits[value].add(row['split'])
        if any(len(values) > 1 for values in splits.values()):
            fail(label + '同时进入开发集与保留集，需重新分配题目')
    hashes = [r['question_hash'] for r in valid_assignments]
    if len(hashes) != len(set(hashes)):
        fail('分配表有重复问题指纹')
    for rows, label, expected in [
        (dev, '开发集', {r['case_id'] for r in valid_assignments if r['split'] == 'development'}),
        (smoke, '冒烟问题导出', {r['case_id'] for r in valid_assignments if r['smoke']})]:
        ids = []
        for row in rows:
            if not isinstance(row, dict):
                fail(label + '存在非对象记录'); continue
            cid = row.get('case_id')
            if not isinstance(cid, str) or not cid:
                fail(label + '题号必须是非空字符串'); continue
            ids.append(cid)
            if label == '冒烟问题导出' and set(row) != QUESTION_FIELDS:
                fail('冒烟问题导出只能包含题号、问题和对话历史，不能包含标准答案')
            if label == '开发集' and row.get('split') != 'development':
                fail('开发集文件混入保留集或 split 缺失：' + str(cid))
            if cid not in expected:
                fail(label + '包含不应出现的题号：' + str(cid))
            if not QUESTION_FIELDS.issubset(row):
                fail(label + '问题字段不完整：' + str(cid)); continue
            if not isinstance(row['question'], str) or not isinstance(row['conversation_history'], list):
                fail(label + '问题或历史的类型错误：' + cid); continue
            if cid not in amap or question_hash(row) != amap[cid]['question_hash']:
                fail(label + '问题内容与分配表不一致：' + str(cid))
        if len(ids) != len(set(ids)) or set(ids) != expected:
            fail(label + '有重复、缺失或多余题号')
    formats = Counter(r.get('format') for r in valid_docs)
    pages = 0
    for row in valid_docs:
        if row.get('format') == 'pdf':
            value = row.get('actual_pages')
            if type(value) is not int or value <= 0:
                fail('PDF 页数缺失或无效：' + str(row.get('id')))
            else:
                pages += value
    splits = Counter(r['split'] for r in valid_assignments)
    tasks = {k: {s: sum(r['primary_task'] == k and r['split'] == s for r in valid_assignments)
                 for s in ('development', 'holdout')} for k in req['tasks']}
    case_formats = Counter(r['primary_source_format'] for r in valid_assignments)
    counts.update(documents=len(valid_docs), formats=dict(formats), pdf_pages=pages,
                  variants=len(valid_variants), cases=len(valid_assignments),
                  development=splits['development'], holdout=splits['holdout'],
                  smoke=sum(bool(r['smoke']) for r in valid_assignments),
                  tasks=tasks, case_formats=dict(case_formats))
    for key in ['documents', 'variants', 'cases', 'development', 'holdout', 'smoke']:
        equal(key, counts[key], req[key])
    for key, value in req['formats'].items():
        equal('独立文件格式 ' + key, formats[key], value)
    if not req['pdf_pages_min'] <= pages <= req['pdf_pages_max']:
        fail(f"独立 PDF 页数：实际 {pages}，要求 {req['pdf_pages_min']}–{req['pdf_pages_max']}")
    for task, values in req['tasks'].items():
        for split, target in values.items():
            equal(task + '/' + split, tasks[task][split], target)
    for fmt, target in req.get('case_formats', {}).items():
        equal('主证据格式题数 ' + fmt, case_formats[fmt], target)
    smoke_freeze_status='legacy_not_frozen'
    if package.get('smoke_freeze_required') is True:
        if 'materials/m06/smoke-freeze.json' not in verified_files:fail('新版本缺少已登记的冒烟冻结文件')
        try:smoke_freeze_status=verify_smoke_freeze(dev,read_json('materials/m06/smoke-freeze.json'))
        except (ValueError,TypeError,KeyError):fail('冒烟冻结核对失败：不要改题或降级检查，请重新导入同版本材料')
    return {'schema_version': '1.0', 'stage': 'M06',
            'smoke_freeze_status':smoke_freeze_status,
            'status': 'failed' if errors else 'passed', 'counts': counts, 'errors': errors,
            'limitations': ['只检查登记信息与文件完整性，不验证答案语义，不计算模型准确率。',
                           'PDF 页数来自教师核验清单；本检查器不解析 PDF。',
                           '保留集只检查匿名分配元数据；未读取保留集题目和答案。',
                           '指纹用于检测意外改动，不构成防篡改签名或语义去重证明。']}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    result = audit(args.root)
    try:
        output = safe_path(args.root, 'reports/M06-material-audit.json')
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    except (OSError, ValueError) as exc:
        parser.exit(2, f'无法保存报告：{exc}\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result['status'] == 'passed' else 1)

if __name__ == '__main__':
    main()
