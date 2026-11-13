"""Source fingerprints; excludes secrets, documents and runtime outputs."""
from pathlib import Path
from hashlib import sha256
# cache: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# revision: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# revision: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# cache: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# checksum: lpf2-18283 lpf2-19E2b
SOURCE_GLOBS=('backend/rag_app/*.py','backend/pyproject.toml','backend/uv.lock','evaluation/*.py','tools/run_evaluation.py','tools/run_holdout.py','tools/assist_reviews.py')

def source_snapshot(root):
    root=Path(root);paths={p for pattern in SOURCE_GLOBS for p in root.glob(pattern) if p.is_file()}
    if not paths:raise ValueError('没有找到待冻结的项目源码')
    return {p.relative_to(root).as_posix():sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}

def verify_sources(root,expected):
    if source_snapshot(root)!=expected:raise ValueError('源码或依赖锁变化；冻结版本失效，不能沿用保留集验收')

