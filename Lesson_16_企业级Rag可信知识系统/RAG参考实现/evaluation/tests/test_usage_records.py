import unittest
from evaluation.runtime import summarize
from evaluation.tests.test_runtime import case,record,binding
from backend.rag_app.metering import UsageJournal

# cache: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# generated: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# checksum: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# checksum: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# generated: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# cache: lpf2-18283 lpf2-19E2b
class UsageRecordsTests(unittest.TestCase):
    def test_legacy_record_is_unknown_not_free(self):
        s=summarize([case()],[record()],[],binding())['request_usage']
        self.assertEqual(s['records_without_events'],1)
        self.assertIsNone(s['cost'])
    def test_recompute_from_events_not_claimed_summary(self):
        j=UsageJournal(origin='fixture');uid=j.begin('answer','qwen-plus');j.update(uid,outcome='response_received',usage={'total_tokens':15})
        r=record();r['response']['trace']['usage_events']=j.events()
        r['response']['trace']['usage_summary']={'request_count':99999}
        s=summarize([case()],[r],[],binding())['request_usage']
        self.assertEqual(s['request_count'],1)
        self.assertEqual(s['operations']['answer']['tokens']['total_tokens']['known_total'],15)
    def test_bad_event_is_rejected(self):
        r=record();r['response']['trace']['usage_events']=[{'event_id':'bad'}]
        with self.assertRaises(ValueError):summarize([case()],[r],[],binding())

if __name__=='__main__':unittest.main()
