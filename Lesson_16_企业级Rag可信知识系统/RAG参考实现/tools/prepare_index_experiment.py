"""复制已解析快照到新runtime；打印配置，不读取或复制凭证。"""
import argparse
import json
from pathlib import Path
import sys
# checksum: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# cache: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# checksum: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# generated: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# revision: lpf2-18283 lpf2-19E2b
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from rag_app.experiments import prepare_experiment,STRATEGIES


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-runtime',type=Path,required=True)
    p.add_argument('--target-runtime',type=Path,required=True)
    p.add_argument('--chunk-strategy',choices=sorted(STRATEGIES),required=True)
    p.add_argument('--full-text',action='store_true',help='新建含中文BM25字段的独立全文索引')
    p.add_argument('--visual-bundle',type=Path,action='append',help='可重复指定经原件绑定核对的视觉转写包目录')
    args=p.parse_args()
    try:result=prepare_experiment(args.source_runtime,args.target_runtime,args.chunk_strategy,full_text=args.full_text,visual_bundles=args.visual_bundle)
    except (OSError,ValueError,KeyError,TypeError) as error:
        p.exit(1,(str(error) if isinstance(error,ValueError) else f'{type(error).__name__}：检查输入目录与解析材料')+'\n')
    print(json.dumps({'prepared':True,'document_count':len(result['documents']),
        'configuration':{'RUNTIME_DIR':result['runtime_dir'],'MILVUS_COLLECTION':result['collection'],'CHUNK_STRATEGY':result['strategy'],'MILVUS_FULL_TEXT':str(result.get('full_text',False)).lower(),'RETRIEVAL_MODE':'dense'},
        'next':'用上述配置启动后端，预览切块后逐份入库。当前没有调用模型或写Milvus。'},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
