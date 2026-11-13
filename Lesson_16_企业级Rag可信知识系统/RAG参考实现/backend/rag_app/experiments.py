"""复制冻结解析快照并隔离索引；凭证、旧向量和问答记录不进入快照。"""
from hashlib import sha256
import json
from pathlib import Path
from uuid import uuid4
from rag_app.core import chunk_blocks
from rag_app.docmind import save_json
from rag_app.storage import Store
from rag_app.structure import blocks_digest, selected_structure_chunks

# cache: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# generated: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# cache: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# generated: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# cache: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# checksum: lpf2-18283 lpf2-19E2b
STRATEGIES={'baseline','table_rows','table_context','multipage_rows','multipage_context'}


def read_plan(folder):
    path=folder/'chunk-plan.json'
    if not path.is_file():raise ValueError('缺少chunk-plan.json核对计划；先对照原文制定计划')
    try:return json.loads(path.read_bytes())
    except (ValueError,UnicodeError):raise ValueError('核对计划不是合法JSON') from None


def prepare_experiment(source_runtime,target_runtime,strategy,full_text=False,visual_bundles=None):
    source=Path(source_runtime).resolve();target=Path(target_runtime).resolve()
    if type(full_text) is not bool:raise ValueError('全文开关必须是布尔值')
    if strategy not in STRATEGIES:raise ValueError('不支持的切块策略')
    if target.exists() or target.is_relative_to(source):raise ValueError('目标必须是不存在的独立目录，不能覆盖或放在源runtime内')
    if not (source/'documents.sqlite3').is_file():raise ValueError('源目录缺少文档元数据；请指定runtime而非项目根目录')
    documents=Store(source).list()
    if not documents or any(d['status'] not in {'parsed','ready'} for d in documents):
        raise ValueError('所有源文档必须已解析或已入库；不能把未完成或失败的文档伪装成已解析')
    augmentations={};bundle_snapshots=[];region_ids=set();bundle_baselines={}
    if visual_bundles:
        if strategy!='baseline':raise ValueError('本节先将视觉补充作为单独消融；组合表格策略需重新核对结构计划')
        from rag_app.visual_workflow import validate_bundle
        for bundle_path in visual_bundles:
            packet,extra=validate_bundle(bundle_path,source)
            region_id=packet['region']['region_id']
            if region_id in region_ids:raise ValueError('同一视觉区域重复提供')
            region_ids.add(region_id)
            bundle_baselines[packet['region']['doc_id']]=packet['region']['baseline_blocks_sha256']
            augmentations.setdefault(packet['region']['doc_id'],[]).extend(extra)
            names=['bundle.json','region.json','image.png','review.html']
            if (Path(bundle_path)/'selection-review.json').exists():names.append('selection-review.json')
            bundle_snapshots.append((packet,{name:(Path(bundle_path)/name).read_bytes() for name in names}))
    snapshots=[];records=[]
    for d in documents:
        folder=source/'documents'/d['doc_id']
        if folder.is_symlink() or folder.resolve().parent!=source/'documents':raise ValueError('文档目录异常')
        originals=list(folder.glob('source.*'))
        if len(originals)!=1 or originals[0].is_symlink():raise ValueError('原文件缺失或不唯一')
        original=originals[0].read_bytes()
        if sha256(original).hexdigest()!=d['sha256']:raise ValueError('原文件指纹与元数据不一致')
        raw=(folder/'blocks.json').read_bytes();blocks=json.loads(raw)
        if not isinstance(blocks,list) or not blocks or any(b.get('doc_id')!=d['doc_id'] for b in blocks):
            raise ValueError('解析块为空或文档编号不一致')
        if d['doc_id'] in augmentations:
            if sha256(raw).hexdigest()!=bundle_baselines[d['doc_id']]:raise ValueError('视觉包验证后解析基线又发生变化')
            blocks=blocks+augmentations[d['doc_id']]
            raw=(json.dumps(blocks,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
        plan=read_plan(folder) if strategy!='baseline' else None
        chunks=selected_structure_chunks(blocks,plan,strategy) if plan is not None else chunk_blocks(blocks)
        if not chunks or len({c['chunk_id'] for c in chunks})!=len(chunks):raise ValueError('片段为空或身份重复')
        records.append({'doc_id':d['doc_id'],'source_sha256':d['sha256'],
                        'blocks_sha256':sha256(raw).hexdigest(),'plan_sha256':blocks_digest(plan) if plan is not None else None})
        snapshots.append((d,originals[0].name,original,raw,plan,len(blocks)))
    # 全部输入预检完成后才创建目标；复制已读字节，避免逐份重读造成混合快照。
    target.mkdir(parents=True,exist_ok=False)
    store=Store(target)
    for d,name,original,raw,plan,count in snapshots:
        folder=target/'documents'/d['doc_id'];folder.mkdir(parents=True)
        (folder/name).write_bytes(original);(folder/'blocks.json').write_bytes(raw)
        if plan is not None:save_json(folder/'chunk-plan.json',plan)
        store.create(d['doc_id'],d['name'],d['kind'],d['sha256'])
        store.move(d['doc_id'],'parsing');store.move(d['doc_id'],'parsed',block_count=count,stage='parse')
    manifest={'version':1,'runtime_dir':str(target),'strategy':strategy,
              'collection':'rag_course_exp_'+uuid4().hex,'collection_state':'uncreated','full_text':full_text,
              'documents':sorted(records,key=lambda r:r['doc_id']),
              'notice':'仅复制冻结原件、解析块和核对计划；尚未调用Embedding或写入Milvus'}
    if bundle_snapshots:
        manifest['visual_augmentation']={'schema_version':'visual-augmentation/1','region_count':len(bundle_snapshots),
            'semantic_verified':False,'bundles':sorted([{'bundle_sha256':p['bundle_sha256'],'region_id':p['region']['region_id'],
                'doc_id':p['region']['doc_id'],'model':p['model'],'prompt_version':p['prompt_version'],'origin':p['origin'],**({'selection_review_sha256':sha256(files['selection-review.json']).hexdigest()} if 'selection-review.json' in files else {})} for p,files in bundle_snapshots],key=lambda x:x['region_id'])}
        for packet,files in bundle_snapshots:
            folder=target/'visual-bundles'/packet['region']['region_id'];folder.mkdir(parents=True)
            for name,raw in files.items():(folder/name).write_bytes(raw)
    save_json(target/'experiment.json',manifest)
    return manifest


def experiment_manifest(pipeline):
    settings=pipeline.settings;path=settings.runtime_dir/'experiment.json'
    if not path.exists():
        if settings.chunk_strategy!='baseline' or settings.milvus_full_text:raise ValueError('优化策略或全文索引必须先准备独立实验目录')
        return None
    try:m=json.loads(path.read_bytes())
    except (ValueError,UnicodeError):raise ValueError('独立实验清单损坏') from None
    if (m.get('version')!=1 or m.get('strategy')!=settings.chunk_strategy or m.get('full_text',False)!=settings.milvus_full_text
        or m.get('collection')!=settings.milvus_collection or m.get('runtime_dir')!=str(settings.runtime_dir.resolve())
        or m.get('collection_state') not in {'uncreated','owned'}):
        raise ValueError('当前配置与独立实验清单不一致；恢复配置或准备新实验')
    return m


def verify_snapshot(pipeline,doc_id,source_hash,blocks_hash,plan_hash):
    m=experiment_manifest(pipeline)
    if m is None:return
    rows=[d for d in m['documents'] if d['doc_id']==doc_id]
    if len(rows)!=1:raise ValueError('文档不在冻结实验清单中')
    expected=rows[0]
    if expected['source_sha256']!=source_hash or expected['blocks_sha256']!=blocks_hash:
        raise ValueError('原文件或解析块指纹与实验快照不一致')
    if expected['plan_sha256']!=plan_hash:raise ValueError('核对计划与实验快照不一致；修改计划应准备新实验')


def ensure_experiment_collection(pipeline,vector_store):
    # 单进程教学：多文档后台任务在这里互斥，避免同时争抢首次创建。
    with pipeline.lock:
        manifest=experiment_manifest(pipeline)
        if manifest is None:return
        if manifest['collection_state']=='uncreated':
            if vector_store.client.has_collection(manifest['collection']):
                raise ValueError('目标collection已存在但没有本实验归属记录；不复用，重新准备新实验')
            vector_store.ensure_collection()
            manifest['collection_state']='owned';save_json(pipeline.settings.runtime_dir/'experiment.json',manifest)
        elif not vector_store.client.has_collection(manifest['collection']):
            raise ValueError('本实验collection已丢失；不能用旧ready状态继续，重新准备并入库')
