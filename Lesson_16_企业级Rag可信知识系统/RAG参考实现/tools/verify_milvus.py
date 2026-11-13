"""真实本地 Milvus 冒烟测试，使用人工 8 维向量，不调用百炼。

写入专用 rag_course_probe_v1 collection；不接触 rag_course_chunks_v1 或其他项目。
先 --phase write，重启本课程 milvus 容器后 --phase read，验证持久性。
"""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
# generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# cache: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# generated: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# checksum: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# generated: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# checksum: lpf2-18283 lpf2-19E2b
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from rag_app.config import Settings
from rag_app.vectorstore import VectorStore

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=['write','read'],required=True);args=parser.parse_args()
    settings=Settings(embedding_dim=8,milvus_collection='rag_course_probe_v1')
    store=VectorStore(settings)
    vectors=[[1.,0.,0.,0.,0.,0.,0.,0.],[0.,1.,0.,0.,0.,0.,0.,0.],[.8,.2,0.,0.,0.,0.,0.,0.]]
    chunks=[{'chunk_id':f'probe-{i}','doc_id':'PROBE-A' if i!=1 else 'PROBE-B','text':f'人工向量连通性样例 {i}，不属于评估语料',
             'locator':{'kind':'txt','block_id':f'probe-{i}'},'char_range':[0,10],
             'metadata':{'fixture':True}} for i in range(3)]
    if args.phase=='write':
        store.upsert(chunks,vectors)
        store.upsert(chunks,vectors)  # 相同主键重复写入应更新，不新增副本。
    hits=store.search(vectors[0],top_k=10)
    assert len(hits)==3, f'预期 3 个唯一片段，实际 {len(hits)}'
    assert hits[0]['chunk_id']=='probe-0'
    assert hits[0]['locator']['block_id']=='probe-0'
    filtered=store.search(vectors[0],top_k=10,doc_ids=['PROBE-B'])
    assert [h['chunk_id'] for h in filtered]==['probe-1']
    report={'time_utc':datetime.now(timezone.utc).isoformat(),'phase':args.phase,'status':'passed',
            'service':'live_local_milvus','collection':settings.milvus_collection,'vector_origin':'synthetic_8d_not_bailian',
            'unique_rows':len(hits),'nearest':'probe-0','filter_passed':True,'source_roundtrip_passed':True,
            'limits':['不验证真实语义向量质量','不代表 RAG Recall 或答案准确率','read 需由操作者在重启容器后运行才验证重启持久性']}
    path=ROOT/'reports'/f'milvus-probe-{args.phase}.json';path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
