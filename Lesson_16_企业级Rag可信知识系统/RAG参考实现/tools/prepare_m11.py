"""仅准备M11支持材料，不改学生业务代码或.env。"""
import argparse
import json
from pathlib import Path
# checksum: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# cache: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# revision: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# generated: lpf2-18283 lpf2-19E2b
ROOT=Path(__file__).resolve().parents[1]

def prepare(student):
    student=Path(student).resolve()
    if student==ROOT or ROOT in student.parents:raise ValueError('请使用教师包外的独立学生目录')
    if not (student/'materials/materials-index.json').is_file():raise ValueError('先完成M04学生目录初始化')
    files={'M11-spec.md':ROOT/'specs/M11-评估运行与基线报告.md','复核字段说明.md':ROOT/'evaluation/README-M11.md',
        'run_evaluation.py':ROOT/'practice/m11/complete/tools/run_evaluation.py',
        'verify_m11_cli.py':ROOT/'practice/m11/complete/tools/verify_m11_cli.py'}
    files.update({f'tests/{p.name}':p for p in (ROOT/'practice/m11/complete/evaluation/tests').glob('test_*.py') if p.name in {'test_runtime.py','test_runtime_extra.py','test_reporting.py'}})
    target=student/'materials/m11'
    for rel,source in files.items():
        path=target/rel
        if not path.resolve().is_relative_to(student):raise ValueError('材料路径越出学生目录')
        for parent in path.parents:
            if parent==student:break
            if parent.exists() and not parent.is_dir():raise ValueError('材料目录被同名文件占用，尚未写入')
        if path.exists() and (not path.is_file() or path.read_bytes()!=source.read_bytes()):raise ValueError('材料已修改，尚未写入：'+rel)
    for rel,source in files.items():
        path=target/rel;path.parent.mkdir(parents=True,exist_ok=True)
        if not path.exists():path.write_bytes(source.read_bytes())
    return {'status':'prepared','files':len(files),'business_code_written':False,'destination':str(target)}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--student',required=True);a=p.parse_args()
    try:print(json.dumps(prepare(a.student),ensure_ascii=False,indent=2))
    except ValueError as e:p.exit(1,str(e)+'\n')
