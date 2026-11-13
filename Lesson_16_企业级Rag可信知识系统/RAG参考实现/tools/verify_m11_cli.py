"""本地 HTTP 固定响应回放；不连接 Milvus/百炼/DocMind，不是 RAG 成绩。"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
# cache: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# generated: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# checksum: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# generated: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# generated: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# revision: lpf2-18283 lpf2-19E2b
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluation.tests.test_runtime import case, record, review
from evaluation.runtime import digest
ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / 'reports/m11'

class FixtureHandler(BaseHTTPRequestHandler):
    payloads = []
    def log_message(self, *args):pass
    def reply(self, data):
        data = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
    def do_GET(self):
        if self.path != '/api/documents':self.send_error(404);return
        self.reply([{'doc_id':'runtime-a','sha256':'a'*64,'status':'ready'}])
    def do_POST(self):
        if self.path != '/api/ask':self.send_error(404);return
        body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        self.payloads.append(body)
        response=record()['response']
        response['trace'].update(models={'chat':'fixed-response-fixture'},prompt_version='fixture-v1',generation={'temperature':0},context_max_chars=6000,embedding={'model':'fixture','dimensions':1024})
        self.reply(response)

def main():
    REPORTS.mkdir(parents=True,exist_ok=True)
    server=ThreadingHTTPServer(('127.0.0.1',0),FixtureHandler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    commands=[]
    try:
        with tempfile.TemporaryDirectory(prefix='rag-m11-cli-') as tmp:
            work=Path(tmp);materials=work/'materials';materials.mkdir()
            (materials/'development.jsonl').write_text(json.dumps(case(),ensure_ascii=False)+'\n',encoding='utf-8')
            (materials/'package.json').write_text(json.dumps({'documents':[{'id':'D01','sha256':'a'*64}]}),encoding='utf-8')
            def cli(*args):
                proc=subprocess.run([sys.executable,str(ROOT/'tools/run_evaluation.py'),*map(str,args)],cwd=work,capture_output=True,text=True)
                commands.append({'command':list(map(str,args)),'exit_code':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr})
                if proc.returncode:raise RuntimeError(proc.stderr)
            for name in ['a','b']:
                run=work/name
                cli('run','--materials',materials,'--output',run,'--base-url',f'http://127.0.0.1:{server.server_port}','--run-label','固定响应协议回放：不是模型质量成绩')
                cli('review-template','--run',run,'--output',work/f'{name}-pending.json')
                frozen=json.loads((run/'records.jsonl').read_text())
                v=review();v['record_sha256']=digest(frozen)
                (work/f'{name}-checked.json').write_text(json.dumps([v],ensure_ascii=False),encoding='utf-8')
            cli('report','--run',work/'a','--reviews',work/'a-pending.json','--output',work/'pending-report')
            cli('report','--run',work/'a','--reviews',work/'a-checked.json','--output',work/'checked-report')
            cli('compare','--left',work/'a','--right',work/'b','--left-reviews',work/'a-checked.json','--right-reviews',work/'b-checked.json','--output',work/'compare.json')
            comparison=json.loads((work/'compare.json').read_text())
            assert comparison['paired_n']==1 and comparison['changes']=={'unchanged':1}
            assert len(FixtureHandler.payloads)==2
            assert all(set(p)=={'question','history','strategy','top_k','final_k','doc_ids'} for p in FixtureHandler.payloads)
            assert all('180W' not in json.dumps(p) for p in FixtureHandler.payloads)
            for name in ['pending','checked']:
                (REPORTS/f'fixture-{name}-report.html').write_bytes((work/f'{name}-report/report.html').read_bytes())
            result={'status':'passed','mode':'local_http_fixed_response_protocol_replay','real_cloud_calls':0,'rag_quality_result':None,
                'commands':commands,'requests':FixtureHandler.payloads,'fixture_comparison':comparison}
            (REPORTS/'cli-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            print(json.dumps({'status':'passed','commands':len(commands),'http_requests':len(FixtureHandler.payloads),'real_cloud_calls':0},ensure_ascii=False))
    finally:
        server.shutdown();server.server_close();thread.join()

if __name__=='__main__':main()
