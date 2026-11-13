#!/usr/bin/env python3
"""
用 LLM 作为评审，从训练集构造“训练前后差异明显”的对比样本。
输出：
1) JSONL 样本：outputs/eval_before_after_judged.jsonl
2) Markdown 报告：reports/before_after_judged.md
"""

import argparse
import json
import os
import random
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

import torch
from openai import OpenAI
from transformers import AutoModelForCausalLM, AutoTokenizer, StoppingCriteria, StoppingCriteriaList
from peft import PeftModel


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, default="data/train_v3_1200_clean.jsonl")
    parser.add_argument("--base-model", type=str, default="/root/autodl-tmp/qwen3_0.6b")
    parser.add_argument("--lora-path", type=str, default="/root/autodl-tmp/outputs/run_20260118_170957/final")
    parser.add_argument("--output", type=str, default="outputs/eval_before_after_judged.jsonl")
    parser.add_argument("--report", type=str, default="reports/before_after_judged.md")
    parser.add_argument("--max-candidates", type=int, default=200)
    parser.add_argument("--target-count", type=int, default=10)
    parser.add_argument("--mode", type=str, default="tool", choices=["tool", "answer"],
                        help="tool: 评审工具调用是否合理；answer: 评审答案是否正确")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--judge-model", type=str, default=os.getenv("JUDGE_MODEL", "qwen-plus"))
    parser.add_argument("--judge-base-url", type=str, default=os.getenv("JUDGE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"))
    parser.add_argument("--judge-api-key", type=str, default=os.getenv("JUDGE_API_KEY", ""))
    parser.add_argument("--apikey-file", type=str, default="apikey.md")
    return parser.parse_args()


def read_apikey_from_file(path: str) -> Optional[str]:
    p = Path(path)
    if not p.exists():
        return None
    text = p.read_text(encoding="utf-8")
    # 取第一条阿里云 key
    m = re.search(r"sk-[A-Za-z0-9_-]{20,}", text)
    return m.group(0) if m else None


def get_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def resolve_dtype(device: str) -> torch.dtype:
    if device == "cuda":
        return torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    return torch.float32


class StopOnTokenSequences(StoppingCriteria):
    def __init__(self, stop_ids_list: List[List[int]]):
        super().__init__()
        self.stop_ids_list = stop_ids_list

    def __call__(self, input_ids, scores, **kwargs) -> bool:
        for stop_ids in self.stop_ids_list:
            if len(input_ids[0]) < len(stop_ids):
                continue
            if input_ids[0][-len(stop_ids):].tolist() == stop_ids:
                return True
        return False


def extract_finish_answer(item: Dict[str, Any]) -> str:
    for m in reversed(item["messages"]):
        if m.get("role") != "assistant":
            continue
        content = m.get("content", "")
        m1 = re.search(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", content, re.DOTALL)
        if not m1:
            continue
        try:
            obj = json.loads(m1.group(1))
        except Exception:
            continue
        if obj.get("name") == "finish":
            return obj.get("arguments", {}).get("answer", "")
    return ""


def build_context_until_last_tool(item: Dict[str, Any]) -> Optional[List[Dict[str, str]]]:
    msgs = item["messages"]
    last_finish = None
    for i in range(len(msgs) - 1, -1, -1):
        if msgs[i].get("role") == "assistant" and "finish" in msgs[i].get("content", ""):
            last_finish = i
            break
    if last_finish is None:
        return None
    last_tool = None
    for i in range(last_finish - 1, -1, -1):
        if msgs[i].get("role") == "tool":
            last_tool = i
            break
    if last_tool is None:
        return None
    return msgs[: last_tool + 1]


def gen_finish_answer(
    model,
    tokenizer,
    device: str,
    stop_ids_list: List[List[int]],
    messages: List[Dict[str, str]],
) -> str:
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    if not text.endswith("<think>\n"):
        text += "<think>\n"
    inputs = tokenizer(text, return_tensors="pt")
    inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=384,
            temperature=0.2,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
            stopping_criteria=StoppingCriteriaList([StopOnTokenSequences(stop_ids_list)]),
        )
    input_len = inputs["input_ids"].shape[1]
    response = tokenizer.decode(out[0][input_len:], skip_special_tokens=True).strip()
    m = re.search(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", response, re.DOTALL)
    if m:
        try:
            obj = json.loads(m.group(1))
            if obj.get("name") == "finish":
                return obj.get("arguments", {}).get("answer", "")
        except Exception:
            pass
    return ""


def gen_tool_call(
    model,
    tokenizer,
    device: str,
    stop_ids_list: List[List[int]],
    question: str,
) -> str:
    system_prompt = (
        "你是专业的研究助手。输出必须严格为两段：先 <think>...</think>，后 <tool_call>{JSON}</tool_call>。"
        "不得输出其他文本。"
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    if not text.endswith("<think>\n"):
        text += "<think>\n"
    inputs = tokenizer(text, return_tensors="pt")
    inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=256,
            temperature=0.2,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
            stopping_criteria=StoppingCriteriaList([StopOnTokenSequences(stop_ids_list)]),
        )
    input_len = inputs["input_ids"].shape[1]
    response = tokenizer.decode(out[0][input_len:], skip_special_tokens=True).strip()
    return response


def judge_answer(client: OpenAI, model: str, question: str, reference: str, answer: str) -> Dict[str, Any]:
    system_prompt = (
        "你是严格的评审员。给定问题、参考答案和模型回答，判断模型回答是否正确。"
        "请输出 JSON：{score: 0-1, verdict: correct|incorrect, reason: string}。"
        "评分依据：内容是否覆盖参考答案关键点，是否有明显错误或遗漏。"
    )
    user_prompt = (
        f"问题：{question}\n\n参考答案：{reference}\n\n模型回答：{answer}\n\n"
        "仅输出 JSON。"
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        temperature=0.0,
    )
    text = resp.choices[0].message.content.strip()
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return {"score": 0.0, "verdict": "incorrect", "reason": "judge_parse_failed"}


def judge_tool(client: OpenAI, model: str, question: str, expected_tool: str, response: str) -> Dict[str, Any]:
    system_prompt = (
        "你是严格的评审员。给定问题、期望工具、模型输出，判断模型是否选择了合理的工具。"
        "输出 JSON：{score: 0-1, verdict: correct|incorrect, reason: string}。"
        "评分依据：工具选择是否符合问题需求；若模型未给出工具调用也判 incorrect。"
    )
    user_prompt = (
        f"问题：{question}\n\n期望工具：{expected_tool}\n\n模型输出：{response}\n\n仅输出 JSON。"
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        temperature=0.0,
    )
    text = resp.choices[0].message.content.strip()
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return {"score": 0.0, "verdict": "incorrect", "reason": "judge_parse_failed"}


def main() -> None:
    args = parse_args()
    random.seed(args.seed)

    # judge client
    api_key = args.judge_api_key or read_apikey_from_file(args.apikey_file)
    if not api_key:
        raise RuntimeError("未找到 JUDGE_API_KEY 或 apikey.md 中的可用 key。")
    judge_client = OpenAI(api_key=api_key, base_url=args.judge_base_url)

    # load data
    data_path = Path(args.data)
    items = [json.loads(x) for x in data_path.read_text(encoding="utf-8").splitlines() if x.strip()]
    random.shuffle(items)

    # load models
    device = get_device()
    dtype = resolve_dtype(device)
    tokenizer = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    base_model = AutoModelForCausalLM.from_pretrained(args.base_model, dtype=dtype, trust_remote_code=True)
    base_model.to(device).eval()

    lora_base = AutoModelForCausalLM.from_pretrained(args.base_model, dtype=dtype, trust_remote_code=True)
    lora_model = PeftModel.from_pretrained(lora_base, args.lora_path)
    lora_model.to(device).eval()

    stop_ids_list = [tokenizer.encode("</tool_call>", add_special_tokens=False)]

    selected = []
    processed = 0
    for item in items:
        if processed >= args.max_candidates:
            break
        processed += 1

        question = next((m["content"] for m in item["messages"] if m.get("role") == "user"), "")
        if not question:
            continue

        if args.mode == "answer":
            context = build_context_until_last_tool(item)
            if not context:
                continue
            reference = extract_finish_answer(item)
            if not reference:
                continue

            base_ans = gen_finish_answer(base_model, tokenizer, device, stop_ids_list, context)
            lora_ans = gen_finish_answer(lora_model, tokenizer, device, stop_ids_list, context)
            if not base_ans and not lora_ans:
                continue

            base_j = judge_answer(judge_client, args.judge_model, question, reference, base_ans)
            lora_j = judge_answer(judge_client, args.judge_model, question, reference, lora_ans)

            base_ok = base_j.get("verdict") == "correct"
            lora_ok = lora_j.get("verdict") == "correct"
            base_score = float(base_j.get("score", 0.0))
            lora_score = float(lora_j.get("score", 0.0))

            if (not base_ok) and lora_ok:
                selected.append({
                    "id": item.get("metadata", {}).get("id", ""),
                    "question": question,
                    "reference": reference,
                    "baseline_answer": base_ans,
                    "lora_answer": lora_ans,
                    "baseline_judge": base_j,
                    "lora_judge": lora_j,
                    "baseline_score": base_score,
                    "lora_score": lora_score,
                })
                if len(selected) >= args.target_count:
                    break
        else:
            expected_tool = ""
            for m in item["messages"]:
                if m.get("role") != "assistant":
                    continue
                content = m.get("content", "")
                m1 = re.search(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", content, re.DOTALL)
                if m1:
                    try:
                        obj = json.loads(m1.group(1))
                        expected_tool = obj.get("name", "")
                    except Exception:
                        expected_tool = ""
                    break
                m2 = re.search(r"<tool_call>.*?<name>(.*?)</name>.*?</tool_call>", content, re.DOTALL)
                if m2:
                    expected_tool = m2.group(1).strip()
                    break
            if not expected_tool:
                continue

            base_resp = gen_tool_call(base_model, tokenizer, device, stop_ids_list, question)
            lora_resp = gen_tool_call(lora_model, tokenizer, device, stop_ids_list, question)

            base_j = judge_tool(judge_client, args.judge_model, question, expected_tool, base_resp)
            lora_j = judge_tool(judge_client, args.judge_model, question, expected_tool, lora_resp)

            base_ok = base_j.get("verdict") == "correct"
            lora_ok = lora_j.get("verdict") == "correct"
            base_score = float(base_j.get("score", 0.0))
            lora_score = float(lora_j.get("score", 0.0))

            if (not base_ok) and lora_ok:
                selected.append({
                    "id": item.get("metadata", {}).get("id", ""),
                    "question": question,
                    "expected_tool": expected_tool,
                    "baseline_output": base_resp,
                    "lora_output": lora_resp,
                    "baseline_judge": base_j,
                    "lora_judge": lora_j,
                    "baseline_score": base_score,
                    "lora_score": lora_score,
                })
                if len(selected) >= args.target_count:
                    break

    out_jsonl = Path(args.output)
    out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    out_jsonl.write_text("\\n".join(json.dumps(x, ensure_ascii=False) for x in selected) + "\\n", encoding="utf-8")

    # report
    report = Path(args.report)
    report.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    lines.append("# 训练前后对比（LLM 评审）")
    lines.append("")
    lines.append(f"筛选规则：基线判定 incorrect，LoRA 判定 correct。模式：{args.mode}")
    lines.append("")
    lines.append("| id | 问题 | 基线评分 | LoRA评分 | 基线结论 | LoRA结论 |")
    lines.append("|---|---|---|---|---|---|")
    for x in selected:
        q = x["question"].replace("\\n", " ")[:60]
        lines.append(
            f"| {x['id']} | {q} | {x['baseline_score']} | {x['lora_score']} | "
            f"{x['baseline_judge'].get('verdict')} | {x['lora_judge'].get('verdict')} |"
        )
    lines.append("")
    lines.append("## 代表性前后对比（截断）")
    for x in selected[:6]:
        lines.append("")
        lines.append(f"### {x['id']}")
        lines.append(f"**问题**：{x['question']}")
        lines.append("")
        lines.append("**基线输出（截断）**")
        lines.append("```")
        lines.append((x.get("baseline_answer") or x.get("baseline_output", ""))[:300])
        lines.append("```")
        lines.append("")
        lines.append("**LoRA 输出（截断）**")
        lines.append("```")
        lines.append((x.get("lora_answer") or x.get("lora_output", ""))[:300])
        lines.append("```")
        lines.append("")
        lines.append(f"**基线评语**：{x['baseline_judge'].get('reason')}")
        lines.append(f"**LoRA 评语**：{x['lora_judge'].get('reason')}")

    report.write_text("\\n".join(lines), encoding="utf-8")
    print(f"输出: {out_jsonl}")
    print(f"报告: {report}")
    print(f"命中数量: {len(selected)}")


if __name__ == "__main__":
    main()
