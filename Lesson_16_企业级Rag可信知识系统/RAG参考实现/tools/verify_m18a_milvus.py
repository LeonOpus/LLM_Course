"""真实本地Milvus BM25 + 原文补全；向量为人工常量，零云调用。"""
from pathlib import Path
import argparse,json,sys,tempfile
from unittest.mock import patch
# generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# generated: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# generated: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# revision: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# checksum: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# generated: lpf2-18283 lpf2-19E2b
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'));sys.path.insert(0,str(ROOT/'tools'))
from demo_context import read_materials
from rag_app.config import Settings
from rag_app.pipeline import Pipeline
from rag_app.docmind import save_json
from rag_app.experiments import prepare_experiment
from rag_app.indexing import index_document,retrieve
from rag_app.context import select_for_pipeline
from rag_app.vectorstore import VectorStore

def verify(output="reports/m18a-milvus-01"):
    out=Path(output)
    if out.exists():raise ValueError("输出目录已存在，请换新编号；尚未连接Milvus")
    blocks,proof=read_materials();vector=None;name=None;cleanup=None
    with tempfile.TemporaryDirectory(prefix='rag-m18a-') as tmp:
        folder=Path(tmp);source=Pipeline(Settings(_env_file=None,runtime_dir=folder/'source',dashscope_api_key=''))
        source.store.create('D31',proof['source_file'],'md',proof['source_sha256']);doc=source.folder('D31');doc.mkdir(parents=True)
        (doc/'source.md').write_bytes((ROOT/'practice/m18a/materials'/proof['source_file']).read_bytes())
        save_json(doc/'blocks.json',blocks);source.store.move('D31','parsing');source.store.move('D31','parsed',block_count=len(blocks))
        manifest=prepare_experiment(source.settings.runtime_dir,folder/'experiment','baseline',full_text=True)
        settings=Settings(_env_file=None,runtime_dir=folder/'experiment',milvus_collection=manifest['collection'],
                          milvus_full_text=True,retrieval_mode='bm25',dashscope_api_key='')
        vector=VectorStore(settings);name=settings.milvus_collection
        if vector.client.has_collection(name):raise ValueError('随机实验集合意外已存在，不接管该集合')
        try:
            pipeline=Pipeline(settings)
            with patch('rag_app.indexing.Bailian') as provider:
                provider.return_value.embed.side_effect=lambda texts:[[1.]+[0.]*1023 for _ in texts]
                index_document(pipeline,'D31');provider.return_value.embed.reset_mock()
                result=retrieve(pipeline,'case_id WO-001 attachments',top_k=3,doc_ids=['D31'])
                provider.return_value.embed.assert_not_called();provider.return_value.answer.assert_not_called()
            assert result['candidates'] and result['candidates'][0]['score_kind']=='bm25'
            before=select_for_pipeline(pipeline,result['candidates'],result['index_profile'],final_k=1)
            settings.context_policy='parent_section'
            after=select_for_pipeline(pipeline,result['candidates'],result['index_profile'],final_k=1)
            by_id={b['locator']['block_id']:b for b in blocks}
            for h in after['hits']:
                for s in h.get('source_spans',[]):
                    original=by_id[s['locator']['block_id']]
                    assert s['text']==original['text'][slice(*s['char_range'])] and s['locator']==original['locator']
            details={'server_version':vector.client.get_server_version(),'query':'case_id WO-001 attachments',
                     'retrieval':result,'baseline':before,'parent_section':after,
                     'source_spans_exact':True,'embedding_origin':'synthetic_constant_1024',
                     'docmind_called':False,'bailian_called':False,'cloud_calls':0,'semantic_quality_measured':False}
        finally:
            if vector.client.has_collection(name):vector.client.drop_collection(name)
            cleanup={'collection':name,'removed':not vector.client.has_collection(name)};vector.client.close()
    report={'status':'passed','details':details,'cleanup':cleanup,'temporary_directory_removed':not folder.exists(),
            'scope':'实际Milvus BM25检索与原文补全；不是百炼语义召回或答案质量实验'}
    out.mkdir(parents=True,exist_ok=False)
    (out/'milvus-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    return {k:v for k,v in report.items() if k!='details'}
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',default='reports/m18a-milvus-01');args=parser.parse_args()
    try:print(json.dumps(verify(args.output),ensure_ascii=False,indent=2))
    except (ValueError,OSError) as error:parser.exit(1,str(error)+'\n')
