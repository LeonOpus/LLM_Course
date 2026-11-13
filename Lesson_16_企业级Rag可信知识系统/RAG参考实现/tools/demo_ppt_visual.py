"""实际PPT转换+固定视觉响应演练。需要本机LibreOffice，不调用云。"""
import argparse,json,sys
from pathlib import Path
from hashlib import sha256
import httpx
# generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# checksum: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# revision: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# generated: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# revision: lpf2-18283 lpf2-19E2b
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from rag_app.config import Settings
from rag_app.pipeline import Pipeline
from rag_app.docmind import save_json
from rag_app.visual_workflow import prepare_region,transcribe_region,validate_bundle
from rag_app.experiments import prepare_experiment
from rag_app.indexing import preview_chunks

def demo(output):
    output=Path(output).resolve()
    if output.exists():raise ValueError('演练目录已存在，请换新名字')
    materials=ROOT/'practice/m19b/materials';proof=json.loads((materials/'provenance.json').read_bytes())
    raw=(materials/proof['file']).read_bytes()
    if sha256(raw).hexdigest()!=proof['source_sha256']:raise ValueError('PPT教学原件指纹变化')
    p=Pipeline(Settings(_env_file=None,runtime_dir=output/'baseline',dashscope_api_key=''))
    p.store.create('D26',proof['file'],'pptx',proof['source_sha256']);folder=p.folder('D26');folder.mkdir(parents=True)
    (folder/'source.pptx').write_bytes(raw)
    blocks=[{'doc_id':'D26','type':'text','text':'X200 压力 流量 bar L/min',
             'locator':{'kind':'pptx','slide':5,'block_id':'fixture-labels'},'metadata':{'parser':'manual_fixture_not_docmind'}}]
    save_json(folder/'blocks.json',blocks);p.store.move('D26','parsing');p.store.move('D26','parsed')
    baseline=(folder/'blocks.json').read_bytes();region=prepare_region(p,'D26',output/'region',slide=5)
    def response(request):
        assert json.loads(request.content)['messages'][1]['content'][0]['type']=='image_url'
        result={'observations':[{'context':'X200压力与流量曲线；20°C清水、额定供电','text':'出口压差1 bar对应流量3.6 L/min；出口压差2 bar时流量为0，不能承诺此点持续输送。','uncertain':False}],
                'warnings':['固定响应演练，不是百炼真实识图；曲线只提供离散点，不能外推为已测结果。']}
        return httpx.Response(200,json={'model':'fixture-visual','choices':[{'message':{'content':json.dumps(result,ensure_ascii=False)},'finish_reason':'stop'}]})
    with httpx.Client(transport=httpx.MockTransport(response)) as http:
        attempt=transcribe_region(output/'region',output/'bundle',Settings(_env_file=None,dashscope_api_key='fixture'),http=http,origin='fixture')
    validate_bundle(output/'bundle',p.settings.runtime_dir)
    manifest=prepare_experiment(p.settings.runtime_dir,output/'augmented','baseline',visual_bundles=[output/'bundle'])
    q=Pipeline(Settings(_env_file=None,runtime_dir=output/'augmented',milvus_collection=manifest['collection']))
    preview=preview_chunks(q,'D26');assert len(preview['chunks'])==2 and attempt['state']=='succeeded'
    assert (folder/'blocks.json').read_bytes()==baseline
    visual=preview['chunks'][-1];assert visual['locator']['slide']==5 and 'page' not in visual['locator']
    report={'status':'passed','original_pptx_sha256':proof['source_sha256'],'renderer_version':region['office']['renderer_version'],
            'slide_count':region['office']['slide_count'],'slide':5,'source_slide':region['source_slide'],
            'baseline_unchanged':True,'baseline_blocks':1,'augmented_blocks':2,'cloud_calls':0,
            'docmind_origin':'manual_fixture','vision_origin':'fixture','semantic_quality_measured':False,
            'native_text_checks':region['office']['native_text_checks'],'preview':preview,
            'notice':'实际LibreOffice与来源绑定；没有真实DocMind、视觉识别、Embedding、Milvus或问答质量实验'}
    save_json(output/'comparison.json',report);return {k:v for k,v in report.items() if k not in {'preview','native_text_checks'}}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    try:print(json.dumps(demo(a.output),ensure_ascii=False,indent=2))
    except (OSError,ValueError) as e:p.exit(1,str(e)+'\n')
