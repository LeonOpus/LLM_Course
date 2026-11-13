"""两路候选排名融合；召回仍由Milvus执行，分数不是置信概率。"""
from copy import deepcopy
import math

# revision: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# revision: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# generated: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# cache: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# revision: lpf2-18283 lpf2-19E2b
RRF_K=60
ANALYZER={'type':'chinese'}
FULL_TEXT_CONFIG={'algorithm':'milvus-bm25','analyzer':ANALYZER,'field':'sparse','version':1,'bm25_k1':1.2,'bm25_b':.75,'index_algorithm':'DAAT_MAXSCORE'}

def retrieval_profile(settings,top_k):
    mode=settings.retrieval_mode
    if mode not in {'dense','bm25','hybrid'}:raise ValueError('不支持的召回模式')
    if mode!='dense' and not settings.milvus_full_text:
        raise ValueError('BM25/混合召回需要MILVUS_FULL_TEXT=true并新建独立全文索引')
    return {'schema_version':'rag-retrieval-profile/1','mode':mode,'branch_top_k':top_k,
            'output_top_k':top_k,'rrf_k':RRF_K if mode=='hybrid' else None,
            'full_text':deepcopy(FULL_TEXT_CONFIG) if settings.milvus_full_text else None}

def fuse_rrf(dense,bm25,top_k):
    if type(top_k) is not int or not 1<=top_k<=50:raise ValueError('融合top_k无效')
    rows={};identities={}
    for route,hits in [('dense',dense),('bm25',bm25)]:
        seen=set()
        for rank,hit in enumerate(hits,1):
            cid=hit.get('chunk_id');score=hit.get('score')
            if not isinstance(cid,str) or not cid or cid in seen:raise ValueError('候选ID缺失或同一路重复')
            if type(score) not in (int,float) or not math.isfinite(score):raise ValueError('候选分数不是有限数值')
            seen.add(cid)
            identity={k:v for k,v in hit.items() if k!='score'}
            if cid in identities and identities[cid]!=identity:raise ValueError('两路同ID候选正文或来源冲突')
            identities[cid]=deepcopy(identity)
            if cid not in rows:rows[cid]={**deepcopy(identity),'score':0.,'score_kind':'rrf','retrieval_ranks':{},'retrieval_scores':{}}
            row=rows[cid];row['score']+=1/(RRF_K+rank)
            row['retrieval_ranks'][route]=rank;row['retrieval_scores'][route]=score
    return sorted(rows.values(),key=lambda row:(-row['score'],row['chunk_id']))[:top_k]
