"""将 M06 材料导入已有学生目录；冲突时停止，保留前后端、规格与配置。"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
# revision: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# checksum: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# cache: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# revision: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# generated: lpf2-18283 lpf2-19E2b
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from practice.m06.check_m06 import safe_path
from tools.export_m06_materials import build, json_bytes

def sha(data):
    return hashlib.sha256(data).hexdigest()

def prepare(student):
    student = Path(student).expanduser().resolve()
    if student == ROOT or ROOT in student.parents or student in ROOT.parents:
        raise ValueError('目标必须是独立学生目录，不能是教师目录或它的父子目录')
    index_path = safe_path(student, 'materials/materials-index.json')
    if not index_path.is_file():
        raise ValueError('未找到 M04 材料索引；先按5.4建立学生目录，不要把教师目录当学生目录')
    index = json.loads(index_path.read_text(encoding='utf-8'))
    if index.get('kind') != 'student_materials_only':
        raise ValueError('学生材料索引类型不符合 M04 约定')
    payloads, package = build()
    updates = {'materials/m06/' + name: data for name, data in payloads.items()}
    updates['tools/check_m06.py'] = (ROOT / 'practice/m06/check_m06.py').read_bytes()
    updates['materials/m06-exercise/test_question_export.py'] = (ROOT / 'practice/m06/exercise/tests/test_question_export.py').read_bytes()
    updates['materials/corpus-guide/格式对照练习.md'] = (ROOT / 'practice/m06/格式对照练习.md').read_bytes()
    for name in ['覆盖与边界.html','覆盖与边界.json']:
        updates['materials/corpus-guide/'+name]=(ROOT/'evaluation'/name).read_bytes()
    manifest = json.loads((ROOT / 'corpus/document-manifest.json').read_text(encoding='utf-8'))
    for variant in package['variants']:
        source_map = json.loads((ROOT / f'corpus/content/{variant["id"]}-source-map.json').read_text(encoding='utf-8'))
        base = next(d for d in manifest['documents'] if d['id'] == source_map['base'])
        projection = {
            'id': variant['id'], 'source_document_id': base['id'],
            'source_file': 'materials/corpus/' + base['output_file'],
            'variant_file': variant['file'], 'scope': source_map['scope'],
            'transformation': source_map['transformation'],
            'source_sha256': source_map['source_sha256'], 'variant_sha256': source_map['sha256'],
            'mapping': [{k: v for k, v in row.items() if k not in {'raster_file', 'raster_sha256'}}
                        for row in source_map['mapping']],
            'note': '原件范围对照，不是DocMind输出；不上传为知识库文档。',
        }
        updates[f'materials/corpus-guide/{variant["id"]}-source-map.json'] = json_bytes(projection)
    for row in package['documents'] + package['variants']:
        updates[row['file']] = (ROOT / row['teacher_source']).read_bytes()
    known = {row['file']: row['sha256'] for row in index.get('files', [])}
    changes, conflicts = [], []
    # Preflight every destination before writing anything; existing unknown files are never adopted.
    for name, data in updates.items():
        path = safe_path(student, name)
        if path.exists():
            if not path.is_file():
                conflicts.append(name + ' 不是普通文件'); continue
            current = path.read_bytes()
            if current == data:
                continue
            if name not in known or sha(current) != known[name]:
                conflicts.append(name + ' 已被修改或不在旧索引中'); continue
            changes.append((name, data, current))
        else:
            changes.append((name, data, None))
    if conflicts:
        raise ValueError('为保留你的修改，导入未执行。请先比较下列文件，不要删除学生项目：\n' + '\n'.join(conflicts))
    # Backups live outside the business upload directory. A timestamp avoids destroying older versions.
    backup = 'materials-backups/M06-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup_root = safe_path(student, backup)
    backup_root.mkdir(parents=True, exist_ok=False)
    (backup_root / 'materials-index.json').write_bytes(index_path.read_bytes())
    for name, data, old in changes:
        if old is not None:
            out = backup_root / name
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(old)
    for name, data, _ in changes:
        out = safe_path(student, name)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
    known.update({name: sha(data) for name, data in updates.items()})
    index.update(stage_materials='M06', documents_available=len(package['documents']),
                 documents=[{k: row[k] for k in ('id', 'file', 'sha256', 'review_status')}
                            for row in package['documents']],
                 evaluation_questions_copied=sum(1 for line in payloads['development.jsonl'].splitlines() if line.strip()),
                 holdout_questions_copied=0, holdout_answers_copied=0,
                 files=[{'file': name, 'sha256': value} for name, value in sorted(known.items())])
    index_path.write_bytes(json_bytes(index))
    return {'status': 'imported', 'changed_files': len(changes), 'student': str(student),
            'backup': backup, 'documents': len(package['documents']),
            'development_cases': index['evaluation_questions_copied'],
            'holdout_questions_copied': 0, 'application_code_copied': False,
            'next': '在学生目录运行 python tools/check_m06.py；导入成功不代表完整材料验收通过。'}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--student', required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.student), ensure_ascii=False, indent=2))
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(2, str(exc) + '\n')
