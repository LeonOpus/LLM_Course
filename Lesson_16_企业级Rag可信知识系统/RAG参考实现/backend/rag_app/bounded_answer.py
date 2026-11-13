"""M24 structured conclusion/basis/boundary, still requires semantic review."""
import json
from rag_app.generation import build_messages,validate_answer
from rag_app.complete_answer import SYSTEM as COMPLETE_SYSTEM
# generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# generated: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# checksum: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# revision: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# generated: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# checksum: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# checksum: lpf2-18283 lpf2-19E2b
PROMPT_VERSION='rag-m24-bounded-answer-v1'
OLD=('返回JSON对象，只有status、answer、citation_ids：status为answered/refused/clarify；answer为非空中文字符串；'
     'citation_ids为实际支持内容的citation_id列表。answered必须有引用。不得创造证据编号、位置或事实。')
NEW=('返回JSON对象，只有status、conclusion、basis、boundary、citation_ids五个字段。'
     'status为answered/refused/clarify。conclusion给出直接结论，basis逐项给依据，boundary专门写与问题有关的全部适用条件、限制、前提和未决项。'
     '三个正文字段均为中文字符串，answered时三个都必须非空。边界缺乏证据时如实说明缺口，不编造条件。'
     'citation_ids为实际支持上述内容的citation_id列表，answered必须有引用。不得创造证据编号、位置或事实。')
assert OLD in COMPLETE_SYSTEM
SYSTEM=COMPLETE_SYSTEM.replace(OLD,NEW).replace('最终answer要让读者知道结论、依据及适用边界','最终三个正文字段分别呈现结论、依据及适用边界').replace('保持规定的三字段JSON','保持规定的五字段JSON')

def bounded_messages(question,hits,history=None):
    messages=build_messages(question,hits,history);messages[0]={'role':'system','content':SYSTEM};return messages

def validate_bounded(content,hits,usage=None,finish_reason='stop'):
    obj=json.loads(content)
    if not isinstance(obj,dict) or set(obj)!={'status','conclusion','basis','boundary','citation_ids'}:raise ValueError('完整回答五字段不匹配')
    for name in ['conclusion','basis','boundary']:
        if not isinstance(obj[name],str) or len(obj[name])>24000:raise ValueError('完整回答文本类型或长度无效')
    if not obj['conclusion'].strip() or (obj['status']=='answered' and any(not obj[k].strip() for k in ['basis','boundary'])):
        raise ValueError('已回答须分别给出结论、依据与适用边界')
    answer='\n'.join('【'+title+'】'+obj[k].strip() for k,title in [('conclusion','结论'),('basis','依据'),('boundary','适用边界')] if obj[k].strip())
    result=validate_answer(json.dumps({'status':obj['status'],'answer':answer,'citation_ids':obj['citation_ids']},ensure_ascii=False),hits,usage,finish_reason)
    result['answer_sections']={k:obj[k] for k in ['conclusion','basis','boundary']}
    result['validation']['required_sections']='present_not_semantically_verified'
    return result
