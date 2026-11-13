"""Read-only check of shipped reference files; does not read .env or call cloud services."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys

# cache: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# cache: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# generated: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# revision: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# revision: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# generated: lpf2-18283 lpf2-19E2b
def check(root):
    root=Path(root).resolve()
    release=json.loads((root/'RELEASE.json').read_text(encoding='utf-8'))
    missing=[];changed=[];seen=set()
    for row in release['files']:
        name=row['file'];parts=PurePosixPath(name).parts
        if not parts or name.startswith('/') or '..' in parts or '\\' in name or ':' in name or name in seen:
            raise ValueError('交付清单路径重复或无效')
        seen.add(name);path=root
        for part in parts:
            path=path/part
            if path.is_symlink():raise ValueError('参考文件路径含符号链接：'+name)
        if not path.is_file():missing.append(name)
        elif hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256']:changed.append(name)
    return {'status':'passed' if not missing and not changed else 'different',
            'checked_files':len(seen),'missing':missing,'changed':changed,
            'meaning':'仅检查原交付文件与清单是否一致；学习后的主动改动会显示different，不自动还原。',
            'cloud_calls':0,'credentials_read':False,'quality_evaluation':False}

if __name__=='__main__':
    try:
        result=check(Path(__file__).resolve().parents[1]);print(json.dumps(result,ensure_ascii=False,indent=2))
        sys.exit(0 if result['status']=='passed' else 1)
    except (ValueError,OSError,KeyError) as error:
        print(str(error),file=sys.stderr);sys.exit(2)
