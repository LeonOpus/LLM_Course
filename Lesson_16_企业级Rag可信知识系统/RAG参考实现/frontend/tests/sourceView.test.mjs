import test from 'node:test';
import assert from 'node:assert/strict';
import {sourceLocation} from '../src/sourceView.ts';
test('PDF明确显示从1开始的页码',()=>assert.equal(sourceLocation({kind:'pdf',page:3,block_id:'p'}),'PDF · 第3页'));
test('Word即使误带page也不声称固定页码',()=>assert.equal(sourceLocation({kind:'docx',page:3,paragraph_index:4,block_id:'p'}),'Word · 正文段落4'));
test('Word表格使用表格编号',()=>assert.equal(sourceLocation({kind:'docx',table_index:2}),'Word · 正文表格2'));
test('Excel保留工作表和合并范围',()=>assert.equal(sourceLocation({kind:'xlsx',sheet:'报价',cell_range:'A1:C1'}),'Excel · 报价!A1:C1'));
test('PPT形状号不是PDF页码',()=>assert.equal(sourceLocation({kind:'pptx',slide:2,shape_id:5}),'PPT · 幻灯片2 · 形状5'));
test('文本保留物理行范围',()=>assert.equal(sourceLocation({kind:'md',line_start:3,line_end:8}),'文本 · 第3–8行'));
test('HTML优先显示可回查XPath而不是虚构页码',()=>assert.equal(sourceLocation({kind:'html',xpath:'/html/body/p'}),'HTML · /html/body/p'));
test('未知或非法页码保留低精度',()=>assert.equal(sourceLocation({kind:'pdf',page:0,block_id:'x'}),'块 x（位置精度待核对）'));

test('PPT视觉来源保留原幻灯片而不显示临时PDF页',()=>assert.equal(sourceLocation({kind:'pptx',slide:5,page:99,coordinate_system:'rendered_view_top_left_normalized',requested_box:[0,0,1,1]}),'PPT · 幻灯片5 · 视觉区域'));
test('PDF视觉区域仍标原PDF页',()=>assert.equal(sourceLocation({kind:'pdf',page:7,coordinate_system:'rendered_view_top_left_normalized',requested_box:[0,0,1,1]}),'PDF · 第7页 · 视觉区域'));
test('独立图片视觉区域有明确标签',()=>assert.equal(sourceLocation({kind:'image',coordinate_system:'rendered_view_top_left_normalized',requested_box:[0,0,1,1]}),'图片 · 视觉区域'));
