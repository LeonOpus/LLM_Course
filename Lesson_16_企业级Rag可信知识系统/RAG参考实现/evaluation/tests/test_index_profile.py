from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from evaluation.runtime import run_suite
from evaluation.tests.test_runtime import case,record


# cache: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# revision: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# cache: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# checksum: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# generated: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# revision: lpf2-18283 lpf2-19E2b
def profile():
    return {'schema_version':'rag-index-profile/1','strategy':'baseline','collection':'rag_course_fixture',
            'documents':[{'doc_id':'runtime-a','source_sha256':'a'*64,'blocks_sha256':'b'*64,
                          'plan_sha256':None,'chunking':{'window':600,'overlap':100,'preserve_tables':False},'manifest_sha256':'c'*64}]}


class IndexProfileTests(unittest.TestCase):
    def run_profiles(self,profiles):
        with tempfile.TemporaryDirectory() as folder:
            responses=[]
            for p in profiles:
                response=deepcopy(record()['response'])
                response['trace'].update(models={'chat':'fixture'},prompt_version='fixture',generation={},context_max_chars=6000,embedding={})
                if p is not None:response['trace']['index_profile']=p
                responses.append(response)
            cases=[{**case(),'case_id':'Q'+str(i)} for i in range(len(profiles))]
            return run_suite(cases,[{'id':'D01','sha256':'a'*64}],
                {'strategy':'baseline','top_k':10,'final_k':5,'require_index_profile':True},Path(folder)/'run',
                lambda:[{'doc_id':'runtime-a','sha256':'a'*64,'status':'ready'}],lambda _:responses.pop(0))

    def test_missing_profile_cannot_pass_required_gate(self):
        r=self.run_profiles([None]);self.assertFalse(r['manifest']['comparable'])

    def test_index_change_during_run_invalidates_comparison(self):
        a=profile();b=deepcopy(a);b['collection']='rag_course_other'
        r=self.run_profiles([a,b]);self.assertFalse(r['manifest']['comparable'])

    def test_stable_profile_recorded_from_actual_trace(self):
        p=profile();r=self.run_profiles([p,p]);self.assertTrue(r['manifest']['comparable'])
        self.assertEqual(r['manifest']['observed_configurations'][0]['index_profile'],p)

    def test_fake_shape_or_source_binding_rejected(self):
        wrong=profile();wrong['documents'][0]['source_sha256']='f'*64
        for p in [{},wrong]:
            with self.subTest(profile=p):self.assertFalse(self.run_profiles([p])['manifest']['comparable'])

    def test_visual_profile_is_frozen_and_invalid_provenance_rejected(self):
        p=profile();p['visual_augmentation']={'schema_version':'visual-augmentation/1','region_count':1,'semantic_verified':False,
            'bundles':[{'doc_id':'runtime-a','region_id':'d'*64,'bundle_sha256':'e'*64,'model':'fixture',
                        'origin':'fixture','prompt_version':'visual-transcription-m19a-v1'}]}
        self.assertTrue(self.run_profiles([p])['manifest']['comparable'])
        for key,value in [('region_count',2),('semantic_verified',True),('bundles',[])]:
            bad=deepcopy(p);bad['visual_augmentation'][key]=value
            self.assertFalse(self.run_profiles([bad])['manifest']['comparable'])
        changed=deepcopy(p);changed['visual_augmentation']['bundles'][0]['model']='different'
        self.assertFalse(self.run_profiles([p,changed])['manifest']['comparable'])

    def test_fixture_visual_cannot_be_formal_holdout_candidate(self):
        from evaluation.holdout import require_live_visual_profile
        p={'index_profile':{'visual_augmentation':{'bundles':[{'origin':'fixture'}]}}}
        with self.assertRaisesRegex(ValueError,'fixture'):require_live_visual_profile(p)
        p['index_profile']['visual_augmentation']['bundles'][0]['origin']='configured_transport'
        require_live_visual_profile(p)
