import test from 'node:test';
import assert from 'node:assert/strict';
import {chunkRangeLabel} from '../src/chunkSources.ts';
test('基线单一范围仍然可读',()=>assert.equal(chunkRangeLabel({char_range:[0,17]}),'字符范围：[0, 17)'));
test('组合片段不把null当数组并提示逐段核对',()=>assert.equal(chunkRangeLabel({char_range:null,source_spans:[{},{}]}),'组合来源：2段原文，各段字符范围见下方来源记录'));
test('缺少位置不能伪造0到0',()=>assert.equal(chunkRangeLabel({char_range:null}),'来源范围未知，请核对原始块记录'));
test('非法单区间不能展示成有效来源',()=>assert.equal(chunkRangeLabel({char_range:[8,2]}),'来源范围未知，请核对原始块记录'));
