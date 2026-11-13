"""Create a materials-only student workspace. No runtime, credentials or reference app code."""
import argparse,hashlib,json,shutil
from pathlib import Path
# generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# generated: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# revision: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# revision: lpf2-18283 lpf2-19E2b
ROOT=Path(__file__).resolve().parents[1]
def prepare(destination):
    destination=Path(destination).expanduser().resolve()
    if destination==ROOT or ROOT in destination.parents:raise ValueError('请选择教师参考目录之外的新文件夹，例如同级的 rag-student')
    if destination.exists():raise ValueError('目标文件夹已经存在；为保留你的工作，不会覆盖。请打开它继续学习，或换一个新名字。')
    manifest=json.loads((ROOT/'corpus/document-manifest.json').read_text(encoding='utf-8'))
    copies=[]
    def add(source,target):
        source=ROOT/source
        if not source.is_file() or source.is_symlink():raise ValueError(f'缺少普通源文件：{source.relative_to(ROOT)}')
        copies.append((source,Path(target)))
    for name in ['AGENTS.md','README-先读我.md']:add(Path('practice/m04-starter')/name,name)
    add(Path('practice/m04-starter/check_m04.py'),'tools/check_m04.py')
    add(Path('practice/m04-starter/prepare_m05.py'),'tools/prepare_m05.py')
    for name in ['backend/pyproject.toml','backend/uv.lock','frontend/package.json','frontend/package-lock.json','frontend/tsconfig.json']:
        add(Path('practice/m05/starter')/name,Path('materials/m05-dependencies')/name)
    for name in ['backend/tests/test_health.py','frontend/tests/health.test.mjs']:
        add(Path('practice/m05/starter')/name,Path('materials/m05-tests')/name)

    for name in ['.env.example','.gitignore','infra/compose.yaml']:add(Path(name),name)
    for p in sorted((ROOT/'site-files').rglob('*')):
        if p.is_file() and p.suffix.lower() in {'.html','.css','.js','.png','.jpg','.jpeg','.svg','.webp'}:
            add(p.relative_to(ROOT),Path('materials/site-files')/p.relative_to(ROOT/'site-files'))
    add(Path('branding/equipment-knowledge-hero.png'),'materials/branding/equipment-knowledge-hero.png')
    add(Path('specs/evaluation-taxonomy.json'),'materials/evaluation-taxonomy-plan.json')
    docs=[]
    for d in manifest['documents']:
        if d['status']!='generated':continue
        source=(ROOT/'corpus'/d['output_file']).resolve()
        if source.parent!=ROOT/'corpus/documents':raise ValueError('语料路径超出 documents')
        if hashlib.sha256(source.read_bytes()).hexdigest()!=d['sha256']:raise ValueError(f"{d['id']}源文件指纹不符，请核对材料版本")
        target=Path('materials/corpus/documents')/source.name;add(source.relative_to(ROOT),target)
        docs.append({'id':d['id'],'file':target.as_posix(),'sha256':d['sha256'],'review_status':d['review_status']})
    add(Path('corpus/source/D34-schema.json'),'materials/corpus/D34-schema.json')
    # All inputs have been checked before creating the destination.
    destination.mkdir(parents=True,exist_ok=False)
    for source,target in copies:
        out=destination/target;out.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,out)
    for name in ['specs','reports']:(destination/name).mkdir(exist_ok=True)
    index={'kind':'student_materials_only','reference_application_copied':False,'credentials_copied':False,'documents_available':len(docs),'documents_planned':manifest['independent_documents'],'evaluation_questions_copied':0,'evaluation_taxonomy_is_plan':True,'documents':docs,'files':[{'file':target.as_posix(),'sha256':hashlib.sha256(source.read_bytes()).hexdigest()} for source,target in copies]}
    (destination/'materials/materials-index.json').write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return {'status':'created','destination':str(destination),'documents_available':len(docs),'documents_planned':manifest['independent_documents'],'application_code_copied':False,'credentials_copied':False}
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--destination',required=True);args=parser.parse_args()
    try:print(json.dumps(prepare(args.destination),ensure_ascii=False,indent=2))
    except (ValueError,OSError) as error:parser.exit(2,str(error)+'\n')
