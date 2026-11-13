import test from 'node:test';
import assert from 'node:assert/strict';
import {startIndex,searchCandidates} from '../src/retrieval.ts';
test('仅入库请求正确编码编号且202只代表已接受',async()=>{
 await startIndex('a b',async(url,init)=>{assert.equal(url,'/api/documents/a%20b/index');assert.equal(init.method,'POST');return Response.json({doc_id:'a b',accepted:true},{status:202});});
});
test('入库响应没有正确编号就拒绝',async()=>{await assert.rejects(startIndex('a',async()=>Response.json({doc_id:'b',accepted:true})),/契约/);});
test('入库失败只请求一次并显示原因',async()=>{
 let count=0;await assert.rejects(startIndex('a',async()=>{count++;return Response.json({detail:'先完成解析'},{status:409});}),/先完成解析/);assert.equal(count,1);
});
test('检索只提交问题和top_k，不偷偷触发生成',async()=>{
 const result=await searchCandidates('  X200功率  ',3,async(url,init)=>{assert.equal(url,'/api/retrieve');assert.deepEqual(JSON.parse(init.body),{question:'X200功率',top_k:3});return Response.json({mode:'live',candidate_count:1,candidates:[{chunk_id:'c1',text:'260W',score:.87,locator:{kind:'csv'}}]});});
 assert.equal(result.candidates[0].score,.87);
});
test('空库结果正常展示为空',async()=>{const result=await searchCandidates('x',10,async()=>Response.json({mode:'no_documents',candidate_count:0,candidates:[]}));assert.equal(result.candidates.length,0);});
test('候选数量与列表不符时不能展示伪成功',async()=>{await assert.rejects(searchCandidates('x',10,async()=>Response.json({mode:'live',candidate_count:4,candidates:[]})),/契约/);});
test('空问题和非法top_k在前端阻止',async()=>{
 const never=async()=>{throw new Error('不应发请求');};
 for(const [q,k] of [[' ',2],['x',0],['x',51],['x',1.5]])await assert.rejects(searchCandidates(q,k,never),/问题|top_k/);
});
