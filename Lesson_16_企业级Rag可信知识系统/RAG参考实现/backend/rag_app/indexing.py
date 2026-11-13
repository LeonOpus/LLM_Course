"""M09：独立的切块、入库和只检索阶段。"""
from hashlib import sha256
import json
import math
import time
from uuid import uuid4
from rag_app.metering import UsageJournal,summarize_events
from rag_app.core import chunk_blocks
from rag_app.docmind import save_json
from rag_app.providers import Bailian
from rag_app.vectorstore import VectorStore
from rag_app.structure import blocks_digest, selected_structure_chunks
from rag_app.experiments import read_plan, experiment_manifest, verify_snapshot, ensure_experiment_collection

from rag_app.hybrid import FULL_TEXT_CONFIG, retrieval_profile, fuse_rrf

# checksum: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# generated: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# generated: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# cache: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# generated: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# generated: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# revision: lpf2-18283 lpf2-19E2b
CONFIG={'window':600,'overlap':100,'preserve_tables':False}

def embedding_config(settings):
    return {'model':settings.embedding_model,'dimension':settings.embedding_dim,
            'base_url':settings.bailian_base_url.rstrip('/')}

def preview_chunks(pipeline, doc_id):
    experiment_manifest(pipeline)
    folder=pipeline.folder(doc_id);item=pipeline.store.get(doc_id)
    originals=list(folder.glob('source.*'))
    if len(originals)!=1 or sha256(originals[0].read_bytes()).hexdigest()!=item['sha256']:
        raise ValueError('原文件指纹不一致：保留现场，重新上传原文件')
    path=folder/'blocks.json'
    if not path.exists():raise ValueError('尚未解析：先点击仅解析，等待 parsed')
    raw=path.read_bytes()
    try:blocks=json.loads(raw)
    except (ValueError,UnicodeError):raise ValueError('解析缓存不是有效 JSON：保留现场检查 blocks.json') from None
    if not isinstance(blocks,list) or not blocks:raise ValueError('解析块必须是非空列表')
    if any(not isinstance(b,dict) or b.get('doc_id')!=doc_id for b in blocks):
        raise ValueError('解析块文档编号与当前文档不一致')
    strategy=pipeline.settings.chunk_strategy;plan=None;config=dict(CONFIG)
    if strategy!='baseline':
        plan=read_plan(folder)
        config={**CONFIG,'strategy':strategy,
                'algorithm_version':'m12c-multipage-v1' if strategy.startswith('multipage_') else 'm12-structure-v1',
                'plan_sha256':blocks_digest(plan)}
    verify_snapshot(pipeline,doc_id,item['sha256'],sha256(raw).hexdigest(),blocks_digest(plan) if plan is not None else None)
    try:chunks=chunk_blocks(blocks,**CONFIG) if strategy=='baseline' else selected_structure_chunks(blocks,plan,strategy)
    except (KeyError,TypeError):raise ValueError('解析块缺少文本或来源定位字段') from None
    if not chunks:raise ValueError('解析结果没有有效文本，不能空入库')
    if strategy in {'multipage_rows','multipage_context'}:
        # selected_structure_chunks已经严格验证计划；不信任源块自带的transformation元数据。
        config.update(plan_schema_version=2,reviewed_table_count=sum(len(g['block_ids']) for g in plan['groups']))
    ids=[c['chunk_id'] for c in chunks]
    if len(set(ids))!=len(ids):raise ValueError('解析块含重复身份，不能覆盖为同一片段')
    return {'doc_id':doc_id,'config':config,'block_count':len(blocks),'chunk_count':len(chunks),
            'blocks_sha256':sha256(raw).hexdigest(),'chunks':chunks,'verification':'preview_only'}

def validate_vector(vector,dimension,label):
    if (not isinstance(vector,list) or len(vector)!=dimension
        or any(type(n) not in (int,float) or not math.isfinite(n) for n in vector)
        or not any(vector)):
        raise ValueError(f'{label}向量维度或数值无效：要求有限数值且不能全零')

def index_document(pipeline, doc_id):
    attempt=uuid4().hex
    journal=UsageJournal(pipeline.settings.runtime_dir,{'phase':'index','doc_id':doc_id,'attempt_id':attempt},origin='configured_transport')
    try:return _index_document(pipeline,doc_id,journal)
    finally:
        save_json(pipeline.settings.runtime_dir/'index-usage'/f'{attempt}.json',
                  {'doc_id':doc_id,'attempt_id':attempt,'events':journal.events(),'summary':summarize_events(journal.events())})

def _index_document(pipeline,doc_id,journal):
    item=pipeline.store.get(doc_id)
    if not item:raise KeyError(doc_id)
    if item['status'] not in {'parsed','indexing'} and not (item['status']=='failed' and item.get('stage')=='index'):
        raise ValueError('先完成解析；仅允许已解析文档或失败的入库任务继续')
    if item['status']!='indexing':pipeline.store.move(doc_id,'indexing',stage='index',error=None)
    preview=preview_chunks(pipeline,doc_id);folder=pipeline.folder(doc_id);settings=pipeline.settings
    chunks=preview['chunks'];config=embedding_config(settings)
    manifest={'version':1,'doc_id':doc_id,'source_sha256':item['sha256'],
              'blocks_sha256':preview['blocks_sha256'],'chunking':preview['config'],
              'embedding':config,'collection':settings.milvus_collection,
              'milvus_uri':settings.milvus_uri,'chunk_ids':[c['chunk_id'] for c in chunks]}
    if settings.milvus_full_text:manifest['full_text']=FULL_TEXT_CONFIG
    manifest_path=folder/'index-manifest.json'
    if manifest_path.exists():
        try:previous=json.loads(manifest_path.read_text(encoding='utf-8'))
        except ValueError:raise ValueError('入库清单损坏：保留现场，不能推测此前写入状态') from None
        if previous!=manifest:raise ValueError('当前内容或配置与冻结的入库清单不同；恢复原配置后重试，或用新 collection 与独立运行目录做新实验')
    else:save_json(manifest_path,manifest)
    save_json(folder/f'chunks-{settings.chunk_strategy}.json',chunks)
    vector_store=None
    if experiment_manifest(pipeline) is not None:
        vector_store=VectorStore(settings)
        ensure_experiment_collection(pipeline,vector_store)
    cache=settings.runtime_dir/'embedding-cache';cache.mkdir(parents=True,exist_ok=True)
    vectors=[];provider=Bailian(settings,usage_journal=journal)
    for start in range(0,len(chunks),10):
        batch=chunks[start:start+10]
        paths=[cache/(sha256(json.dumps({'embedding':config,'text':c['text']},ensure_ascii=False,sort_keys=True).encode()).hexdigest()+'.json') for c in batch]
        resolved={};missing=[]
        for i,path in enumerate(paths):
            if path.exists():
                try:vector=json.loads(path.read_text(encoding='utf-8'))
                except (ValueError,UnicodeError):raise ValueError('向量缓存不是有效 JSON：保留该文件，检查后单独移出缓存再重试') from None
                validate_vector(vector,settings.embedding_dim,'缓存')
                resolved[i]=vector
            else:missing.append(i)
        if resolved:journal.record_cache(settings.embedding_model,len(resolved))
        if missing:
            new=provider.embed([batch[i]['text'] for i in missing])
            if not isinstance(new,list) or len(new)!=len(missing):raise ValueError('向量响应数量不匹配，停止入库')
            for v in new:validate_vector(v,settings.embedding_dim,'响应')
            for i,v in zip(missing,new):save_json(paths[i],v);resolved[i]=v
        vectors.extend(resolved[i] for i in range(len(batch)))
    # 收齐并校验全部向量以后才写数据库。分批 upsert 不是跨批事务；失败文档靠 ready 过滤隔离。
    (vector_store if vector_store is not None else VectorStore(settings)).upsert(chunks,vectors)
    return pipeline.store.move(doc_id,'ready',chunk_count=len(chunks),indexed_at=time.time(),error=None,stage='ready')

def retrieve(pipeline, question, top_k=10, doc_ids=None):
    identity=uuid4().hex
    journal=UsageJournal(pipeline.settings.runtime_dir,{'phase':'query','retrieval_id':identity},origin='configured_transport')
    try:
        result=_retrieve(pipeline,question,top_k,doc_ids,journal)
        result['usage_events']=journal.events()
        return result
    except Exception as error:
        error.usage_events=journal.events()
        raise

def _retrieve(pipeline,question,top_k,doc_ids,journal):
    if not isinstance(question,str) or not question.strip() or len(question)>2000:
        raise ValueError('问题须为1～2000字符的非空文本')
    if type(top_k) is not int or not 1<=top_k<=50:raise ValueError('top_k 必须是1～50的整数')
    if doc_ids is not None and (not isinstance(doc_ids,list) or any(not isinstance(d,str) for d in doc_ids)):
        raise ValueError('doc_ids 必须是文档编号列表')
    start=time.perf_counter();settings=pipeline.settings;config=embedding_config(settings)
    retrieval_config=retrieval_profile(settings,top_k)
    experiment_manifest(pipeline)
    profile={'schema_version':'rag-index-profile/1','strategy':settings.chunk_strategy,
             'collection':settings.milvus_collection,'documents':[]}
    ready=[d['doc_id'] for d in pipeline.store.list() if d['status']=='ready' and (doc_ids is None or d['doc_id'] in doc_ids)]
    for doc_id in ready:
        path=pipeline.folder(doc_id)/'index-manifest.json'
        if not path.exists():raise ValueError('已入库文档缺少索引配置清单，不能验证查询与文档向量是否匹配')
        try:manifest=json.loads(path.read_text(encoding='utf-8'))
        except ValueError:raise ValueError('已入库文档的索引配置清单损坏') from None
        if manifest.get('embedding')!=config or manifest.get('collection')!=settings.milvus_collection or manifest.get('milvus_uri')!=settings.milvus_uri:
            raise ValueError('查询配置与已入库文档不匹配；恢复原配置或在独立运行目录重建实验')
        if manifest.get('full_text')!=(FULL_TEXT_CONFIG if settings.milvus_full_text else None):
            raise ValueError('全文配置与冻结的入库清单不同；准备新独立索引')
        preview=preview_chunks(pipeline,doc_id)
        if (manifest.get('chunking')!=preview['config'] or manifest.get('blocks_sha256')!=preview['blocks_sha256']
            or manifest.get('source_sha256')!=pipeline.store.get(doc_id)['sha256']
            or manifest.get('chunk_ids')!=[c['chunk_id'] for c in preview['chunks']]):
            raise ValueError('分块配置或内容与已入库清单不匹配；请准备新实验重新入库')
        profile['documents'].append({'doc_id':doc_id,'source_sha256':manifest['source_sha256'],
            'blocks_sha256':manifest['blocks_sha256'],'plan_sha256':preview['config'].get('plan_sha256'),
            'chunking':preview['config'],'manifest_sha256':blocks_digest(manifest)})
    profile['documents'].sort(key=lambda row:row['doc_id'])
    frozen_experiment=experiment_manifest(pipeline)
    if frozen_experiment and frozen_experiment.get('visual_augmentation'):
        profile['visual_augmentation']=frozen_experiment['visual_augmentation']
    from rag_app.source_scope import resolve_scope
    scope=resolve_scope(question,pipeline.store.list(),ready) if settings.source_scope=='explicit' else {'decision':'off','doc_ids':ready,'locator':None}
    search_ready=scope['doc_ids']
    scope_kw={'locator':scope['locator']} if scope['locator'] else {}
    hits=[];routes={'dense':[],'bm25':[]};timing={'embed_ms':0,'retrieve_ms':0,'dense_ms':0,'bm25_ms':0,'fusion_ms':0}
    if search_ready:
        vector_store=VectorStore(settings)
        experiment=experiment_manifest(pipeline)
        if experiment is not None and (experiment['collection_state']!='owned' or not vector_store.client.has_collection(settings.milvus_collection)):
            raise ValueError('实验collection归属未确认或已丢失；重新准备并入库，不能当作空检索成功')
        if not vector_store.client.has_collection(settings.milvus_collection):
            raise ValueError('已入库collection丢失，不能当空检索成功')
        if settings.milvus_full_text:vector_store.verify_full_text()
        if settings.retrieval_mode in {'dense','hybrid'}:
            t=time.perf_counter();vectors=Bailian(settings,usage_journal=journal).embed([question.strip()])
            if len(vectors)!=1:raise ValueError('查询向量响应数量不符')
            validate_vector(vectors[0],settings.embedding_dim,'查询')
            timing['embed_ms']=(time.perf_counter()-t)*1000
            t=time.perf_counter();routes['dense']=vector_store.search(vectors[0],top_k,search_ready,**scope_kw)
            timing['dense_ms']=(time.perf_counter()-t)*1000
        if settings.retrieval_mode in {'bm25','hybrid'}:
            t=time.perf_counter();routes['bm25']=vector_store.search_bm25(question.strip(),top_k,search_ready,**scope_kw)
            timing['bm25_ms']=(time.perf_counter()-t)*1000
        t=time.perf_counter()
        hits=fuse_rrf(routes['dense'],routes['bm25'],top_k) if settings.retrieval_mode=='hybrid' else [{**h,'score_kind':'cosine' if settings.retrieval_mode=='dense' else 'bm25'} for h in routes[settings.retrieval_mode]]
        timing['fusion_ms']=(time.perf_counter()-t)*1000 if settings.retrieval_mode=='hybrid' else 0
        timing['retrieve_ms']=timing['dense_ms']+timing['bm25_ms']+timing['fusion_ms']
    timing['total_ms']=(time.perf_counter()-start)*1000
    return {'mode':'live' if ready else 'no_documents','question':question.strip(),'top_k':top_k,
            'source_scope':scope,'ready_doc_ids':ready,'candidate_count':len(hits),'candidates':hits,'embedding':config,
            'timing':timing,'index_profile':profile,'retrieval_profile':retrieval_config,'retrieval_routes':routes,'notice':'检索分数不是答案正确率；本接口没有调用生成模型或重排模型'}
