"""
日志格式化工具
提供清晰的可视化日志输出，帮助理解 Memory 和 Agent 执行流程
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime


class MemoryLogFormatter:
    """
    Memory 日志格式化器
    为学生提供清晰、可视化的执行过程展示
    """

    # ANSI 颜色代码
    COLORS = {
        'header': '\033[95m',    # 紫色
        'blue': '\033[94m',      # 蓝色
        'cyan': '\033[96m',      # 青色
        'green': '\033[92m',     # 绿色
        'yellow': '\033[93m',    # 黄色
        'red': '\033[91m',       # 红色
        'bold': '\033[1m',       # 粗体
        'end': '\033[0m'         # 结束
    }

    # 是否启用颜色输出
    _use_colors = True

    @classmethod
    def disable_colors(cls):
        """禁用颜色输出（用于日志文件）"""
        cls._use_colors = False

    @classmethod
    def _c(cls, color: str, text: str) -> str:
        """应用颜色"""
        if cls._use_colors:
            return f"{cls.COLORS.get(color, '')}{text}{cls.COLORS['end']}"
        return text

    @classmethod
    def phase_header(cls, phase: str, icon: str = "📌") -> str:
        """
        输出阶段标题

        示例输出:
        ╔══════════════════════════════════════════════════════════╗
        ║ 📌 Memory Read Phase                                     ║
        ╚══════════════════════════════════════════════════════════╝
        """
        width = 58
        title = f" {icon} {phase} "
        padding = width - len(title)
        left_pad = padding // 2
        right_pad = padding - left_pad

        lines = [
            cls._c('header', "╔" + "═" * width + "╗"),
            cls._c('header', "║") + cls._c('bold', title.center(width)) + cls._c('header', "║"),
            cls._c('header', "╚" + "═" * width + "╝")
        ]
        return "\n" + "\n".join(lines)

    @classmethod
    def sub_header(cls, text: str) -> str:
        """
        输出子标题

        示例输出:
        ┌─── Buffer State ───────────────────────────────────┐
        """
        width = 55
        title = f"─── {text} "
        padding = "─" * (width - len(title))
        return cls._c('cyan', f"┌{title}{padding}┐")

    @classmethod
    def sub_footer(cls) -> str:
        """子标题结束线"""
        return cls._c('cyan', "└" + "─" * 55 + "┘")

    @classmethod
    def step(cls, num: int, text: str) -> str:
        """
        输出步骤

        示例输出:
        [Step 1] 检索历史记忆
        """
        return cls._c('cyan', f"[Step {num}]") + " " + cls._c('bold', text)

    @classmethod
    def arrow(cls, text: str) -> str:
        """
        带箭头的行

        示例输出:
        ──► 查询: "低空经济"
        """
        return cls._c('green', "  ──►") + f" {text}"

    @classmethod
    def info(cls, label: str, value: Any) -> str:
        """
        信息行

        示例输出:
        │  Buffer Size: 3 / 10
        """
        return cls._c('cyan', "│") + f"  {label}: {value}"

    @classmethod
    def memory_read_start(cls, query: str) -> str:
        """Memory Read 开始"""
        output = [
            cls.phase_header("Memory Read Phase", "📖"),
            cls.step(1, "检索历史记忆"),
            cls.arrow(f"查询: \"{query[:50]}{'...' if len(query) > 50 else ''}\"")
        ]
        return "\n".join(output)

    @classmethod
    def memory_read_result(cls,
                           short_term_count: int,
                           long_term_count: int,
                           context_length: int,
                           user_profile: Dict[str, Any]) -> str:
        """Memory Read 结果"""
        output = [
            "",
            cls.sub_header("Retrieval Result"),
            cls.info("Short-term (缓冲区)", f"{short_term_count} 条对话"),
            cls.info("Long-term (Milvus)", f"{long_term_count} 条相关记忆"),
            cls.info("Context Length", f"{context_length} 字符"),
            cls.sub_footer(),
            "",
            cls.sub_header("User Profile"),
            cls.info("Preferences", user_profile.get('preferences', {})),
            cls.info("Interests", user_profile.get('interests', [])),
            cls.sub_footer(),
            "",
            cls._c('green', "  ✓ Memory Read 完成")
        ]
        return "\n".join(output)

    @classmethod
    def memory_write_start(cls, role: str, content_preview: str) -> str:
        """Memory Write 开始"""
        output = [
            cls.phase_header("Memory Write Phase", "📝"),
            cls.step(1, f"保存 {role} 消息到缓冲区"),
            cls.arrow(f"内容: \"{content_preview}\"")
        ]
        return "\n".join(output)

    @classmethod
    def buffer_state(cls,
                     size: int,
                     window: int,
                     threshold: int,
                     turns: List[Dict] = None,
                     label: str = "") -> str:
        """
        显示缓冲区状态

        示例输出:
        ┌─── Buffer State (After Write) ────────────────────┐
        │  Size: 3 / 10 (threshold: 8)
        │  Recent Turns:
        │    [user]      我想了解低空经济...
        │    [assistant] 低空经济是指...
        └───────────────────────────────────────────────────┘
        """
        title = f"Buffer State{' (' + label + ')' if label else ''}"
        output = [
            "",
            cls.sub_header(title),
            cls.info("Size", f"{size} / {window} (threshold: {threshold})")
        ]

        if turns:
            output.append(cls._c('cyan', "│") + "  Recent Turns:")
            for turn in turns[-3:]:  # 最多显示3条
                role = turn.get('role', 'unknown')
                content = turn.get('content', '')[:35]
                if len(turn.get('content', '')) > 35:
                    content += "..."
                role_color = 'blue' if role == 'user' else 'green'
                output.append(
                    cls._c('cyan', "│") +
                    f"    {cls._c(role_color, f'[{role:9}]')} {content}"
                )
        else:
            output.append(cls._c('cyan', "│") + "  (empty)")

        output.append(cls.sub_footer())
        return "\n".join(output)

    @classmethod
    def archive_triggered(cls, from_size: int, archived_count: int, summary: str) -> str:
        """归档触发"""
        output = [
            "",
            cls._c('yellow', "  ⚡ Archive Triggered!"),
            cls.arrow(f"缓冲区溢出: {from_size} 条"),
            cls.arrow(f"归档数量: {archived_count} 条"),
            cls.arrow(f"生成摘要: \"{summary[:50]}...\""),
            cls._c('green', "  ──► 摘要已存入 Milvus (episodic memory)")
        ]
        return "\n".join(output)

    @classmethod
    def milvus_state(cls, connected: bool, entity_count: int = 0) -> str:
        """Milvus 状态"""
        output = [
            "",
            cls.sub_header("Milvus State"),
            cls.info("Connected", cls._c('green', "Yes") if connected else cls._c('red', "No"))
        ]
        if connected:
            output.append(cls.info("Entities", entity_count))
        output.append(cls.sub_footer())
        return "\n".join(output)

    @classmethod
    def agent_execution_start(cls, agent_name: str, task: str) -> str:
        """Agent 执行开始"""
        output = [
            cls.phase_header(f"Agent Execution: {agent_name}", "🤖"),
            cls.arrow(f"Task: \"{task[:60]}{'...' if len(task) > 60 else ''}\"")
        ]
        return "\n".join(output)

    @classmethod
    def sop_node_start(cls, node_id: str, node_name: str, agent_type: str) -> str:
        """SOP 节点开始"""
        return cls._c('cyan', f"  ┌─► [{node_id}]") + f" {node_name} ({agent_type})"

    @classmethod
    def sop_node_complete(cls, node_id: str, status: str, duration: float = None) -> str:
        """SOP 节点完成"""
        status_icon = "✓" if status == "completed" else "✗"
        status_color = "green" if status == "completed" else "red"
        dur_str = f" ({duration:.1f}s)" if duration else ""
        return cls._c(status_color, f"  └─► {status_icon} {node_id}: {status}{dur_str}")

    @classmethod
    def task_complete(cls, success: bool, duration: float,
                      nodes_executed: int) -> str:
        """任务完成"""
        if success:
            output = [
                "",
                cls.phase_header("Task Completed", "✅"),
                cls.info("Status", cls._c('green', "SUCCESS")),
                cls.info("Duration", f"{duration:.2f}s"),
                cls.info("Nodes Executed", nodes_executed)
            ]
        else:
            output = [
                "",
                cls.phase_header("Task Failed", "❌"),
                cls.info("Status", cls._c('red', "FAILED")),
                cls.info("Duration", f"{duration:.2f}s")
            ]
        return "\n".join(output)

    @classmethod
    def divider(cls) -> str:
        """分隔线"""
        return cls._c('cyan', "─" * 60)


# 创建全局实例方便使用
log_fmt = MemoryLogFormatter()


# 测试代码
if __name__ == "__main__":
    print(log_fmt.memory_read_start("低空经济的发展趋势"))
    print(log_fmt.memory_read_result(
        short_term_count=3,
        long_term_count=5,
        context_length=450,
        user_profile={"preferences": {"chart_color": "red"}, "interests": ["低空经济"]}
    ))
    print(log_fmt.divider())
    print(log_fmt.buffer_state(3, 10, 8, [
        {"role": "user", "content": "我想了解低空经济"},
        {"role": "assistant", "content": "低空经济是指各种航空器的低空飞行活动"}
    ], "After Write"))
    print(log_fmt.archive_triggered(8, 6, "用户讨论了低空经济的定义和应用场景"))
    print(log_fmt.milvus_state(True, 15))
    print(log_fmt.task_complete(True, 12.5, 3))
