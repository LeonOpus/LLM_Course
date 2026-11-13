"""将训练数据中的 tool_call 统一为 JSON 格式，并补全 <think> 标签。"""

import argparse
import json
import re
from typing import Any, Dict, List


TOOL_CALL_XML_RE = re.compile(
    r"<tool_call>\s*<name>(.*?)</name>\s*<arguments>(.*?)</arguments>\s*</tool_call>",
    re.DOTALL,
)
ARG_TAG_RE = re.compile(r"<(\w+)>(.*?)</\1>", re.DOTALL)


def _parse_xml_arguments(args_text: str) -> Dict[str, Any]:
    args: Dict[str, Any] = {}
    for key, value in ARG_TAG_RE.findall(args_text):
        value = value.strip()
        if key == "references":
            # references 尝试解析为列表
            try:
                args[key] = json.loads(value)
                continue
            except Exception:
                pass
        args[key] = value
    return args


def _normalize_tool_call(content: str) -> str:
    match = TOOL_CALL_XML_RE.search(content)
    if not match:
        return content

    name = match.group(1).strip()
    args_text = match.group(2).strip()
    try:
        if args_text.startswith("{"):
            args = json.loads(args_text)
        else:
            args = _parse_xml_arguments(args_text)
    except Exception:
        args = {"raw": args_text}

    tool_json = json.dumps(
        {"name": name, "arguments": args},
        ensure_ascii=False,
        indent=2,
    )
    new_tool_call = f"<tool_call>\n{tool_json}\n</tool_call>"
    return TOOL_CALL_XML_RE.sub(new_tool_call, content)


def _normalize_think(content: str) -> str:
    if "<think>" in content and "</think>" in content:
        return content
    if "<tool_call>" not in content:
        return content
    prefix, suffix = content.split("<tool_call>", 1)
    prefix = prefix.strip()
    if not prefix:
        think_block = "<think>\n继续执行下一步。\n</think>\n\n"
    else:
        # 兼容 "思考：" / "思考:" 前缀
        prefix = re.sub(r"^思考[:：]\s*", "", prefix)
        think_block = f"<think>\n{prefix}\n</think>\n\n"
    return f"{think_block}<tool_call>{suffix}"


def normalize_messages(messages: List[Dict[str, Any]], convert_tool_role: bool) -> List[Dict[str, Any]]:
    for msg in messages:
        role = msg.get("role")
        if role == "tool_response" and convert_tool_role:
            msg["role"] = "tool"
            content = msg.get("content", "")
            if content.startswith("[工具返回]\n"):
                msg["content"] = content.replace("[工具返回]\n", "", 1)
            continue
        if role != "assistant":
            continue
        content = msg.get("content", "")
        content = _normalize_tool_call(content)
        content = _normalize_think(content)
        msg["content"] = content
    return messages


def main() -> None:
    parser = argparse.ArgumentParser(description="统一 JSON tool_call 格式")
    parser.add_argument("--input", type=str, required=True, help="输入数据路径")
    parser.add_argument("--output", type=str, required=True, help="输出数据路径")
    parser.add_argument("--convert-tool-role", action="store_true", help="将 tool_response 转为 tool")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f_in, open(
        args.output, "w", encoding="utf-8"
    ) as f_out:
        for line in f_in:
            item = json.loads(line)
            item["messages"] = normalize_messages(
                item.get("messages", []),
                convert_tool_role=args.convert_tool_role
            )
            f_out.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"已完成规范化，输出: {args.output}")


if __name__ == "__main__":
    main()
