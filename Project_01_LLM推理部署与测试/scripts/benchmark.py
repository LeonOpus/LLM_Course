"""Small client-side streaming benchmark for an OpenAI-compatible local server."""
import argparse
import asyncio
import csv
import json
import math
import os
import statistics
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import httpx

PROMPTS = [
    '请用简洁的中文解释大模型推理中的 KV Cache，并说明它的作用。',
    '请用简洁的中文解释首 token 延迟，并说明用户何时能看到回答。',
    '请解释什么是连续批处理，以及它对推理服务吞吐的作用。',
    '请简要说明模型显存不足时，可以从哪些方向排查。',
    '请说明模型推理测试中，为什么需要记录输入与输出长度。',
    '请说明推理服务的吞吐量与单次请求延迟有什么区别。',
]


def percentile(values, q):
    if not values:
        return None
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    low, high = math.floor(pos), math.ceil(pos)
    return ordered[low] + (ordered[high] - ordered[low]) * (pos - low)


def distribution(values):
    if not values:
        return {'n': 0, 'mean': None, 'p50': None, 'p95': None}
    return {'n': len(values), 'mean': statistics.mean(values),
            'p50': percentile(values, .50), 'p95': percentile(values, .95)}


def sample_gpu(stop, rows):
    while not stop.is_set():
        try:
            p = subprocess.run(['nvidia-smi', '--query-gpu=index,memory.used,utilization.gpu',
                                '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=3)
            if p.returncode == 0:
                for line in p.stdout.strip().splitlines():
                    idx, mem, util = (x.strip() for x in line.split(','))
                    rows.append({'timestamp_utc': datetime.now(timezone.utc).isoformat(),
                                 'index': idx, 'memory_used_mib': mem, 'gpu_util_percent': util})
        except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
            pass
        stop.wait(.5)


async def one(client, semaphore, args, index):
    queued = time.perf_counter()
    async with semaphore:
        start = time.perf_counter()
        row = {'request_id': index, 'client_queue_ms': (start-queued)*1000,
               'ok': False, 'http_status': None, 'error': None}
        first = None
        received_done = False
        finish_reason = None
        usage = None
        response_text = ''
        body = {'model': args.model, 'messages': [{'role': 'user', 'content': PROMPTS[index % len(PROMPTS)]}],
                'max_tokens': args.output_tokens, 'temperature': 0, 'stream': True,
                'stream_options': {'include_usage': True}}
        try:
            async with client.stream('POST', args.base_url.rstrip('/')+'/v1/chat/completions', json=body) as response:
                row['http_status'] = response.status_code
                if response.status_code != 200:
                    content = await response.aread()
                    row['error'] = f'HTTP {response.status_code}: '+content.decode('utf-8', 'replace')[:300]
                else:
                    async for line in response.aiter_lines():
                        if not line.startswith('data:'):
                            continue
                        data = line[5:].strip()
                        if data == '[DONE]':
                            received_done = True
                            break
                        if not data:
                            continue
                        event = json.loads(data)
                        if event.get('error'):
                            raise RuntimeError(str(event['error'])[:300])
                        if event.get('usage') is not None:
                            usage = event['usage']
                        for choice in event.get('choices', []):
                            piece = choice.get('delta', {}).get('content') or ''
                            if piece:
                                if first is None:
                                    first = time.perf_counter()
                                response_text += piece
                            if choice.get('finish_reason') is not None:
                                finish_reason = choice['finish_reason']
        except (httpx.HTTPError, ValueError, RuntimeError) as exc:
            row['error'] = f'{type(exc).__name__}: {str(exc)[:300]}'
        end = time.perf_counter()
        if row['error'] is None and not received_done:
            row['error'] = 'stream ended without [DONE]'
        if row['error'] is None and first is None:
            row['error'] = 'no non-empty text received'
        if row['error'] is None and not isinstance(usage, dict):
            row['error'] = 'missing server usage; cannot verify output token count'
        if row['error'] is None and (not isinstance(usage.get('completion_tokens'), int)
                                     or usage['completion_tokens'] < 1):
            row['error'] = 'missing or invalid completion_tokens'
        row.update({'duration_ms': (end-start)*1000,
                    'ttft_ms': (first-start)*1000 if first is not None else None,
                    'prompt_tokens': usage.get('prompt_tokens') if usage else None,
                    'output_tokens': usage.get('completion_tokens') if usage else None,
                    'finish_reason': finish_reason,
                    'text_chars': len(response_text)})
        if row['error'] is None:
            row['ok'] = True
            count = row['output_tokens']
            # End includes final SSE usage/[DONE] transport; a first output chunk can
            # contain multiple tokens, so this is a client-side approximation.
            row['tpot_ms'] = (row['duration_ms']-row['ttft_ms'])/(count-1) if count > 1 else None
        else:
            row['tpot_ms'] = None
        return row


async def run(args):
    run_dir = Path(args.output_dir)
    run_dir.mkdir(parents=True, exist_ok=False)
    semaphore = asyncio.Semaphore(args.concurrency)
    stop = threading.Event()
    gpu = []
    sampler = threading.Thread(target=sample_gpu, args=(stop, gpu), daemon=True)
    sampler.start()
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(args.timeout), trust_env=False) as client:
            # Warm-up is separate from the measured run.
            warmup = [await one(client, semaphore, args, i) for i in range(args.warmup)]
            if any(not row['ok'] for row in warmup):
                (run_dir/'warmup.json').write_text(json.dumps(warmup, ensure_ascii=False, indent=2))
                raise RuntimeError('预热失败，未开始计时；详情见 warmup.json')
            start = time.perf_counter()
            records = await asyncio.gather(*(one(client, semaphore, args, i) for i in range(args.requests)))
            wall = time.perf_counter() - start
    finally:
        stop.set()
        sampler.join(timeout=4)
        with (run_dir/'gpu.csv').open('w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['timestamp_utc','index','memory_used_mib','gpu_util_percent'])
            writer.writeheader(); writer.writerows(gpu)
    success = [r for r in records if r['ok']]
    summary = {'created_at_utc': datetime.now(timezone.utc).isoformat(),
               'base_url': args.base_url, 'model': args.model, 'concurrency': args.concurrency,
               'requests': args.requests, 'warmup': args.warmup, 'max_output_tokens': args.output_tokens,
               'workload': 'six short Chinese prompts, repeated; closed-loop concurrency',
               'wall_seconds': wall, 'success': len(success), 'failed': len(records)-len(success),
               'request_throughput_rps': len(success)/wall,
               'output_throughput_tokens_s': sum(r['output_tokens'] for r in success)/wall,
               'ttft_ms': distribution([r['ttft_ms'] for r in success]),
               'tpot_ms': distribution([r['tpot_ms'] for r in success if r['tpot_ms'] is not None]),
               'e2e_ms': distribution([r['duration_ms'] for r in success]),
               'prompt_tokens': distribution([r['prompt_tokens'] for r in success if isinstance(r['prompt_tokens'],int)]),
               'output_tokens': distribution([r['output_tokens'] for r in success]),
               'gpu_samples': len(gpu),
               'metric_notes': 'TTFT first non-empty text chunk; TPOT=(E2E-TTFT)/(server completion tokens-1); E2E ends at [DONE]. Client queue before semaphore excluded per request; throughput uses total wall time. SSE chunks may contain multiple tokens.'}
    (run_dir/'requests.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in records),encoding='utf-8')
    (run_dir/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    if len(success) != len(records):
        raise SystemExit('存在失败请求，结果已保存；请检查 requests.jsonl')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base-url', default='http://127.0.0.1:18101')
    p.add_argument('--model', default='qwen-local')
    p.add_argument('--concurrency',type=int,required=True)
    p.add_argument('--requests',type=int,default=24)
    p.add_argument('--warmup',type=int,default=2)
    p.add_argument('--output-tokens',type=int,default=48)
    p.add_argument('--timeout',type=float,default=120)
    p.add_argument('--output-dir',required=True)
    a=p.parse_args()
    if a.concurrency<1 or a.requests<1 or a.warmup<0 or a.output_tokens<1 or a.timeout<=0:
        p.error('concurrency, requests, output-tokens, timeout must be positive; warmup nonnegative')
    u=urlsplit(a.base_url)
    if u.scheme!='http' or u.hostname not in ('127.0.0.1','localhost','::1'):
        p.error('只接受本机 HTTP 地址，避免误向外部服务发起压测')
    asyncio.run(run(a))


if __name__=='__main__':main()
