from copy import deepcopy
from pathlib import Path
import sys
import unittest
# checksum: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# generated: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# cache: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# generated: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# revision: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# cache: lpf2-18283 lpf2-19E2b
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from rag_app.structure import blocks_digest
from rag_app.multipage import merged_table, multipage_chunks, compare_multipage

HEADER='<tr><th colspan="2">报价</th></tr><tr><th>编码</th><th>单价/元</th></tr>'
def fixture():
    blocks=[{'doc_id':'D','type':'table','text':'<table>'+HEADER+'<tr><td>'+code+'</td><td>35</td></tr></table>',
             'locator':{'kind':'pdf','page':page,'block_id':f't{page}'}} for page,code in [(3,'A'),(4,'B')]]
    blocks.append({'doc_id':'D','type':'text','text':'仅批准数量进入报价。','locator':{'kind':'pdf','page':3,'block_id':'note'}})
    p={'schema_version':2,'blocks_sha256':blocks_digest(blocks),'review_note':'固定测试，逐页核对',
       'groups':[{'doc_id':'D','block_ids':['t3','t4'],'header_rows':2,'context_block_ids':['note']}]}
    return blocks,p

class MultipageTests(unittest.TestCase):
    def test_cross_page_rows_and_exact_sources(self):
        b,p=fixture();before=deepcopy(b)
        chunks=multipage_chunks(b,p,window=600,include_context=True)
        tables=[c for c in chunks if c.get('source_spans')]
        self.assertEqual(len(tables),1)
        c=tables[0];self.assertEqual(c['locator']['page'],3)
        self.assertEqual([s['locator']['page'] for s in c['source_spans'] if s['role']=='data_row'],[3,4])
        for s in c['source_spans']:
            original=next(x for x in b if x['locator']['block_id']==s['locator']['block_id'])
            self.assertEqual(s['text'],original['text'][slice(*s['char_range'])])
        self.assertEqual(b,before);self.assertIsNone(c['char_range'])
        self.assertIn('仅批准数量',c['text']);self.assertLessEqual(len(c['text']),600)

    def test_merged_header_paths_and_rowspan(self):
        html='<table><tr><th rowspan="2">型号</th><th>计费</th></tr><tr><th>元</th></tr><tr><td>A</td><td>35</td></tr></table>'
        parsed=merged_table(html,2)
        self.assertEqual(parsed['paths'],[['型号'],['计费','元']])

    def test_bad_html_and_spans_rejected(self):
        cases=[HEADER.replace('colspan="2"','colspan="0"'),HEADER.replace('colspan="2"','colspan="65"'),
               HEADER.replace('colspan="2"','colspan="2" colspan="2"'),HEADER.replace('colspan="2"','rowspan="3"'),
               HEADER+'<!-- hidden -->',HEADER+'x',HEADER.replace('报价','<b>报价</b>')]
        for h in cases:
            with self.subTest(h=h),self.assertRaises(ValueError):merged_table('<table>'+h+'<tr><td>A</td><td>35</td></tr></table>',2)
        for cell in ['<td colspan="2">A</td>','<td rowspan="2">A</td><td>35</td>']:
            with self.subTest(cell=cell),self.assertRaises(ValueError):merged_table('<table>'+HEADER+'<tr>'+cell+'</tr></table>',2)

    def test_unit_or_column_change_rejected(self):
        b,p=fixture();b[1]['text']=b[1]['text'].replace('单价/元','单价/美元');p['blocks_sha256']=blocks_digest(b)
        with self.assertRaisesRegex(ValueError,'表头'):multipage_chunks(b,p)

    def test_stale_plan_duplicate_reverse_and_cross_document(self):
        for mode in ['stale','duplicate','reverse','otherdoc','missingnote','boolheader']:
            b,p=fixture();g=p['groups'][0]
            if mode=='stale':p['blocks_sha256']='old'
            if mode=='duplicate':g['block_ids'].append('t3')
            if mode=='reverse':g['block_ids'].reverse()
            if mode=='otherdoc':b[1]['doc_id']='OTHER';p['blocks_sha256']=blocks_digest(b)
            if mode=='missingnote':g['context_block_ids']=['missing']
            if mode=='boolheader':g['header_rows']=True
            with self.subTest(mode=mode),self.assertRaises(ValueError):multipage_chunks(b,p)

    def test_budget_and_determinism(self):
        b,p=fixture()
        with self.assertRaisesRegex(ValueError,'预算'):multipage_chunks(b,p,window=100,overlap=10)
        self.assertEqual(multipage_chunks(b,p),multipage_chunks(b,p))
        self.assertNotEqual(multipage_chunks(b,p)[0]['chunk_id'],multipage_chunks(b,p,include_context=True)[0]['chunk_id'])

    def test_comparison_baseline_and_coverage(self):
        from rag_app.core import chunk_blocks
        b,p=fixture();r=compare_multipage(b,p,window=230,overlap=20)
        self.assertEqual(r['variants']['B0']['chunks'],chunk_blocks(b,window=230,overlap=20))
        self.assertEqual(r['variants']['P2+C2']['complete_rows'],2)
        self.assertEqual(r['variants']['P2+C2']['rows_with_header_and_context'],2)
        self.assertEqual(r['cloud_calls'],0);self.assertIsNone(r['retrieval_recall'])

    def test_unplanned_table_preserved_warning(self):
        b,p=fixture();extra=deepcopy(b[0]);extra['locator']['block_id']='unplanned';b.append(extra);p['blocks_sha256']=blocks_digest(b)
        r=compare_multipage(b,p)
        self.assertIn('unplanned',r['warnings'][0])
        self.assertTrue(any(c['locator']['block_id']=='unplanned' for c in r['variants']['P2']['chunks']))

    def test_holes_header_overlap_and_data_overflow(self):
        bad=[
            '<tr><th rowspan="2">A</th><th>B</th></tr><tr><th colspan="2">C</th></tr>',
            '<tr><th>A</th><th rowspan="2">B</th></tr><tr><th colspan="2">C</th></tr>',
            '<tr><th>A</th><th>B</th></tr><tr><th>C</th></tr>',
            '<tr><th></th><th>B</th></tr><tr><th>C</th><th>D</th></tr>',
        ]
        for h in bad:
            with self.subTest(h=h),self.assertRaises(ValueError):merged_table('<table>'+h+'<tr><td>x</td><td>1</td></tr></table>',2)

    def test_unicode_offsets_entities_and_repeated_label(self):
        html='<table>\n<tr><th rowspan="2">型&#21495;</th><th>元</th></tr>\n<tr><th>元</th></tr>\n<tr><td>A<br/>B</td><td>35</td></tr></table>'
        r=merged_table(html,2)
        self.assertEqual(r['paths'],[['型号'],['元','元']])
        self.assertEqual(r['data_values'],[['A B','35']])
        self.assertEqual([html[a:z].startswith('<tr>') and html[a:z].endswith('</tr>') for a,z in r['spans']],[True]*3)

    def test_same_page_and_reused_group_rejected(self):
        b,p=fixture();b[1]['locator']['page']=3;p['blocks_sha256']=blocks_digest(b)
        with self.assertRaisesRegex(ValueError,'递增'):multipage_chunks(b,p)
        b,p=fixture();p['groups'].append(deepcopy(p['groups'][0]))
        with self.assertRaisesRegex(ValueError,'其他'):multipage_chunks(b,p)

    def test_many_rows_once_and_budget(self):
        b,p=fixture()
        for block in b[:2]:
            block['text']=block['text'].replace('</table>',''.join(f'<tr><td>{i}</td><td>35</td></tr>' for i in range(15))+'</table>')
        p['blocks_sha256']=blocks_digest(b)
        chunks=multipage_chunks(b,p,window=230,overlap=20,include_context=True)
        rows=[(s['locator']['block_id'],tuple(s['char_range'])) for c in chunks for s in c.get('source_spans',[]) if s['role']=='data_row']
        self.assertEqual(len(rows),32);self.assertEqual(len(set(rows)),32)
        self.assertTrue(all(len(c['text'])<=230 for c in chunks))

if __name__=='__main__':unittest.main()
