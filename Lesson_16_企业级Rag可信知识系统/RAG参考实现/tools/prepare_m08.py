"""只把M08依赖、测试和规格放入学生materials；不写业务代码。"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path

# generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# cache: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# cache: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# generated: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# generated: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# cache: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# generated: lpf2-18283 lpf2-19E2b
ROOT=Path(__file__).resolve().parents[1]

def plan_files():
    source=ROOT/'practice/m08/complete'
    plan={}
    for name in ['pyproject.toml','uv.lock']:
        plan[f'backend-dependencies/{name}']=(source/'backend'/name).read_bytes()
    for p in sorted((source/'backend/tests').glob('*.py')):
        plan[f'backend-tests/{p.name}']=p.read_bytes()
    for p in sorted((source/'frontend/tests').glob('*.mjs')):
        plan[f'frontend-tests/{p.name}']=p.read_bytes()
    plan['M08-spec.md']=(ROOT/'specs/M08-多格式与来源核对.md').read_bytes()
    preview=(ROOT/'corpus/previews/D26/slide-05.png').read_bytes()
    metadata=(ROOT/'corpus/previews/D26/slide-05-source.json').read_bytes()
    provenance=json.loads(metadata)
    if sha256(preview).hexdigest()!=provenance['preview_sha256']:
        raise ValueError('D26预览图指纹改变，请先核对渲染版本')
    if sha256((ROOT/provenance['source_file']).read_bytes()).hexdigest()!=provenance['source_sha256']:
        raise ValueError('D26原PPT指纹改变，不能继续分发旧预览图')
    plan['previews/D26-slide-05.png']=preview
    plan['previews/D26-slide-05-source.json']=metadata
    return plan

def prepare(student):
    student=Path(student).resolve()
    if student==ROOT or ROOT in student.parents: raise ValueError('请使用教师包以外的独立学生项目')
    if not (student/'materials/materials-index.json').is_file(): raise ValueError('未找到M04学生材料索引；先按5.4创建学生目录')
    target=student/'materials/m08';files=plan_files()
    # 全量预检先于写入：修改过的材料不会被静默覆盖。
    for rel,data in files.items():
        path=target/rel
        if not path.resolve().is_relative_to(student): raise ValueError('材料路径通过链接离开学生目录')
        for parent in path.parents:
            if parent==student: break
            if parent.exists() and not parent.is_dir():
                raise ValueError(f'材料目录位置已有文件，未写入任何材料：{parent.relative_to(student)}')
        if path.exists() and (not path.is_file() or path.read_bytes()!=data):
            raise ValueError(f'已有不同内容，未写入任何材料：materials/m08/{rel}')
    for rel,data in files.items():
        path=target/rel;path.parent.mkdir(parents=True,exist_ok=True)
        if not path.exists(): path.write_bytes(data)
    return {'status':'prepared','files':len(files),'destination':str(target),'business_code_written':False,
            'sha256':{rel:sha256(data).hexdigest() for rel,data in files.items()}}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--student',required=True);args=parser.parse_args()
    try: print(json.dumps(prepare(args.student),ensure_ascii=False,indent=2))
    except ValueError as e: parser.exit(1,f'{e}\n')
