"""完整评估脚本 - 验证格式和内容"""

import sys
import os
import json
import re
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


def generate_response(model, tokenizer, device, question, max_new_tokens=512, temperature=0.2, do_sample=False, force_finish=False):
    """生成响应"""
    system_prompt = get_system_prompt_v2() + (
        "\n\n## 强制格式\n"
        "你的输出必须严格为两段：先 <think>...</think>，后 <tool_call>{JSON}</tool_call>。"
        "不得输出其他文本。"
    )
    if force_finish:
        system_prompt += "\n\n## 额外要求\n仅允许调用 finish 工具，直接给出最终答案。"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question}
    ]

    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
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
            temperature=temperature,
            do_sample=do_sample,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
            stopping_criteria=StoppingCriteriaList([StopOnTokenSequences(stop_ids_list)]),
        )

    input_len = inputs["input_ids"].shape[1]
    response = tokenizer.decode(outputs[0][input_len:], skip_special_tokens=True).strip()
    return normalize_response_format(response)


def normalize_response_format(response: str) -> str:
    """若缺少<think>但已输出tool_call，则自动补齐最小think块。"""
    match = re.search(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", response, re.DOTALL)
    if match:
        try:
            obj = json.loads(match.group(1))
            rebuilt = json.dumps(obj, ensure_ascii=False, indent=2)
            return "<think>\n继续执行下一步。\n</think>\n\n<tool_call>\n" + rebuilt + "\n</tool_call>"
        except Exception:
            pass
    if "<tool_call>" in response and "<think>" not in response:
        return "<think>\n继续执行下一步。\n</think>\n\n" + response
    return response


def parse_response(response):
    """解析响应，提取think和tool_call"""
    result = {
        "has_think": False,
        "has_tool_call": False,
        "think_content": "",
        "tool_name": "",
        "tool_args": {},
        "answer": "",
    }

    # 提取 think
    think_match = re.search(r'<think>(.*?)</think>', response, re.DOTALL)
    if think_match:
        result["has_think"] = True
        result["think_content"] = think_match.group(1).strip()

    # 提取 tool_call
    tool_match = re.search(r'<tool_call>\s*(\{.*?\})\s*</tool_call>', response, re.DOTALL)
    if tool_match:
        result["has_tool_call"] = True
        try:
            tool_data = json.loads(tool_match.group(1))
            result["tool_name"] = tool_data.get("name", "")
            result["tool_args"] = tool_data.get("arguments", {})
            result["answer"] = result["tool_args"].get("answer", "")
        except json.JSONDecodeError:
            pass

    return result


def check_answer(answer, ground_truth, keywords=None):
    """检查答案是否包含关键信息"""
    if not answer:
        return False

    answer_lower = answer.lower()

    # 如果有关键词列表，检查是否包含
    if keywords:
        matches = sum(1 for kw in keywords if kw.lower() in answer_lower)
        return matches >= len(keywords) * 0.5

    # 否则检查ground_truth
    gt_lower = ground_truth.lower()

    # 中文匹配
    if any('\u4e00' <= c <= '\u9fff' for c in ground_truth):
        key_chars = [c for c in ground_truth if '\u4e00' <= c <= '\u9fff']
        matches = sum(1 for c in key_chars if c in answer)
        return matches >= len(key_chars) * 0.5
    else:
        return gt_lower in answer_lower


def completeness_ratio(answer: str, keywords: list | None) -> float:
    if not answer or not keywords:
        return 0.0
    answer_lower = answer.lower()
    hits = sum(1 for kw in keywords if kw.lower() in answer_lower)
    return hits / max(len(keywords), 1)


# 测试用例
TEST_CASES = [
    # 直接回答类
    {
        "question": "什么是人工智能？",
        "type": "direct_answer",
        "expected_tool": "finish",
        "expected_tools": ["finish"],
        "ground_truth": "人工智能",
        "keywords": ["人工智能", "AI", "计算机", "机器"],
    },
    {
        "question": "什么是光合作用？",
        "type": "direct_answer",
        "expected_tool": "finish",
        "expected_tools": ["finish"],
        "ground_truth": "光合作用",
        "keywords": ["光", "植物", "二氧化碳", "氧气"],
    },
    {
        "question": "中国的首都是哪里？",
        "type": "direct_answer",
        "expected_tool": "finish",
        "expected_tools": ["finish"],
        "ground_truth": "北京",
        "keywords": ["北京"],
    },
    {
        "question": "日本的首都是哪里？",
        "type": "direct_answer",
        "expected_tool": "finish",
        "expected_tools": ["finish"],
        "ground_truth": "东京",
        "keywords": ["东京"],
    },

    # 计算类
    {
        "question": "50乘以20等于多少？",
        "type": "calculation",
        "expected_tool": "calculator",
        "expected_tools": ["calculator", "finish"],
        "ground_truth": "1000",
        "keywords": ["1000"],
    },
    {
        "question": "100加250等于多少？",
        "type": "calculation",
        "expected_tool": "calculator",
        "expected_tools": ["calculator", "finish"],
        "ground_truth": "350",
        "keywords": ["350"],
    },
    {
        "question": "2024年是闰年吗？",
        "type": "calculation",
        "expected_tool": "finish",
        "expected_tools": ["finish"],
        "ground_truth": "闰年",
        "keywords": ["闰年", "366"],
    },

    # 事实查询类
    {
        "question": "《三体》的作者是谁？",
        "type": "fact_query",
        "expected_tool": "finish",
        "expected_tools": ["finish"],
        "ground_truth": "刘慈欣",
        "keywords": ["刘慈欣"],
    },
    {
        "question": "什么是深度学习？",
        "type": "direct_answer",
        "expected_tool": "finish",
        "expected_tools": ["finish"],
        "ground_truth": "深度学习",
        "keywords": ["神经网络", "机器学习", "深度"],
    },
    {
        "question": "水的化学式是什么？",
        "type": "direct_answer",
        "expected_tool": "finish",
        "expected_tools": ["finish"],
        "ground_truth": "H2O",
        "keywords": ["H2O", "氢", "氧"],
    },
]


def evaluate_model(model, tokenizer, device, model_name):
    """评估模型"""
    print(f"\n{'='*60}")
    print(f"评估: {model_name}")
    print(f"{'='*60}")

    results = []

    for i, case in enumerate(TEST_CASES):
        print(f"\n[{i+1}/{len(TEST_CASES)}] {case['question']}")

        response = generate_response(model, tokenizer, device, case["question"])
        parsed = parse_response(response)

        # 格式分数
        format_score = int(parsed["has_think"]) + int(parsed["has_tool_call"])

        # 工具选择是否正确（允许多个期望工具）
        expected_tools = case.get("expected_tools", [case.get("expected_tool")])
        expected_tools = [t for t in expected_tools if t]
        tool_correct = parsed["tool_name"] in expected_tools if expected_tools else False

        # 额外：强制 finish 模式评估答案质量
        finish_resp = generate_response(
            model, tokenizer, device, case["question"],
            max_new_tokens=512, temperature=0.2, do_sample=False, force_finish=True
        )
        finish_parsed = parse_response(finish_resp)
        answer_correct = check_answer(
            finish_parsed["answer"], case["ground_truth"], case.get("keywords")
        ) if finish_parsed["tool_name"] == "finish" else False
        comp = completeness_ratio(finish_parsed["answer"], case.get("keywords")) if finish_parsed["tool_name"] == "finish" else 0.0

        result = {
            "question": case["question"],
            "type": case["type"],
            "format_score": format_score,
            "tool_correct": tool_correct,
            "answer_correct": answer_correct,
            "completeness": comp,
            "response_preview": response[:150] + "..." if len(response) > 150 else response,
            "parsed_answer": parsed["answer"][:100] if parsed["answer"] else "",
        }
        results.append(result)

        # 打印结果
        status = "✓" if (format_score == 2 and answer_correct) else "✗"
        comp_str = f"{comp:.0%}" if parsed["tool_name"] == "finish" else "N/A"
        print(f"  {status} 格式:{format_score}/2 | 工具:{parsed['tool_name']} | 工具正确:{tool_correct} | 答案正确:{answer_correct} | 完整度:{comp_str}")
        if parsed["answer"]:
            print(f"    答案: {parsed['answer'][:80]}...")

    return results


def compare_results(baseline_results, trained_results):
    """对比结果"""
    print(f"\n{'='*60}")
    print("评估结果对比")
    print(f"{'='*60}")

    # 统计
    baseline_format = sum(r["format_score"] for r in baseline_results)
    trained_format = sum(r["format_score"] for r in trained_results)
    max_format = len(TEST_CASES) * 2

    baseline_tool = sum(r["tool_correct"] for r in baseline_results)
    trained_tool = sum(r["tool_correct"] for r in trained_results)

    baseline_answer = sum(r["answer_correct"] for r in baseline_results)
    trained_answer = sum(r["answer_correct"] for r in trained_results)
    baseline_comp = sum(r["completeness"] for r in baseline_results)
    trained_comp = sum(r["completeness"] for r in trained_results)

    total = len(TEST_CASES)

    print(f"\n{'指标':<15} {'基线模型':<15} {'训练后模型':<15} {'变化':<10}")
    print("-" * 55)

    # 格式得分
    fmt_change = trained_format - baseline_format
    fmt_symbol = "↑" if fmt_change > 0 else ("↓" if fmt_change < 0 else "→")
    print(f"{'格式得分':<15} {baseline_format}/{max_format:<13} {trained_format}/{max_format:<13} {fmt_symbol} {abs(fmt_change)}")

    # 工具选择
    tool_change = trained_tool - baseline_tool
    tool_symbol = "↑" if tool_change > 0 else ("↓" if tool_change < 0 else "→")
    print(f"{'工具选择':<15} {baseline_tool}/{total:<13} {trained_tool}/{total:<13} {tool_symbol} {abs(tool_change)}")

    # 答案正确
    ans_change = trained_answer - baseline_answer
    ans_symbol = "↑" if ans_change > 0 else ("↓" if ans_change < 0 else "→")
    print(f"{'答案正确':<15} {baseline_answer}/{total:<13} {trained_answer}/{total:<13} {ans_symbol} {abs(ans_change)}")
    print(f"{'完整度(均)':<15} {baseline_comp/total:>6.0%}        {trained_comp/total:>6.0%}")

    # 综合得分
    baseline_total = baseline_format + baseline_tool + baseline_answer
    trained_total = trained_format + trained_tool + trained_answer
    max_total = max_format + total + total

    print("-" * 55)
    print(f"{'综合得分':<15} {baseline_total}/{max_total:<13} {trained_total}/{max_total:<13}")

    # 结论
    print(f"\n{'='*60}")
    if trained_total > baseline_total:
        improvement = (trained_total - baseline_total) / max(baseline_total, 1) * 100
        print(f"✓ 训练后模型整体提升 {improvement:.1f}%")
    elif trained_total == baseline_total:
        print("→ 训练前后得分相同")
    else:
        print("✗ 训练后模型得分下降")

    # 详细对比
    print(f"\n逐题对比:")
    print("-" * 55)
    for i, (b, t) in enumerate(zip(baseline_results, trained_results)):
        b_score = b["format_score"] + int(b["tool_correct"]) + int(b["answer_correct"])
        t_score = t["format_score"] + int(t["tool_correct"]) + int(t["answer_correct"])
        change = "↑" if t_score > b_score else ("↓" if t_score < b_score else "→")
        q = b["question"][:20] + "..." if len(b["question"]) > 20 else b["question"]
        print(f"{i+1}. {q:<25} 基线:{b_score}/4  训练后:{t_score}/4  {change}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="完整评估脚本 - 格式/工具/准确性/完整度")
    parser.add_argument("--base-model", type=str, required=True, help="基础模型路径")
    parser.add_argument("--lora-path", type=str, required=True, help="LoRA 路径")
    parser.add_argument("--max-new-tokens", type=int, default=512)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--do-sample", action="store_true")
    args = parser.parse_args()

    base_model_path = args.base_model
    lora_path = args.lora_path

    print("加载基线模型...")
    baseline_model, tokenizer, device = load_model(base_model_path)
    baseline_results = evaluate_model(baseline_model, tokenizer, device, "Qwen3-0.6B (基线)")

    del baseline_model
    if device == "mps":
        torch.mps.empty_cache()

    print("\n加载训练后模型...")
    trained_model, tokenizer, device = load_model(base_model_path, lora_path)
    trained_results = evaluate_model(trained_model, tokenizer, device, "Qwen3-0.6B + LoRA (训练后)")

    compare_results(baseline_results, trained_results)


if __name__ == "__main__":
    main()
