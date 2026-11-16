import asyncio
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import httpx

path=Path(__file__).resolve().parents[1]/'scripts'/'benchmark.py'
spec=importlib.util.spec_from_file_location('benchmark',path)
benchmark=importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)


def test_percentile_interpolates_and_handles_empty():
    assert benchmark.percentile([], .95) is None
    assert benchmark.percentile([3,1,2], .5)==2
    assert benchmark.percentile([0,10], .95)==9.5


def run_request(body):
    def handler(_request):
        return httpx.Response(200, text=body, headers={'content-type':'text/event-stream'})
    async def run():
        args=SimpleNamespace(base_url='http://127.0.0.1:18101',model='local',output_tokens=4)
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await benchmark.one(client,asyncio.Semaphore(1),args,0)
    return asyncio.run(run())


def test_stream_reports_usage_and_tpot():
    row=run_request('data: {"choices":[{"delta":{"content":"你好"},"finish_reason":null}]}\n\n'
                    'data: {"choices":[],"usage":{"prompt_tokens":10,"completion_tokens":3}}\n\n'
                    'data: [DONE]\n\n')
    assert row['ok'] and row['output_tokens']==3 and row['ttft_ms'] is not None
    assert row['tpot_ms'] >= 0


def test_stream_missing_usage_is_failure_not_zero_throughput():
    row=run_request('data: {"choices":[{"delta":{"content":"你好"}}]}\n\n'
                    'data: [DONE]\n\n')
    assert not row['ok'] and 'usage' in row['error'] and row['tpot_ms'] is None
