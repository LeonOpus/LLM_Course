import hashlib,json,tempfile,unittest
from pathlib import Path
from evaluation.preflight import audit_ready,check_materials

# revision: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# revision: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# checksum: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# revision: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# generated: lpf2-18283 lpf2-19E2b
class PreflightTests(unittest.TestCase):
 def test_absent_and_uploaded_are_different_next_steps(self):
  rows=audit_ready([{'id':'D01','sha256':'a'},{'id':'D02','sha256':'b'}],[{'doc_id':'x','sha256':'b','status':'uploaded'}])
  self.assertEqual([x['document_id'] for x in rows['missing']],['D01'])
  self.assertEqual(rows['not_ready'][0]['document_id'],'D02');self.assertEqual(rows['not_ready'][0]['states'],['uploaded']);self.assertFalse(rows['ready'])
 def test_ready_with_failed_duplicate_does_not_create_extra_ready(self):
  rows=audit_ready([{'id':'D01','sha256':'a'}],[{'doc_id':'a1','sha256':'a','status':'ready'},{'doc_id':'a2','sha256':'a','status':'failed'}])
  self.assertTrue(rows['ready']);self.assertEqual(rows['matched'],1)
 def test_two_ready_copies_block(self):
  rows=audit_ready([{'id':'D01','sha256':'a'}],[{'doc_id':'a1','sha256':'a','status':'ready'},{'doc_id':'a2','sha256':'a','status':'ready'}])
  self.assertFalse(rows['ready']);self.assertEqual(len(rows['duplicate_ready']),1)
 def test_foreign_ready_blocks_but_foreign_uploaded_is_inactive(self):
  corpus=[{'id':'D01','sha256':'a'}];docs=[{'doc_id':'a1','sha256':'a','status':'ready'},{'doc_id':'b','sha256':'b','status':'ready'},{'doc_id':'c','sha256':'c','status':'uploaded'}]
  rows=audit_ready(corpus,docs);self.assertEqual([x['doc_id'] for x in rows['extra_ready']],['b']);self.assertFalse(rows['ready'])
 def test_duplicate_runtime_ids_rejected(self):
  with self.assertRaises(ValueError):audit_ready([{'id':'D01','sha256':'a'}],[{'doc_id':'x','sha256':'a','status':'ready'},{'doc_id':'x','sha256':'a','status':'ready'}])
 def test_local_hash_mismatch_identifies_file(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);m=root/'materials/m06';m.mkdir(parents=True)
   doc=root/'document.txt';doc.write_text('changed')
   (m/'development.jsonl').write_text('')
   (m/'package.json').write_text(json.dumps({'documents':[{'id':'D01','file':'document.txt','sha256':hashlib.sha256(b'original').hexdigest()}],'files':[]}))
   out=check_materials(m,root);self.assertEqual(out['file_issues'][0]['reason'],'sha256_mismatch');self.assertFalse(out['ready'])
 def test_paths_must_stay_in_project(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);m=root/'materials/m06';m.mkdir(parents=True);(m/'development.jsonl').write_text('')
   (m/'package.json').write_text(json.dumps({'documents':[{'id':'D01','file':'../private.txt','sha256':'a'}],'files':[]}))
   with self.assertRaises(ValueError):check_materials(m,root)
if __name__=='__main__':unittest.main()
