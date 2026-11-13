from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from evaluation.runtime import run_suite
from evaluation.tests.test_runtime import case,record

# revision: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# revision: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# checksum: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# revision: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# generated: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# checksum: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# checksum: lpf2-18283 lpf2-19E2b
def profile(mode='dense'):
 return {'schema_version':'rag-retrieval-profile/1','mode':mode,'branch_top_k':10,'output_top_k':10,
         'rrf_k':60 if mode=='hybrid' else None,'full_text':{'algorithm':'milvus-bm25','analyzer':{'type':'chinese'},'field':'sparse','version':1,'bm25_k1':1.2,'bm25_b':.75,'index_algorithm':'DAAT_MAXSCORE'}}

class RetrievalProfileTests(unittest.TestCase):
 def run_profiles(self,profiles):
  with tempfile.TemporaryDirectory() as folder:
   responses=[]
   for p in profiles:
    response=deepcopy(record()['response']);response['trace'].update(models={'chat':'fixture'},prompt_version='fixture',generation={},context_max_chars=6000,embedding={})
    if p is not None:response['trace']['retrieval_profile']=p
    responses.append(response)
   return run_suite([{**case(),'case_id':'Q'+str(i)} for i in range(len(profiles))],[{'id':'D01','sha256':'a'*64}],
     {'strategy':'baseline','top_k':10,'final_k':5,'require_retrieval_profile':True},Path(folder)/'run',
     lambda:[{'doc_id':'runtime-a','sha256':'a'*64,'status':'ready'}],lambda _:responses.pop(0))
 def test_missing_retrieval_config_fails_required_gate(self):
  self.assertFalse(self.run_profiles([None])['manifest']['comparable'])
 def test_mode_changed_mid_run_cannot_compare(self):
  self.assertFalse(self.run_profiles([profile(),profile('hybrid')])['manifest']['comparable'])
 def test_actual_configuration_frozen_not_just_label(self):
  p=profile('hybrid');r=self.run_profiles([p,p]);self.assertTrue(r['manifest']['comparable'])
  self.assertEqual(r['manifest']['observed_configurations'][0]['retrieval_profile'],p)
 def test_invalid_mode_k_or_fulltext_rejected(self):
  for updates in [{'mode':'magic'},{'branch_top_k':True},{'output_top_k':5},{'full_text':None},{'rrf_k':1}]:
   p=profile('hybrid');p.update(updates)
   with self.subTest(updates=updates):self.assertFalse(self.run_profiles([p])['manifest']['comparable'])
