"""M12A：结构保真测试，不是模型质量测试。"""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
# generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# cache: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# checksum: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# cache: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# cache: lpf2-18283 lpf2-19E2b
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from rag_app.core import chunk_blocks
from rag_app.structure import blocks_digest, compare_structure, table_rows


def block(text, uid='table', kind='table', doc='D-fixture'):
    return {'doc_id': doc, 'type': kind, 'text': text,
            'locator': {'kind': 'pdf', 'block_id': uid, 'page': 2},
            'metadata': {'text_origin': 'test_fixture'}}


def table(values):
    return '<table>\n<tr><th>型号</th><th>功率(W)</th></tr>\n' + '\n'.join(
        '<tr><td>'+name+'</td><td>'+value+'</td></tr>' for name, value in values) + '\n</table>'


def plan(blocks, context=None):
    return {'schema_version': 1, 'blocks_sha256': blocks_digest(blocks),
            'review_note': '测试固定样例：表头为第1行，附加说明已核对',
            'tables': [{'doc_id': 'D-fixture', 'block_id': 'table', 'header_rows': 1,
                        'context_block_ids': context or []}]}


class StructureTests(unittest.TestCase):
    def setUp(self):
        self.blocks = [block(table([('X'+str(i), str(i*10)) for i in range(10)])),
                       block('只适用于常温水。', 'note', 'text')]

    def test_baseline_identical_and_input_unchanged(self):
        before=deepcopy(self.blocks)
        result=compare_structure(self.blocks, plan(self.blocks), window=140, overlap=20)
        self.assertEqual(result['variants']['B0']['chunks'], chunk_blocks(self.blocks, window=140, overlap=20))
        self.assertEqual(self.blocks,before)
        result['variants']['P1']['chunks'][0]['locator']['page']=99
        self.assertEqual(self.blocks,before)

    def test_rows_complete_header_repeated_and_budget_bounded(self):
        r=compare_structure(self.blocks,plan(self.blocks),window=140,overlap=20)
        p=r['variants']['P1'];report=p['tables'][0]
        self.assertEqual(report['data_rows'],10)
        self.assertEqual(report['covered_complete_rows'],10)
        for c in p['chunks']:
            self.assertLessEqual(len(c['text']),140)
            if c['type']=='table':
                self.assertIn('<th>功率(W)</th>',c['text'])
                self.assertIsNone(c['char_range'])
                self.assertTrue(c['source_spans'])

    def test_every_source_span_roundtrips_to_original(self):
        r=compare_structure(self.blocks,plan(self.blocks,['note']),window=160,overlap=20)
        lookup={b['locator']['block_id']:b for b in self.blocks}
        for key in ['P1','P1+C1']:
            for c in r['variants'][key]['chunks']:
                for s in c.get('source_spans',[]):
                    start,end=s['char_range']
                    self.assertEqual(s['text'],lookup[s['locator']['block_id']]['text'][start:end])
        c=r['variants']['P1+C1']['chunks'][0]
        self.assertIn('只适用于常温水。',c['text'])
        self.assertEqual(c['source_spans'][-1]['role'],'context')
        self.assertEqual(c['source_spans'][-1]['locator']['block_id'],'note')

    def test_stable_identity_and_strategy_sensitive(self):
        p=plan(self.blocks,['note']);a=compare_structure(self.blocks,p,window=160,overlap=20)
        self.assertEqual(a,compare_structure(self.blocks,p,window=160,overlap=20))
        self.assertNotEqual(a['variants']['P1']['chunks'][0]['chunk_id'],a['variants']['P1+C1']['chunks'][0]['chunk_id'])

    def test_changed_frozen_blocks_rejected(self):
        p=plan(self.blocks);self.blocks[0]['text']+=' '
        with self.assertRaisesRegex(ValueError,'指纹'):compare_structure(self.blocks,p)

    def test_duplicate_identity_rejected(self):
        self.blocks.append(deepcopy(self.blocks[0]))
        with self.assertRaisesRegex(ValueError,'重复'):compare_structure(self.blocks,plan(self.blocks))

    def test_unknown_and_cross_document_context_rejected(self):
        other=block('不属于此文档','else','text','D-other');self.blocks.append(other)
        for ctx in [['else'],['missing'],['table'],['note','note']]:
            with self.subTest(ctx=ctx),self.assertRaises(ValueError):
                compare_structure(self.blocks,plan(self.blocks,ctx))

    def test_unknown_or_duplicate_table_plan_rejected(self):
        p=plan(self.blocks);p['tables'][0]['block_id']='missing'
        with self.assertRaises(ValueError):compare_structure(self.blocks,p)
        p=plan(self.blocks);p['tables']*=2
        with self.assertRaisesRegex(ValueError,'重复'):compare_structure(self.blocks,p)

    def test_unreviewed_table_remains_baseline_with_warning(self):
        p=plan(self.blocks);p['tables']=[]
        r=compare_structure(self.blocks,p,window=140,overlap=20)
        self.assertEqual(r['variants']['B0']['chunks'],r['variants']['P1']['chunks'])
        self.assertIn('未列入核对计划',r['warnings'][0])

    def test_row_too_large_stops_without_truncation(self):
        with self.assertRaisesRegex(ValueError,'完整数据行'):compare_structure(self.blocks,plan(self.blocks),window=65,overlap=0)

    def test_invalid_table_and_merged_cells_not_silently_flattened(self):
        examples=['<table><tr><td>A</td></tr>',
                  '<table><tr><td rowspan="2">A</td></tr><tr></tr></table>',
                  '<table><tr><td><table><tr><td>A</td></tr></table></td></tr></table>',
                  '<table><tr><td>A</td></tr><tr><td>B</td><td>C</td></tr></table>',
                  '<table><tr><td>A</td></tr><script>bad</script></table>',
                  '<table><tr><td>A</td></tr></table>lost',
                  '<table><tr><td>A</td></tr>LOST<tr><td>B</td></tr></table>']
        for raw in examples:
            with self.subTest(raw=raw),self.assertRaises(ValueError):table_rows(raw)

    def test_entities_br_and_wrapper_preserved_as_exact_spans(self):
        raw='<table><thead><tr><th>A&amp;B</th></tr></thead><tbody><tr><td>&lt;5<br/>W</td></tr></tbody></table>'
        rows=table_rows(raw)
        self.assertEqual([raw[a:b] for a,b in rows],['<tr><th>A&amp;B</th></tr>','<tr><td>&lt;5<br/>W</td></tr>'])

    def test_header_rows_cannot_consume_all_rows(self):
        for n in [0,True,11,-1,'1']:
            p=plan(self.blocks);p['tables'][0]['header_rows']=n
            with self.subTest(n=n),self.assertRaises(ValueError):compare_structure(self.blocks,p)

    def test_unicode_separator_does_not_corrupt_offsets(self):
        raw='<table>\n<tr><th>A</th></tr>\n<tr><td>甲\u2028乙</td></tr>\n<tr><td>C</td></tr></table>'
        self.assertEqual([raw[a:b] for a,b in table_rows(raw)],
                         ['<tr><th>A</th></tr>','<tr><td>甲\u2028乙</td></tr>','<tr><td>C</td></tr>'])

    def test_duplicate_text_rows_counted_by_position(self):
        blocks=[block(table([('A','10')]*10))]
        r=compare_structure(blocks,plan(blocks),window=110,overlap=0)
        self.assertEqual(r['variants']['P1']['tables'][0]['covered_complete_rows'],10)
        self.assertLess(r['variants']['B0']['tables'][0]['covered_complete_rows'],10)

    def test_row_coverage_does_not_mean_header_and_context_in_same_chunk(self):
        r=compare_structure(self.blocks,plan(self.blocks,['note']),window=160,overlap=20)
        b=r['variants']['B0']['tables'][0];p=r['variants']['P1']['tables'][0];c=r['variants']['P1+C1']['tables'][0]
        self.assertLess(b['rows_with_header'],b['covered_complete_rows'])
        self.assertEqual(p['rows_with_header'],10)
        self.assertEqual(p['rows_with_header_and_context'],0)
        self.assertEqual(c['rows_with_header_and_context'],10)


if __name__=='__main__':unittest.main()
