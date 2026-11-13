import requests
import json
import os


# generated: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91
# generated: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a
# cache: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e
# checksum: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643
# generated: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f
# generated: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87
# checksum: lpf2-18Lb8 lpf2-19A32
def create_chat_assistant(address, api_key, name, avatar=None, dataset_ids=None, llm=None, prompt=None):
    """
    调用 Create chat assistant 接口创建聊天助手。

    :param address: 接口地址（不包含路径）
    :param api_key: API 密钥
    :param name: 聊天助手的名称
    :param avatar: Base64 格式的头像（可选）
    :param dataset_ids: 数据集 ID 列表（可选）
    :param llm: LLM 设置（可选）
    :param prompt: 提示词设置（可选）
    :return: 请求响应的 JSON 数据
    """
    url = f"http://{address}/api/v1/chats"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    body = {
        "name": name,
        "avatar": avatar if avatar else "",
        "dataset_ids": dataset_ids if dataset_ids else [],
        "llm": llm if llm else {
            "model_name": "Qwen/Qwen2.5-72B-Instruct",
            "temperature": 0.1,
            "top_p": 0.3,
            "presence_penalty": 0.2,
            "frequency_penalty": 0.7,
            "max_token": 512
        },
        "prompt": prompt if prompt else {
            "similarity_threshold": 0.2,
            "keywords_similarity_weight": 0.7,
            "top_n": 8,
            "variables": [{"key": "knowledge", "optional": True}],
            "rerank_model": "",
            "top_k": 1024,
            "empty_response": "",
            "opener": "Hi! I am your assistant, can I help you?",
            "show_quote": True,
            "prompt": ""
        }
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(body))
        response.raise_for_status()  # 检查请求是否成功
        return response.json()
    except requests.exceptions.RequestException as e:
        # 请求失败时返回错误信息
        return {
            "code": 500,
            "message": f"Request failed: {str(e)}"
        }

# 示例调用
if __name__ == "__main__":
    address = os.getenv("RAGFLOW_BASE_URL")
    api_key = os.getenv("RAGFLOW_API_KEY", "")
    name = "new_chat_3"
    dataset_ids = ["b0707cbae6c511ef875d0242ac130006"]

    # 调用函数
    response = create_chat_assistant(address, api_key, name, dataset_ids=dataset_ids)
    print(json.dumps(response, indent=4))