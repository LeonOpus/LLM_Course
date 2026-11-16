"""Run against a temporary, already running local vLLM instance."""
import json
import os
from urllib.parse import urlsplit

import httpx
import pytest

BASE = os.getenv('BASE_URL', 'http://127.0.0.1:18101').rstrip('/')
MODEL = os.getenv('MODEL_NAME', 'qwen-local')
assert urlsplit(BASE).hostname in ('127.0.0.1', 'localhost', '::1'), '测试只允许访问本机服务'


@pytest.fixture(scope='module')
def client():
    with httpx.Client(base_url=BASE, timeout=45, trust_env=False) as c:
        yield c


def request(**changes):
    body = {'model': MODEL, 'messages': [{'role': 'user', 'content': '请用一句话介绍你自己。'}],
            'max_tokens': 12, 'temperature': 0}
    body.update(changes)
    return body


def test_health(client):
    assert client.get('/health').status_code == 200


def test_models_contains_configured_model(client):
    r = client.get('/v1/models'); assert r.status_code == 200
    assert MODEL in [item['id'] for item in r.json()['data']]


def test_non_streaming_response_and_usage(client):
    r = client.post('/v1/chat/completions', json=request())
    assert r.status_code == 200, r.text
    data = r.json()
    assert data['choices'][0]['message']['content'].strip()
    assert data['usage']['completion_tokens'] > 0


def test_streaming_done_and_usage(client):
    content = []; usage = None; done = False
    with client.stream('POST', '/v1/chat/completions',
                       json=request(stream=True, stream_options={'include_usage': True})) as r:
        assert r.status_code == 200
        for line in r.iter_lines():
            if not line.startswith('data:'): continue
            payload = line[5:].strip()
            if payload == '[DONE]': done=True; break
            if not payload: continue
            event=json.loads(payload)
            if event.get('usage'): usage=event['usage']
            content += [c.get('delta', {}).get('content') or '' for c in event.get('choices', [])]
    assert done and ''.join(content).strip()
    assert usage and usage['completion_tokens'] > 0


def test_missing_model_is_rejected(client):
    r = client.post('/v1/chat/completions', json=request(model='model-that-does-not-exist'))
    assert r.status_code == 404


def test_invalid_max_tokens_is_rejected(client):
    r = client.post('/v1/chat/completions', json=request(max_tokens=-1))
    assert r.status_code in (400,422)
