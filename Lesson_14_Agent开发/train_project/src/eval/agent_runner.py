"""Agent 推理运行器"""

import json
import re
import time
from typing import Dict, List, Optional, Generator
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.prompts import get_system_prompt
from tools.tool_executor import ToolExecutor


def get_device() -> str:
    """获取可用设备"""
    if torch.cuda.is_available():
        return "cuda"
    elif torch.backends.mps.is_available():
        return "mps"
    else:
        return "cpu"


class AgentRunner:
    """Agent 推理运行器"""

    def __init__(
        self,
        model_path: str,
        search_api_key: str,
        llm_api_key: str = None,
        llm_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    ):
        self.device = get_device()
        print(f"Using device: {self.device}")

        # 加载模型和 tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_path,
            trust_remote_code=True
        )
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        # 注意：MPS 不支持 device_map="auto"
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.float16 if self.device != "cpu" else torch.float32,
            trust_remote_code=True
        )
        self.model.to(self.device)
        self.model.eval()

        # 工具执行器
        self.tool_executor = ToolExecutor(search_api_key, llm_api_key, llm_base_url)
        self.system_prompt = get_system_prompt()

    def run(
        self,
        question: str,
        max_steps: int = 10,
        temperature: float = 0.7,
        max_new_tokens: int = 2048,
        verbose: bool = True
    ) -> Dict:
        """运行 agent 回答问题"""

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": question}
        ]

        trajectory = []
        final_answer = None

        for step in range(max_steps):
            if verbose:
                print(f"\n--- Step {step + 1} ---")

            # 生成响应
            response = self._generate(messages, temperature, max_new_tokens)

            if verbose:
                print(f"Assistant: {response[:500]}...")

            trajectory.append({
                "step": step + 1,
                "role": "assistant",
                "content": response
            })

            # 解析工具调用
            tool_call = self._parse_tool_call(response)

            if tool_call is None:
                # 格式错误，提示重试
                messages.append({"role": "assistant", "content": response})
                messages.append({
                    "role": "user",
                    "content": "请按正确格式输出<think>和<tool_call>。"
                })
                continue

            if tool_call["name"] == "finish":
                # 完成
                final_answer = tool_call["arguments"].get("answer", "")
                evidence = tool_call["arguments"].get("evidence", "")

                if verbose:
                    print(f"\n=== Final Answer ===")
                    print(f"Answer: {final_answer}")
                    print(f"Evidence: {evidence}")

                return {
                    "question": question,
                    "answer": final_answer,
                    "evidence": evidence,
                    "trajectory": trajectory,
                    "num_steps": step + 1
                }

            # 执行工具
            tool_response = self.tool_executor.execute(tool_call)

            if verbose:
                print(f"Tool Response: {tool_response[:300]}...")

            trajectory.append({
                "step": step + 1,
                "role": "tool_response",
                "tool_name": tool_call["name"],
                "content": tool_response
            })

            # 更新消息历史（统一格式）
            messages.append({"role": "assistant", "content": response})
            messages.append({"role": "user", "content": f"[工具返回]\n{tool_response}"})

            # 避免 API 限流
            time.sleep(0.3)

        # 超过最大步数
        return {
            "question": question,
            "answer": None,
            "evidence": None,
            "trajectory": trajectory,
            "num_steps": max_steps,
            "error": "exceeded_max_steps"
        }

    def run_stream(
        self,
        question: str,
        max_steps: int = 10,
        temperature: float = 0.7,
        max_new_tokens: int = 2048
    ) -> Generator[Dict, None, None]:
        """流式运行 agent"""

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": question}
        ]

        for step in range(max_steps):
            yield {"type": "step_start", "step": step + 1}

            # 生成响应
            response = self._generate(messages, temperature, max_new_tokens)
            yield {"type": "assistant", "content": response}

            # 解析工具调用
            tool_call = self._parse_tool_call(response)

            if tool_call is None:
                messages.append({"role": "assistant", "content": response})
                messages.append({
                    "role": "user",
                    "content": "请按正确格式输出<think>和<tool_call>。"
                })
                yield {"type": "format_error"}
                continue

            if tool_call["name"] == "finish":
                yield {
                    "type": "finish",
                    "answer": tool_call["arguments"].get("answer", ""),
                    "evidence": tool_call["arguments"].get("evidence", "")
                }
                return

            # 执行工具
            yield {"type": "tool_call", "tool": tool_call}
            tool_response = self.tool_executor.execute(tool_call)
            yield {"type": "tool_response", "content": tool_response}

            # 更新消息
            messages.append({"role": "assistant", "content": response})
            messages.append({"role": "user", "content": f"[工具返回]\n{tool_response}"})

            time.sleep(0.3)

        yield {"type": "error", "error": "exceeded_max_steps"}

    def _generate(
        self,
        messages: List[Dict],
        temperature: float,
        max_new_tokens: int
    ) -> str:
        """生成模型响应"""

        # 使用 apply_chat_template
        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )

        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=16384 - max_new_tokens
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                do_sample=temperature > 0,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id
            )

        # 解码，只取新生成的部分
        input_length = inputs["input_ids"].shape[1]
        generated_ids = outputs[0][input_length:]
        response = self.tokenizer.decode(generated_ids, skip_special_tokens=True)

        return response.strip()

    def _parse_tool_call(self, content: str) -> Optional[Dict]:
        """解析工具调用"""
        match = re.search(r'<tool_call>\s*(\{.*?\})\s*</tool_call>', content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                return None
        return None


class BatchEvaluator:
    """批量评估器"""

    def __init__(self, agent_runner: AgentRunner):
        self.agent = agent_runner

    def evaluate(
        self,
        test_data: List[Dict],
        output_path: str = None,
        verbose: bool = True
    ) -> Dict:
        """评估测试集"""

        results = []
        correct = 0
        total = len(test_data)

        for i, item in enumerate(test_data):
            question = item["question"]
            ground_truth = item.get("ground_truth", "")

            if verbose:
                print(f"\n{'='*50}")
                print(f"[{i+1}/{total}] {question}")
                print(f"Ground Truth: {ground_truth}")

            # 运行 agent
            result = self.agent.run(question, verbose=verbose)
            result["ground_truth"] = ground_truth

            # 简单的正确性判断
            if result["answer"]:
                is_correct = self._check_answer(result["answer"], ground_truth)
                result["is_correct"] = is_correct
                if is_correct:
                    correct += 1
            else:
                result["is_correct"] = False

            results.append(result)

            if verbose:
                print(f"Correct: {result['is_correct']}")

        # 计算指标
        accuracy = correct / total if total > 0 else 0
        avg_steps = sum(r["num_steps"] for r in results) / total if total > 0 else 0

        summary = {
            "total": total,
            "correct": correct,
            "accuracy": accuracy,
            "avg_steps": avg_steps,
            "results": results
        }

        # 保存结果
        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            print(f"\nResults saved to {output_path}")

        return summary

    def _check_answer(self, answer: str, ground_truth: str) -> bool:
        """检查答案是否正确（简单匹配）"""
        if not ground_truth:
            return True  # 无标准答案，默认正确

        answer_lower = answer.lower()
        gt_lower = ground_truth.lower()

        # 对中文使用字符匹配
        if any('\u4e00' <= c <= '\u9fff' for c in ground_truth):
            key_chars = [c for c in ground_truth if '\u4e00' <= c <= '\u9fff']
            matches = sum(1 for c in key_chars if c in answer)
            return matches >= len(key_chars) * 0.5
        else:
            # 英文：关键词匹配
            keywords = [w for w in gt_lower.split() if len(w) > 2]
            if not keywords:
                return gt_lower in answer_lower
            matches = sum(1 for kw in keywords if kw in answer_lower)
            return matches >= len(keywords) * 0.5
