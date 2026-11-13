import json,tempfile,unittest
from hashlib import sha256
from pathlib import Path
import httpx
from PIL import Image
from rag_app.config import Settings
from rag_app.pipeline import Pipeline
from rag_app.docmind import save_json
from rag_app.visual_workflow import prepare_region,transcribe_region,validate_bundle
from rag_app.experiments import prepare_experiment
from rag_app.indexing import preview_chunks

# generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# generated: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# cache: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# revision: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# revision: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# cache: lpf2-18283 lpf2-19E2b
GOOD={'observations':[{'context':'固定协议样例','text':'IN → 设备 → OUT','uncertain':False}], 'warnings':[]}

class VisualWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.p=Pipeline(Settings(_env_file=None,runtime_dir=self.root/'base',dashscope_api_key=''))
        folder=self.p.settings.runtime_dir/'documents'/'doc';folder.mkdir(parents=True)
        self.source=folder/'source.png';Image.new('RGB',(400,200),'white').save(self.source)
        self.p.store.create('doc','figure.png','image',sha256(self.source.read_bytes()).hexdigest())
        save_json(folder/'blocks.json',[{'doc_id':'doc','type':'text','text':'IN OUT','locator':{'kind':'image','block_id':'ocr'}}])
        self.p.store.move('doc','parsing');self.p.store.move('doc','parsed')
        self.calls=[]
    def prepare(self):
        self.region=self.root/'region';prepare_region(self.p,'doc',self.region)
        return self.region
    def transcribe(self,content=None,finish='stop'):
        if not hasattr(self,'region'):self.prepare()
        def handler(request):
            self.calls.append(json.loads(request.content))
            return httpx.Response(200,json={'model':'fixture-vl','choices':[{'message':{'content':content or json.dumps(GOOD)},'finish_reason':finish}], 'usage':{'prompt_tokens':10,'completion_tokens':20,'total_tokens':30}})
        with httpx.Client(transport=httpx.MockTransport(handler)) as http:
            return transcribe_region(self.region,self.root/'bundle',Settings(_env_file=None,dashscope_api_key='fixture'),http=http,origin='fixture')
    def test_missing_key_stops_before_output_or_request(self):
        self.prepare()
        with self.assertRaisesRegex(ValueError,'DASHSCOPE'):transcribe_region(self.region,self.root/'bundle',self.p.settings)
        self.assertFalse((self.root/'bundle').exists())
    def test_valid_bundle_is_unverified_and_usage_is_separate(self):
        result=self.transcribe();self.assertEqual(result['state'],'succeeded')
        packet,blocks=validate_bundle(self.root/'bundle',self.p.settings.runtime_dir)
        self.assertEqual(len(blocks),1);self.assertFalse(blocks[0]['metadata']['semantic_verified'])
        self.assertEqual(packet['origin'],'fixture');self.assertEqual(len(self.calls),1)
        summary=json.loads((self.root/'bundle'/'usage-summary.json').read_text())
        self.assertEqual(summary['operations']['vision']['tokens']['total_tokens']['known_total'],30)
        self.assertIn('未经语义核验',(self.root/'bundle'/'review.html').read_text())
    def test_bad_output_preserves_attempt_without_a_success_packet(self):
        result=self.transcribe(content='broken');self.assertEqual(result['state'],'failed')
        self.assertTrue((self.root/'bundle'/'attempt.json').exists());self.assertFalse((self.root/'bundle'/'bundle.json').exists())
        self.assertEqual(len(self.calls),1)
    def test_original_blocks_and_image_tampering_are_rejected(self):
        self.transcribe();folder=self.p.folder('doc');path=folder/'blocks.json'
        original=path.read_bytes();path.write_bytes(original+b' ')
        with self.assertRaisesRegex(ValueError,'解析'):validate_bundle(self.root/'bundle',self.p.settings.runtime_dir)
        path.write_bytes(original);(self.root/'bundle'/'image.png').write_bytes(b'bad')
        with self.assertRaisesRegex(ValueError,'图'):validate_bundle(self.root/'bundle',self.p.settings.runtime_dir)
    def test_augmentation_uses_new_runtime_and_preserves_baseline(self):
        self.transcribe();before=(self.p.folder('doc')/'blocks.json').read_bytes()
        target=self.root/'experiment';m=prepare_experiment(self.p.settings.runtime_dir,target,'baseline',visual_bundles=[self.root/'bundle'])
        self.assertEqual((self.p.folder('doc')/'blocks.json').read_bytes(),before)
        p=Pipeline(Settings(_env_file=None,runtime_dir=target,milvus_collection=m['collection']))
        preview=preview_chunks(p,'doc');self.assertEqual(preview['block_count'],2)
        self.assertEqual(preview['chunks'][-1]['metadata']['text_origin'],'vision_model_unverified')
        self.assertEqual(m['visual_augmentation']['region_count'],1)
        self.assertTrue((target/'visual-bundles').is_dir())
    def test_duplicate_region_or_empty_usable_output_fails_before_new_runtime(self):
        self.transcribe();target=self.root/'experiment'
        with self.assertRaisesRegex(ValueError,'重复'):prepare_experiment(self.p.settings.runtime_dir,target,'baseline',visual_bundles=[self.root/'bundle']*2)
        self.assertFalse(target.exists())

    def test_all_uncertain_is_saved_but_cannot_be_an_augmentation(self):
        content={'observations':[{'context':'','text':'无法辨认','uncertain':True}],'warnings':[]}
        attempt=self.transcribe(content=json.dumps(content));self.assertEqual(attempt['usable_observations'],0)
        with self.assertRaisesRegex(ValueError,'没有可用'):validate_bundle(self.root/'bundle',self.p.settings.runtime_dir)

    def test_timeout_is_one_attempt_with_unknown_usage_not_free(self):
        self.prepare();calls=[]
        def handler(request):calls.append(1);raise httpx.ReadTimeout('fixture',request=request)
        with httpx.Client(transport=httpx.MockTransport(handler)) as http:
            result=transcribe_region(self.region,self.root/'bundle',Settings(_env_file=None,dashscope_api_key='fixture'),http=http,origin='fixture')
        self.assertEqual(result['state'],'failed');self.assertEqual(calls,[1])
        summary=json.loads((self.root/'bundle'/'usage-summary.json').read_text())
        self.assertIsNone(summary['operations']['vision']['tokens']['total_tokens']['known_total'])
        self.assertIsNone(summary['cost'])

    def test_original_change_and_locator_forgery_are_rejected(self):
        from rag_app.visual import digest
        self.transcribe();source=self.source.read_bytes();self.source.write_bytes(source+b' ')
        with self.assertRaisesRegex(ValueError,'原件'):validate_bundle(self.root/'bundle',self.p.settings.runtime_dir)
        self.source.write_bytes(source)
        folder=self.root/'bundle';region=json.loads((folder/'region.json').read_bytes());region['locator']['block_id']='forged'
        packet=json.loads((folder/'bundle.json').read_bytes());packet['region']=region
        packet['bundle_sha256']=digest({k:v for k,v in packet.items() if k!='bundle_sha256'})
        save_json(folder/'region.json',region);save_json(folder/'bundle.json',packet)
        with self.assertRaisesRegex(ValueError,'定位'):validate_bundle(folder,self.p.settings.runtime_dir)

if __name__=='__main__':unittest.main()
