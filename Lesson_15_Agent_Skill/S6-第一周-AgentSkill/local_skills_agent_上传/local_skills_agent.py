# ============================================================================
# Copyright (c) 2026 深维大模型（DeepDimension AI）
# All Rights Reserved. 版权所有，盗版必究。
#
# 本软件及其相关文档受版权法保护。未经深维大模型书面授权，
# 任何单位和个人不得擅自复制、修改、分发或以其他方式使用本软件
# 的全部或部分内容。违者将依法追究法律责任。
# ============================================================================
"""
Local Agent Skills — 基于阿里千问模型的本地 Agent Skills 实现

核心思路：
- Anthropic 的 Agent Skills 本质是 "system prompt + tool calling + 代码执行" 的组合
- 阿里千问通过 Anthropic SDK 兼容接口完整支持这三项
- 我们在本地实现 Skill 管理、代码执行和 Agent 循环，无需依赖 Anthropic 云端

架构对比：
  Anthropic 原版                    本地实现
  ─────────────                    ────────
  container.skills                → system prompt 注入 Skill 元数据
  server_tool_use (自动)           → 标准 tool_use (显式 agent loop)
  云端代码执行沙箱                  → 本地 subprocess 执行
  Files API (file_id 下载)         → 直接保存到本地 output/ 目录
"""

import os
import sys
import json
import subprocess
import time
from pathlib import Path
from dotenv import load_dotenv
import anthropic
import yaml

# ============================================================
# 0. 初始化
# ============================================================
load_dotenv()

client = anthropic.Anthropic(
    api_key=os.environ.get("DASHSCOPE_API_KEY"),
    base_url=os.environ.get("DASHSCOPE_BASE_URL"),
)

# 千问最新最强模型
MODEL = "qwen3-max"

# 项目路径
PROJECT_DIR = Path(__file__).parent
SKILLS_DIR = PROJECT_DIR / "skills"
OUTPUT_DIR = PROJECT_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def rel_path(abs_path) -> str:
    """将绝对路径转为相对于项目目录的相对路径，便于阅读"""
    try:
        return str(Path(abs_path).relative_to(PROJECT_DIR))
    except ValueError:
        return str(abs_path)


# ============================================================
# 1. SkillManager — 本地 Skill 管理
#    对标 Anthropic 的 container.skills + skills.list()
#    从本地 skills/ 目录扫描、加载 Skill
# ============================================================
class SkillManager:
    """管理本地 Skill 目录"""

    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
        self.skills = {}  # name -> {name, description, path, content}
        self._scan()

    def _scan(self):
        """扫描 skills/ 目录，解析每个 SKILL.md 的 YAML frontmatter"""
        if not self.skills_dir.exists():
            return
        for skill_dir in self.skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue
            content = skill_md.read_text(encoding="utf-8")
            meta = self._parse_frontmatter(content)
            if meta:
                self.skills[meta["name"]] = {
                    "name": meta["name"],
                    "description": meta.get("description", ""),
                    "path": rel_path(skill_dir),
                    "skill_md_path": str(skill_md),        # 绝对路径，供 read_file 使用
                    "skill_md_rel": rel_path(skill_md),    # 相对路径，供显示使用
                    "content": content,
                }

    def _parse_frontmatter(self, content: str) -> dict | None:
        """解析 SKILL.md 开头的 YAML frontmatter"""
        if not content.startswith("---"):
            return None
        parts = content.split("---", 2)
        if len(parts) < 3:
            return None
        try:
            return yaml.safe_load(parts[1])
        except yaml.YAMLError:
            return None

    def list_skills(self) -> list[dict]:
        """列出所有 Skill 的元数据"""
        return list(self.skills.values())

    def get_skill_content(self, name: str) -> str | None:
        """获取指定 Skill 的完整 SKILL.md 内容（第二级披露）"""
        skill = self.skills.get(name)
        return skill["content"] if skill else None

    def build_system_prompt(self) -> str:
        """
        构建 system prompt，注入所有 Skill 的元数据（第一级披露）

        对标 Anthropic 的 container.skills 自动注入。
        模型看到元数据后，可以通过 read_file 工具按需加载完整 SKILL.md。
        """
        prompt_parts = [
            "你是一个强大的 AI 助手，具备代码执行和文件操作能力。",
            "",
            "你可以使用以下工具来完成任务：",
            "- read_file: 读取本地文件内容",
            "- write_file: 创建或写入文件",
            "- execute_python: 执行 Python 代码",
            "- execute_bash: 执行 Bash 命令",
            "- list_directory: 列出目录内容",
            "",
            "## 重要：execute_python 使用规则",
            "**每次 execute_python 调用都是独立进程，变量不会在多次调用之间共享。**",
            "因此你必须：",
            "1. 在每次 execute_python 调用中包含完整的 import 和数据定义",
            "2. 如果需要多步操作（如先生成图表再生成PDF），把所有代码写在同一次调用中",
            "3. 或者通过文件（CSV/JSON/PNG）在多次调用之间传递数据",
            "4. 不要假设上一次调用的变量仍然存在",
            "",
            f"生成的文件请保存到: {OUTPUT_DIR}（绝对路径，执行代码时使用此路径）",
            "",
            "## 重要：中文支持",
            "- matplotlib 图表中文字体已自动配置，无需手动设置",
            "- reportlab 生成 PDF 时，中文字体已自动注册为 'ChineseFont'（常规）和 'ChineseFontBold'（粗体）",
            "- **生成 PDF 时必须使用 fontName='ChineseFont'**，不要用 Helvetica/SimSun 等未注册的字体",
            "- 示例：ParagraphStyle(name='cn', fontName='ChineseFont', fontSize=12)",
            "",
            "## 重要：PDF 页面背景色",
            "- reportlab 默认页面是白色背景",
            "- 如果设计参考要求深色背景，必须用 canvas 的 onFirstPage/onLaterPages 回调在每一页绘制全页背景矩形：",
            "  ```",
            "  def draw_page_bg(canvas, doc):",
            "      canvas.saveState()",
            "      canvas.setFillColor(HexColor('#0a0a0f'))  # 从参考文件中提取的背景色",
            "      canvas.rect(0, 0, doc.pagesize[0], doc.pagesize[1], fill=True, stroke=False)",
            "      canvas.restoreState()",
            "  doc.build(story, onFirstPage=draw_page_bg, onLaterPages=draw_page_bg)",
            "  ```",
            "- **背景色的具体色值应从设计参考文件中提取，不要用白色**",
            "",
        ]

        if self.skills:
            prompt_parts.append("## 可用的 Agent Skills")
            prompt_parts.append("")
            prompt_parts.append(
                "以下是已安装的 Skills。当用户请求匹配某个 Skill 的描述时，"
                "请先使用 read_file 工具读取对应的 SKILL.md 获取详细指令，"
                "然后按照指令执行。"
            )
            prompt_parts.append("")
            for skill in self.skills.values():
                prompt_parts.append(f"### {skill['name']}")
                prompt_parts.append(f"- 描述: {skill['description']}")
                prompt_parts.append(f"- 指令文件: {skill['skill_md_path']}")
                prompt_parts.append("")

        return "\n".join(prompt_parts)


# ============================================================
# 2. LocalCodeExecutor — 本地代码执行
#    对标 Anthropic 的云端代码执行沙箱
#    通过 subprocess 在本地执行 Python/Bash
# ============================================================
class LocalCodeExecutor:
    """本地代码执行器"""

    TIMEOUT = 180  # 单次执行超时（秒）

    # 禁止执行的危险命令关键词
    BLOCKED_COMMANDS = ["rm -rf /", "mkfs", "dd if=", ":(){", "fork bomb"]

    # matplotlib 预处理：强制 Agg 后端（防止 plt.show() 阻塞）+ 中文字体
    MPL_PREAMBLE = (
        "import matplotlib as _mpl\n"
        "_mpl.use('Agg')\n"
        "_mpl.rcParams['font.sans-serif'] = ['PingFang HK', 'Heiti TC', 'Arial Unicode MS', 'STHeiti', 'SimSong']\n"
        "_mpl.rcParams['axes.unicode_minus'] = False\n"
    )

    # reportlab 预处理：注册中文字体，使 PDF 能正确显示中文
    REPORTLAB_PREAMBLE = (
        "from reportlab.pdfbase import pdfmetrics as _pm\n"
        "from reportlab.pdfbase.ttfonts import TTFont as _TTFont\n"
        "try:\n"
        "    _pm.registerFont(_TTFont('ChineseFont', '/Library/Fonts/Arial Unicode.ttf'))\n"
        "    _pm.registerFont(_TTFont('ChineseFontBold', '/System/Library/Fonts/STHeiti Medium.ttc'))\n"
        "except: pass\n"
        "# 中文字体已注册：使用 'ChineseFont' 或 'ChineseFontBold' 作为字体名\n"
        "# 示例：canvas.setFont('ChineseFont', 12) 或 ParagraphStyle(fontName='ChineseFont')\n"
    )

    @staticmethod
    def execute_python(code: str) -> dict:
        """执行 Python 代码，返回 stdout/stderr"""
        for blocked in LocalCodeExecutor.BLOCKED_COMMANDS:
            if blocked in code:
                return {"stdout": "", "stderr": f"安全限制：禁止执行包含 '{blocked}' 的代码", "return_code": 1}

        # 如果代码中使用了 matplotlib，自动注入配置
        if "matplotlib" in code or "plt" in code:
            code = LocalCodeExecutor.MPL_PREAMBLE + code
            code = code.replace("plt.show()", "# plt.show() removed - non-interactive")

        # 如果代码中使用了 reportlab，自动注册中文字体
        if "reportlab" in code:
            code = LocalCodeExecutor.REPORTLAB_PREAMBLE + code

        try:
            result = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True,
                text=True,
                timeout=LocalCodeExecutor.TIMEOUT,
                cwd=str(OUTPUT_DIR),
            )
            return {
                "stdout": result.stdout[-5000:] if len(result.stdout) > 5000 else result.stdout,
                "stderr": result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr,
                "return_code": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"stdout": "", "stderr": f"执行超时（{LocalCodeExecutor.TIMEOUT}秒）", "return_code": 1}
        except Exception as e:
            return {"stdout": "", "stderr": str(e), "return_code": 1}

    @staticmethod
    def execute_bash(command: str) -> dict:
        """执行 Bash 命令"""
        for blocked in LocalCodeExecutor.BLOCKED_COMMANDS:
            if blocked in command:
                return {"stdout": "", "stderr": f"安全限制：禁止执行包含 '{blocked}' 的命令", "return_code": 1}
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=LocalCodeExecutor.TIMEOUT,
                cwd=str(OUTPUT_DIR),
            )
            return {
                "stdout": result.stdout[-5000:] if len(result.stdout) > 5000 else result.stdout,
                "stderr": result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr,
                "return_code": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"stdout": "", "stderr": f"执行超时（{LocalCodeExecutor.TIMEOUT}秒）", "return_code": 1}
        except Exception as e:
            return {"stdout": "", "stderr": str(e), "return_code": 1}

    @staticmethod
    def read_file(file_path: str) -> dict:
        """读取本地文件内容"""
        try:
            path = Path(file_path)
            if not path.exists():
                return {"content": "", "error": f"文件不存在: {file_path}"}
            content = path.read_text(encoding="utf-8")
            # 限制返回大小，避免 token 爆炸
            if len(content) > 20000:
                content = content[:20000] + "\n\n... [文件过大，已截断] ..."
            return {"content": content, "error": ""}
        except Exception as e:
            return {"content": "", "error": str(e)}

    @staticmethod
    def write_file(file_path: str, content: str) -> dict:
        """写入文件"""
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return {"success": True, "path": str(path), "error": ""}
        except Exception as e:
            return {"success": False, "path": file_path, "error": str(e)}

    @staticmethod
    def list_directory(dir_path: str) -> dict:
        """列出目录内容"""
        try:
            path = Path(dir_path)
            if not path.exists():
                return {"entries": [], "error": f"目录不存在: {dir_path}"}
            entries = []
            for item in sorted(path.iterdir()):
                entries.append({
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else None,
                })
            return {"entries": entries, "error": ""}
        except Exception as e:
            return {"entries": [], "error": str(e)}


# ============================================================
# 3. 工具定义 — 传给模型的 tools 参数
#    对标 Anthropic 的 server_tool_use (text_editor + bash)
#    改为标准的 Anthropic tool calling 格式
# ============================================================
TOOLS = [
    {
        "name": "read_file",
        "description": "读取本地文件的内容。用于读取 Skill 指令文件（SKILL.md）或其他参考文件。",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "要读取的文件的绝对路径或相对路径",
                }
            },
            "required": ["file_path"],
        },
    },
    {
        "name": "write_file",
        "description": "创建或覆盖写入一个文件。用于保存生成的代码、数据或报告。",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "要写入的文件路径",
                },
                "content": {
                    "type": "string",
                    "description": "要写入的文件内容",
                },
            },
            "required": ["file_path", "content"],
        },
    },
    {
        "name": "execute_python",
        "description": "执行一段 Python 代码。代码在本地运行，工作目录为 output/。可以使用 pandas、matplotlib、numpy 等已安装的库。",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "要执行的 Python 代码",
                }
            },
            "required": ["code"],
        },
    },
    {
        "name": "execute_bash",
        "description": "执行一条 Bash 命令。工作目录为 output/。",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "要执行的 Bash 命令",
                }
            },
            "required": ["command"],
        },
    },
    {
        "name": "list_directory",
        "description": "列出指定目录下的文件和子目录。",
        "input_schema": {
            "type": "object",
            "properties": {
                "dir_path": {
                    "type": "string",
                    "description": "要列出内容的目录路径",
                }
            },
            "required": ["dir_path"],
        },
    },
]


# ============================================================
# 4. 工具调用分发 — 将 tool_use 分发到对应的执行函数
# ============================================================
def dispatch_tool(tool_name: str, tool_input: dict) -> str:
    """根据工具名分发到对应的执行函数，返回 JSON 字符串结果"""
    executor = LocalCodeExecutor()

    if tool_name == "read_file":
        result = executor.read_file(tool_input["file_path"])
    elif tool_name == "write_file":
        result = executor.write_file(tool_input["file_path"], tool_input["content"])
    elif tool_name == "execute_python":
        result = executor.execute_python(tool_input["code"])
    elif tool_name == "execute_bash":
        result = executor.execute_bash(tool_input["command"])
    elif tool_name == "list_directory":
        result = executor.list_directory(tool_input["dir_path"])
    else:
        result = {"error": f"未知工具: {tool_name}"}

    return json.dumps(result, ensure_ascii=False)


# ============================================================
# 5. AgentLoop — 核心 Agent 循环
#    对标 Anthropic 的 messages.create() 内部自动循环
#    我们改为显式循环：调用模型 → 执行工具 → 返回结果 → 再调用
# ============================================================
def agent_loop(user_prompt: str, system_prompt: str, max_iterations: int = 30):
    """
    Agent 循环：持续与模型交互直到任务完成

    流程：
    1. 发送用户请求 + system prompt + tools 给千问模型
    2. 如果模型返回 tool_use → 在本地执行 → 将结果追加到 messages
    3. 重复直到模型返回 end_turn（不再调用工具）

    Args:
        user_prompt: 用户的请求
        system_prompt: 包含 Skill 元数据的 system prompt
        max_iterations: 最大循环次数（防止无限循环）
    """
    messages = [{"role": "user", "content": user_prompt}]

    # 打印完整的 system prompt
    print("=" * 60)
    print("[System Prompt]")
    print("=" * 60)
    print(system_prompt)
    print()
    print("=" * 60)
    print(f"[用户请求] {user_prompt}")
    print("=" * 60)

    for iteration in range(max_iterations):
        print(f"\n{'─' * 60}")
        print(f"  第 {iteration + 1} 轮")
        print(f"{'─' * 60}")

        # 打印本轮发送给模型的 messages 输入
        print(f"  [输入] messages 共 {len(messages)} 条:")
        for i, msg in enumerate(messages):
            role = msg["role"]
            content = msg.get("content", "")
            if isinstance(content, str):
                preview = content[:150].replace("\n", " ")
                print(f"    [{i}] {role}: {preview}...")
            elif isinstance(content, list):
                # tool_result 列表或 content blocks
                types = []
                for item in content:
                    if isinstance(item, dict):
                        types.append(item.get("type", "?"))
                    else:
                        types.append(getattr(item, "type", "?"))
                print(f"    [{i}] {role}: [{', '.join(types)}]")
            else:
                print(f"    [{i}] {role}: (content blocks)")

        # 调用千问模型
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=8192,
                system=system_prompt,
                messages=messages,
                tools=TOOLS,
            )
        except anthropic.RateLimitError:
            print("   [限流] 等待 30 秒后重试...")
            time.sleep(30)
            continue
        except anthropic.InternalServerError:
            print("   [过载] 等待 30 秒后重试...")
            time.sleep(30)
            continue

        print(f"   stop_reason: {response.stop_reason}")

        # 处理响应中的每个 content block
        tool_calls = []
        for block in response.content:
            if hasattr(block, "text"):
                print(f"\n   [模型回复] {block.text[:500]}")
            elif block.type == "tool_use":
                # 模型请求调用工具
                tool_name = block.name
                tool_input = block.input
                tool_id = block.id
                input_preview = json.dumps(tool_input, ensure_ascii=False)[:200]
                print(f"   [工具调用] {tool_name}({input_preview})")
                tool_calls.append((tool_id, tool_name, tool_input))

        # 如果没有工具调用（end_turn），任务完成
        if response.stop_reason == "end_turn" or not tool_calls:
            print("\n" + "=" * 60)
            print("[完成] 模型已完成任务")
            # 打印最终文本回复
            for block in response.content:
                if hasattr(block, "text"):
                    print(f"\n{block.text}")
            break

        # 将 assistant 的完整回复追加到 messages
        # 注意：必须将完整的 response.content 回传，保持对话连续性
        messages.append({"role": "assistant", "content": response.content})

        # 执行每个工具调用，收集结果
        tool_results = []
        for tool_id, tool_name, tool_input in tool_calls:
            print(f"   [执行中] {tool_name}...")
            result_str = dispatch_tool(tool_name, tool_input)
            result_preview = result_str[:300]
            print(f"   [结果] {result_preview}")
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_id,
                "content": result_str,
            })

        # 将 tool_result 追加到 messages
        messages.append({"role": "user", "content": tool_results})

    else:
        print(f"\n[警告] 达到最大迭代次数 {max_iterations}，强制停止")

    # 列出 output 目录中生成的文件
    output_files = [f for f in OUTPUT_DIR.iterdir() if f.is_file()]
    if output_files:
        print("\n" + "=" * 60)
        print("[生成的文件]")
        for f in output_files:
            size = f.stat().st_size
            print(f"   {rel_path(f)} ({size:,} bytes)")

    # 保存完整的 messages 到 output 目录
    from datetime import datetime

    def _serialize(obj):
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
        "model": MODEL,
        "user_prompt": user_prompt,
        "timestamp": ts,
        "messages": _serialize(messages),
    }
    try:
        log_path.write_text(json.dumps(log_data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print(f"\n[对话记录] 已保存到 {rel_path(log_path)}")
    except Exception as e:
        print(f"\n[对话记录] 保存失败: {e}")


# ============================================================
# 6. 主程序
# ============================================================
def main():
    """
    用法:
        python local_skills_agent.py "你的请求"
        python local_skills_agent.py list                # 列出本地 Skill
        python local_skills_agent.py test                # 运行测试用例

    示例:
        python local_skills_agent.py "分析销售数据：Q1=120万, Q2=150万, Q3=98万, Q4=200万"
        python local_skills_agent.py "帮我写一个冒泡排序的Python脚本"
    """
    # 初始化 SkillManager：扫描 skills/ 目录下所有包含 SKILL.md 的子目录
    # 解析每个 SKILL.md 的 YAML frontmatter（name + description），建立 Skill 索引
    skill_mgr = SkillManager(SKILLS_DIR)

    # 无参数时显示帮助信息和已安装的 Skill 列表
    if len(sys.argv) < 2:
        print(main.__doc__)
        print("\n已安装的 Skills:")
        for s in skill_mgr.list_skills():
            print(f"  - {s['name']}: {s['description']}")
        return

    # 获取用户输入的命令（list / test / 自由文本提问）
    action = sys.argv[1]

    # "list" 命令：展示所有本地 Skill 的详细信息（名称、描述、目录路径）
    if action == "list":
        print("=" * 60)
        print("本地已安装的 Agent Skills")
        print("=" * 60)
        for s in skill_mgr.list_skills():
            print(f"\n  名称: {s['name']}")
            print(f"  描述: {s['description']}")
            print(f"  路径: {s['path']}")
        if not skill_mgr.list_skills():
            print("  （无）请在 skills/ 目录下创建 Skill")
        return

    # "test" 命令：用预设的数据分析请求跑一次完整的 Agent 循环
    # 先打印 system prompt 预览（确认 Skill 元数据已注入），然后启动 agent_loop
    if action == "test":
        system_prompt = skill_mgr.build_system_prompt()
        agent_loop(
            "请帮我分析一组2026年W奶茶店销售数据：Q1=120万, Q2=150万, Q3=198万, Q4=200万，给出趋势分析和可视化图表",
            system_prompt,
        )
        return

    # 自由提问模式：将命令行参数拼接为用户请求
    # 构建包含 Skill 元数据的 system prompt，然后启动 agent loop
    # 模型会根据请求内容自动判断是否需要触发某个 Skill
    user_prompt = " ".join(sys.argv[1:])
    system_prompt = skill_mgr.build_system_prompt()
    agent_loop(user_prompt, system_prompt)


if __name__ == "__main__":
    main()
