"""构建格式强化数据集：仅保留标准<think>+<tool_call> JSON。"""

import argparse
import json
import re
from typing import Any, Dict, List


TOOL_CALL_JSON_RE = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL)


def extract_tool_call(content: str) -> Dict[str, Any] | None:
    match = TOOL_CALL_JSON_RE.search(content)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except Exception:
        return None


def normalize_assistant_content(tool_call: Dict[str, Any]) -> str:
    tool_json = json.dumps(tool_call, ensure_ascii=False, indent=2)
    return "<think>\n继续执行下一步。\n</think>\n\n<tool_call>\n" + tool_json + "\n</tool_call>"


def normalize_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for msg in messages:
        if msg.get("role") != "assistant":
            normalized.append(msg)
            continue
        tool_call = extract_tool_call(msg.get("content", ""))
        if tool_call:
            normalized.append({"role": "assistant", "content": normalize_assistant_content(tool_call)})
        else:
            # 无法提取 tool_call 的 assistant 消息直接跳过
            continue
    return normalized


def main() -> None:
    parser = argparse.ArgumentParser(description="构建格式强化数据集")
    parser.add_argument("--input", type=str, required=True, help="输入数据路径")
    parser.add_argument("--output", type=str, required=True, help="输出数据路径")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f_in, open(
        args.output, "w", encoding="utf-8"
    ) as f_out:
        for line in f_in:
            item = json.loads(line)
            item["messages"] = normalize_messages(item.get("messages", []))
            f_out.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"格式强化数据已生成: {args.output}")


if __name__ == "__main__":
    main()
