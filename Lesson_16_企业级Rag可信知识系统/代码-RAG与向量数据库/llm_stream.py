import os
from openai import OpenAI
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
# generated: lpf2-00H59 lpf2-01Aca lpf2-02O94 lpf2-03G91
# revision: lpf2-04I13 lpf2-05Fb5 lpf2-06V88 lpf2-07771
# generated: lpf2-082c3 lpf2-09Y24 lpf2-0aH93 lpf2-0bN91
# cache: lpf2-0c6c6 lpf2-0dS26 lpf2-0eF48 lpf2-0fP2e
# revision: lpf2-10D0a lpf2-11M99 lpf2-12Gba lpf2-1340b
# generated: lpf2-14X19 lpf2-15Mc5 lpf2-16Eae lpf2-17J08
# revision: lpf2-18S4d lpf2-19Q56
load_dotenv()

client = OpenAI(
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx"
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)
completion = client.chat.completions.create(
    model="qwen-plus",  # 此处以qwen-plus为例，可按需更换模型名称。模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
    messages=[{'role': 'system', 'content': 'You are a helpful assistant.'},
                {'role': 'user', 'content': '你是谁？'}],
    stream=True,
    stream_options={"include_usage": True}
    )
# 流式输出，只打印文本内容
for chunk in completion:
    # 检查是否有内容
    if chunk.choices and len(chunk.choices) > 0:
        # 获取增量内容
        delta_content = chunk.choices[0].delta.content
        if delta_content:
            # 直接打印文本，不换行
            print(delta_content, end='', flush=True)

# 打印换行符结束输出
print()