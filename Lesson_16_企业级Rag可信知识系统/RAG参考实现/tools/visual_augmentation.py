"""PDF/图片原图裁剪与百炼视觉转写。prepare不调用云；transcribe每次最多一次请求。"""
import argparse,json,sys
from pathlib import Path
# generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# revision: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# generated: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# revision: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# generated: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# generated: lpf2-18283 lpf2-19E2b
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from rag_app.config import Settings
from rag_app.pipeline import Pipeline
from rag_app.visual_workflow import prepare_region,transcribe_region

def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('prepare');p.add_argument('--runtime',type=Path,required=True)
    identity=p.add_mutually_exclusive_group(required=True);identity.add_argument('--doc-id');identity.add_argument('--document-name',help='与上传时完全相同的文件名；重名时必须改用doc-id')
    p.add_argument('--page',type=int);p.add_argument('--slide',type=int);p.add_argument('--box',nargs=4,type=float);p.add_argument('--output',type=Path,required=True)
    p=sub.add_parser('transcribe');p.add_argument('--region',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--prompt-version',choices=['visual-transcription-m19a-v1','visual-relations-m24-v2'],default='visual-transcription-m19a-v1')
    args=parser.parse_args()
    try:
        if args.command=='prepare':
            if not (args.runtime/'documents.sqlite3').is_file():raise ValueError('runtime不存在或不是已解析运行目录；本次不会创建空库')
            pipeline=Pipeline(Settings(runtime_dir=args.runtime.resolve()))
            doc_id=args.doc_id
            if args.document_name:
                matches=[d for d in pipeline.store.list() if d['name']==args.document_name]
                if len(matches)!=1:raise ValueError('文件名未找到或存在重名；在文档列表核对doc_id')
                doc_id=matches[0]['doc_id']
            result=prepare_region(pipeline,doc_id,args.output,page=args.page,box=args.box,slide=args.slide)
        else:result=transcribe_region(args.region,args.output,Settings(),prompt_version=args.prompt_version)
    except (OSError,ValueError,KeyError,TypeError) as error:
        parser.exit(1,(str(error) if isinstance(error,ValueError) else type(error).__name__+'：检查目录与输入清单')+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if result.get('state')=='failed':raise SystemExit(1)

if __name__=='__main__':main()
