import json
from copy import deepcopy
import unittest
from rag_app.ledger import validate_ledger, ledger_messages, generation_profile
from rag_app.config import Settings

# cache: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# cache: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# cache: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# generated: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# generated: lpf2-18283 lpf2-19E2b
HITS=[{'chunk_id':'c1','doc_id':'d1','text':'2026版规则：每30分钟收取100元，不足30分钟向上取整。','locator':{'page':2}}]
REF={'citation_id':'c1','quote':HITS[0]['text']}
QUESTION='按2026版规则，实际服务17分钟收多少？'

def payload():
    return {'status':'answered','message':'','applicability':{'state':'supported','reason':'问题明确指定2026版。','evidence':[REF]},
            'claims':[{'text':'采用2026版按30分钟向上取整的规则。','evidence':[REF]}],
            'calculations':[{'label':'服务费','inputs':[
                {'id':'minutes','value':'17','unit':'分钟','source':{'kind':'question','quote':QUESTION}},
                {'id':'interval','value':'30','unit':'分钟','source':{'kind':'evidence',**REF}},
                {'id':'price','value':'100','unit':'元/计费段','source':{'kind':'evidence',**REF}}],
                'steps':[{'id':'ratio','op':'div','args':['minutes','interval']},
                         {'id':'count','op':'ceil','args':['ratio']},
                         {'id':'fee','op':'mul','args':['count','price']}],'result':'fee','unit':'元'}]}

def validate(obj):return validate_ledger(json.dumps(obj,ensure_ascii=False),HITS,QUESTION,{'total_tokens':20},'stop')

class LedgerTests(unittest.TestCase):
    def test_calculation_is_recomputed_and_locations_come_from_context(self):
        result=validate(payload())
        self.assertIn('100 元',result['answer'])
        self.assertEqual(result['ledger']['calculations'][0]['computed'],'100')
        self.assertEqual(result['citations'][0]['locator'],{'page':2})
        self.assertEqual(result['validation']['semantic_support'],'not_evaluated')
        self.assertEqual(result['validation']['arithmetic'],'passed')
    def test_quote_must_be_exact_and_belong_to_citation(self):
        for ref in [{'citation_id':'invented','quote':HITS[0]['text']},{'citation_id':'c1','quote':'每30分钟免费'}]:
            obj=payload();obj['claims'][0]['evidence']=[ref]
            with self.subTest(ref=ref),self.assertRaises(ValueError):validate(obj)
    def test_supported_requires_evidence_and_missing_cannot_answer(self):
        for state in ['missing','conflict']:
            obj=payload();obj['applicability']['state']=state
            with self.subTest(state=state),self.assertRaises(ValueError):validate(obj)
        obj=payload();obj['applicability']['evidence']=[]
        with self.assertRaises(ValueError):validate(obj)
    def test_refusal_and_clarification_preserve_reason_without_calculations(self):
        for status in ['refused','clarify']:
            obj=payload();obj.update(status=status,message='请提供规则版本。',claims=[],calculations=[])
            obj['applicability'].update(state='missing',evidence=[])
            self.assertEqual(validate(obj)['answer'],'请提供规则版本。')
            obj['calculations']=payload()['calculations']
            with self.assertRaises(ValueError):validate(obj)
    def test_arbitrary_answer_and_extra_model_fields_rejected(self):
        for key,value in [('answer','免费'),('citation_ids',['evil'])]:
            obj=payload();obj[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate(obj)
        obj=payload();obj['message']='另送一年保修。'
        with self.assertRaises(ValueError):validate(obj)
    def test_numeric_value_must_be_in_declared_source_and_sign_preserved(self):
        for value in ['7','170','-17','NaN','1e100','true']:
            obj=payload();obj['calculations'][0]['inputs'][0]['value']=value
            with self.subTest(value=value),self.assertRaises(ValueError):validate(obj)
    def test_division_zero_forward_reference_and_unsupported_op_rejected(self):
        for args,op in [(['later','price'],'mul'),(['price','price'],'exec')]:
            obj=payload();obj['calculations'][0]['steps'][0].update(args=args,op=op)
            with self.subTest(op=op),self.assertRaises(ValueError):validate(obj)
        obj=payload();obj['calculations'][0]['steps'].insert(0,{'id':'zero','op':'sub','args':['price','price']})
        obj['calculations'][0]['steps'][1]['args']=['minutes','zero']
        with self.assertRaises(ValueError):validate(obj)
    def test_duplicate_and_unused_inputs_or_steps_fail(self):
        for kind in ['duplicate','unused_input','unused_step']:
            obj=payload();calc=obj['calculations'][0]
            if kind=='duplicate':calc['inputs'].append(deepcopy(calc['inputs'][0]))
            elif kind=='unused_input':calc['inputs'].append({**deepcopy(calc['inputs'][0]),'id':'extra'})
            else:calc['steps'].append({'id':'extra','op':'add','args':['price','price']})
            with self.subTest(kind=kind),self.assertRaises(ValueError):validate(obj)
    def test_finalization_and_result_contract_limits(self):
        with self.assertRaises(ValueError):validate_ledger(json.dumps(payload()),HITS,QUESTION,finish_reason='length')
        for mutation in ['empty','overlong','wrong_type']:
            obj=payload()
            if mutation=='empty':obj.update(claims=[],calculations=[])
            if mutation=='overlong':obj['claims'][0]['text']='字'*2001
            if mutation=='wrong_type':obj['calculations']={}
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):validate(obj)
    def test_decimal_addition_and_percent_conversion(self):
        from rag_app.ledger import _calculate
        calc={'label':'十进制演练','inputs':[
            {'id':'a','value':'0.1','unit':'元','source':{'kind':'question','quote':'0.1元加0.2元'}},
            {'id':'b','value':'0.2','unit':'元','source':{'kind':'question','quote':'0.1元加0.2元'}}],
            'steps':[{'id':'sum','op':'add','args':['a','b']}],'result':'sum','unit':'元'}
        result,_,_=_calculate(calc,{},'0.1元加0.2元')
        self.assertEqual(result['computed'],'0.3')
        calc.update(inputs=[{'id':'p','value':'0.5','unit':'%','source':{'kind':'question','quote':'0.5%'}}],
                    steps=[{'id':'ratio','op':'percent','args':['p']}],result='ratio',unit='无量纲')
        result,_,_=_calculate(calc,{},'0.5%')
        self.assertEqual(result['computed'],'0.005')
        calc['inputs'][0]['unit']='元'
        with self.assertRaises(ValueError):_calculate(calc,{},'0.5%')
    def test_semantically_wrong_claim_is_not_falsely_certified(self):
        obj=payload();obj['claims'][0]['text']='2025版永久免费。'
        result=validate(obj)
        self.assertEqual(result['validation']['semantic_support'],'not_evaluated')
        self.assertEqual(result['validation']['applicability'],'model_declared_not_verified')
    def test_prompt_keeps_question_history_evidence_and_structured_schema(self):
        messages=ledger_messages(QUESTION,HITS,[{'role':'user','content':'我问售后计费。'}])
        self.assertEqual(messages[1]['content'],'我问售后计费。')
        self.assertEqual(json.loads(messages[-1]['content'])['question'],QUESTION)
        self.assertIn('calculations',messages[0]['content'])
        self.assertIn('conflict',messages[0]['content'])
    def test_profile_different_from_baseline_and_default_off(self):
        settings=Settings(_env_file=None)
        self.assertEqual(settings.generation_policy,'baseline')
        a=generation_profile(settings)
        settings.generation_policy='evidence_ledger';b=generation_profile(settings)
        self.assertNotEqual(a,b)
        self.assertEqual(b['semantic_support'],'not_evaluated')

if __name__=='__main__':unittest.main()
