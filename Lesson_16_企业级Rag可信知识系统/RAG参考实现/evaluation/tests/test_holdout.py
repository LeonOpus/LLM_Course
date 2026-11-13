from copy import deepcopy
from pathlib import Path
import tempfile,unittest,json
from evaluation.holdout import partition,teacher_request,source_snapshot,verify_sources,guarded_ask,reserve_attempt
from evaluation.runtime import safe_request,digest

# generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# revision: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# generated: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# cache: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# checksum: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# generated: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# generated: lpf2-18283 lpf2-19E2b
class HoldoutBoundaryTests(unittest.TestCase):
    def dataset(self):
        cases=[]
        for i in range(200):
            split='development' if i<140 else 'holdout'
            cases.append({'case_id':f'Q{i+1:03}','split':split,'smoke':i<20,'review_status':'source_checked_by_author','question':f'问题{i}',
                          'fact_family_id':'dev' if i<140 else 'held','related_fact_family_ids':[],'target_fact_ids':['d' if i<140 else 'h']})
        registry={'families':{'dev':{'split':'development'},'held':{'split':'holdout'}},'atoms':{'d':{'family_id':'dev'},'h':{'family_id':'held'}}}
        return cases,registry
    def test_counts_and_alias_family_isolation(self):
        cases,reg=self.dataset();parts=partition(cases,reg);self.assertEqual([len(p) for p in parts],[140,60])
        cases[-1]['target_fact_ids']=['alias'];reg['atoms']['alias']={'alias_of':'d'}
        with self.assertRaises(ValueError):partition(cases,reg)
    def test_duplicate_missing_or_unreviewed_rejected(self):
        for kind in ['missing','duplicate','review']:
            cases,reg=self.dataset()
            if kind=='missing':cases.pop()
            elif kind=='duplicate':cases[-1]['case_id']=cases[0]['case_id']
            else:cases[-1]['review_status']='draft'
            with self.assertRaises(ValueError):partition(cases,reg)
    def test_teacher_request_whitelist_student_still_rejects(self):
        c=self.dataset()[0][-1];c.update(gold_answer_points=[{'text':'secret gold'}],scope_documents=['secret scope'],conversation_history=[])
        config={'strategy':'baseline','top_k':10,'final_k':5}
        with self.assertRaises(ValueError):safe_request(c,config,[])
        body=teacher_request(c,config,['real-doc']);self.assertEqual(set(body),{'question','history','strategy','top_k','final_k','doc_ids'})
        self.assertNotIn('secret',json.dumps(body));self.assertEqual(c['split'],'holdout')
    def test_sources_ignore_secrets_but_detect_added_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'backend/rag_app').mkdir(parents=True);(root/'backend/rag_app/app.py').write_text('x=1');(root/'.env').write_text('secret')
            snapshot=source_snapshot(root);self.assertNotIn('.env',snapshot);verify_sources(root,snapshot)
            (root/'backend/rag_app/new.py').write_text('x=2')
            with self.assertRaises(ValueError):verify_sources(root,snapshot)
    def test_drift_preserves_response_and_stops_further_requests(self):
        calls=[];state={};profile={'models':{'chat':'a'}}
        ask=guarded_ask(lambda body:(calls.append(body) or {'status':'answered','answer':'x','trace':{'models':{'chat':'b'}}}),profile,state)
        first=ask({});self.assertEqual(first['answer'],'x');self.assertTrue(state['drift'])
        with self.assertRaises(ValueError):ask({})
        self.assertEqual(len(calls),1)
    def test_attempt_reservation_survives_new_output_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=reserve_attempt(tmp,'a'*64,{'output':'run-one'});self.assertTrue(path.is_file())
            with self.assertRaises(ValueError):reserve_attempt(tmp,'a'*64,{'output':'run-two'})


class HoldoutIntegrationTests(unittest.TestCase):
    def setUp(self):
        from tools.demo_holdout import prepare
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.project=self.root/'project';(self.project/'backend/rag_app').mkdir(parents=True);(self.project/'backend/rag_app/a.py').write_text('x=1')
        self.out=self.root/'demo';self.artifact,self.cases,self.registry,self.docs,self.response,self.health=prepare(self.out,self.project)
    def run_held(self,ask=None,docs=None):
        from evaluation.holdout import run_holdout
        return run_holdout(self.artifact,self.project,self.cases,self.registry,self.out/'held',self.out/'attempts',lambda:self.health,lambda:self.docs if docs is None else docs,ask or (lambda body:deepcopy(self.response)))
    def test_60_keeps_holdout_labels_and_pending_grades(self):
        result=self.run_held();self.assertEqual(result['execution_counts'],{'ok':60});self.assertTrue(result['manifest']['comparable'])
        saved=json.loads((self.out/'held/cases.json').read_text());self.assertTrue(all(c['split']=='holdout' for c in saved));self.assertIsNone(result['metrics']['answer_accuracy']['value'])
    def test_unreviewed_development_cannot_freeze(self):
        from evaluation.holdout import freeze
        with self.assertRaisesRegex(ValueError,'评分'):
            freeze(self.project,self.out/'development',[],self.cases,self.registry,self.out/'bad-freeze.json','这是尚未完成评分的开发运行')
        self.assertFalse((self.out/'bad-freeze.json').exists())
    def test_drift_stops_and_makes_run_noncomparable(self):
        calls=[];response=deepcopy(self.response);response['trace']['models']['chat']='other'
        result=self.run_held(lambda body:(calls.append(body) or response));self.assertEqual(len(calls),1);self.assertFalse(result['manifest']['comparable'])
        self.assertEqual(result['execution_counts'],{'ok':1,'error':3,'not_run':56})
    def test_source_or_corpus_change_blocks_before_asking(self):
        with self.assertRaises(ValueError):self.run_held(lambda body:self.fail('must not ask'),docs=[])
        (self.project/'backend/rag_app/a.py').write_text('x=2')
        with self.assertRaises(ValueError):self.run_held(lambda body:self.fail('must not ask'))
        self.assertFalse((self.out/'attempts').exists())
    def test_context_policy_change_blocks_before_asking(self):
        self.health['context_configuration']['context_policy']='parent_section'
        with self.assertRaisesRegex(ValueError,'上下文'):self.run_held(lambda body:self.fail('must not ask'))
        self.assertFalse((self.out/'attempts').exists())
    def test_source_change_during_run_invalidates_persisted_manifest(self):
        def ask(body):
            (self.project/'backend/rag_app/a.py').write_text('x=2');return deepcopy(self.response)
        with self.assertRaises(ValueError):self.run_held(ask)
        manifest=json.loads((self.out/'held/manifest.json').read_text());self.assertFalse(manifest['comparable']);self.assertEqual(manifest['status'],'interrupted')
    def test_plan_requires_same_frozen_dataset_and_distinct_candidate(self):
        from evaluation.holdout import plan_pair,validate_plan
        with self.assertRaises(ValueError):plan_pair(self.artifact,self.artifact,self.out/'bad-plan.json')
        other=deepcopy(self.artifact);other['candidate_sha256']='f'*64;other['holdout_sha256']='e'*64;other['freeze_sha256']=digest({k:v for k,v in other.items() if k!='freeze_sha256'})
        with self.assertRaises(ValueError):plan_pair(self.artifact,other,self.out/'bad-plan.json')
    def test_selection_reason_does_not_allow_second_attempt(self):
        from evaluation.holdout import freeze
        reviews=json.loads((self.out/'development-reviews.json').read_text())
        second=freeze(self.project,self.out/'development',reviews,self.cases,self.registry,self.out/'another-freeze.json','换一个理由并不会产生一个新的待测版本')
        self.assertEqual(second['candidate_sha256'],self.artifact['candidate_sha256'])
    def test_teacher_cli_plan_run_compare_uses_api_health(self):
        from unittest.mock import patch
        from tools.demo_holdout import prepare
        from tools.run_holdout import main
        prepare(self.out/'candidate',self.project,final_k=4)
        plan=self.out/'cli-plan.json';base=self.out/'cli-baseline';candidate=self.out/'cli-candidate';called=[]
        main(['plan','--baseline',str(self.out/'freeze.json'),'--candidate',str(self.out/'candidate/freeze.json'),'--output',str(plan)])
        def http(path,body=None):
            called.append(path)
            if path=='/api/health':return deepcopy(self.health)
            if path=='/api/documents':return deepcopy(self.docs)
            if path=='/api/ask':
                self.assertEqual(set(body),{'question','history','strategy','top_k','final_k','doc_ids'})
                return deepcopy(self.response)
            self.fail('wrong HTTP route')
        with patch('tools.run_holdout.teacher_dataset',return_value=(self.cases,self.registry)),patch('tools.run_holdout.http_client',return_value=http):
            for arm,out in [('baseline',base),('candidate',candidate)]:
                main(['run','--plan',str(plan),'--arm',arm,'--output',str(out),'--project',str(self.project),'--teacher-data',str(self.out)])
        empty=self.out/'empty.json';empty.write_text('[]')
        main(['compare','--plan',str(plan),'--baseline-run',str(base),'--candidate-run',str(candidate),'--baseline-reviews',str(empty),'--candidate-reviews',str(empty),'--output',str(self.out/'cli-comparison.json')])
        self.assertEqual(called.count('/api/ask'),120)
        result=json.loads((self.out/'cli-comparison.json').read_text());self.assertEqual(result['pending'],60);self.assertIsNone(result['answer_accuracy_delta'])
        from evaluation.holdout import compare_planned
        late=json.loads(plan.read_text());late['created_at']='2099-01-01T00:00:00+00:00';late['plan_sha256']=digest({k:v for k,v in late.items() if k!='plan_sha256'})
        with self.assertRaisesRegex(ValueError,'早于'):compare_planned(late,base,candidate,[],[])

if __name__=='__main__':unittest.main()
