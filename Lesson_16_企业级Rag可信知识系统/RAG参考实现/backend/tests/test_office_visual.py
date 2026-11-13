import io,json,tempfile,unittest,zipfile,subprocess
from pathlib import Path
from unittest.mock import patch
from rag_app.office_visual import ppt_manifest,convert_ppt

# checksum: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# cache: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# generated: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# cache: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# revision: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# checksum: lpf2-18283 lpf2-19E2b
P='http://schemas.openxmlformats.org/presentationml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
class OfficeVisualTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
    def package(self,targets=('slides/slide2.xml','slides/slide1.xml')):
        buf=io.BytesIO()
        with zipfile.ZipFile(buf,'w') as z:
            z.writestr('ppt/presentation.xml',f'<p:presentation xmlns:p="{P}" xmlns:r="{R}"><p:sldIdLst><p:sldId id="300" r:id="r2"/><p:sldId id="301" r:id="r1"/></p:sldIdLst><p:sldSz cx="9144000" cy="5143500"/></p:presentation>')
            z.writestr('ppt/_rels/presentation.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'+''.join(f'<Relationship Id="r{i}" Type="{R}/slide" Target="{t}"/>' for i,t in zip([2,1],targets))+'</Relationships>')
            z.writestr('ppt/slides/slide2.xml',f'<p:sld xmlns:p="{P}" show="0"/>');z.writestr('ppt/slides/slide1.xml',f'<p:sld xmlns:p="{P}"/>')
        return buf.getvalue()
    def test_original_order_and_hidden_are_preserved(self):
        m=ppt_manifest(self.package());self.assertEqual(m['slide_count'],2)
        self.assertEqual(m['slides'][0],{'slide':1,'slide_id':'300','slide_part':'ppt/slides/slide2.xml','hidden':True})
        self.assertEqual(m['slide_size_emu'],[9144000,5143500])
    def test_invalid_relationship_or_duplicate_target_fails(self):
        for targets in [('../evil.xml','slides/slide1.xml'),('slides/slide1.xml','slides/slide1.xml')]:
            with self.assertRaises(ValueError):ppt_manifest(self.package(targets))
    def test_failed_converter_and_missing_output_are_not_success(self):
        binary=self.root/'soffice';binary.write_text('fixture')
        for response in [subprocess.CompletedProcess([],1,'','bad'),subprocess.CompletedProcess([],0,'','')]:
            with patch('rag_app.office_visual.subprocess.run',side_effect=[subprocess.CompletedProcess([],0,'LibreOffice fixture',''),response]),self.assertRaisesRegex(ValueError,'转换失败'):convert_ppt(self.package(),str(binary))
    def test_timeout_is_bounded_and_explained(self):
        binary=self.root/'soffice';binary.write_text('fixture')
        with patch('rag_app.office_visual.subprocess.run',side_effect=[subprocess.CompletedProcess([],0,'LibreOffice fixture',''),subprocess.TimeoutExpired('fixture',60)]),self.assertRaisesRegex(ValueError,'超时'):convert_ppt(self.package(),str(binary))

    def fake_conversion(self,count=2,width=160,height=90):
        import pypdfium2 as pdfium
        binary=self.root/'soffice';binary.write_text('fixture');commands=[]
        def call(cmd,**kw):
            commands.append(cmd)
            if '--version' in cmd:return subprocess.CompletedProcess(cmd,0,'LibreOffice fixture','')
            self.assertLessEqual(kw['timeout'],60);self.assertFalse(kw.get('shell',False))
            document=pdfium.PdfDocument.new()
            for _ in range(count):page=document.new_page(width,height);page.close()
            out=Path(cmd[cmd.index('--outdir')+1])/'source.pdf';document.save(out);document.close()
            return subprocess.CompletedProcess(cmd,0,'converted','')
        return str(binary),commands,call

    def test_conversion_includes_hidden_no_notes_and_isolated_profile(self):
        binary,commands,call=self.fake_conversion()
        with patch('rag_app.office_visual.subprocess.run',side_effect=call):pdf,m=convert_ppt(self.package(),binary)
        self.assertTrue(pdf.startswith(b'%PDF'));self.assertEqual(m['slide_count'],2)
        conversion=commands[-1];self.assertTrue(any(x.startswith('-env:UserInstallation=file:') for x in conversion))
        options=json.loads(conversion[conversion.index('--convert-to')+1].split(':',2)[2])
        self.assertEqual(options['ExportHiddenSlides']['value'],'true');self.assertEqual(options['ExportNotesPages']['value'],'false')
        self.assertFalse(Path(conversion[-1]).exists())

    def test_wrong_page_count_or_aspect_is_rejected(self):
        for count,width,height in [(1,160,90),(2,160,160)]:
            binary,_,call=self.fake_conversion(count,width,height)
            with patch('rag_app.office_visual.subprocess.run',side_effect=call),self.assertRaises(ValueError):convert_ppt(self.package(),binary)

    def test_ppt_locator_preserves_original_slide_and_never_pdf_page(self):
        from rag_app.visual import render_region
        source=self.root/'source.pptx';source.write_bytes(self.package());binary,_,call=self.fake_conversion()
        with patch('rag_app.office_visual.resolve_binary',return_value=binary),patch('rag_app.office_visual.subprocess.run',side_effect=call):
            png,r=render_region(source,'pptx','doc',slide=1)
        self.assertEqual(r['locator']['slide'],1);self.assertEqual(r['locator']['slide_part'],'ppt/slides/slide2.xml')
        self.assertTrue(r['locator']['hidden']);self.assertNotIn('page',r['locator'])
        self.assertEqual(r['office']['renderer_version'],'LibreOffice fixture')
        for options in [{'page':1,'slide':1},{'slide':0},{'slide':True}]:
            with self.assertRaises(ValueError):render_region(source,'pptx','doc',**options)

    def test_repeated_first_character_corruption_is_rejected(self):
        from rag_app.office_visual import cjk_integrity
        expected=set('压力与流量曲线测试条件')
        with self.assertRaisesRegex(ValueError,'错码'):cjk_integrity(expected,'压压压压压压')
        self.assertEqual(cjk_integrity(expected,'压力与流量曲线测试条件')['unique_cjk_coverage'],1.)
        self.assertIsNone(cjk_integrity(set(),'123')['unique_cjk_coverage'])

    def test_ppt_bundle_round_trip_and_renderer_drift(self):
        import httpx
        from hashlib import sha256
        from rag_app.config import Settings
        from rag_app.pipeline import Pipeline
        from rag_app.docmind import save_json
        from rag_app.visual_workflow import prepare_region,transcribe_region,validate_bundle
        from rag_app.visual import render_region
        from rag_app.experiments import prepare_experiment
        from rag_app.indexing import preview_chunks
        raw=self.package();p=Pipeline(Settings(_env_file=None,runtime_dir=self.root/'base'))
        p.store.create('doc','source.pptx','pptx',sha256(raw).hexdigest());folder=p.folder('doc');folder.mkdir(parents=True)
        (folder/'source.pptx').write_bytes(raw);save_json(folder/'blocks.json',[{'doc_id':'doc','type':'text','text':'fixture labels','locator':{'kind':'pptx','slide':1,'block_id':'ocr'}}])
        p.store.move('doc','parsing');p.store.move('doc','parsed');before=(folder/'blocks.json').read_bytes()
        binary,_,call=self.fake_conversion()
        with patch('rag_app.office_visual.resolve_binary',return_value=binary),patch('rag_app.office_visual.subprocess.run',side_effect=call):
            prepare_region(p,'doc',self.root/'region',slide=1)
            def response(request):return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps({'observations':[{'context':'fixture','text':'A → B','uncertain':False}],'warnings':[]})},'finish_reason':'stop'}]})
            with httpx.Client(transport=httpx.MockTransport(response)) as http:transcribe_region(self.root/'region',self.root/'bundle',Settings(_env_file=None,dashscope_api_key='fixture'),http=http,origin='fixture')
            _,blocks=validate_bundle(self.root/'bundle',p.settings.runtime_dir)
            self.assertEqual(blocks[0]['locator']['slide'],1);self.assertNotIn('page',blocks[0]['locator'])
            manifest=prepare_experiment(p.settings.runtime_dir,self.root/'augmented','baseline',visual_bundles=[self.root/'bundle'])
            new=Pipeline(Settings(_env_file=None,runtime_dir=self.root/'augmented',milvus_collection=manifest['collection']))
            self.assertEqual(preview_chunks(new,'doc')['block_count'],2);self.assertEqual(before,(folder/'blocks.json').read_bytes())
            png,region=render_region(folder/'source.pptx','pptx','doc',slide=1);region['office']['renderer_version']='different'
            with patch('rag_app.visual_workflow.render_region',return_value=(png,region)),self.assertRaisesRegex(ValueError,'重新渲染'):validate_bundle(self.root/'bundle',p.settings.runtime_dir)
