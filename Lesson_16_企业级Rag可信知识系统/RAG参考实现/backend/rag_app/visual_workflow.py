"""Source-bound offline visual augmentation. JSON validity is not semantic verification."""
import json,html
from hashlib import sha256
from pathlib import Path
from uuid import uuid4
from rag_app.docmind import save_json
from rag_app.storage import Store
from rag_app.visual import render_region,digest,validate_observations,observation_blocks,request_body,PROMPT_VERSION,PROMPTS
from rag_app.providers import Bailian,ProviderError
from rag_app.metering import UsageJournal,summarize_events

# generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# cache: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# generated: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# revision: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# revision: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# generated: lpf2-18283 lpf2-19E2b
def source_snapshot(runtime,doc_id):
    runtime=Path(runtime).resolve()
    if not (runtime/'documents.sqlite3').is_file():raise ValueError('源runtime缺少documents.sqlite3')
    document=Store(runtime).get(doc_id)
    if not document or document['status'] not in {'parsed','ready'}:raise ValueError('先完成DocMind解析，再准备视觉区域')
    folder=runtime/'documents'/doc_id
    if folder.is_symlink() or folder.resolve().parent!=runtime/'documents':raise ValueError('文档路径异常')
    originals=list(folder.glob('source.*'))
    if len(originals)!=1 or originals[0].is_symlink():raise ValueError('原件缺失或不唯一')
    if sha256(originals[0].read_bytes()).hexdigest()!=document['sha256']:raise ValueError('原件指纹不匹配')
    raw=(folder/'blocks.json').read_bytes();blocks=json.loads(raw)
    if not isinstance(blocks,list) or not blocks or any(b.get('doc_id')!=doc_id for b in blocks):raise ValueError('解析块异常')
    return document,originals[0],raw

def prepare_region(pipeline,doc_id,output,*,page=None,box=None,slide=None):
    output=Path(output)
    if output.exists():raise ValueError('区域输出目录已存在；换新目录，保留旧实验')
    document,source,raw=source_snapshot(pipeline.settings.runtime_dir,doc_id)
    png,region=render_region(source,document['kind'],doc_id,page=page,box=box,slide=slide)
    region['baseline_blocks_sha256']=sha256(raw).hexdigest()
    output.mkdir(parents=True,exist_ok=False)
    (output/'image.png').write_bytes(png);save_json(output/'region.json',region)
    return region

def read_region(folder):
    folder=Path(folder);region=json.loads((folder/'region.json').read_bytes());png=(folder/'image.png').read_bytes()
    if not isinstance(region,dict) or sha256(png).hexdigest()!=region.get('image_sha256'):raise ValueError('裁剪图指纹不匹配')
    # This check protects ordinary corruption, not deliberate tampering with all hashes.
    identity={k:region[k] for k in ['doc_id','kind','source_sha256','page','box','render_size','pixel_box','image_sha256','transform']}
    if region.get('kind')=='pptx':identity.update({k:region[k] for k in ['slide','office','source_slide']})
    if digest(identity)!=region.get('region_id'):raise ValueError('区域清单指纹不匹配')
    return region,png

def transcribe_region(region_folder,output,settings,*,http=None,origin='configured_transport',prompt_version=PROMPT_VERSION):
    output=Path(output)
    if output.exists():raise ValueError('转写输出目录已存在；每次调用使用新目录')
    if not settings.dashscope_api_key.get_secret_value():raise ValueError('缺少DASHSCOPE_API_KEY；本次没有调用模型')
    if http is not None and origin!='fixture':raise ValueError('注入的HTTP transport必须标记fixture')
    if origin not in {'fixture','configured_transport'}:raise ValueError('转写来源无效')
    region,png=read_region(region_folder)
    body=request_body(png,settings.vision_model,prompt_version=prompt_version)
    request_config={k:body[k] for k in ['model','temperature','enable_thinking','max_tokens','response_format']}
    output.mkdir(parents=True,exist_ok=False)
    (output/'image.png').write_bytes(png);save_json(output/'region.json',region)
    uid=uuid4().hex;journal=UsageJournal(output,{'phase':'vision','attempt_id':uid},origin)
    attempt={'attempt_id':uid,'state':'started','origin':origin,'region_id':region['region_id'],'model':settings.vision_model}
    save_json(output/'attempt.json',attempt)
    provider=Bailian(settings,http=http,usage_journal=journal)
    try:
        result=provider.transcribe_image(png,prompt_version=prompt_version)
        packet={'schema_version':'visual-bundle/1','region':region,'model':settings.vision_model,
                'prompt_version':prompt_version,'request_sha256':digest(body),'request_config':request_config,'origin':origin,'result':result,'semantic_verified':False}
        packet['bundle_sha256']=digest(packet)
        save_json(output/'bundle.json',packet)
        attempt.update(state='succeeded',usable_observations=sum(not r['uncertain'] for r in result['observations']['observations']))
        render_review(output,packet)
    except ProviderError as error:
        attempt.update(state='failed',error=str(error),model_output=error.model_output)
    finally:
        if http is None:provider.http.close()
        save_json(output/'attempt.json',attempt);save_json(output/'usage-summary.json',summarize_events(journal.events()))
    return attempt

def validate_bundle(folder,runtime):
    folder=Path(folder);region,png=read_region(folder)
    packet=json.loads((folder/'bundle.json').read_bytes())
    if (packet.get('schema_version')!='visual-bundle/1' or packet.get('prompt_version') not in PROMPTS
        or packet.get('region')!=region or packet.get('semantic_verified') is not False
        or packet.get('origin') not in {'fixture','configured_transport'}
        or not isinstance(packet.get('model'),str) or not packet['model']
        or packet.get('bundle_sha256')!=digest({k:v for k,v in packet.items() if k!='bundle_sha256'})):
        raise ValueError('视觉包清单或指纹不一致')
    document,source,raw=source_snapshot(runtime,region['doc_id'])
    if document['sha256']!=region['source_sha256']:raise ValueError('视觉包绑定的原件已变化')
    if sha256(raw).hexdigest()!=region['baseline_blocks_sha256']:raise ValueError('视觉包绑定的解析基线已变化')
    # Re-render from the actual original, rather than trusting user-edited locators.
    actual_png,actual_region=render_region(source,document['kind'],region['doc_id'],page=region['page'],box=region['box'],slide=region.get('slide'))
    actual_region['baseline_blocks_sha256']=sha256(raw).hexdigest()
    if actual_png!=png or actual_region!=region:raise ValueError('裁剪图或定位与原件重新渲染结果不一致')
    result=packet['result'];observations=validate_observations(result['raw_output'],result['finish_reason'])
    body=request_body(png,packet['model'],prompt_version=packet['prompt_version'])
    if ('request_sha256' in packet or packet['prompt_version']!=PROMPT_VERSION) and packet.get('request_sha256')!=digest(body):raise ValueError('视觉请求指纹不匹配')
    if packet.get('request_config')!={k:body[k] for k in ['model','temperature','enable_thinking','max_tokens','response_format']}:raise ValueError('视觉请求配置与本版本契约不一致')
    if observations!=result['observations']:raise ValueError('视觉转写与模型原始输出不一致')
    blocks=observation_blocks(region,observations,packet['model'],prompt_version=packet['prompt_version'])
    selection_path=folder/'selection-review.json'
    if selection_path.exists():
        from rag_app.visual_selection import select_observations
        selection=json.loads(selection_path.read_bytes());indices,meta=select_observations(packet,selection)
        by_index=dict(zip([i for i,r in enumerate(observations['observations']) if not r['uncertain']],blocks))
        blocks=[by_index[i] for i in indices]
        for block in blocks:
            block['metadata']['observation_selection']=meta
            if 'retained_warning_indices' in meta:
                block['metadata']['warnings']=[observations['warnings'][i] for i in meta['retained_warning_indices']]
    if not blocks:raise ValueError('没有可用的非uncertain视觉转写；不能创建空优化实验')
    for block in blocks:block['metadata'].update(bundle_sha256=packet['bundle_sha256'],origin=packet['origin'])
    return packet,blocks

def render_review(output,packet):
    esc=lambda v:html.escape(str(v))
    rows=''.join('<tr><td>'+esc(r['context'])+'</td><td>'+esc(r['text'])+'</td><td>'+('排除' if r['uncertain'] else '候选；仍需核对')+'</td></tr>' for r in packet['result']['observations']['observations'])
    page='''<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>原图与视觉转写核对</title><style>body{font:16px/1.7 system-ui;margin:24px auto;max-width:1100px;padding:0 18px;color:#24374b}img{max-width:100%;max-height:650px;object-fit:contain}table{width:100%;border-collapse:collapse;table-layout:fixed}td,th{padding:10px;border:1px solid #cad5df;overflow-wrap:anywhere}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#eef3f7;padding:16px}.notice{background:#fff3d6;padding:14px}</style><h1>原图 → 视觉转写 → 候选片段</h1><p class="notice">未经语义核验。格式正确不代表事实正确；uncertain=false也不代表已经人工确认。对照图题、型号、单位、箭头与分支逐条核对。</p>'''
    page+='<p>调用来源：'+esc(packet['origin'])+'；模型：'+esc(packet['model'])+'</p><img src="image.png" alt="从原件渲染的指定区域"><h2>转写候选</h2><table><thead><tr><th>图题与条件</th><th>模型转写</th><th>是否进入实验索引</th></tr></thead><tbody>'+rows+'</tbody></table><h2>警告</h2><pre>'+esc(json.dumps(packet['result']['observations']['warnings'],ensure_ascii=False,indent=2))+'</pre><details><summary>展开原件定位与渲染记录</summary><pre>'+esc(json.dumps(packet['region'],ensure_ascii=False,indent=2))+'</pre></details></html>'
    (Path(output)/'review.html').write_text(page,encoding='utf-8')
