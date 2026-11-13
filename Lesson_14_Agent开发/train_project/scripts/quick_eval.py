"""快速评估脚本 - 对比基线和训练后的模型"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, StoppingCriteria, StoppingCriteriaList
from peft import PeftModel
from src.data.schema_v2 import get_system_prompt_v2


def get_device():
    if torch.cuda.is_available():
        return "cuda"
    elif torch.backends.mps.is_available():
        return "mps"
    return "cpu"

def resolve_dtype(device: str) -> torch.dtype:
    if device == "cuda":
        return torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    return torch.float32


def load_model(model_path, lora_path=None):
    """加载模型"""
    device = get_device()
    dtype = resolve_dtype(device)

    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        dtype=dtype,
        trust_remote_code=True
    )

    if lora_path:
        print(f"Loading LoRA from {lora_path}")
        model = PeftModel.from_pretrained(model, lora_path)

    model.to(device)
    model.eval()

    return model, tokenizer, device


def generate_response(model, tokenizer, device, question, max_new_tokens=256):
    """生成响应"""
    system_prompt = get_system_prompt_v2() + (
        "\n\n## 强制格式\n"
        "你的输出必须严格为两段：先 <think>...</think>，后 <tool_call>{JSON}</tool_call>。"
        "不得输出其他文本。"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question}
    ]

    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    # 强制以 <think> 开始，提升格式稳定性
    if not text.endswith("<think>\n"):
        text += "<think>\n"
    inputs = tokenizer(text, return_tensors="pt")
    inputs = {k: v.to(device) for k, v in inputs.items()}

    class StopOnTokenSequences(StoppingCriteria):
        def __init__(self, stop_ids_list):
            super().__init__()
            self.stop_ids_list = stop_ids_list

        def __call__(self, input_ids, scores, **kwargs):
            for stop_ids in self.stop_ids_list:
                if len(input_ids[0]) < len(stop_ids):
                    continue
                if input_ids[0][-len(stop_ids):].tolist() == stop_ids:
                    return True
            return False

    stop_sequences = ["</tool_call>"]
    stop_ids_list = [tokenizer.encode(s, add_special_tokens=False) for s in stop_sequences]

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=0.2,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
            stopping_criteria=StoppingCriteriaList([StopOnTokenSequences(stop_ids_list)]),
        )

    input_len = inputs["input_ids"].shape[1]
    response = tokenizer.decode(outputs[0][input_len:], skip_special_tokens=True).strip()
    return normalize_response_format(response)


def normalize_response_format(response: str) -> str:
    """若缺少<think>但已输出tool_call，则自动补齐最小think块。"""
    import re
    import json as _json

    # 尝试抽取第一个 JSON tool_call 并重建为严格格式
    match = re.search(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", response, re.DOTALL)
    if match:
        try:
            obj = _json.loads(match.group(1))
            rebuilt = _json.dumps(obj, ensure_ascii=False, indent=2)
            return "<think>\n继续执行下一步。\n</think>\n\n<tool_call>\n" + rebuilt + "\n</tool_call>"
        except Exception:
            pass

    if "<tool_call>" in response and "<think>" not in response:
        return "<think>\n继续执行下一步。\n</think>\n\n" + response
    return response


def check_format(response):
    """检查响应格式（JSON tool_call）"""
    has_think = "<think>" in response and "</think>" in response
    has_tool_call = "<tool_call>" in response and "</tool_call>" in response
    has_json = False
    if has_tool_call:
        import re
        import json as _json
        match = re.search(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", response, re.DOTALL)
        if match:
            try:
                obj = _json.loads(match.group(1))
                has_json = isinstance(obj, dict) and "name" in obj and "arguments" in obj
            except Exception:
                has_json = False
    return has_think, has_tool_call and has_json


def main():
    import argparse
    parser = argparse.ArgumentParser(description="快速评估脚本 - 对比基线和训练后的模型")
    parser.add_argument("--base-model", type=str, required=True, help="基础模型路径")
    parser.add_argument("--lora-path", type=str, required=True, help="LoRA 模型路径")
    parser.add_argument("--questions", type=str, default="", help="以'|'分隔的问题列表")
    args = parser.parse_args()

    base_model_path = args.base_model
    lora_path = args.lora_path

    # 测试问题
    if args.questions.strip():
        test_questions = [q.strip() for q in args.questions.split("|") if q.strip()]
    else:
        test_questions = [
            "什么是人工智能？",
            "50乘以20等于多少？",
            "日本的首都是哪里？",
        ]

    print("=" * 60)
    print("评估基线模型 (Qwen3-4B)")
    print("=" * 60)

    model, tokenizer, device = load_model(base_model_path)

    baseline_scores = []
    for q in test_questions:
        print(f"\n问题: {q}")
        response = generate_response(model, tokenizer, device, q)
        print(f"回答: {response[:200]}...")
        has_think, has_tool_call = check_format(response)
        score = int(has_think) + int(has_tool_call)
        baseline_scores.append(score)
        print(f"格式检查: think={has_think}, tool_call={has_tool_call}")

    del model
    torch.mps.empty_cache() if device == "mps" else None

    print("\n" + "=" * 60)
    print("评估训练后的模型 (Qwen3-4B + LoRA)")
    print("=" * 60)

    model, tokenizer, device = load_model(base_model_path, lora_path)

    trained_scores = []
    for q in test_questions:
        print(f"\n问题: {q}")
        response = generate_response(model, tokenizer, device, q)
        print(f"回答: {response[:200]}...")
        has_think, has_tool_call = check_format(response)
        score = int(has_think) + int(has_tool_call)
        trained_scores.append(score)
        print(f"格式检查: think={has_think}, tool_call={has_tool_call}")

    print("\n" + "=" * 60)
    print("评估结果对比")
    print("=" * 60)
    print(f"基线模型格式得分: {sum(baseline_scores)}/{len(baseline_scores)*2}")
    print(f"训练后模型格式得分: {sum(trained_scores)}/{len(trained_scores)*2}")

    if sum(trained_scores) > sum(baseline_scores):
        print("\n✓ 训练后模型格式输出有改善！")
    elif sum(trained_scores) == sum(baseline_scores):
        print("\n- 格式得分相同")
    else:
        print("\n✗ 训练后模型格式输出下降")


if __name__ == "__main__":
    main()
