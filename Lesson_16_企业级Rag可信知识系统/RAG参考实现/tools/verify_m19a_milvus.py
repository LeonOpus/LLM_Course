"""Actual local Milvus BM25 transport test, with fixed vision response and synthetic vectors."""
import argparse,json,sys,tempfile
from pathlib import Path
from unittest.mock import patch
# generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# cache: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# revision: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# cache: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# checksum: lpf2-18283 lpf2-19E2b
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'));sys.path.insert(0,str(ROOT/'tools'))
from demo_visual import demo
from rag_app.config import Settings
from rag_app.pipeline import Pipeline
from rag_app.experiments import prepare_experiment
from rag_app.indexing import index_document,retrieve
from rag_app.vectorstore import VectorStore
from rag_app.generation import validate_answer
from rag_app.docmind import save_json

def verify(output="reports/m19a-milvus-01"):
    output=Path(output)
    if output.exists():raise ValueError("Output exists; Milvus has not been connected. Choose a new output directory.")
    with tempfile.TemporaryDirectory(prefix='rag-m19a-') as tmp:
        root=Path(tmp);demo(root/'demo')
        manifest=prepare_experiment(root/'demo/baseline',root/'experiment','baseline',full_text=True,visual_bundles=[root/'demo/bundle'])
        settings=Settings(_env_file=None,runtime_dir=root/'experiment',milvus_collection=manifest['collection'],milvus_full_text=True,retrieval_mode='bm25',dashscope_api_key='')
        vector=VectorStore(settings);name=settings.milvus_collection;details=None;removed=False
        if vector.client.has_collection(name):raise ValueError('随机集合已存在，不接管')
        try:
            pipeline=Pipeline(settings)
            with patch('rag_app.indexing.Bailian') as provider:
                provider.return_value.embed.side_effect=lambda texts:[[1.]+[0.]*1023 for _ in texts]
                index_document(pipeline,'D35');provider.return_value.embed.reset_mock()
                result=retrieve(pipeline,'停机维护排液口不能当作正常输送出口',top_k=10)
                provider.return_value.embed.assert_not_called()
            hits=[h for h in result['candidates'] if h.get('metadata',{}).get('text_origin')=='vision_model_unverified']
            assert hits and all(h['metadata']['origin']=='fixture' for h in hits)
            assert result['index_profile']['visual_augmentation']==manifest['visual_augmentation']
            answer=validate_answer(json.dumps({'status':'answered','answer':'固定协议回答，不是模型生成。','citation_ids':[hits[0]['chunk_id']]}),hits)
            assert answer['citations'][0]['metadata']['semantic_verified'] is False
            details={'server_version':vector.client.get_server_version(),'retrieval':result,'citation':answer['citations'][0],
                     'vector_origin':'synthetic_constant_1024','vision_origin':'fixture','docmind_called':False,'bailian_called':False,'cloud_calls':0,'semantic_quality_measured':False}
        finally:
            if vector.client.has_collection(name):vector.client.drop_collection(name)
            removed=not vector.client.has_collection(name);vector.client.close()
    report={'status':'passed','details':details,'cleanup':{'collection':name,'removed':removed},'temporary_directory_removed':not root.exists(),
            'scope':'原图绑定、视觉候选、实际Milvus BM25、引用元数据传递；不证明识图、语义召回或问答质量'}
    save_json(output/'milvus-verification.json',report)
    return {k:v for k,v in report.items() if k!='details'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',default='reports/m19a-milvus-01');a=p.parse_args()
    try:print(json.dumps(verify(a.output),ensure_ascii=False,indent=2))
    except (OSError,ValueError) as error:p.exit(1,str(error)+'\n')
