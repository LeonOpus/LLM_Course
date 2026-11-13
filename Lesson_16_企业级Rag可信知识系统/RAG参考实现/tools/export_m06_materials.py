"""Read the public, pre-exported M06 materials; no teacher dataset is required."""
import hashlib
import json
from pathlib import Path, PurePosixPath
# cache: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# generated: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# cache: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# revision: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# revision: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# revision: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# revision: lpf2-18283 lpf2-19E2b
ROOT=Path(__file__).resolve().parents[1]
NAMES={'package.json','development.jsonl','smoke-questions.jsonl','assignment-index.json','taxonomy.json','smoke-freeze.json'}
def sha(data):return hashlib.sha256(data).hexdigest()
def json_bytes(value):return (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
def build():
    folder=ROOT/'student-export/m06'
    manifest=json.loads((folder/'EXPORT.json').read_text(encoding='utf-8'))
    rows=manifest.get('files',[])
    if len(rows)!=len(NAMES) or {r['file'] for r in rows}!=NAMES:
        raise ValueError('M06公开材料清单不完整或含非公开文件')
    payloads={}
    for row in rows:
        path=folder/row['file']
        if path.is_symlink() or not path.is_file():raise ValueError('M06材料不是普通文件')
        data=path.read_bytes()
        if sha(data)!=row['sha256']:raise ValueError('M06材料指纹不符：'+row['file'])
        payloads[row['file']]=data
    package=json.loads(payloads['package.json'])
    for row in package['files']:
        prefix='materials/m06/'
        name=row['file'].removeprefix(prefix)
        if not row['file'].startswith(prefix) or name not in NAMES or sha(payloads[name])!=row['sha256']:
            raise ValueError('M06包内清单与公开材料不一致')
    cases=[json.loads(line) for line in payloads['development.jsonl'].splitlines() if line.strip()]
    if len(cases)!=140 or any(c.get('split')!='development' for c in cases):
        raise ValueError('公开开发集必须只有140条开发题')
    for row in package['documents']+package['variants']:
        rel=PurePosixPath(row['teacher_source'])
        if len(rel.parts)!=3 or rel.parts[0]!='corpus' or rel.parts[1] not in {'documents','variants'} or '..' in rel.parts or '\\' in str(rel):
            raise ValueError('业务材料源路径无效')
        path=ROOT/str(rel)
        if path.is_symlink() or path.resolve().parent!=(ROOT/rel.parts[0]/rel.parts[1]).resolve():
            raise ValueError('业务材料源路径越界')
        if sha(path.read_bytes())!=row['sha256']:raise ValueError('业务材料指纹不符：'+row['id'])
    return payloads,package
