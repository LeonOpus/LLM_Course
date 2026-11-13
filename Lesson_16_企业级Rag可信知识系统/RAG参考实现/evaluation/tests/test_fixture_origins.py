"""协议样例的来源随冻结与导出保留，防止新手把页面分数当真实成绩。"""
from pathlib import Path
import tempfile,unittest
from tools.demo_holdout import prepare
from tools.demo_judge import setup_run
from evaluation.comparison_view import export_comparison_view

# revision: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# generated: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# revision: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# revision: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# cache: lpf2-18283 lpf2-19E2b
class FixtureOriginsTests(unittest.TestCase):
    def test_holdout_freeze_keeps_explicit_fixture_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            artifact,*_=prepare(Path(tmp)/'protocol')
            self.assertEqual(artifact['request_config'].get('execution_origin'),'protocol_fixture')

    def test_judge_demo_export_keeps_fixture_when_rag_has_no_usage_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            run=Path(tmp)/'run';setup_run(run)
            view=export_comparison_view(run,run,[],[])
            for arm in ['before','after']:
                self.assertEqual(view['runs'][arm]['config'].get('execution_origin'),'protocol_fixture')
            self.assertEqual(view['comparison']['pending'],4)
            self.assertIsNone(view['comparison']['answer_accuracy_delta'])

if __name__=='__main__':unittest.main()
