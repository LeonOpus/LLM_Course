import test from 'node:test';
import assert from 'node:assert/strict';
import {fetchHealth} from '../src/health.ts';

const HEALTH={status:'ok',service:'rag-backend',verification:'configuration_only',configured:{bailian:false,docmind:false,rerank:false},models:{chat:'qwen-plus',embedding:'text-embedding-v4',dimension:1024},supported_extensions:['.csv'],strategies:['baseline','rerank'],context_configuration:{context_policy:'baseline'},index_configuration:{chunk_strategy:'baseline',collection:'x'},query_configuration:{retrieval_mode:'dense',query_rewrite:'off',generation_policy:'baseline'}};

test('发出真实形状的GET请求，读取status=ok', async () => {
  let calls = 0;
  const result = await fetchHealth(async (url, init) => {
    calls++;
    assert.equal(url, '/api/health');
    assert.equal(init.method, 'GET');
    assert.ok(init.signal instanceof AbortSignal);
    return new Response(JSON.stringify(HEALTH));
  });
  assert.equal(calls, 1);
  assert.deepEqual(result, HEALTH);
});
test('网络失败不能冒充已连接', async () => {
  await assert.rejects(fetchHealth(async () => {throw new TypeError('Failed to fetch');}), /网络|无法连接/);
});
test('HTTP503不能冒充成功', async () => {
  await assert.rejects(fetchHealth(async () => new Response('upstream unavailable', {status: 503})), /503/);
});
test('200但不是JSON也必须失败', async () => {
  await assert.rejects(fetchHealth(async () => new Response('<html>proxy page</html>')), /JSON/);
});
test('200且JSON不符合契约必须失败', async () => {
  await assert.rejects(fetchHealth(async () => new Response(JSON.stringify({status: 'failed'}))), /响应格式/);
});
test('超时终止请求，给出可理解的信息', async () => {
  let aborted = false;
  await assert.rejects(fetchHealth(async (_url, init) => new Promise((_resolve, reject) => {
    init.signal.addEventListener('abort', () => {aborted = true; reject(new DOMException('Aborted', 'AbortError'));}, {once: true});
  }), 15), /超时/);
  assert.equal(aborted, true);
});
test('响应头已到但JSON正文超时，也必须显示超时', async () => {
  await assert.rejects(fetchHealth(async (_url, init) => ({
    ok: true, status: 200,
    json: () => new Promise((_resolve, reject) => {
      init.signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')), {once: true});
    })
  }), 15), /超时/);
});

test('上下文策略必须由后端明确返回，缺失或未知不可猜测',async()=>{for(const context_configuration of [undefined,{context_policy:'invented'}])await assert.rejects(fetchHealth(async()=>Response.json({...HEALTH,context_configuration})),/上下文/);const result=await fetchHealth(async()=>Response.json({...HEALTH,context_configuration:{context_policy:'parent_section'}}));assert.equal(result.context_configuration.context_policy,'parent_section');});
