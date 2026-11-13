import unittest
from rag_app.core import validate_locator, chunk_blocks, transition

# generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# generated: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# cache: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# revision: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# cache: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# revision: lpf2-18283 lpf2-19E2b
class SourceTests(unittest.TestCase):
    def test_pdf_page_and_stable_block(self):
        x = {"kind":"pdf", "block_id":"b1", "page":2}
        self.assertEqual(validate_locator(x), x)
    def test_bad_pdf_pages(self):
        for page in [0, -1, True, "2", None]:
            with self.subTest(page=page), self.assertRaises(ValueError):
                validate_locator({"kind":"pdf", "block_id":"b1", "page":page})
    def test_docx_no_invented_page(self):
        self.assertEqual(validate_locator({"kind":"docx", "block_id":"p2", "heading_path":["安装"]})["block_id"], "p2")
        with self.assertRaises(ValueError):
            validate_locator({"kind":"docx", "block_id":"p2", "page":3})
    def test_excel_partial_location_is_honest(self):
        self.assertEqual(validate_locator({"kind":"xlsx", "block_id":"t1"})["block_id"], "t1")
        with self.assertRaises(ValueError):
            validate_locator({"kind":"xlsx", "block_id":"t1", "cell_range":"A1:C5"})
    def test_text_line_interval(self):
        with self.assertRaises(ValueError):
            validate_locator({"kind":"txt", "block_id":"b1", "line_start":5, "line_end":2})
    def test_ppt_slide(self):
        self.assertEqual(validate_locator({"kind":"pptx", "block_id":"s2", "slide":2})["slide"], 2)
    def test_unsupported_or_empty_id(self):
        for x in [{"kind":"video", "block_id":"a"}, {"kind":"pdf", "block_id":"", "page":1}]:
            with self.assertRaises(ValueError): validate_locator(x)

class ChunkTests(unittest.TestCase):
    def block(self, text, kind="paragraph", block_id="b1", page=1):
        return {"doc_id":"D02", "text":text, "type":kind, "locator":{"kind":"pdf", "block_id":block_id, "page":page}}
    def test_overlap_and_source_offsets(self):
        out=chunk_blocks([self.block("ABCDEFGHIJ")], window=6, overlap=2)
        self.assertEqual([x["text"] for x in out], ["ABCDEF", "EFGHIJ"])
        self.assertEqual([x["char_range"] for x in out], [[0,6],[4,10]])
        self.assertEqual(out[1]["locator"]["page"], 1)
        self.assertNotEqual(out[0]["chunk_id"], out[1]["chunk_id"])
    def test_no_cross_page_merge(self):
        out=chunk_blocks([self.block("aaa"),self.block("bbb",block_id="b2",page=2)])
        self.assertEqual([x["locator"]["page"] for x in out],[1,2])
    def test_table_preserved(self):
        out=chunk_blocks([self.block("型号|功率\nX200|260W", "table")],window=6,overlap=1,preserve_tables=True)
        self.assertEqual(len(out), 1)
        self.assertIn("260W", out[0]["text"])
    def test_table_excess_is_explicit(self):
        with self.assertRaises(ValueError): chunk_blocks([self.block("x"*20,"table")],preserve_tables=True,table_limit=10)
    def test_invalid_windows(self):
        for window,overlap in [(0,0),(3,3),(3,-1),(True,0)]:
            with self.assertRaises(ValueError): chunk_blocks([],window=window,overlap=overlap)
    def test_empty_text_dropped(self):
        self.assertEqual(chunk_blocks([self.block("  ")]), [])
    def test_ids_stable_but_content_sensitive(self):
        a=chunk_blocks([self.block("abc")])[0]["chunk_id"]
        self.assertEqual(a,chunk_blocks([self.block("abc")])[0]["chunk_id"])
        self.assertNotEqual(a,chunk_blocks([self.block("abd")])[0]["chunk_id"])



class StateTests(unittest.TestCase):
    def test_no_skip_to_ready(self):
        with self.assertRaises(ValueError): transition("uploaded","ready")
    def test_success_chain(self):
        states=["uploaded","parsing","parsed","indexing","ready"]
        for a,b in zip(states,states[1:]): self.assertEqual(transition(a,b),b)
    def test_failure_and_explicit_retry(self):
        self.assertEqual(transition("parsing","failed"),"failed")
        self.assertEqual(transition("failed","parsing"),"parsing")
        with self.assertRaises(ValueError): transition("ready","uploaded")

if __name__=="__main__": unittest.main()
