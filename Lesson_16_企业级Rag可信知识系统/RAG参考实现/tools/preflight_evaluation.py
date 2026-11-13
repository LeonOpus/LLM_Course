"""M11只读预检；只GET本机文档接口，不发送问答或模型请求。"""
import argparse,json,sys
from pathlib import Path
# revision: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# cache: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# checksum: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# revision: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# checksum: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# cache: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# checksum: lpf2-18283 lpf2-19E2b
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from evaluation.preflight import check_materials,audit_ready
from tools.run_evaluation import http_client

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--materials',default='materials/m06');p.add_argument('--base-url',default='http://127.0.0.1:8000');p.add_argument('--output',required=True);a=p.parse_args()
    dest=Path(a.output)
    if dest.exists():p.exit(1,'输出已存在，请换新文件保留原证据\n')
    try:
        material=check_materials(a.materials,ROOT);corpus=material.pop('corpus');documents=None;http_reads=0;error=None
        if material['ready']:
            try:http_reads+=1;documents=audit_ready(corpus,http_client(a.base_url)('/api/documents'))
            except Exception as exc:error={'type':type(exc).__name__,'message':'无法核对本机文档接口，请检查后端连接与返回结构；未发送问答'}
        ready=material['ready'] and documents is not None and documents['ready']
        report={'mode':'read_only_preflight','status':'corpus_ready' if ready else 'needs_attention','can_start_corpus_bound_run':ready,'materials':material,'application_documents':documents,'service_error':error,'http_get_attempts':http_reads,'ask_requests':0,'cloud_calls':0,'quality_verified':False,'next_step':'先按5.10核对真实服务单题，再启动20题正式运行' if ready else '处理本报告列出的材料或文档状态；不要执行整批问答'}
        dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
        print(json.dumps({'status':report['status'],'counts':material['counts'],'ready_documents':documents['matched'] if documents else None,'missing_documents':len(documents['missing']) if documents else None,'not_ready_documents':len(documents['not_ready']) if documents else None,'ask_requests':0,'output':str(dest)},ensure_ascii=False))
        return 0 if ready else 2
    except (ValueError,KeyError,OSError,json.JSONDecodeError) as exc:p.exit(1,f'预检输入无法读取或校验（{type(exc).__name__}），请核对目录与材料，未发送问答\n')
if __name__=='__main__':raise SystemExit(main())
