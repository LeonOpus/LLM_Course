import test from 'node:test';
import assert from 'node:assert/strict';
import {parseComparison,percent,filterCases,hasFixtureEvidence} from '../src/evaluation.ts';
import {readFileSync} from 'node:fs';
const fixture=()=>JSON.parse(readFileSync(new URL('./fixtures/comparison.json',import.meta.url),'utf8'));
test('待复核不是0%',()=>{assert.equal(percent(null),'待确认 / 不适用');assert.equal(percent(0),'0.0%');});
test('导入工具产物并保留演练来源',()=>{const x=parseComparison(JSON.stringify(fixture()));assert.equal(x.runs.before.config.execution_origin,'protocol_fixture');assert.equal(x.comparison.paired_n,0);});
test('空文件和错误版本不展示旧成绩',()=>{assert.throws(()=>parseComparison(''));const x=fixture();x.schema_version='unknown';assert.throws(()=>parseComparison(JSON.stringify(x)),/版本/);});
test('不一致的pending数被拒绝',()=>{const x=fixture();x.comparison.pending=0;assert.throws(()=>parseComparison(JSON.stringify(x)),/配对/);});
test('未复核不能伪装成gain',()=>{const x=fixture();x.cases[0].change='gain';assert.throws(()=>parseComparison(JSON.stringify(x)),/变化/);});
test('重复题号不能虚增样本量',()=>{const x=fixture();x.cases.push(x.cases[0]);assert.throws(()=>parseComparison(JSON.stringify(x)),/题号|数量/);});
test('分母不足时不能声称有百分比',()=>{const x=fixture();x.runs.before.metrics.answer_accuracy.value=1;assert.throws(()=>parseComparison(JSON.stringify(x)),/指标/);});
test('过滤按状态分类和问题同时生效',()=>{const x=parseComparison(JSON.stringify(fixture()));assert.equal(filterCases(x.cases,'pending','T01','180').length,0);assert.equal(filterCases(x.cases,'pending','T01','X100').length,1);assert.equal(filterCases(x.cases,'gain','','').length,0);});
test('HTML样式的回答保留为普通文本',()=>{const x=fixture();x.cases[0].before.answer='<img src=x onerror=alert(1)>';assert.equal(parseComparison(JSON.stringify(x)).cases[0].before.answer,x.cases[0].before.answer);});
test('畸形耗时不能让展开题目时页面崩溃',()=>{const x=fixture();x.cases[0].before.elapsed_ms='soon';assert.throws(()=>parseComparison(JSON.stringify(x)),/耗时/);});

const changed=()=>JSON.parse(readFileSync(new URL('./fixtures/comparison-changes.json',import.meta.url),'utf8'));
test('逐题评分与汇总正确率必须一致',()=>{const x=changed();x.runs.before.metrics.answer_accuracy.value=0.99;assert.throws(()=>parseComparison(JSON.stringify(x)),/正确率/);});
test('逐题执行状态与汇总数量必须一致',()=>{const x=fixture();x.runs.before.execution_counts={error:1};assert.throws(()=>parseComparison(JSON.stringify(x)),/执行/);});
test('失败运行不能混入已确认正确率',()=>{const x=changed();x.cases[0].before.execution='error';assert.throws(()=>parseComparison(JSON.stringify(x)),/失败|执行/);});
test('完整四题演练仍然有效',()=>{const x=parseComparison(JSON.stringify(changed()));assert.equal(x.comparison.paired_n,3);assert.equal(x.comparison.pending,1);assert.equal(x.comparison.answer_accuracy_delta,0);});

function unmarked(){const x=fixture();delete x.runs.before.config.execution_origin;delete x.runs.after.config.execution_origin;return x;}
test('用量事件已经标为fixture时比较页不能漏掉演练提示',()=>{const x=unmarked();x.runs.before.request_usage={origins:{fixture:2}};assert.equal(hasFixtureEvidence(x),true);});
test('仅逐题trace留有固定事件也显示演练提示',()=>{const x=unmarked();x.cases[0].after.trace.usage_events=[{origin:'fixture'}];assert.equal(hasFixtureEvidence(x),true);});
test('configured_transport不自动宣称已证实云调用或固定演练',()=>{const x=unmarked();x.runs.before.request_usage={origins:{configured_transport:2}};assert.equal(hasFixtureEvidence(x),false);});
test('旧包来源标记继续识别',()=>{assert.equal(hasFixtureEvidence(fixture()),true);});

test('仅视觉索引含固定候选也必须显示演练提示',()=>{const index_profile={visual_augmentation:{bundles:[{origin:'fixture'}]}};for(const target of ['run','trace']){const x=unmarked();if(target==='run')x.runs.after.observed_configurations=[{index_profile}];else x.cases[0].after.trace.index_profile=index_profile;assert.equal(hasFixtureEvidence(x),true);}});
test('配置通路的视觉包不能被猜成固定演练',()=>{const x=unmarked();x.runs.after.observed_configurations=[{index_profile:{visual_augmentation:{bundles:[{origin:'configured_transport'}]}}}];assert.equal(hasFixtureEvidence(x),false);});
