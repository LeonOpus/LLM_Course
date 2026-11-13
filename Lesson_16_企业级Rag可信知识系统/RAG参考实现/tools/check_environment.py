"""在项目根目录运行。仅输出配置是否存在，不输出密钥内容。"""
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import urllib.request

# cache: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# checksum: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# generated: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# cache: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# checksum: lpf2-18283 lpf2-19E2b
ROOT=Path(__file__).resolve().parents[1]

def command(name,args):
    executable=shutil.which(name)
    if not executable: return {'ok':False,'reason':f'找不到 {name}：安装后重新打开终端'}
    try:
        result=subprocess.run([executable,*args],capture_output=True,text=True,timeout=25)
        return {'ok':result.returncode==0,'version':result.stdout.strip()[:200] if result.returncode==0 else '',
                'reason':None if result.returncode==0 else '命令失败：检查工具是否启动、权限和终端环境'}
    except subprocess.TimeoutExpired: return {'ok':False,'reason':'命令超时'}

def endpoint(url):
    try:
        with urllib.request.urlopen(url,timeout=5) as response:
            return {'ok':response.status==200,'status_code':response.status}
    except Exception: return {'ok':False,'reason':'服务未启动或地址不匹配'}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--live-local',action='store_true',help='额外检查本机后端与 Milvus，不调用付费模型');args=parser.parse_args()
    env={}
    path=ROOT/'.env'
    if path.exists():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                k,v=line.split('=',1);env[k.strip()]=v.strip().strip('"\'')
    credentials={name:bool(os.environ.get(name) or env.get(name)) for name in ['DASHSCOPE_API_KEY','ALIBABA_CLOUD_ACCESS_KEY_ID','ALIBABA_CLOUD_ACCESS_KEY_SECRET']}
    result={'platform':platform.system(),'architecture':platform.machine(),'python_running_checker':platform.python_version(),
            'cwd_is_project_root':Path.cwd().resolve()==ROOT,'free_disk_gb':round(shutil.disk_usage(ROOT).free/1024**3,1),
            'files':{name:(ROOT/name).exists() for name in ['backend/pyproject.toml','backend/uv.lock','frontend/package.json','frontend/package-lock.json','infra/compose.yaml','branding/equipment-knowledge-hero.png']},
            'tools':{'uv':command('uv',['--version']),'node':command('node',['--version']),'npm':command('npm',['--version']),
                     'docker_client':command('docker',['--version']),'docker_server':command('docker',['version','--format','{{.Server.Version}}']),
                     'docker_compose':command('docker',['compose','version','--short'])},
            'credentials_present':credentials,'credential_check':'presence_only_not_validity'}
    if args.live_local:
        result['local_services']={'backend':endpoint('http://127.0.0.1:8000/api/health'),'milvus':endpoint('http://127.0.0.1:9091/healthz')}
    result['local_tools_ok']=all(v['ok'] for v in result['tools'].values()) and all(result['files'].values())
    print(json.dumps(result,ensure_ascii=False,indent=2))
    output=ROOT/'reports'/f'environment-{platform.system().lower()}.json';output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return 0 if result['local_tools_ok'] else 1

if __name__=='__main__': sys.exit(main())
