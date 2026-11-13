import test from 'node:test';
import assert from 'node:assert/strict';
import {readContextDebug} from '../src/contextPresentation.ts';
const hit={chunk_id:'parent',doc_id:'D31',text:'原文条件',type:'parent_context',source_spans:[{text:'原文条件',locator:{line_start:7},char_range:[0,4]}]};
test('旧记录不猜测上下文策略与预算',()=>{assert.equal(readContextDebug({}).mode,'未知');assert.equal(readContextDebug(null).used,null);});
test('读取最终上下文而非候选；父块不伪造召回分数',()=>{const x=readContextDebug({context_profile:{mode:'parent_section'},context:[hit],selection:{text_chars:4,max_chars:6000,decisions:[]},candidates:[{text:'候选'}]});assert.equal(x.mode,'同小节原文补全');assert.equal(x.hits[0].text,'原文条件');assert.equal(x.hits[0].score,undefined);assert.deepEqual(x.hits[0].source_spans,hit.source_spans);assert.equal(x.used,4);});
test('回退、合并和预算排除要显示原因',()=>{const x=readContextDebug({selection:{decisions:[{action:'kept_child',reason:'parent_budget'},{action:'merged',reason:'parent_already_selected'},{action:'excluded',reason:'char_budget'}]}});assert.match(x.decisions[0].label,/预算.*保留子块/);assert.match(x.decisions[1].label,/合并/);assert.match(x.decisions[2].label,/排除/);});
test('异常预算与无效数组不显示为有效测量',()=>{const x=readContextDebug({context_profile:{mode:'invented'},context:'wrong',selection:{text_chars:-1,max_chars:'6000',decisions:[null]}});assert.equal(x.used,null);assert.equal(x.max,null);assert.deepEqual(x.hits,[]);assert.deepEqual(x.decisions,[]);});
