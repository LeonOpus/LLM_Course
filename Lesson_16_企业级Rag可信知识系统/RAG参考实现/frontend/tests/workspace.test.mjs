import test from 'node:test';
import assert from 'node:assert/strict';
import {fetchHealth} from '../src/health.ts';
import {documentCounts,createRequestGate,pageForHash} from '../src/workspace.ts';
import {consumeAnswer} from '../src/answer.ts';
const id='a'.repeat(32),hit={chunk_id:'c',doc_id:'d',text:'真实来源文本',locator:{line_start:1}};
const payload={status:'answered',answer:'有据的文本',citations:[hit],run_id:id,timing:{total_ms:1},trace:{run_id:id,mode:'live',candidates:[hit],context:[hit]}};
const response=events=>new Response(events.map(x=>'data: '+JSON.stringify(x)+'\n\n').join(''),{headers:{'Content-Type':'text/event-stream'}});
export const health={status:'ok',service:'rag-backend',verification:'configuration_only',configured:{bailian:false,docmind:false,rerank:false},models:{chat:'qwen-plus',embedding:'text-embedding-v4',dimension:1024},supported_extensions:['.csv'],strategies:['baseline','rerank'],context_configuration:{context_policy:'baseline'},index_configuration:{chunk_strategy:'baseline',collection:'x'},query_configuration:{retrieval_mode:'dense',query_rewrite:'off',generation_policy:'baseline'}};
test('概览读取完整公开配置，布尔配置不能冒充云调用成功',async()=>{assert.deepEqual(await fetchHealth(async()=>Response.json(health)),health);await assert.rejects(fetchHealth(async()=>Response.json({...health,configured:{bailian:'true'}})),/契约/);});
test('旧三字段health不足以支持完整页面',async()=>{await assert.rejects(fetchHealth(async()=>Response.json({status:'ok',service:'rag-backend',verification:'process_only'})),/契约/);});
test('概览统计只从实际文档列表计算',()=>{assert.deepEqual(documentCounts([{doc_id:'a',status:'parsed'},{doc_id:'b',status:'ready'},{doc_id:'c',status:'failed'}]),{total:3,ready:1});assert.throws(()=>documentCounts({count:100}));assert.throws(()=>documentCounts([{doc_id:'a',status:'invented'}]));});
test('新预览取消旧请求且旧身份失效',()=>{const gate=createRequestGate(),a=gate.begin(),b=gate.begin();assert.equal(a.signal.aborted,true);assert.equal(a.current(),false);assert.equal(b.current(),true);gate.dispose();assert.equal(b.signal.aborted,true);assert.equal(b.current(),false);});
test('最终结果缺字段或损坏时不展示',async()=>{for(const broken of [{...payload,trace:null},{...payload,citations:[{...hit,locator:null}]},{...payload,timing:{total_ms:-1}},{...payload,trace:{...payload.trace,run_id:'b'.repeat(32)}}])await assert.rejects(consumeAnswer('q',[],()=>{},undefined,async()=>response([{type:'result',payload:broken}])));});
test('跨运行混流在最终结果之前拦住',async()=>{const seen=[];await assert.rejects(consumeAnswer('q',[],e=>seen.push(e),undefined,async()=>response([{type:'phase',stage:'retrieve',run_id:'b'.repeat(32)},{type:'result',payload}])));assert.equal(seen.some(e=>e.type==='result'),false);});
test('完整结果保留真实trace、来源与耗时',async()=>{const seen=[];await consumeAnswer('q',[],e=>seen.push(e),undefined,async()=>response([{type:'phase',stage:'retrieve',run_id:id},{type:'result',payload}]));assert.deepEqual(seen.at(-1).payload,payload);});

test('页面书签仅接受已知入口，旧或未知入口回概览',()=>{assert.equal(pageForHash('#documents'),'文档');assert.equal(pageForHash('#ask'),'知识问答');assert.equal(pageForHash('#invented'),'概览');});
