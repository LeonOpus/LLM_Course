# ============================================================================
# Copyright (c) 2026 深维大模型（DeepDimension AI）
# All Rights Reserved. 版权所有，盗版必究。
#
# 本软件及其相关文档受版权法保护。未经深维大模型书面授权，
# 任何单位和个人不得擅自复制、修改、分发或以其他方式使用本软件
# 的全部或部分内容。违者将依法追究法律责任。
# ============================================================================
"""
Local Agent Skills — Web 前端
通过 Flask + SSE 实时展示 Agent 循环的每一步
"""

import os
import sys
import json
import time
import queue
import threading
from pathlib import Path
from flask import Flask, render_template, request, Response, jsonify
from dotenv import load_dotenv
import anthropic
import yaml

# 复用核心模块
from local_skills_agent import (
    SkillManager, LocalCodeExecutor, TOOLS, dispatch_tool,
    PROJECT_DIR, SKILLS_DIR, OUTPUT_DIR, rel_path,
)

load_dotenv()

app = Flask(__name__)

client = anthropic.Anthropic(
    api_key=os.environ.get("DASHSCOPE_API_KEY"),
    base_url=os.environ.get("DASHSCOPE_BASE_URL"),
)
DEFAULT_MODEL = "kimi-k2.5"
AVAILABLE_MODELS = [
    {"id": "qwen3-max", "name": "Qwen3-Max", "provider": "阿里"},
    {"id": "kimi-k2.5", "name": "Kimi K2.5", "provider": "月之暗面"},
    {"id": "glm-5", "name": "GLM-5", "provider": "智谱"},
    {"id": "qwen3-coder-plus", "name": "Qwen3-Coder-Plus", "provider": "阿里"},
]
skill_mgr = SkillManager(SKILLS_DIR)

# 前端显示时，将绝对路径替换为相对路径（模型内部仍使用绝对路径）
_ABS_PREFIX = str(PROJECT_DIR) + "/"


def display_path(text: str) -> str:
    """将文本中的绝对路径替换为相对路径，仅用于前端展示"""
    return text.replace(_ABS_PREFIX, "./")


def agent_loop_stream(user_prompt: str, event_queue: queue.Queue, model: str = DEFAULT_MODEL):
    """
    Agent 循环，将每一步通过 event_queue 发送给前端

    事件类型：
    - system_prompt: system prompt 内容
    - user_input: 用户请求
    - round_start: 新一轮开始
    - round_input: 本轮发送给模型的 messages 摘要
    - model_text: 模型的文本回复
    - tool_call: 模型请求调用工具
    - tool_result: 工具执行结果
    - done: 任务完成
    - error: 出错
    - files: 生成的文件列表
    """
    system_prompt = skill_mgr.build_system_prompt()
    messages = [{"role": "user", "content": user_prompt}]

    # 记录运行前已有的文件，用于最后只展示本次新增的
    existing_files = {f.name for f in OUTPUT_DIR.iterdir() if f.is_file()}

    # 发送 system prompt（前端展示用相对路径）
    event_queue.put({"type": "system_prompt", "content": display_path(system_prompt)})
    event_queue.put({"type": "user_input", "content": user_prompt})

    max_iterations = 20
    for iteration in range(max_iterations):
        # 发送轮次信息
        event_queue.put({"type": "round_start", "round": iteration + 1})

        # 构建本轮输入摘要
        input_summary = []
        for i, msg in enumerate(messages):
            role = msg["role"]
            content = msg.get("content", "")
            if isinstance(content, str):
                input_summary.append({"index": i, "role": role, "preview": display_path(content[:200])})
            elif isinstance(content, list):
                types = []
                for item in content:
                    if isinstance(item, dict):
                        types.append(item.get("type", "?"))
                    else:
                        types.append(getattr(item, "type", "?"))
                input_summary.append({"index": i, "role": role, "preview": f"[{', '.join(types)}]"})
            else:
                input_summary.append({"index": i, "role": role, "preview": "(content blocks)"})
        event_queue.put({"type": "round_input", "messages": input_summary})

        # 调用模型
        try:
            response = client.messages.create(
                model=model,
                max_tokens=8192,
                system=system_prompt,
                messages=messages,
                tools=TOOLS,
            )
        except (anthropic.RateLimitError, anthropic.InternalServerError) as e:
            event_queue.put({"type": "error", "content": f"{type(e).__name__}，30秒后重试..."})
            time.sleep(30)
            continue
        except Exception as e:
            event_queue.put({"type": "error", "content": str(e)})
            event_queue.put({"type": "done"})
            break

        # 处理响应
        tool_calls = []
        for block in response.content:
            if hasattr(block, "text"):
                event_queue.put({"type": "model_text", "content": display_path(block.text), "round": iteration + 1})
            elif block.type == "tool_use":
                tool_input_str = display_path(json.dumps(block.input, ensure_ascii=False))
                event_queue.put({
                    "type": "tool_call",
                    "tool_name": block.name,
                    "tool_input": tool_input_str,
                    "round": iteration + 1,
                })
                tool_calls.append((block.id, block.name, block.input))

        # 完成
        if response.stop_reason == "end_turn" or not tool_calls:
            # 只收集本次新增的文件
            files = []
            img_exts = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
            for f in OUTPUT_DIR.iterdir():
                if f.is_file() and f.name not in existing_files:
                    is_image = f.suffix.lower() in img_exts
                    files.append({
                        "name": f.name,
                        "path": rel_path(f),
                        "size": f.stat().st_size,
                        "is_image": is_image,
                    })
            event_queue.put({"type": "files", "files": files})
            event_queue.put({"type": "done"})
            break

        # 追加 assistant 回复
        messages.append({"role": "assistant", "content": response.content})

        # 执行工具
        tool_results = []
        for tool_id, tool_name, tool_input in tool_calls:
            result_str = dispatch_tool(tool_name, tool_input)
            # 截断过长结果
            result_preview = result_str[:2000] if len(result_str) > 2000 else result_str
            event_queue.put({
                "type": "tool_result",
                "tool_name": tool_name,
                "result": display_path(result_preview),
                "round": iteration + 1,
            })
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_id,
                "content": result_str,
            })

        messages.append({"role": "user", "content": tool_results})
    else:
        event_queue.put({"type": "error", "content": f"达到最大迭代次数 {max_iterations}"})
        event_queue.put({"type": "done"})

    # 保存完整的 messages 到 output 目录
    from datetime import datetime

    def _serialize(obj):
        """将 messages 中的 Anthropic SDK 对象转为可序列化的 dict"""
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if isinstance(obj, list):
            return [_serialize(i) for i in obj]
        if isinstance(obj, dict):
            return {k: _serialize(v) for k, v in obj.items()}
        return obj

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = OUTPUT_DIR / f"chat_log_{ts}.json"
    log_data = {
        "model": model,
        "user_prompt": user_prompt,
        "timestamp": ts,
        "messages": _serialize(messages),
    }
    try:
        log_path.write_text(json.dumps(log_data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    except Exception:
        pass


@app.route("/")
def index():
    skills = skill_mgr.list_skills()
    return render_template("index.html", skills=skills, models=AVAILABLE_MODELS, default_model=DEFAULT_MODEL)


@app.route("/run", methods=["POST"])
def run():
    prompt = request.json.get("prompt", "")
    model = request.json.get("model", DEFAULT_MODEL)
    if not prompt:
        return jsonify({"error": "请输入请求内容"}), 400

    eq = queue.Queue()
    thread = threading.Thread(target=agent_loop_stream, args=(prompt, eq, model), daemon=True)
    thread.start()

    def generate():
        while True:
            try:
                event = eq.get(timeout=300)
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                if event["type"] == "done":
                    break
            except queue.Empty:
                yield f"data: {json.dumps({'type': 'error', 'content': '超时'}, ensure_ascii=False)}\n\n"
                break

    return Response(generate(), mimetype="text/event-stream")


@app.route("/files/<path:filename>")
def serve_file(filename):
    from flask import send_from_directory
    return send_from_directory(str(OUTPUT_DIR), filename)


if __name__ == "__main__":
    print(f"启动 Local Agent Skills Web UI")
    print(f"可用模型: {[m['id'] for m in AVAILABLE_MODELS]}")
    print(f"Skills: {[s['name'] for s in skill_mgr.list_skills()]}")
    print(f"打开浏览器访问: http://localhost:5080")
    app.run(host="0.0.0.0", port=5080, debug=False)
