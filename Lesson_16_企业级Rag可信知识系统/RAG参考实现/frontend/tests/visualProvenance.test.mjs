import test from 'node:test';
import assert from 'node:assert/strict';
import {visualNotice,tableNotice} from '../src/visualProvenance.ts';
test('模型标记始终提示未核验，不因布尔值误改而背书',()=>{for(const semantic_verified of [false,true])assert.match(visualNotice({text_origin:'vision_model_unverified',vision_model:'test',semantic_verified}),/视觉模型转写.*未经语义核验/);});
test('旧片段没有视觉来源就不猜测',()=>{for(const v of [null,{},[],{text_origin:'docmind'}])assert.equal(visualNotice(v),null);});
test('表格降级提示不被错误的已核验字段覆盖',()=>{for(const table_structure_validated of [true,false])assert.match(tableNotice({table_representation:'provider_markdown_fallback',table_structure_validated}),/行列关系尚未核验/);});
test('正常表格不凭空标记结构异常',()=>{for(const v of [null,{},[],{parser:'docmind'}])assert.equal(tableNotice(v),null);});
