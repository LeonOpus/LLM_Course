"""真实文件格式小样例：检查来源语义、合并关系、缓存缺失与对齐歧义。"""
from hashlib import sha256
import tempfile
from pathlib import Path
import unittest
from docx import Document
from openpyxl import Workbook
from pptx import Presentation
from pptx.util import Inches
from pypdf import PdfWriter
from rag_app.source_inspection import inspect_source,reconcile_blocks

# cache: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# generated: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# generated: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# revision: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# cache: lpf2-18283 lpf2-19E2b
class SourceInspectionTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.folder=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def test_docx_preserves_body_order_and_merged_table(self):
        path=self.folder/'x.docx';doc=Document();doc.add_heading('规格',level=1);doc.add_paragraph('型号X200')
        table=doc.add_table(rows=2,cols=2);table.cell(0,0).merge(table.cell(0,1)).text='额定值（W）';table.cell(1,0).text='X200';table.cell(1,1).text='260'
        doc.add_paragraph('限制条件另见工况。');doc.save(path);before=path.read_bytes()
        result=inspect_source('doc',path);blocks=result['blocks']
        self.assertEqual([b['type'] for b in blocks],['title','text','table','text'])
        self.assertEqual(blocks[1]['locator']['paragraph_index'],2)
        self.assertEqual(blocks[2]['locator']['table_index'],1)
        self.assertIn('colspan="2"',blocks[2]['text']);self.assertEqual(blocks[2]['text'].count('额定值'),1)
        self.assertEqual(blocks[3]['locator']['paragraph_index'],3)
        self.assertTrue(all('page' not in b['locator'] for b in blocks))
        self.assertEqual(path.read_bytes(),before)
    def test_xlsx_formula_without_cache_is_not_zero_or_calculated(self):
        path=self.folder/'x.xlsx';wb=Workbook();ws=wb.active;ws.title='报价';ws.append(['型号','含税金额（元）']);ws.append(['X200','=100+20']);wb.save(path)
        report=inspect_source('doc',path)
        formula=[c for b in report['blocks'] for c in b['metadata'].get('cells',[]) if c.get('formula')][0]
        self.assertEqual(formula['coordinate'],'B2');self.assertEqual(formula['formula'],'=100+20');self.assertIsNone(formula['cached_value'])
        self.assertEqual(formula['cached_value_status'],'missing')
        self.assertTrue(any(w['code']=='formula_cache_missing' for w in report['warnings']))
        row=[b for b in report['blocks'] if b['locator'].get('cell_range')=='A2:B2'][0]
        self.assertEqual(row['locator']['sheet'],'报价');self.assertIn('未缓存',row['text']);self.assertNotIn('120',row['text'])
    def test_xlsx_merged_header_and_hidden_sheet_are_explicit(self):
        path=self.folder/'x.xlsx';wb=Workbook();ws=wb.active;ws.merge_cells('A1:C1');ws['A1']='设备规格';ws.append(['型号','功率','单位']);ws.append(['X200',260,'W']);hidden=wb.create_sheet('旧版本');hidden.sheet_state='hidden';hidden['A1']='旧资料';wb.save(path)
        report=inspect_source('doc',path)
        self.assertIn('A1:C1',report['structure']['sheets'][0]['merged_ranges'])
        self.assertEqual(report['blocks'][0]['locator']['cell_range'],'A1:C1')
        self.assertEqual(report['structure']['sheets'][1]['visibility'],'hidden')
        self.assertEqual([b['text'] for b in report['blocks'] if b['locator']['sheet']=='旧版本'],['A1: 旧资料'])
    def test_markdown_fence_blank_lines_kept_with_physical_line_range(self):
        path=self.folder/'x.md';path.write_text('# 参数\n\n```json\n{\n\n "power":260\n}\n```\n\n限制：带温度条件。\n')
        report=inspect_source('doc',path);code=[b for b in report['blocks'] if b['type']=='code'][0]
        self.assertEqual((code['locator']['line_start'],code['locator']['line_end']),(3,8))
        self.assertIn('\n\n',code['text']);self.assertEqual(code['locator']['heading_path'],['参数'])
    def test_html_does_not_include_script_and_has_structural_locator(self):
        path=self.folder/'x.html';path.write_text('<html><body><h1>参数</h1><section id="spec"><p>型号 X200</p><table><tr><th>功率</th><td>260W</td></tr></table></section><script>malicious()</script></body></html>')
        report=inspect_source('doc',path);text='\n'.join(b['text'] for b in report['blocks'])
        self.assertNotIn('malicious',text);self.assertIn('260W',text)
        p=[b for b in report['blocks'] if b['text']=='型号 X200'][0]
        self.assertEqual(p['locator']['html_anchor'],'spec');self.assertTrue(p['locator']['xpath'].endswith('/section/p'))
        self.assertNotIn('page',p['locator'])
    def test_pptx_slide_shape_and_emu_coordinates_not_pdf_points(self):
        path=self.folder/'x.pptx';prs=Presentation();slide=prs.slides.add_slide(prs.slide_layouts[6]);shape=slide.shapes.add_textbox(Inches(1),Inches(1),Inches(3),Inches(1));shape.text='型号X200\n260W';prs.save(path)
        report=inspect_source('doc',path);block=report['blocks'][0]
        self.assertEqual(block['locator']['slide'],1);self.assertEqual(block['locator']['shape_id'],shape.shape_id)
        self.assertEqual(block['locator']['coordinate_system'],'office_emu');self.assertNotIn('page',block['locator'])
    def test_pdf_inspection_does_not_pretend_local_ocr(self):
        path=self.folder/'x.pdf';writer=PdfWriter();writer.add_blank_page(width=300,height=400)
        with path.open('wb') as f:writer.write(f)
        report=inspect_source('doc',path)
        self.assertEqual(report['blocks'],[]);self.assertEqual(report['structure']['page_count'],1)
        self.assertTrue(any(w['code']=='docmind_required' for w in report['warnings']))
    def test_text_inspection_fingerprint_and_line_boundaries(self):
        path=self.folder/'x.txt';path.write_text('参数\n260W\n\n边界条件\n');raw=path.read_bytes();report=inspect_source('doc',path)
        self.assertEqual(report['source_sha256'],sha256(raw).hexdigest())
        self.assertEqual([(b['locator']['line_start'],b['locator']['line_end']) for b in report['blocks']],[(1,2),(4,4)])
        self.assertEqual(report['role'],'source_audit');self.assertFalse(report['replaces_docmind'])
    def test_exact_matching_ambiguous_and_unmatched_do_not_invent_locator(self):
        source={'blocks':[{'text':'260W','locator':{'block_id':'a'}},{'text':'260W','locator':{'block_id':'b'}},{'text':'型号 X200','locator':{'block_id':'c'}}]}
        parsed=[{'text':'260W','locator':{'block_id':'cloud1'}},{'text':'型号 X200','locator':{'block_id':'cloud2'}},{'text':'2600W','locator':{'block_id':'cloud3'}}]
        import copy
        before=copy.deepcopy(parsed);result=reconcile_blocks(parsed,source)
        self.assertEqual([x['status'] for x in result],['ambiguous','unique_exact','unmatched'])
        self.assertEqual(result[1]['matches'][0]['block_id'],'c');self.assertEqual(parsed,before)

    def test_html_line_break_preserves_field_boundary(self):
        path=self.folder/'x.html';path.write_text('<p>型号X200<br/>功率260W</p>')
        report=inspect_source('doc',path)
        self.assertEqual(report['blocks'][0]['text'],'型号X200\n功率260W')

    def test_html_navigation_preserved_once(self):
        path=self.folder/'x.html';path.write_text('<nav><ul><li>参数</li><li>维护</li></ul></nav>')
        report=inspect_source('doc',path)
        self.assertEqual(len(report['blocks']),1)
        self.assertEqual(report['blocks'][0]['type'],'navigation')
        self.assertIn('参数',report['blocks'][0]['text']);self.assertIn('维护',report['blocks'][0]['text'])
