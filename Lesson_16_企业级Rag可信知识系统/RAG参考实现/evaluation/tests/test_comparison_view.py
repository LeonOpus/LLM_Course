import json,tempfile,unittest
from pathlib import Path
from evaluation.tests import test_reporting as fixtures
from evaluation.comparison_view import export_comparison_view

# checksum: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# generated: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# generated: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# generated: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# cache: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# revision: lpf2-18283 lpf2-19E2b
class ComparisonView(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  self.left=self.root/'left';self.right=self.root/'right'
  helper=fixtures.ReportingTests();helper.make_run(self.left);helper.make_run(self.right)
 def tearDown(self):self.tmp.cleanup()
 def bundle(self):return export_comparison_view(self.left,self.right,[],[])
 def test_unreviewed_pairs_remain_pending(self):
  b=self.bundle();self.assertEqual(b['schema_version'],'rag-comparison-view/1')
  self.assertEqual(b['comparison']['paired_n'],0);self.assertIsNone(b['comparison']['answer_accuracy_delta'])
  self.assertEqual(b['cases'][0]['change'],'pending')
 def test_question_and_observed_answer_are_available(self):
  c=self.bundle()['cases'][0];self.assertTrue(c['question']);self.assertEqual(c['before']['answer'],'X100功率180W')
  self.assertIn('candidates',c['before']['trace'])
 def test_gold_answers_are_not_exported_as_model_context(self):
  b=self.bundle();self.assertNotIn('gold_answer_points',json.dumps(b));self.assertNotIn('gold_evidence',json.dumps(b))
 def test_fixture_origin_is_preserved(self):
  self.assertEqual(self.bundle()['runs']['before']['config']['execution_origin'],'protocol_fixture')
 def test_modified_frozen_records_are_rejected(self):
  p=self.right/'records.jsonl';p.write_text(p.read_text().replace('180W','999W'))
  with self.assertRaisesRegex(ValueError,'指纹'):self.bundle()
 def test_mismatched_corpus_not_accepted(self):
  p=self.right/'manifest.json';m=json.loads(p.read_text());m['corpus_sha256']='0'*64;p.write_text(json.dumps(m))
  with self.assertRaises(ValueError):self.bundle()

if __name__=='__main__':unittest.main()
