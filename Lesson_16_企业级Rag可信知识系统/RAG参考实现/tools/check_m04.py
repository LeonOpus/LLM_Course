"""检查规格文件的完整性与追踪关系；不证明业务语义或应用已经实现。"""
from pathlib import Path
import json,sys
# revision: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# revision: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# cache: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# generated: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# revision: lpf2-18283 lpf2-19E2b
ROOT=Path(__file__).resolve().parents[1]
def check(root):
    errors=[];specs=root/'specs'
    for name in ('requirements.md','architecture.md','api-contract.md'):
        p=specs/name
        if not p.exists() or len(p.read_text(encoding='utf-8').strip())<100:errors.append(f'{name}缺少内容')
    objects={}
    for name in ('acceptance.json','tasks.json'):
        try:objects[name]=json.loads((specs/name).read_text(encoding='utf-8'))
        except (OSError,json.JSONDecodeError) as e:errors.append(f'{name}无法读取为JSON：{type(e).__name__}')
    acceptance=objects.get('acceptance.json',{});cases=acceptance.get('cases',[]) if isinstance(acceptance,dict) else []
    if not isinstance(cases,list):cases=[];errors.append('cases必须是列表')
    found=[]
    for case in cases:
        if not isinstance(case,dict):errors.append('每条验收必须是对象');continue
        if isinstance(case.get('id'),str):found.append(case['id'])
        for key in ('id','stage','given','when','then','test_kind'):
            if not isinstance(case.get(key),str) or not case[key].strip():errors.append(f'{case.get("id")}缺少{key}')
        if case.get('status')!='pending':errors.append(f'{case.get("id")}尚未开发，status应为pending')
        if case.get('test_kind') not in ('unit','integration_fixture','integration_live','browser','evaluation'):errors.append(f'{case.get("id")}的test_kind不合法')
    required={f'AC-{n:02d}' for n in range(1,13)}
    if not required<=set(found):errors.append('至少保留AC-01至AC-12；不能删除难做的验收')
    if len(found)!=len(set(found)):errors.append('验收ID重复')
    tasks=objects.get('tasks.json',{});tasks=tasks.get('tasks',[]) if isinstance(tasks,dict) else []
    if not isinstance(tasks,list):tasks=[];errors.append('tasks必须是列表')
    task_ids=[t['id'] for t in tasks if isinstance(t,dict) and isinstance(t.get('id'),str)]
    if not tasks:errors.append('任务列表不能为空')
    if len(task_ids)!=len(tasks) or any(not i for i in task_ids) or len(task_ids)!=len(set(task_ids)):errors.append('任务ID缺失或重复')
    linked=set()
    for task in tasks:
        if not isinstance(task,dict):errors.append('每项任务必须是对象');continue
        if not isinstance(task.get('title'),str) or not task['title'].strip():errors.append('任务缺少title')
        if task.get('status')!='pending':errors.append('任务应保持pending')
        refs=task.get('acceptance_ids');deps=task.get('depends_on')
        if not isinstance(refs,list) or not refs or any(r not in found for r in refs):errors.append(f'{task.get("id")}的验收引用无效')
        else:linked.update(refs)
        if not isinstance(deps,list) or any(d not in task_ids or d==task.get('id') for d in deps):errors.append(f'{task.get("id")}的依赖无效')
    if not required<=linked:errors.append('有必要验收项没有安排实现任务')
    if not errors:
        graph={t['id']:t['depends_on'] for t in tasks};active=set();done=set()
        def visit(k):
            if k in active:raise ValueError('任务依赖存在循环')
            if k in done:return
            active.add(k)
            for dep in graph[k]:visit(dep)
            active.remove(k);done.add(k)
        try:
            for k in graph:visit(k)
        except ValueError as e:errors.append(str(e))
    return {'status':'failed' if errors else 'passed','scope':'spec_structure_and_traceability_only','application_implemented':False,'cases':len(cases),'tasks':len(tasks),'errors':errors}
if __name__=='__main__':
    report=check(ROOT);print(json.dumps(report,ensure_ascii=False,indent=2));sys.exit(1 if report['errors'] else 0)
