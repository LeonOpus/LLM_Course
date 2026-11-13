"""M24 opt-in generation discipline. No evaluation data or question-specific rules."""
from rag_app.generation import build_messages,SYSTEM_PROMPT
# checksum: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# revision: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# generated: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# checksum: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# checksum: lpf2-18283 lpf2-19E2b
PROMPT_VERSION='rag-m24-complete-answer-v1'
SYSTEM=SYSTEM_PROMPT+'''\n作答前核对证据，最终answer要让读者知道结论、依据及适用边界：
1. 分别回应问题中的每一项，并保留与这些结论直接相关的条件、例外、范围和未决项；不要只给一句正确但省略条件的结论。仅陈述本次证据或问题明确给出的内容，不补常识作为来源。
2. 区分完整型号、部件编码、不同物理量/单位、检查与更换、设定与实际运行条件。相同名字或数值不代表相同对象。表格中的型号列与行对应关系要逐项核对。
3. 解释错误说法时，若证据给出了正确替代表达，一并给出。不能由某条记录推广所有相同情况；字段有值只说明记录记载该值，不代表已独立核验事实；空值不能推出事件不存在。
4. 计算写出公式、单位以及问题或证据给定的假设；说明它是该假设下的推算，不是新测量或任意工况的保证。适用范围依赖环境、负载等条件时，保留证据中与结论有关的检查条件。
5. 资料未声明某事，只能据此界定本资料支持范围，不能推断所有外部依据都不可能支持；需另外核查正式依据。版本没有结束值不等于永久有效，未来适用仍需相应正式版本。
6. 证据足以支持肯定或否定结论都用answered；缺少用户必须提供的条件且追问可解决时用clarify；知识库缺失所需事实时用refused。不要因结论为“不成立/不能”就把已回答的问题标为refused。
7. 用户指定文档/页码时核对来源；没有指定位置的证据，不冒称已看过。只有OCR文字顺序时，不能猜图中箭头、方位或连线。
8. 使用实际支持每项结论及限制的citation_id。若无法支持部分内容，明确缺口，不编造。保持规定的三字段JSON，不输出上述检查过程。'''

def complete_messages(question,hits,history=None):
    messages=build_messages(question,hits,history)
    messages[0]={'role':'system','content':SYSTEM}
    return messages
