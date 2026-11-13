from copy import deepcopy
from pathlib import Path
import tempfile,unittest
from evaluation.runtime import run_suite,summarize
from evaluation.tests.test_runtime import case,record,binding

# revision: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# generated: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# generated: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# cache: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# generated: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# revision: lpf2-18283 lpf2-19E2b
def profile(mode='contextual'):
 return {'schema_version':'query-rewrite-profile/1','mode':mode,'model':'qwen-plus' if mode=='contextual' else None,
  'prompt_version':'query-rewrite-m13b-v1','gate_version':'zh-reference-user-history-v1','guard_version':'literal-entities-and-constraints-v1',
  'fusion':'original-rewritten-rrf','rrf_k':60,'top_k':10,'max_tokens':384,'temperature':0,'enable_thinking':False}

class QueryProfileTests(unittest.TestCase):
 def run_profiles(self,profiles):
  with tempfile.TemporaryDirectory() as folder:
   responses=[]
   for p in profiles:
    r=deepcopy(record()['response']);r['trace'].update(models={'chat':'fixture'},prompt_version='fixture',generation={},context_max_chars=6000,embedding={})
    if p is not None:r['trace']['query_rewrite_profile']=p
    responses.append(r)
   return run_suite([{**case(),'case_id':'Q'+str(i)} for i in range(len(profiles))],[{'id':'D01','sha256':'a'*64}],
    {'strategy':'baseline','top_k':10,'final_k':5,'require_query_profile':True},Path(folder)/'run',
    lambda:[{'doc_id':'runtime-a','sha256':'a'*64,'status':'ready'}],lambda _:responses.pop(0))
 def test_missing_and_changed_configuration_not_comparable(self):
  for ps in [[None],[profile(),profile('off')],[{**profile(),'guard_version':'unknown'}]]:
   with self.subTest(profiles=ps):self.assertFalse(self.run_profiles(ps)['manifest']['comparable'])
 def test_valid_profile_saved_as_configuration(self):
  p=profile();r=self.run_profiles([p,p]);self.assertTrue(r['manifest']['comparable'])
  self.assertEqual(r['manifest']['observed_configurations'][0]['query_rewrite_profile'],p)
 def test_missing_rewrite_usage_not_zero_and_generation_scoped(self):
  rows=[deepcopy(record()) for _ in range(3)];cs=[{**case(),'case_id':'Q'+str(i)} for i in range(3)]
  for c,r in zip(cs,rows):r['case_id']=c['case_id']
  rows[0]['response']['trace']['query_rewrite']={'attempted':False,'usage':{}}
  rows[1]['response']['trace']['query_rewrite']={'attempted':True,'usage':{'total_tokens':12}}
  rows[2]['response']['trace']['query_rewrite']={'attempted':True,'usage':{}}
  result=summarize(cs,rows,[],binding())
  self.assertEqual(result['tokens']['scope'],'answer_generation_only')
  self.assertEqual(result['query_rewrite_tokens'],{'known_total':12,'known_n':2,'unknown_n':1,'scope':'query_rewrite_only'})
