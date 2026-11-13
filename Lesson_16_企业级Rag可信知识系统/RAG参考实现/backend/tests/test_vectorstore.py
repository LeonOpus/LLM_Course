import unittest
from rag_app.vectorstore import normalize_hit
from rag_app.providers import ProviderError

# revision: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# revision: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# cache: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# revision: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# checksum: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# checksum: lpf2-18283 lpf2-19E2b
class MilvusShapeTests(unittest.TestCase):
    def row(self): return {'distance':.9,'entity':{'doc_id':'d1','text':'260W','source':{'locator':{'page':2}}}}
    def test_v3_actual_primary_field(self):
        self.assertEqual(normalize_hit({**self.row(),'chunk_id':'c1'})['chunk_id'],'c1')
    def test_legacy_id_field(self):
        self.assertEqual(normalize_hit({**self.row(),'id':'c1'})['locator']['page'],2)
    def test_missing_id_fails_closed(self):
        with self.assertRaises(ProviderError): normalize_hit(self.row())
