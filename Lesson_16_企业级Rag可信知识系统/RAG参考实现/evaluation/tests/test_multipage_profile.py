import unittest
from copy import deepcopy
from evaluation.runtime import valid_index_profile

# revision: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# checksum: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# checksum: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# cache: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# cache: lpf2-18283 lpf2-19E2b
class MultipageProfileTests(unittest.TestCase):
    def profile(self):
        return {'schema_version':'rag-index-profile/1','strategy':'multipage_context','collection':'rag_course_example',
                'documents':[{'doc_id':'D','source_sha256':'a'*64,'blocks_sha256':'b'*64,'manifest_sha256':'c'*64,'plan_sha256':'d'*64,
                              'chunking':{'strategy':'multipage_context','plan_sha256':'d'*64,'algorithm_version':'m12c-multipage-v1',
                                          'plan_schema_version':2,'reviewed_table_count':2,'window':600,'overlap':100,'preserve_tables':False}}]}
    def test_new_strategy_and_empty_reviewed_set_supported(self):
        p=self.profile();self.assertTrue(valid_index_profile(p,{'D':{'sha256':'a'*64}}))
        p['strategy']='multipage_rows';p['documents'][0]['chunking']['strategy']='multipage_rows';p['documents'][0]['chunking']['reviewed_table_count']=0
        self.assertTrue(valid_index_profile(p,{'D':{'sha256':'a'*64}}))
    def test_wrong_algorithm_schema_and_budget_rejected(self):
        for key,value in [('algorithm_version','m12-structure-v1'),('plan_schema_version',1),('plan_schema_version',True),
                          ('reviewed_table_count',-1),('reviewed_table_count',True),('window',2000),('overlap',0),('preserve_tables',True)]:
            p=self.profile();p['documents'][0]['chunking'][key]=value
            with self.subTest(key=key,value=value):self.assertFalse(valid_index_profile(p,{'D':{'sha256':'a'*64}}))
if __name__=='__main__':unittest.main()
