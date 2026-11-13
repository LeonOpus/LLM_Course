"""真实教学原图 + 固定HTTP响应；零云调用，不是视觉模型准确率实验。"""
import argparse,json,sys,shutil
from pathlib import Path
from hashlib import sha256
import httpx
# generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# checksum: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# cache: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# checksum: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# cache: lpf2-18283 lpf2-19E2b
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from rag_app.config import Settings
from rag_app.pipeline import Pipeline
from rag_app.docmind import save_json
from rag_app.visual_workflow import prepare_region,transcribe_region
from rag_app.experiments import prepare_experiment
from rag_app.indexing import preview_chunks

def demo(output):
    output=Path(output).resolve()
    if output.exists():raise ValueError('演练目录已存在，请换新名字')
    material=ROOT/'practice/m19a/materials';proof=json.loads((material/'provenance.json').read_bytes())
    source=material/proof['file'];raw=source.read_bytes()
    if sha256(raw).hexdigest()!=proof['source_sha256']:raise ValueError('教学原件指纹变化')
    pipeline=Pipeline(Settings(_env_file=None,runtime_dir=output/'baseline',dashscope_api_key=''))
    pipeline.store.create('D35',source.name,'image',proof['source_sha256']);folder=pipeline.folder('D35');folder.mkdir(parents=True)
    (folder/'source.png').write_bytes(raw)
    baseline=[{'doc_id':'D35','type':'text','text':'X200 IN OUT DRAIN 供液容器 用液端 维护排液路径',
               'locator':{'kind':'image','block_id':'fixture-labels'},'metadata':{'parser':'authored_fixture_not_docmind'}}]
    save_json(folder/'blocks.json',baseline);pipeline.store.move('D35','parsing');pipeline.store.move('D35','parsed')
    before=(folder/'blocks.json').read_bytes();prepare_region(pipeline,'D35',output/'region')
    calls=[]
    def handler(request):
        body=json.loads(request.content);calls.append({'model':body['model'],'message_count':len(body['messages'])})
        observations={'observations':[
            {'context':'X200接口与流向图；蓝色实线为正常输送路径','text':'供液容器经IN进入设备，设备经OUT通向用液端。','uncertain':False},
            {'context':'X200接口与流向图；铜色虚线为停机维护排液路径','text':'DRAIN指向维护排液路径，停机维护排液口不能当作正常输送出口。','uncertain':False},
            {'context':'图中未标出','text':'不能由此确认内部机械结构或阀门操作。','uncertain':True}], 'warnings':['固定响应只测试流程；实际视觉输出可能不同。']}
        return httpx.Response(200,json={'model':'fixture-qwen3-vl-plus','choices':[{'message':{'content':json.dumps(observations,ensure_ascii=False)},'finish_reason':'stop'}], 'usage':{'prompt_tokens':120,'completion_tokens':80,'total_tokens':200}})
    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        attempt=transcribe_region(output/'region',output/'bundle',Settings(_env_file=None,dashscope_api_key='fixture'),http=http,origin='fixture')
    manifest=prepare_experiment(output/'baseline',output/'augmented','baseline',visual_bundles=[output/'bundle'])
    optimized=Pipeline(Settings(_env_file=None,runtime_dir=output/'augmented',milvus_collection=manifest['collection'],dashscope_api_key=''))
    a=preview_chunks(pipeline,'D35');b=preview_chunks(optimized,'D35')
    assert (folder/'blocks.json').read_bytes()==before and len(calls)==1 and attempt['state']=='succeeded'
    report={'status':'passed','docmind_called':False,'bailian_called':False,'milvus_called':False,
            'http_origin':'fixture','semantic_quality_measured':False,'baseline_unchanged':True,
            'baseline_chunk_count':a['chunk_count'],'augmented_chunk_count':b['chunk_count'],
            'baseline':a,'augmented':b,'collection_prepared_but_uncreated':manifest['collection'],
            'limitations':['基线标签为人工演练块，不是DocMind返回。','视觉关系为固定响应，不是百炼识图结果。','1→3是片段数量，不是召回率或准确率提升。']}
    save_json(output/'comparison.json',report)
    return {k:v for k,v in report.items() if k not in {'baseline','augmented'}}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    try:print(json.dumps(demo(args.output),ensure_ascii=False,indent=2))
    except (OSError,ValueError) as error:parser.exit(1,str(error)+'\n')
