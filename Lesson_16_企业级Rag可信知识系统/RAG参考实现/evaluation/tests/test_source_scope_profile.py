from copy import deepcopy
from pathlib import Path
import tempfile,unittest
from evaluation.runtime import run_suite
from evaluation.tests.test_runtime import case,record

# revision: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# revision: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# generated: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# checksum: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# generated: lpf2-18283 lpf2-19E2b
def profile(mode='explicit'):
 return {'mode':mode,'version':'explicit-registered-document-page-v1'}
class ScopeProfileTests(unittest.TestCase):
 def run_profiles(self,profiles):
  with tempfile.TemporaryDirectory() as folder:
   responses=[]
   for p in profiles:
    r=deepcopy(record()['response']);r['trace'].update(models={'chat':'fixture'},prompt_version='fixture',generation={},context_max_chars=6000,embedding={})
    if p is not None:r['trace']['source_scope_profile']=p
    responses.append(r)
   return run_suite([{**case(),'case_id':'Q'+str(i)} for i in range(len(profiles))],[{'id':'D01','sha256':'a'*64}],
    {'strategy':'baseline','top_k':10,'final_k':5,'require_source_scope_profile':True},Path(folder)/'run',
    lambda:[{'doc_id':'runtime-a','sha256':'a'*64,'status':'ready'}],lambda _:responses.pop(0))
 def test_missing_changed_unknown_are_not_comparable(self):
  for ps in [[None],[profile(),profile('off')],[{**profile(),'version':'unknown'}]]:
   with self.subTest(profiles=ps):self.assertFalse(self.run_profiles(ps)['manifest']['comparable'])
 def test_valid_profile_saved(self):
  p=profile();r=self.run_profiles([p,p]);self.assertTrue(r['manifest']['comparable'])
  self.assertEqual(r['manifest']['observed_configurations'][0]['source_scope_profile'],p)
