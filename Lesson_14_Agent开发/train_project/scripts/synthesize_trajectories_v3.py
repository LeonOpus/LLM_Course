"""
轨迹合成脚本 V3 - 多线程版本
===============================

特点：
1. 多线程并行生成（默认 8 线程）
2. 限制工具调用次数（最多 4 次，含 finish）
3. 更严格的格式控制
"""

import os
import sys
import json
import time
import argparse
import re
import threading
from typing import Dict, List, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 读取 .env（固定为项目根目录）
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from openai import OpenAI
from src.data.schema_v2 import (
    get_system_prompt_v2,
    validate_trajectory,
    INDUSTRIES,
    QUESTION_TYPES
)
from src.data.seed_questions_v2 import SEED_QUESTIONS
from src.tools.tool_executor import ToolExecutor

# 线程安全的计数器
class Counter:
    def __init__(self):
        self.value = 0
        self.lock = threading.Lock()

    def increment(self):
        with self.lock:
            self.value += 1
            return self.value


class TrajectoryGenerator:
    """轨迹生成器 - 多线程版本"""

    MODEL_CONFIGS = {
        "deepseek-v3": {
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "model_name": "deepseek-v3.2"
        },
        "qwen-plus": {
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "model_name": "qwen-plus"
        }
    }

    def __init__(
        self,
        search_api_keys: List[str],
        jina_api_keys: List[str],
        llm_api_keys: List[str],
        model: str = "deepseek-v3",
        max_turns: int = 5
    ):
        config = self.MODEL_CONFIGS.get(model, self.MODEL_CONFIGS["deepseek-v3"])

        self._llm_api_keys = llm_api_keys
        self._search_api_keys = search_api_keys
        self._jina_api_keys = jina_api_keys
        self._base_url = config["base_url"]
        self.model = config["model_name"]
        self.max_turns = max_turns
        self.system_prompt = get_system_prompt_v2()

    def _get_tool_executor(self, key_index: int):
        """每个线程创建独立的 ToolExecutor"""
        return ToolExecutor(
            search_api_key=self._search_api_keys[key_index],
            jina_api_key=self._jina_api_keys[key_index]
        )

    def generate_trajectory(self, seed_question: Dict, key_index: int, progress_counter: Counter = None) -> Optional[Dict]:
        """为单个种子问题生成完整轨迹"""
        question = seed_question["question"]
        industry = seed_question["industry"]
        question_type = seed_question["question_type"]
        question_id = seed_question["id"]

        # 每个线程独立的工具执行器与 LLM client
        tool_executor = self._get_tool_executor(key_index)
        llm_client = OpenAI(
            api_key=self._llm_api_keys[key_index],
            base_url=self._base_url
        )

        if progress_counter:
            count = progress_counter.increment()
            print(f"[{count}] {question_id}: 生成中...")
        else:
            print(f"[{question_id}] 生成中...")

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": question}
        ]

        final_messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": question}
        ]

        tools_used = []
        tool_call_count = 0  # 工具调用计数（不含 finish）

        for turn in range(self.max_turns):
            try:
                response = llm_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=2000,
                    timeout=60
                )
                assistant_content = response.choices[0].message.content
            except Exception as e:
                print(f"  [{question_id}] 错误: {e}")
                # 重试一次
                time.sleep(2)
                try:
                    response = llm_client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        temperature=0.7,
                        max_tokens=2000,
                        timeout=60
                    )
                    assistant_content = response.choices[0].message.content
                except Exception as e2:
                    print(f"  [{question_id}] 重试失败: {e2}")
                    return None

            final_messages.append({"role": "assistant", "content": assistant_content})
            messages.append({"role": "assistant", "content": assistant_content})

            tool_call = self._extract_tool_call(assistant_content)

            if not tool_call:
                # 未调用工具时直接要求 finish，保证轨迹闭合
                messages.append({
                    "role": "user",
                    "content": "未检测到工具调用，请直接使用 finish 输出最终答案：\n<tool_call>\n{\"name\": \"finish\", \"arguments\": {\"answer\": \"你的回答，包含[1][2]引用\", \"references\": [\"[1] 来源\", \"[2] 来源\"]}}\n</tool_call>"
                })
                continue

            tool_name = tool_call.get("name")
            tools_used.append(tool_name)

            if tool_name == "finish":
                break

            tool_call_count += 1

            # 如果已经调用了 3 次非 finish 工具，强制结束
            if tool_call_count >= 3:
                # 执行当前工具后强制要求 finish
                tool_result = tool_executor.execute(tool_call)
                final_messages.append({"role": "tool_response", "content": tool_result})
                messages.append({"role": "user", "content": f"[工具返回]\n{tool_result}\n\n你已达到工具调用上限，请立即用 finish 输出答案。"})
                continue

            # 执行工具
            tool_result = tool_executor.execute(tool_call)
            final_messages.append({"role": "tool_response", "content": tool_result})
            messages.append({"role": "user", "content": f"[工具返回]\n{tool_result}"})

            time.sleep(0.3)  # 避免 API 限流

        # 构建轨迹
        num_steps = len([m for m in final_messages if m.get("role") == "assistant"])

        trajectory = {
            "messages": final_messages,
            "metadata": {
                "id": question_id,
                "industry": industry,
                "industry_zh": INDUSTRIES.get(industry, ""),
                "question_type": question_type,
                "question_type_zh": QUESTION_TYPES.get(question_type, ""),
                "num_steps": num_steps,
                "tools_used": list(set(tools_used)),
                "has_citation": self._check_citation(final_messages),
                "total_tokens": 0,
                "created_at": datetime.now().strftime("%Y-%m-%d")
            }
        }

        is_valid, errors = validate_trajectory(trajectory)
        status = "✓" if is_valid else f"✗ {errors[0][:30]}..."
        print(f"  [{question_id}] {num_steps}步 {tools_used} {status}")

        if not is_valid:
            trajectory["metadata"]["validation_errors"] = errors

        return trajectory

    def _extract_tool_call(self, content: str) -> Optional[Dict]:
        """提取工具调用 - 支持 JSON 和 XML 格式"""
        # 1. 标准 JSON 格式
        pattern = r'<tool_call>\s*(\{.*?\})\s*</tool_call>'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # 2. XML 格式 (DeepSeek 风格)
        # <tool_call><name>search</name><arguments><query>xxx</query></arguments></tool_call>
        xml_pattern = r'<tool_call>\s*<name>(\w+)</name>\s*<arguments>(.*?)</arguments>\s*</tool_call>'
        xml_match = re.search(xml_pattern, content, re.DOTALL)
        if xml_match:
            tool_name = xml_match.group(1)
            args_content = xml_match.group(2).strip()

            # 解析 XML 格式的参数
            args = {}
            if tool_name == "search":
                query_match = re.search(r'<query>(.*?)</query>', args_content, re.DOTALL)
                if query_match:
                    args["query"] = query_match.group(1).strip()
            elif tool_name == "visit":
                url_match = re.search(r'<url>(.*?)</url>', args_content, re.DOTALL)
                goal_match = re.search(r'<goal>(.*?)</goal>', args_content, re.DOTALL)
                if url_match:
                    args["url"] = url_match.group(1).strip()
                if goal_match:
                    args["goal"] = goal_match.group(1).strip()
                else:
                    args["goal"] = "提取关键信息"
            elif tool_name == "calculator":
                expr_match = re.search(r'<expression>(.*?)</expression>', args_content, re.DOTALL)
                if expr_match:
                    args["expression"] = expr_match.group(1).strip()
            elif tool_name == "finish":
                answer_match = re.search(r'<answer>(.*?)</answer>', args_content, re.DOTALL)
                refs_match = re.search(r'<references>(.*?)</references>', args_content, re.DOTALL)
                if answer_match:
                    args["answer"] = answer_match.group(1).strip()
                if refs_match:
                    # 解析引用列表
                    refs_content = refs_match.group(1)
                    refs = re.findall(r'<ref>(.*?)</ref>', refs_content)
                    if refs:
                        args["references"] = refs
                    else:
                        args["references"] = [refs_content.strip()] if refs_content.strip() else []

            if args:
                return {"name": tool_name, "arguments": args}

        # 3. 直接 JSON 格式
        pattern3 = r'\{"name"\s*:\s*"(\w+)"\s*,\s*"arguments"\s*:\s*(\{[^}]+\})\}'
        match3 = re.search(pattern3, content)
        if match3:
            try:
                return {"name": match3.group(1), "arguments": json.loads(match3.group(2))}
            except json.JSONDecodeError:
                pass

        return None

    def _check_citation(self, messages: List[Dict]) -> bool:
        """检查是否有引用"""
        for msg in messages:
            if msg.get("role") == "assistant":
                if re.search(r'\[\d+\]', msg.get("content", "")):
                    return True
        return False


def generate_single(args):
    """单个任务生成函数（供线程池使用）"""
    generator, seed_q, counter, key_index = args
    try:
        return generator.generate_trajectory(seed_q, key_index, counter)
    except Exception as e:
        print(f"  [{seed_q['id']}] 异常: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="轨迹合成脚本 V3 - 多线程版本")
    parser.add_argument("--num_samples", type=int, default=50, help="生成样本数量")
    parser.add_argument("--output", type=str, default="data/train_v3.jsonl", help="输出文件路径")
    parser.add_argument("--start_idx", type=int, default=0, help="起始索引")
    parser.add_argument("--threads-per-key", type=int, default=6, help="每个 key 的线程数")
    parser.add_argument("--model", type=str, default="deepseek-v3", help="Teacher 模型")
    parser.add_argument("--llm-keys", type=str, default="", help="逗号分隔的 LLM API keys")
    parser.add_argument("--search-keys", type=str, default="", help="逗号分隔的 search keys")
    parser.add_argument("--jina-keys", type=str, default="", help="逗号分隔的 jina keys")
    args = parser.parse_args()

    def _split_keys(raw: str, env_key: str) -> List[str]:
        if raw.strip():
            keys = [k.strip() for k in raw.split(",") if k.strip()]
        else:
            keys = [k.strip() for k in os.environ.get(env_key, "").split(",") if k.strip()]
        return keys

    llm_keys = _split_keys(args.llm_keys, "LLM_KEYS")
    search_keys = _split_keys(args.search_keys, "SEARCH_KEYS")
    jina_keys = _split_keys(args.jina_keys, "JINA_KEYS")

    if not llm_keys or not search_keys or not jina_keys:
        raise ValueError("缺少 API keys，请通过参数或环境变量 LLM_KEYS/SEARCH_KEYS/JINA_KEYS 提供。")

    # keys 数量要一致，便于均匀分配
    key_count = min(len(llm_keys), len(search_keys), len(jina_keys))
    llm_keys = llm_keys[:key_count]
    search_keys = search_keys[:key_count]
    jina_keys = jina_keys[:key_count]

    generator = TrajectoryGenerator(
        search_api_keys=search_keys,
        jina_api_keys=jina_keys,
        llm_api_keys=llm_keys,
        model=args.model,
        max_turns=5
    )

    os.makedirs(os.path.dirname(args.output) if os.path.dirname(args.output) else ".", exist_ok=True)

    def build_balanced_questions(num_samples: int) -> List[Dict]:
        buckets: Dict[str, List[Dict]] = {}
        for q in SEED_QUESTIONS:
            key = f"{q['industry']}::{q['question_type']}"
            buckets.setdefault(key, []).append(q)
        keys = sorted(buckets.keys())
        # 轮询选取，保证分布均匀
        result: List[Dict] = []
        idx = 0
        while len(result) < num_samples:
            key = keys[idx % len(keys)]
            # 轮询桶内问题
            bucket = buckets[key]
            pick = bucket[len(result) % len(bucket)]
            result.append(pick)
            idx += 1
        return result

    questions = build_balanced_questions(args.num_samples)

    print("=" * 60)
    total_threads = key_count * args.threads_per_key
    print(f"轨迹合成 V3 | 模型: {args.model} | 线程: {total_threads} (keys={key_count})")
    print(f"样本: {len(questions)} | 输出: {args.output}")
    print("=" * 60)

    counter = Counter()
    trajectories = []

    start_time = time.time()

    # 多线程生成
    with ThreadPoolExecutor(max_workers=total_threads) as executor:
        tasks = [(generator, q, counter, i % key_count) for i, q in enumerate(questions)]
        futures = {executor.submit(generate_single, task): task[1]["id"] for task in tasks}

        with tqdm(total=len(futures), desc="生成进度", ncols=90) as pbar:
            for future in as_completed(futures):
                result = future.result()
                if result:
                    trajectories.append(result)
                pbar.update(1)

    # 保存结果
    with open(args.output, "w", encoding="utf-8") as f:
        for t in trajectories:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")

    elapsed = time.time() - start_time
    valid_count = sum(1 for t in trajectories if "validation_errors" not in t.get("metadata", {}))

    print("\n" + "=" * 60)
    print(f"完成: {len(trajectories)} 条 | 验证通过: {valid_count} | 耗时: {elapsed:.1f}秒")
    print("=" * 60)


if __name__ == "__main__":
    main()
