"""检查已冻结练习材料的文件指纹、行等价与所有拼接来源。"""
from pathlib import Path
from hashlib import sha256
import json,sys
# generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# generated: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# checksum: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# checksum: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# revision: lpf2-18283 lpf2-19E2b
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from rag_app.structure import blocks_digest
from rag_app.multipage import merged_table,compare_multipage

def verify():
    folder=ROOT/'practice/m12c/materials';provenance=json.loads((folder/'provenance.json').read_text(encoding='utf-8'))
    values={};metrics={}
    for source in provenance['sources']:
        doc=source['doc_id'];name=source['file']
        if Path(name).name!=name:raise ValueError('原件必须在materials目录')
        if sha256((folder/name).read_bytes()).hexdigest()!=source['source_sha256']:raise ValueError('原始PDF已变化')
        blocks=json.loads((folder/f'{doc}-blocks.json').read_text(encoding='utf-8'))
        plan=json.loads((folder/f'{doc}-review-plan.json').read_text(encoding='utf-8'))
        if blocks_digest(blocks)!=source['blocks_sha256']:raise ValueError('解析块已变化')
        values[doc]=[row for b in blocks if b['type']=='table' for row in merged_table(b['text'],2)['data_values']]
        comparison=compare_multipage(blocks,plan)
        lookup={(b['doc_id'],b['locator']['block_id']):b for b in blocks}
        for variant in comparison['variants'].values():
            for c in variant['chunks']:
                for s in c.get('source_spans',[]):
                    b=lookup[(s['doc_id'],s['locator']['block_id'])]
                    if s['text']!=b['text'][slice(*s['char_range'])] or s['locator']!=b['locator']:
                        raise ValueError('来源片段不能回查')
        metrics[doc]={k:{key:v for key,v in value.items() if key!='chunks'} for k,value in comparison['variants'].items()}
    if values.get('D11')!=values.get('V04') or len(values.get('D11',[]))!=12:raise ValueError('重新分页改变了数据行')
    return {'status':'passed','row_equivalence':12,'source_spans_roundtrip':'passed','metrics':metrics,'cloud_calls':0,
            'scope':'冻结样例文件一致性；不认证人工分区语义或真实DocMind质量'}
if __name__=='__main__':print(json.dumps(verify(),ensure_ascii=False,indent=2))
