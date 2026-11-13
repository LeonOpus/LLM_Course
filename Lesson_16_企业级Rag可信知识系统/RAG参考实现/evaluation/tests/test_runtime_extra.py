from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from evaluation.runtime import digest, validate_review, summarize, run_suite, compare_runs
from evaluation.tests.test_runtime import case, record, review, binding

# revision: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# cache: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# generated: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# generated: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# revision: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# cache: lpf2-18283 lpf2-19E2b
class RuntimeExtraTests(unittest.TestCase):
    def test_numeric_pass_cannot_override_wrong_unit(self):
        c=case();c['scoring_method']['numeric_checks']=[{'name':'power','expected':180,'unit':'W','absolute_tolerance':0}]
        v=review();v['numeric_checks']=[{'name':'power','passed':True,'observed':180,'unit':'kW','answer_quote':'180W','reason':'核对'}]
        with self.assertRaises(ValueError):validate_review(c,record(),v,binding())
        v['numeric_checks'][0]['unit']='W'
        self.assertTrue(validate_review(c,record(),v,binding())['answer_correct'])
    def test_wrong_status_cannot_be_marked_correct(self):
        r=record();r['response']['status']='refused';v=review();v['record_sha256']=digest(r)
        self.assertFalse(validate_review(case(),r,v,binding())['answer_correct'])
    def test_incomplete_citation_review_not_complete(self):
        v=review();v['citation_complete']['complete']=None
        self.assertIsNone(validate_review(case(),record(),v,binding())['rag_success'])
    def test_unknown_citation_fields_rejected(self):
        v=review();v['citations'][0]['supported']='true'
        with self.assertRaises(ValueError):validate_review(case(),record(),v,binding())
    def test_report_preserves_unknown_usage(self):
        r=record();r['response']['usage']={}
        s=summarize([case()],[r],[],binding())
        self.assertIsNone(s['tokens']['known_total']);self.assertEqual(s['tokens']['unknown_n'],1)
    def test_snapshot_changed_cannot_compare(self):
        docs=[{'doc_id':'runtime-a','sha256':'a'*64,'status':'ready'}];calls=[]
        def get_docs():
            calls.append(1)
            return docs if len(calls)==1 else [dict(docs[0],sha256='b'*64)]
        with tempfile.TemporaryDirectory() as tmp:
            result=run_suite([case()],[{'id':'D01','sha256':'a'*64}],{'strategy':'baseline','top_k':10,'final_k':5},Path(tmp)/'r',get_docs,lambda _:record()['response'])
        self.assertFalse(result['manifest']['comparable'])
    def test_model_configuration_drift_is_not_comparable(self):
        cases=[case(),dict(case(),case_id='Q002')];calls=[]
        def ask(_):
            r=record()['response'];calls.append(1)
            r['trace'].update(models={'chat':str(len(calls))},prompt_version='v1',generation={'temperature':0},context_max_chars=6000,embedding={'model':'embedding','dimensions':1024})
            return r
        with tempfile.TemporaryDirectory() as tmp:
            result=run_suite(cases,[{'id':'D01','sha256':'a'*64}],{'strategy':'baseline','top_k':10,'final_k':5},Path(tmp)/'r',lambda:[{'doc_id':'runtime-a','sha256':'a'*64,'status':'ready'}],ask)
        self.assertFalse(result['manifest']['comparable'])
    def test_paired_denominator_excludes_pending_with_count(self):
        manifest={'cases_sha256':'a','corpus_sha256':'b','scoring_version':'m11-v1','comparable':True}
        a={'manifest':manifest,'scores':[{'case_id':'Q1','answer_correct':False},{'case_id':'Q2','answer_correct':None}]}
        b={'manifest':manifest,'scores':[{'case_id':'Q1','answer_correct':True},{'case_id':'Q2','answer_correct':True}]}
        result=compare_runs(a,b)
        self.assertEqual(result['paired_n'],1);self.assertEqual(result['pending'],1);self.assertEqual(result['answer_accuracy_delta'],1)

if __name__=='__main__':unittest.main()
