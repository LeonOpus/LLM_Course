"""
LLM 扩写种子问题（Claude / GPT / Gemini 等）
========================================

功能：
1. 读取 seed_questions_v2.py 中的种子问题
2. 使用 LLM 生成 5 个变体（表述改写、参数变化等）
3. 以 JSONL 形式输出扩写结果，便于后续轨迹合成
"""

import argparse
import json
import os
import re
import time
from typing import Any, Dict, List, Optional

from src.data.seed_questions_v2 import SEED_QUESTIONS
from llm import LLMManager


EXPANSION_PROMPT = """你是一个银行对公业务咨询专家。现在需要你基于给定的种子问题，生成多个变体问题。

## 种子问题
{seed_query}

## 行业: {industry}
## 问题类型: {question_type}

## 要求
请生成 5 个变体问题，每个变体需要：
1. 保持相同的核心意图
2. 使用不同的表达方式
3. 可以改变具体参数（时间、金额、地点等）
4. 语言自然，符合真实用户习惯

## 变体类型
1. 表述改写：用不同的词汇和句式表达相同意思
2. 参数变化：改变时间、金额、比例等具体数值
3. 场景迁移：将问题迁移到相似但不同的场景
4. 深度延伸：在原问题基础上追问更深入的细节
5. 组合扩展：将原问题与相关问题组合

## 输出格式
请以 JSON 数组格式输出：
```json
[
  {{
    "variant_type": "表述改写",
    "query": "变体问题内容",
    "changes": "说明与原问题的差异"
  }},
  ...
]
```
"""


def _extract_json_array(text: str) -> Optional[List[Dict[str, Any]]]:
    """从模型输出中提取 JSON 数组。"""
    if not text:
        return None

    # 优先提取 ```json ... ``` 代码块
    fence_match = re.search(r"```json\s*(\[.*?\])\s*```", text, re.DOTALL)
    if fence_match:
        candidate = fence_match.group(1)
    else:
        # 退化为抓第一个 JSON 数组
        array_match = re.search(r"(\[.*\])", text, re.DOTALL)
        if not array_match:
            return None
        candidate = array_match.group(1)

    try:
        data = json.loads(candidate)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        return None

    return None


def _normalize_variants(items: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """过滤并规范化模型输出。"""
    normalized: List[Dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        variant_type = str(item.get("variant_type", "")).strip()
        query = str(item.get("query", "")).strip()
        changes = str(item.get("changes", "")).strip()
        if not query:
            continue
        normalized.append({
            "variant_type": variant_type,
            "query": query,
            "changes": changes
        })
    return normalized


def expand_one(llm: LLMManager, model: str, seed: Dict[str, Any]) -> Optional[List[Dict[str, str]]]:
    prompt = EXPANSION_PROMPT.format(
        seed_query=seed["question"],
        industry=seed["industry"],
        question_type=seed["question_type"]
    )
    response = llm.call_model(model_name=model, prompt=prompt, system_prompt=None, stream=False)
    variants = _extract_json_array(response)
    if not variants:
        return None
    return _normalize_variants(variants)


def main():
    parser = argparse.ArgumentParser(description="LLM 扩写种子问题")
    parser.add_argument("--model", type=str, default="claude-opus-4-5", help="模型名称（见 llm.py）")
    parser.add_argument("--output", type=str, default="data/expanded_seeds.jsonl", help="输出文件")
    parser.add_argument("--start-idx", type=int, default=0, help="起始索引")
    parser.add_argument("--limit", type=int, default=0, help="限制处理数量（0 表示全部）")
    parser.add_argument("--sleep", type=float, default=0.5, help="每条之间的休眠时间")
    args = parser.parse_args()

    llm = LLMManager()

    seeds = SEED_QUESTIONS[args.start_idx:]
    if args.limit > 0:
        seeds = seeds[:args.limit]

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)

    total = len(seeds)
    success = 0

    with open(args.output, "w", encoding="utf-8") as f:
        for idx, seed in enumerate(seeds, start=1):
            print(f"[{idx}/{total}] {seed['id']} 扩写中...")
            variants = expand_one(llm, args.model, seed)
            if not variants:
                print(f"  - 扩写失败或解析失败：{seed['id']}")
                continue

            record = {
                "seed_id": seed["id"],
                "seed_query": seed["question"],
                "industry": seed["industry"],
                "question_type": seed["question_type"],
                "variants": variants
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            success += 1
            time.sleep(args.sleep)

    print(f"完成：{success}/{total} 条写入 {args.output}")


if __name__ == "__main__":
    main()
