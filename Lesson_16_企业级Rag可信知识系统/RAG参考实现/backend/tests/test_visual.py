import base64,json,tempfile,unittest
from pathlib import Path
from copy import deepcopy
from unittest.mock import patch
from PIL import Image
from rag_app.visual import render_region,request_body,validate_observations,observation_blocks

# revision: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# revision: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# cache: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# generated: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# checksum: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# cache: lpf2-18283 lpf2-19E2b
GOOD={'observations':[{'context':'X200接口图','text':'蓝色实线从IN进入设备，再由OUT通向用液端。','uncertain':False},
                      {'context':'小字','text':'局部标签不能辨认','uncertain':True}],'warnings':['图片内容需原件核对']}

class VisualTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.source=self.root/'source.png';Image.new('RGB',(640,320),'white').save(self.source)
    def region(self,**kw):return render_region(self.source,'image','d',box=[0,0,1,1],**kw)
    def test_image_crop_is_bound_to_source_and_actual_pixels(self):
        png,region=self.region();self.assertEqual(region['render_size'],[640,320])
        self.assertEqual(region['locator']['kind'],'image');self.assertNotIn('page',region['locator'])
        self.assertEqual(region['locator']['coordinate_system'],'rendered_view_top_left_normalized')
        self.assertNotEqual(png,b'');self.assertEqual(len(region['source_sha256']),64)
    def test_bad_box_page_type_and_unsupported_format_fail(self):
        for box in [[-1,0,1,1],[0,0,0,1],[0,0,True,1],[0,0,float('nan'),1]]:
            with self.subTest(box=box),self.assertRaises(ValueError):render_region(self.source,'image','d',box=box)
        with self.assertRaises(ValueError):self.region(page=1)
        with self.assertRaises(ValueError):render_region(self.source,'pptx','d')
    def test_request_sends_exact_png_and_no_question_or_gold(self):
        png,r=self.region();body=request_body(png,'qwen3-vl-plus')
        url=body['messages'][1]['content'][0]['image_url']['url']
        self.assertEqual(base64.b64decode(url.split(',')[1]),png)
        self.assertEqual(body['response_format'],{'type':'json_object'});self.assertFalse(body['enable_thinking'])
        self.assertNotIn('doc_id',json.dumps(body));self.assertNotIn('gold_answer',json.dumps(body))
    def test_valid_schema_does_not_claim_truth_and_uncertain_not_indexed(self):
        png,r=self.region();o=validate_observations(json.dumps(GOOD),finish_reason='stop')
        blocks=observation_blocks(r,o,'qwen3-vl-plus')
        self.assertEqual(len(blocks),1);self.assertLessEqual(len(blocks[0]['text']),600)
        self.assertEqual(blocks[0]['metadata']['text_origin'],'vision_model_unverified')
        self.assertEqual(blocks[0]['locator'],{**r['locator'],'block_id':blocks[0]['locator']['block_id']})
        self.assertFalse(blocks[0]['metadata']['semantic_verified'])
    def test_duplicate_keys_truncation_extra_fields_and_long_text_rejected(self):
        bad=deepcopy(GOOD);bad['observations'][0]['text']='a'*301
        for content,finish in [(json.dumps(bad),'stop'),(json.dumps(GOOD),'length'),('{"observations":[],"observations":[],"warnings":[]}','stop'),(json.dumps({**GOOD,'approved':True}),'stop')]:
            with self.subTest(content=content[:30]),self.assertRaises(ValueError):validate_observations(content,finish)
    def test_non_boolean_uncertainty_and_empty_claim_rejected(self):
        for value in [None,1,'false']:
            bad=deepcopy(GOOD);bad['observations'][0]['uncertain']=value
            with self.assertRaises(ValueError):validate_observations(json.dumps(bad),'stop')

    def test_pdf_page_render_is_real_and_locator_is_one_based(self):
        import pypdfium2 as pdfium
        document=pdfium.PdfDocument.new();page=document.new_page(200,100);source=self.root/'source.pdf'
        document.save(source);page.close();document.close()
        png,r=render_region(source,'pdf','pdf-doc',page=1)
        self.assertEqual(r['render_size'],[400,200]);self.assertEqual(r['locator']['page'],1)
        self.assertTrue(png.startswith(b'\x89PNG'))
        with self.assertRaisesRegex(ValueError,'超出'):render_region(source,'pdf','pdf-doc',page=2)

if __name__=='__main__':unittest.main()
