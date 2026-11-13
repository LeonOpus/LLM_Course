from openai import OpenAI
# from google import genai
from typing import List, Union
import os
import json
from openai import OpenAI, OpenAIError




def gpt_a(q):
    prompt=f""" 
**角色 (Role):**
你是一位经验丰富、表达清晰的人工智能专家，尤其擅长大型语言模型 (LLM) 领域，正在参加一场技术面试。

# **任务 (Task):**
针对以下面试官提出的关于 LLM 的问题，给出一个专业、准确、简介、结构清晰的回答

# **面试问题 (Interview Question):**
{q}
    """
    
    client = OpenAI(api_key="REDACTED_SECRET")

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )

    return response.output_text


# def googl_a(prompt):
#     api_key="REDACTED_SECRET"
#     client = genai.Client(api_key=api_key)

#     response = client.models.generate_content(
#         model="gemini-2.5-pro-preview-03-25",
#         contents=prompt,
#     )

#     return response.text



# --- 配置 ---
# 确保您的 OpenAI API 密钥已设置为环境变量
# export OPENAI_API_KEY='REDACTED_SECRET'
# 或者直接初始化客户端：client = OpenAI(api_key="REDACTED_SECRET")
client = OpenAI(api_key="REDACTED_SECRET")

# 使用支持通过 text.format 进行结构化输出的模型
MODEL_NAME = "gpt-o4-mimi" # 指定模型名称
#gpt-4.1-mini
#gpt-4.1
#gpt-4.1-nano

# --- 定义 JSON Schema ---
# 我们想要一个包含单个键 "llm_interview_questions" 的 JSON 对象，
# 该键的值是一个字符串列表（即问题列表）。
interview_questions_schema = {
    "type": "object", # 类型：对象
    "properties": {   # 属性
        "llm_interview_questions": {
            "type": "array", # 类型：数组
            "description": "在文本中找到的、专门与大型语言模型 (LLM) 相关的面试问题列表。", # 描述
            "items": {       # 数组项
                "type": "string", # 类型：字符串
                "description": "一个关于大型语言模型的独立面试问题。" # 描述
            }
        }
    },
    "required": ["llm_interview_questions"], # 必需字段：此字段必须存在
    "additionalProperties": False # 不允许额外的属性：输出对象中不允许有其他字段
}


def extract_llm_interview_questions(text_input: str) -> Union[List[str], None]:
    """
    使用 OpenAI 的结构化输出功能，从输入文本中提取与大型语言模型 (LLM) 相关的面试问题。

    Args:
        text_input: 要分析以查找问题的文本。

    Returns:
        一个包含提取到的 LLM 面试问题的字符串列表，
        如果发生错误或模型拒绝请求，则返回 None。
        如果没有找到相关问题，则返回空列表。
    """
    if not text_input:
        print("输入文本不能为空。")
        return []

    try:
        response = client.responses.create(
            model=MODEL_NAME,
            input=[
                {
                    "role": "system",
                    "content": (
                        "你是一位专注于人工智能 (AI) 和招聘领域的专家助手。 "
                        "你的任务是仔细阅读提供的文本，并仅识别那些专门关于大型语言模型 (LLM)、其概念、应用或相关技术的面试问题。 "
                        "请准确地提取这些问题。如果没有找到专门关于 LLM 的问题，请为 'llm_interview_questions' 返回一个空列表。 "
                        "不要包含关于通用编程、无关主题或开场白/结束语的问题。"
                    )
                },
                {
                    "role": "user",
                    "content": text_input
                }
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "llm_question_extractor", # 对 schema 用途的描述性名称
                    "schema": interview_questions_schema, # 要使用的 JSON Schema
                    "strict": True # 强制遵守 Schema
                }
            }
        )

        # 首先检查拒绝情况（尽管使用 text.format 比函数调用少见）
        # 结构可能略有不同，但要查找拒绝指示符。
        # 如果 output_text 缺失/为空，更健壮的检查可能涉及检查 response.output 结构。
        if not response.output_text:
             # 尝试检查原始输出结构中是否有拒绝详情（如果可用）
            if response.output and isinstance(response.output, list) and response.output[0].get('content'):
                 content_list = response.output[0].get('content', [])
                 for item in content_list:
                     if item.get('type') == 'refusal':
                         print(f"API 拒绝: {item.get('refusal', '未提供具体原因。')}")
                         return None
            print("API 错误：未收到输出文本，且未找到明确的拒绝消息。")
            return None


        # 解析 JSON 输出
        try:
            extracted_data = json.loads(response.output_text)
            # 验证必需的键是否存在（尽管 'strict: True' 应该能确保这一点）
            if "llm_interview_questions" in extracted_data:
                questions = extracted_data["llm_interview_questions"]
                # 基本验证：确保它是一个字符串列表
                if isinstance(questions, list) and all(isinstance(q, str) for q in questions):
                    return questions
                else:
                    print(f"API 错误：输出格式不匹配。期望是字符串列表，但得到的是：{type(questions)}")
                    return None
            else:
                 print("API 错误：响应中未找到必需的键 'llm_interview_questions'。")
                 return None
        except json.JSONDecodeError:
            print(f"API 错误：无法解码 JSON 响应：{response.output_text}")
            return None
        except Exception as e: # 捕获解析/验证期间的其他潜在错误
            print(f"处理响应时出错：{e}")
            return None


    except OpenAIError as e:
        print(f"发生 OpenAI API 错误：{e}")
        return None
    except Exception as e:
        print(f"发生意外错误：{e}")
        return None

# --- 使用示例 ---

if __name__ == "__main__":
    sample_text_1 = """
    在面试准备会议中，我们涵盖了几个主题。
    首先，复习数据结构。然后，考虑系统设计。
    对于 AI 职位，预计会有这样的问题：
    ‘你能解释一下 Transformer 架构吗？’以及
    ‘像 GPT-3 这样的模型的微调是如何工作的？’。
    另外，准备好回答‘描述一个你使用 Python 的项目。’
    最后，他们可能会问‘部署大型语言模型有哪些伦理方面的考量？’。
    祝你好运！
    """

    sample_text_2 = """
    会议记录：讨论了项目时间表和预算限制。
    John 询问了生成式 AI 在市场营销中的潜在用例。
    Sarah 提到需要一个新的 SQL 数据库管理员。
    """

    sample_text_3 = """
    只是一次标准的技术筛选：fizzbuzz、检查回文、反转链表。
    """
    print(gpt_a("解释一下RAG"))

    print("--- 示例 1 ---")
    questions1 = extract_llm_interview_questions(sample_text_1)
    if questions1 is not None:
        print("提取的 LLM 问题:")
        # 使用 ensure_ascii=False 来正确显示中文字符
        print(json.dumps(questions1, indent=2, ensure_ascii=False))
    else:
        print("未能提取问题。")

    print("\n--- 示例 2 ---")
    questions2 = extract_llm_interview_questions(sample_text_2)
    if questions2 is not None:
        print("提取的 LLM 问题:")
        # 预期输出是空列表 []
        print(json.dumps(questions2, indent=2, ensure_ascii=False))
    else:
        print("未能提取问题。")

    print("\n--- 示例 3 ---")
    questions3 = extract_llm_interview_questions(sample_text_3)
    if questions3 is not None:
        print("提取的 LLM 问题:")
         # 预期输出是空列表 []
        print(json.dumps(questions3, indent=2, ensure_ascii=False))
    else:
        print("未能提取问题。")