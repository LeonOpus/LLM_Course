from copy import deepcopy
from pathlib import Path
import json,tempfile,unittest,sys
# cache: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# cache: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# generated: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# checksum: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# cache: lpf2-18283 lpf2-19E2b
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'backend'))
from evaluation.judging import build_messages,validate_proposal,judge_one,revise_review,decision_fields
from evaluation.tests.test_runtime import case,record,binding,review
from evaluation.reporting import review_template
from rag_app.config import Settings
from rag_app.providers import Bailian
from rag_app.metering import UsageJournal
import httpx

def proposal():
    original=review();template=review_template(case(),record())
    for row in original['critical_errors']:row.setdefault('answer_quote','')
    return {k:v for k,v in original.items() if k not in {'case_id','record_sha256','reviewer'}}

class JudgingTests(unittest.TestCase):
    def test_prompt_separates_untrusted_data_and_omits_unneeded_trace(self):
        r=record();r['response']['trace']['usage_events']=[{'secret':'not needed'}]
        messages=build_messages(case(),r,binding())
        self.assertEqual([m['role'] for m in messages],['system','user']);self.assertIn('JSON',messages[0]['content'])
        self.assertNotIn('not needed',json.dumps(messages));self.assertIn('gold_answer_points',messages[1]['content'])
    def test_student_cannot_grade_holdout_or_oversized_silently(self):
        c=case();c['split']='holdout'
        with self.assertRaises(ValueError):build_messages(c,record(),binding())
        self.assertTrue(build_messages(c,record(),binding(),teacher_holdout=True))
        c=case();c['question']='x'*130000
        with self.assertRaises(ValueError):build_messages(c,record(),binding())
    def test_valid_output_is_always_model_assisted(self):
        r=validate_proposal(proposal(),case(),record(),binding(),'qwen-plus')
        self.assertEqual(r['reviewer']['kind'],'model_assisted');self.assertEqual(r['case_id'],'Q001')
    def test_reviewer_injection_missing_groups_and_invented_quotes_fail(self):
        for mutate in [lambda p:p.update(reviewer={'kind':'human'}),lambda p:p.update(retrieval_groups=[]),lambda p:p['points'][0].update(answer_quote='invented'),lambda p:p['behavior'].update(correct='true')]:
            p=proposal();mutate(p)
            with self.assertRaises(ValueError):validate_proposal(p,case(),record(),binding(),'qwen-plus')
    def test_invalid_json_still_records_judge_usage(self):
        j=UsageJournal(origin='fixture');s=Settings(_env_file=None,dashscope_api_key='fixture')
        def handler(request):
            body=json.loads(request.content);self.assertFalse(body['enable_thinking']);self.assertEqual(body['response_format'],{'type':'json_object'})
            return httpx.Response(200,json={'choices':[{'message':{'content':'not-json'},'finish_reason':'stop'}],'usage':{'prompt_tokens':100,'completion_tokens':10,'total_tokens':110}})
        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            result=judge_one(Bailian(s,client,j),case(),record(),binding(),'qwen-plus')
        self.assertEqual(result['status'],'invalid_output');self.assertTrue(all(v is None for _,v in decision_fields(result['review'])))
        self.assertEqual(j.events()[0]['operation'],'judge');self.assertEqual(j.events()[0]['usage']['counts']['total_tokens'],110)
    def test_length_finish_cannot_become_accepted(self):
        j=UsageJournal(origin='fixture');s=Settings(_env_file=None,dashscope_api_key='fixture')
        with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,json={'choices':[{'message':{'content':json.dumps(proposal())},'finish_reason':'length'}]}))) as client:
            result=judge_one(Bailian(s,client,j),case(),record(),binding(),'qwen-plus')
        self.assertEqual(result['status'],'invalid_output')
    def test_partial_human_revision_stays_provisional(self):
        old=validate_proposal(proposal(),case(),record(),binding(),'qwen-plus');new=deepcopy(old);new['points'][0]['reason']='人工核对功率与单位'
        changed,audit=revise_review(old,new,case(),record(),binding(),'老师A','核对参数原件',False)
        self.assertEqual(changed['reviewer']['kind'],'model_assisted');self.assertTrue(audit['changes']);self.assertEqual(old['points'][0]['reason'],'功率与单位一致')
    def test_full_human_review_requires_no_pending_and_bound_record(self):
        old=validate_proposal(proposal(),case(),record(),binding(),'qwen-plus');new=deepcopy(old)
        changed,audit=revise_review(old,new,case(),record(),binding(),'老师A','逐项核查原件与回答',True)
        self.assertEqual(changed['reviewer']['kind'],'human')
        new['points'][0]['passed']=None
        with self.assertRaises(ValueError):revise_review(old,new,case(),record(),binding(),'老师A','仍有待核实要点',True)
        r=record();r['response']['answer']='changed'
        with self.assertRaises(ValueError):revise_review(old,old,case(),r,binding(),'老师A','原记录已改变',False)


class JudgeBatchTests(unittest.TestCase):
    def setUp(self):
        from tools.demo_judge import setup_run
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        setup_run(self.root/'run',fail_last=False)
    def test_three_invalid_responses_stop_next_call(self):
        from evaluation.judge_batch import grade_run
        journal=UsageJournal(origin='fixture');calls=[]
        def handler(request):
            calls.append(1);return httpx.Response(200,json={'choices':[{'message':{'content':'bad'},'finish_reason':'stop'}]})
        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            batch=grade_run(self.root/'run',self.root/'grade',Bailian(Settings(_env_file=None,dashscope_api_key='fixture'),client,journal),'qwen-plus',limit=4)
        self.assertEqual(len(calls),3);self.assertEqual(batch['result_counts'],{'invalid_output':3,'not_run_after_three_errors':1});self.assertEqual(batch['answer_judgments']['pending'],4)
    def test_holdout_without_frozen_manifest_rejected_before_call(self):
        from evaluation.judge_batch import grade_run
        from evaluation.runtime import digest
        cases=json.loads((self.root/'run/cases.json').read_text());cases[0]['split']='holdout'
        (self.root/'run/cases.json').write_text(json.dumps(cases));manifest=json.loads((self.root/'run/manifest.json').read_text());manifest['cases_sha256']=digest(cases);(self.root/'run/manifest.json').write_text(json.dumps(manifest))
        for teacher in [True,False]:
            with self.assertRaises(ValueError):grade_run(self.root/'run',self.root/'grade',None,'qwen-plus',teacher_holdout=teacher)
        self.assertFalse((self.root/'grade').exists())
    def test_protocol_revision_preserves_original_and_audit(self):
        from tools.demo_judge import demo
        result=demo(self.root/'protocol');self.assertTrue(result['semantic_mistake_corrected'])
        original=json.loads((self.root/'protocol/suggestions/reviews.json').read_text());changed=json.loads((self.root/'protocol/full/reviews.json').read_text())
        self.assertTrue(original[0]['points'][0]['passed']);self.assertFalse(changed[0]['points'][0]['passed'])
        audit=json.loads((self.root/'protocol/full/revision.json').read_text());self.assertIn('/points/0/passed',[d['path'] for d in audit['changes']])
    def test_judge_has_separate_price_rule(self):
        from rag_app.pricing import estimate,pricing_context
        j=UsageJournal(origin='fixture');uid=j.begin('judge','qwen-plus',pricing_context=pricing_context('https://dashscope.aliyuncs.com',{'enable_thinking':False}))
        j.update(uid,outcome='response_received',usage={'prompt_tokens':100,'completion_tokens':10,'total_tokens':110});event=j.events()[0];event['started_at']='2026-09-16T12:00:00+08:00'
        card=json.loads((Path(__file__).resolve().parents[2]/'pricing/beijing-judge-2026-09-16.json').read_text())
        value=estimate([event],card);self.assertEqual(value['estimated_total_cny'],'0.0001');self.assertEqual(value['rows'][0]['operation'],'judge')
    def test_duplicate_json_keys_and_nan_rejected(self):
        from evaluation.judging import _json
        for raw in ['{"x":1,"x":2}','{"x":NaN}','{"x":1e309}']:
            with self.assertRaises(ValueError):_json(raw)
    def test_report_escapes_model_html(self):
        from evaluation.judge_batch import html_report
        value=html_report({},[{'case_id':'Q001','status':'invalid_output','raw_output':'<script>bad()</script>'}])
        self.assertNotIn('<script>',value);self.assertIn('&lt;script&gt;',value)


    def test_propose_cli_uses_provider_and_writes_provisional_review(self):
        from unittest.mock import patch
        from tools.assist_reviews import main
        from tools.demo_judge import wrong_suggestion
        from evaluation.reporting import load_run
        _,cases,records=load_run(self.root/'run');raw=wrong_suggestion(cases[0],records[0])
        client=httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,json={'choices':[{'message':{'content':json.dumps(raw)},'finish_reason':'stop'}],'usage':{'prompt_tokens':100,'completion_tokens':10,'total_tokens':110}})))
        settings=Settings(_env_file=None,dashscope_api_key='fixture')
        with patch('rag_app.config.Settings',return_value=settings),patch('httpx.Client',return_value=client):
            main(['propose','--run',str(self.root/'run'),'--output',str(self.root/'cli-grade'),'--limit','1'])
        reviews=json.loads((self.root/'cli-grade/reviews.json').read_text());self.assertEqual(reviews[0]['reviewer']['kind'],'model_assisted')
        self.assertEqual(len(list((self.root/'cli-grade/usage-runtime/usage-events').glob('*.json'))),1)


    def test_teacher_scope_checks_actual_freeze_file(self):
        from tools.demo_holdout import demo
        from evaluation.judge_batch import grade_run
        demo(self.root/'held-protocol');run=self.root/'held-protocol/holdout';journal=UsageJournal(origin='fixture')
        with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,json={'choices':[{'message':{'content':'{}'},'finish_reason':'stop'}]}))) as client:
            provider=Bailian(Settings(_env_file=None,dashscope_api_key='fixture'),client,journal)
            result=grade_run(run,self.root/'teacher-grade',provider,'qwen-plus',limit=1,teacher_holdout=True)
            self.assertEqual(result['recorded_judge_requests'],1)
            frozen=json.loads((run/'freeze.json').read_text());frozen['holdout_sha256']='0'*64;(run/'freeze.json').write_text(json.dumps(frozen))
            with self.assertRaises(ValueError):grade_run(run,self.root/'bad-teacher-grade',provider,'qwen-plus',limit=1,teacher_holdout=True)
            self.assertEqual(len(journal.events()),1)

if __name__=='__main__':unittest.main()
