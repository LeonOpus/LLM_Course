"""Record a small, public-safe environment manifest for a benchmark run."""
import argparse
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def version(package):
    try:return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:return None


def sha256(path):
    digest=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(8*1024*1024), b''):digest.update(chunk)
    return digest.hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--model-dir',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();model=Path(a.model_dir)
    gpu=subprocess.run(['nvidia-smi','--query-gpu=name,memory.total,driver_version',
                        '--format=csv,noheader,nounits'],capture_output=True,text=True,check=True)
    data={'captured_at_utc':datetime.now(timezone.utc).isoformat(),
          'platform':platform.platform(),'python':sys.version.split()[0],
          'gpu_rows':gpu.stdout.strip().splitlines(),
          'packages':{p:version(p) for p in ('vllm','torch','transformers','httpx','uvicorn','outlines','lm-format-enforcer')},
          'model_name':model.name,'model_file_sha256':{name:sha256(model/name) for name in ('config.json','tokenizer_config.json','model.safetensors')},
          'server':{'model_alias':'qwen-local','dtype':'half','max_model_len':1024,
                    'gpu_memory_utilization':.45,'enforce_eager':True,'guided_decoding_backend':'lm-format-enforcer',
                    'host':'127.0.0.1','port':18101},
          'notes':'vLLM distribution reports 0.6.3; module reports dev because vllm._version is missing. This is a local GPU experiment, not an NPU or production result.'}
    output=Path(a.output)
    if output.exists():raise SystemExit('输出文件已存在，避免覆盖')
    output.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('已保存环境清单:',output)


if __name__=='__main__':main()
