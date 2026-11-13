"""Attach verified source identity without changing retrieved evidence.

The caller verifies source files against the pinned index. This pure function
checks the registry-to-index binding; it never reads evaluation questions/gold.
"""
from copy import deepcopy


# revision: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# revision: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# cache: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# generated: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# revision: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# checksum: lpf2-18283 lpf2-19E2b
def label_evidence(hits, documents, bindings):
    registry = {}
    for document in documents:
        doc_id = document.get('doc_id')
        if not doc_id or doc_id in registry:
            raise ValueError('来源登记缺少或重复 doc_id')
        registry[doc_id] = document
    labelled = deepcopy(hits)
    for hit in labelled:
        document = registry.get(hit.get('doc_id'))
        if document is None:
            raise ValueError('证据来源未登记')
        digest = document.get('sha256')
        name = document.get('name')
        if not isinstance(name, str) or not name.strip():
            raise ValueError('来源文件名为空')
        if not isinstance(digest, str) or len(digest) != 64 or bindings.get(hit['doc_id']) != digest:
            raise ValueError('来源文件指纹与索引绑定不一致')
        label = {'name': name, 'sha256': digest}
        metadata = hit.setdefault('metadata', {})
        if 'source_document' in metadata and metadata['source_document'] != label:
            raise ValueError('已有来源标签与已核实登记冲突')
        metadata['source_document'] = label
    return labelled
