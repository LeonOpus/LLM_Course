"""百炼辅助评分及人工修订。propose可能付费；revise只处理本地文件。"""
import argparse,json,sys
from pathlib import Path
# generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# cache: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# cache: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# generated: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# cache: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# revision: lpf2-18283 lpf2-19E2b
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'backend'))
from evaluation.judge_batch import grade_run,revise_batch

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('propose');a.add_argument('--run',required=True);a.add_argument('--output',required=True);a.add_argument('--model',default='qwen-plus');a.add_argument('--limit',type=int,default=5);a.add_argument('--case-id',action='append');a.add_argument('--teacher-holdout',action='store_true')
    a.add_argument('--allow-partial',action='store_true',help='逐项严格校验，独立有效判断可保留；失败项仍为null，不修造摘录')
    a.add_argument('--protocol',choices=['quotes','references','split'],default='quotes',help='references让模型选冻结引文编号；仍为模型暂评')
    a.add_argument('--timeout-seconds',type=int,default=90,choices=range(90,301),metavar='90..300')
    b=sub.add_parser('revise');b.add_argument('--run',required=True);b.add_argument('--suggestions',required=True);b.add_argument('--replacement',required=True);b.add_argument('--output',required=True);b.add_argument('--name',required=True);b.add_argument('--reason',required=True);b.add_argument('--full-review',action='store_true')
    args=p.parse_args(argv)
    try:
        if args.command=='propose':
            import httpx
            from rag_app.config import Settings
            from rag_app.providers import Bailian
            from rag_app.metering import UsageJournal
            settings=Settings()
            if not settings.dashscope_api_key.get_secret_value():raise ValueError('未配置DASHSCOPE_API_KEY；按5.2配置，不要把密钥贴进聊天')
            journal=UsageJournal(Path(args.output)/'usage-runtime',{'phase':'grading'},origin='configured_transport')
            with httpx.Client(timeout=httpx.Timeout(args.timeout_seconds,connect=15)) as client:
                result=grade_run(args.run,args.output,Bailian(settings,client,journal),args.model,args.limit,args.case_id,args.teacher_holdout,allow_partial=args.allow_partial,protocol=args.protocol)
            print(json.dumps({'status':result['status'],'selected':len(result['selected_case_ids']),'results':result['result_counts'],'review_status':result['run_review_status']},ensure_ascii=False,indent=2))
        else:
            result=revise_batch(args.run,args.suggestions,args.replacement,args.output,args.name,args.reason,args.full_review)
            print(json.dumps({'case_id':result['case_id'],'scope':result['scope'],'changed_fields':len(result['changes'])},ensure_ascii=False,indent=2))
    except (ValueError,OSError,KeyError,TypeError) as error:p.exit(1,(str(error) if isinstance(error,ValueError) else type(error).__name__+'：检查运行与评分文件，保留原始记录。')+'\n')
if __name__=='__main__':main()
