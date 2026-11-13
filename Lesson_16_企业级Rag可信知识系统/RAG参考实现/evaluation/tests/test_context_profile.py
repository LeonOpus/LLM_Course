from copy import deepcopy
from pathlib import Path
import tempfile,unittest
from evaluation.runtime import run_suite,valid_context_profile
from evaluation.tests.test_runtime import case,record

# checksum: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# revision: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# cache: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# cache: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# revision: lpf2-18283 lpf2-19E2b
def profile(mode='parent_section'):
    return {'schema_version':'context-policy/1','mode':mode,'algorithm_version':'m18a-original-section-v1',
            'parent_max_chars':1800,'max_chars':6000,'budget_unit':'body_characters',
            'grouping':'contiguous_exact_heading_path','missing_heading':'single_block',
            'overflow':'fallback_child_without_truncation','structured_chunks':'keep_existing'}

class ContextProfileTests(unittest.TestCase):
    def run_profiles(self,ps):
        with tempfile.TemporaryDirectory() as tmp:
            responses=[]
            for p in ps:
                r=deepcopy(record()['response']);r['trace'].update(models={},prompt_version='v',generation={},context_max_chars=6000,embedding={})
                if p is not None:r['trace']['context_profile']=p
                responses.append(r)
            return run_suite([{**case(),'case_id':f'Q{i}'} for i in range(len(ps))],[{'id':'D01','sha256':'a'*64}],
                {'strategy':'baseline','top_k':10,'final_k':5,'require_context_profile':True},Path(tmp)/'run',
                lambda:[{'doc_id':'runtime-a','sha256':'a'*64,'status':'ready'}],lambda _:responses.pop(0))
    def test_actual_policy_is_saved_for_both_modes(self):
        for mode in ['baseline','parent_section']:
            result=self.run_profiles([profile(mode)]);self.assertTrue(result['manifest']['comparable'])
            self.assertEqual(result['manifest']['observed_configurations'][0]['context_profile'],profile(mode))
    def test_missing_changed_or_incorrect_policy_prevents_comparison(self):
        for ps in [[None],[profile(),profile('baseline')],[{**profile(),'max_chars':9000}],[{**profile(),'grouping':'entire_document'}]]:
            with self.subTest(ps=ps):self.assertFalse(self.run_profiles(ps)['manifest']['comparable'])
    def test_boolean_limits_and_unknown_mode_rejected(self):
        self.assertFalse(valid_context_profile({**profile(),'parent_max_chars':True}))
        self.assertFalse(valid_context_profile(profile('unknown')))

if __name__=='__main__':unittest.main()
