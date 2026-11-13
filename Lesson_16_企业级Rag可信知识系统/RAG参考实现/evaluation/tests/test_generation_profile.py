from copy import deepcopy
from pathlib import Path
import tempfile,unittest
from evaluation.runtime import run_suite
from evaluation.tests.test_runtime import case,record

# cache: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# generated: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# generated: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# generated: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# revision: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# checksum: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# checksum: lpf2-18283 lpf2-19E2b
def profile(mode='evidence_ledger'):
    return {'schema_version':'generation-policy/1','mode':mode,
            'prompt_version':'rag-m10-v1' if mode=='baseline' else 'rag-m14-ledger-v1',
            'validator_version':'membership-v1' if mode=='baseline' else 'ledger-quotes-decimal-v1',
            'decimal_precision':None if mode=='baseline' else 28,'semantic_support':'not_evaluated'}

class GenerationProfileTests(unittest.TestCase):
    def run_profiles(self,profiles,prompt_override=None):
        with tempfile.TemporaryDirectory() as folder:
            responses=[]
            for p in profiles:
                r=deepcopy(record()['response']);r['trace'].update(models={'chat':'fixture'},
                    prompt_version=prompt_override or (p['prompt_version'] if p else 'legacy'),generation={},context_max_chars=6000,embedding={})
                if p is not None:r['trace']['generation_profile']=p
                responses.append(r)
            return run_suite([{**case(),'case_id':'Q'+str(i)} for i in range(len(profiles))],[{'id':'D01','sha256':'a'*64}],
                {'strategy':'baseline','top_k':10,'final_k':5,'require_generation_profile':True},Path(folder)/'run',
                lambda:[{'doc_id':'runtime-a','sha256':'a'*64,'status':'ready'}],lambda _:responses.pop(0))
    def test_missing_changed_or_unknown_profile_not_comparable(self):
        for ps in [[None],[profile(),profile('baseline')],[{**profile(),'semantic_support':'passed'}],[{**profile(),'decimal_precision':True}]]:
            with self.subTest(profiles=ps):self.assertFalse(self.run_profiles(ps)['manifest']['comparable'])
    def test_actual_prompt_must_match_policy(self):
        self.assertFalse(self.run_profiles([profile()],prompt_override='rag-m10-v1')['manifest']['comparable'])
    def test_stable_policy_saved_and_baseline_supported(self):
        for mode in ['baseline','evidence_ledger']:
            p=profile(mode);result=self.run_profiles([p,p])
            self.assertTrue(result['manifest']['comparable'])
            self.assertEqual(result['manifest']['observed_configurations'][0]['generation_profile'],p)

if __name__=='__main__':unittest.main()
