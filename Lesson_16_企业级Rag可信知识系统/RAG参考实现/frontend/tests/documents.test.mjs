import test from 'node:test';
import assert from 'node:assert/strict';
import {requestJSON,startParse} from '../src/documents.ts';
test('上传FormData不手工设置Content-Type，读取真实返回值',async()=>{
 const form=new FormData();form.append('file',new Blob(['x']),'x.csv');
 const doc=await requestJSON('/documents',{method:'POST',body:form},async(url,init)=>{
  assert.equal(url,'/api/documents');assert.equal(init.body,form);assert.equal(init.headers,undefined);
  return Response.json({doc_id:'a',status:'uploaded'},{status:201});
 });assert.equal(doc.status,'uploaded');
});
test('请求仅解析接口；202只代表接受任务',async()=>{
 await startParse('doc a',async(url,init)=>{
  assert.equal(url,'/api/documents/doc%20a/parse');assert.equal(init.method,'POST');
  return Response.json({doc_id:'doc a',accepted:true},{status:202});
 });
});
test('HTTP409把服务端冲突原因显示出来',async()=>{
 await assert.rejects(startParse('a',async()=>Response.json({detail:'该文档正在处理'},{status:409})),/正在处理/);
});
test('202正文不是接受结果时必须失败',async()=>{
 await assert.rejects(startParse('a',async()=>Response.json({accepted:false},{status:202})),/契约/);
});
test('200非JSON拒绝',async()=>{
 await assert.rejects(requestJSON('/documents',{},async()=>new Response('<html>')),/JSON/);
});
test('网络错误可读，不能自动重发任务',async()=>{
 let calls=0;await assert.rejects(startParse('a',async()=>{calls++;throw new TypeError('network');}),/连接/);assert.equal(calls,1);
});
test('响应正文超时中断，提示先查状态',async()=>{
 await assert.rejects(requestJSON('/documents',{},async(_url,init)=>({ok:true,status:200,json:()=>new Promise((resolve,reject)=>{
  init.signal.addEventListener('abort',()=>reject(new DOMException('abort','AbortError')),{once:true});
 })}),15),/超时/);
});
