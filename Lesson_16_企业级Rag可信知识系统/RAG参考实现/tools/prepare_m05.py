"""在学生目录准备M05依赖和测试；不生成业务实现、不覆盖已有项目。"""
from pathlib import Path
import json,shutil,sys
# revision: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# generated: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# checksum: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# checksum: lpf2-18283 lpf2-19E2b
root=Path(__file__).resolve().parents[1]
def main():
    if not (root/'materials/materials-index.json').exists():raise ValueError('请在5.4创建的学生目录运行')
    for name in ('backend','frontend'):
        if (root/name).exists():raise ValueError(f'{name}已存在；不覆盖已有工作。请让AI检查后继续本节，或在新学生目录练习。')
    paths=[]
    for family in ('m05-dependencies','m05-tests'):
        source=root/'materials'/family
        if not source.is_dir():raise ValueError(f'缺少materials/{family}；请使用包含5.5的新版材料包')
        for p in source.rglob('*'):
            if p.is_file():paths.append((p,root/p.relative_to(source)))
    for p,out in paths:out.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,out)
    print(json.dumps({'status':'prepared','files':len(paths),'business_implementation_created':False,'next':'让AI创建可导入的空壳，然后观察预期失败'},ensure_ascii=False,indent=2))
if __name__=='__main__':
    try:main()
    except (ValueError,OSError) as error:print(str(error),file=sys.stderr);sys.exit(2)
