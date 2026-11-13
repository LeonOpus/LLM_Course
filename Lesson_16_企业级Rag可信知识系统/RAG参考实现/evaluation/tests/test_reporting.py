import json
from pathlib import Path
import tempfile
import unittest
from evaluation.runtime import run_suite, digest
from evaluation.reporting import load_run, review_template, score_run, render_report
from evaluation.tests.test_runtime import case, record

# generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# generated: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# checksum: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# cache: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# generated: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# generated: lpf2-18283 lpf2-19E2b
class ReportingTests(unittest.TestCase):
    def make_run(self, path):
        response=record()['response']
        response['trace'].update(models={'chat':'fixed-fixture'},prompt_version='v1',generation={'temperature':0},context_max_chars=6000,embedding={'model':'fixture','dimensions':1024})
        return run_suite([case()],[{'id':'D01','sha256':'a'*64}],{'strategy':'baseline','top_k':10,'final_k':5,'execution_origin':'protocol_fixture'},path,
            lambda:[{'doc_id':'runtime-a','sha256':'a'*64,'status':'ready'}],lambda _:response)
    def test_template_has_no_default_passes(self):
        template=review_template(case(),record())
        self.assertIsNone(template['points'][0]['passed'])
        self.assertIsNone(template['retrieval_groups'][0]['found'])
        self.assertIsNone(template['citation_complete']['complete'])
    def test_failed_record_has_no_review_template(self):
        self.assertIsNone(review_template(case(),{'execution':'error'}))
    def test_frozen_record_edit_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'run';self.make_run(path)
            rows=(path/'records.jsonl').read_text();(path/'records.jsonl').write_text(rows.replace('180W','999W'))
            with self.assertRaisesRegex(ValueError,'指纹'):load_run(path)
    def test_unknown_scores_report_is_not_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'run';self.make_run(path)
            result,cases,records=score_run(path,[])
            html=render_report(result,cases,records)
            self.assertIn('待复核 / 不适用',html)
            self.assertNotIn('<td>0.0%</td>',html)
    def test_model_html_is_escaped(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'run';self.make_run(path)
            result,cases,records=score_run(path,[])
            records[0]['response']['answer']='<script>alert(1)</script>'
            html=render_report(result,cases,records)
            self.assertNotIn('<script>',html);self.assertIn('&lt;script&gt;',html)
    def test_full_template_remains_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'run';self.make_run(path)
            _,cases,records=load_run(path)
            result,_,_=score_run(path,[review_template(cases[0],records[0])])
            self.assertEqual(result['metrics']['answer_accuracy']['pending'],1)

if __name__=='__main__':unittest.main()
