"""
Memory Integration Demo
演示 CEO Agent 与 Memory 系统的集成

运行方式:
    cd week4_project
    python tests/demo_memory_integration.py

本演示展示:
1. 第一次任务执行 - Memory 为空
2. Memory 状态变化 - 任务结果被保存
3. 第二次任务执行 - Memory 被检索并使用
4. Memory 最终状态 - 包含两次任务的历史
"""

import asyncio
import sys
import json
from pathlib import Path

# 添加项目根目录到 path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import validate_config
from core.agents.ceo import CEOAgent
from core.memory.memory_pipeline import MemoryPipeline

# 彩色输出
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}  {text}{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}\n")

def print_step(step: int, text: str):
    print(f"{Colors.CYAN}[Step {step}]{Colors.ENDC} {Colors.BOLD}{text}{Colors.ENDC}")

def print_memory_state(pipeline: MemoryPipeline, label: str):
    """打印当前 Memory 状态"""
    print(f"\n{Colors.YELLOW}--- Memory State: {label} ---{Colors.ENDC}")

    # 短期缓冲区
    buffer_state = pipeline.get_buffer_state()
    print(f"{Colors.BLUE}Short-term Buffer:{Colors.ENDC}")
    print(f"  - Size: {buffer_state['buffer_size']} / {buffer_state['window_size']}")
    print(f"  - Archive Threshold: {buffer_state['threshold']}")

    if buffer_state['recent_turns']:
        print(f"  - Recent Turns:")
        for turn in buffer_state['recent_turns']:
            content_preview = turn['content'][:50] + '...' if len(turn['content']) > 50 else turn['content']
            print(f"      [{turn['role']}] {content_preview}")
    else:
        print(f"  - Recent Turns: (empty)")

    # 用户画像
    print(f"{Colors.BLUE}User Profile:{Colors.ENDC}")
    print(f"  - Preferences: {pipeline.user_profile.get('preferences', {})}")
    print(f"  - Interests: {pipeline.user_profile.get('interests', [])}")

    # Milvus 状态
    print(f"{Colors.BLUE}Long-term Store (Milvus):{Colors.ENDC}")
    if pipeline._initialized:
        try:
            count = pipeline.milvus.collection.num_entities if pipeline.milvus.collection else 0
            print(f"  - Connected: Yes")
            print(f"  - Entities: {count}")
        except:
            print(f"  - Connected: Yes (count unavailable)")
    else:
        print(f"  - Connected: No")

    print(f"{Colors.YELLOW}{'─'*40}{Colors.ENDC}\n")


async def demo_task_execution(ceo: CEOAgent, task: str, task_num: int):
    """执行单个任务并展示详细过程"""
    print_step(task_num, f"执行任务: {task}")

    print(f"\n{Colors.GREEN}>>> Input:{Colors.ENDC}")
    print(f"    Task: {task}")
    print(f"    Context: {{}}")

    # 执行任务
    print(f"\n{Colors.CYAN}>>> Executing...{Colors.ENDC}")
    result = await ceo.execute(task=task, context={})

    # 显示输出
    print(f"\n{Colors.GREEN}>>> Output:{Colors.ENDC}")
    print(f"    Success: {result.success}")
    print(f"    Execution Time: {result.execution_time:.2f}s")

    if result.metadata:
        print(f"    Metadata:")
        print(f"      - SOP: {result.metadata.get('sop_name', 'N/A')}")
        print(f"      - Nodes Executed: {result.metadata.get('nodes_executed', 0)}")

        if result.metadata.get('execution_logs'):
            print(f"      - Execution Logs:")
            for log in result.metadata['execution_logs']:
                status_color = Colors.GREEN if log['status'] == 'completed' else Colors.RED
                print(f"          {log['node']}: {status_color}{log['status']}{Colors.ENDC}")

    if result.output:
        print(f"\n{Colors.GREEN}>>> Result Preview:{Colors.ENDC}")
        output_str = str(result.output)
        if len(output_str) > 500:
            print(f"    {output_str[:500]}...")
        else:
            print(f"    {output_str}")

    return result


async def main():
    print_header("Memory Integration Demo")

    # 验证配置
    print_step(0, "验证配置")
    if not validate_config():
        print(f"{Colors.RED}配置验证失败，请检查 .env 文件{Colors.ENDC}")
        return
    print(f"{Colors.GREEN}配置验证通过{Colors.ENDC}\n")

    # ==================== 初始化 ====================
    print_header("Phase 1: 初始化")

    print_step(1, "初始化 CEO Agent (含 Memory)")
    ceo = CEOAgent()

    print(f"    - CEO Agent: {ceo.name}")
    print(f"    - Memory Enabled: {ceo._memory_enabled}")
    print(f"    - Available Agents: {list(ceo.agents.keys())}")

    # 显示初始 Memory 状态
    print_memory_state(ceo.memory, "Initial (Empty)")

    # ==================== 第一次任务执行 ====================
    print_header("Phase 2: 第一次任务执行 (Memory 为空)")

    # 简化任务以加快演示
    task1 = "简要介绍低空经济的定义和主要应用领域"

    print(f"{Colors.YELLOW}注意: 此时 Memory 为空，CEO 将直接执行任务{Colors.ENDC}\n")

    result1 = await demo_task_execution(ceo, task1, 1)

    # 显示任务1后的 Memory 状态
    print_memory_state(ceo.memory, "After Task 1")

    # ==================== 模拟用户偏好更新 ====================
    print_header("Phase 3: 更新用户偏好")

    print_step(2, "更新用户画像")
    await ceo.memory.update_user_profile("preferences", {
        "chart_color": "red",
        "language": "zh-CN",
        "detail_level": "concise"
    })
    await ceo.memory.update_user_profile("interests", ["低空经济", "无人机", "市场分析"])

    print(f"{Colors.GREEN}用户偏好已更新{Colors.ENDC}")
    print_memory_state(ceo.memory, "After Profile Update")

    # ==================== 第二次任务执行 ====================
    print_header("Phase 4: 第二次任务执行 (Memory 有历史)")

    task2 = "分析无人机物流配送的发展趋势"

    print(f"{Colors.YELLOW}注意: 此时 Memory 包含:{Colors.ENDC}")
    print(f"  - 第一次任务的历史")
    print(f"  - 用户偏好 (红色图表, 简洁风格)")
    print(f"  - 用户兴趣 (低空经济, 无人机)")
    print(f"{Colors.YELLOW}CEO 将检索这些信息并注入 context{Colors.ENDC}\n")

    result2 = await demo_task_execution(ceo, task2, 2)

    # 显示任务2后的 Memory 状态
    print_memory_state(ceo.memory, "After Task 2")

    # ==================== 检索演示 ====================
    print_header("Phase 5: Memory 检索演示")

    print_step(3, "检索与 '无人机' 相关的记忆")

    context = await ceo.memory.retrieve_context("无人机配送服务")

    print(f"\n{Colors.GREEN}>>> Retrieval Result:{Colors.ENDC}")
    print(f"    Short-term memories: {len(context.short_term)}")
    print(f"    Long-term memories: {len(context.relevant_memories)}")
    print(f"\n    Compressed Context:")
    print(f"    {'-'*40}")
    print(f"    {context.compressed_context[:500] if context.compressed_context else '(empty)'}...")
    print(f"    {'-'*40}")

    print(f"\n    User Profile:")
    print(f"    {json.dumps(context.user_profile, ensure_ascii=False, indent=4)}")

    # ==================== 总结 ====================
    print_header("Demo Summary")

    print(f"""
{Colors.BOLD}Memory Integration 工作流:{Colors.ENDC}

1. {Colors.BLUE}[Memory Read]{Colors.ENDC} CEO.execute() 开始时
   └─ retrieve_context(task) → 检索历史记忆和用户偏好
   └─ 注入到 context["memory_context"], context["user_profile"]

2. {Colors.GREEN}[Task Execution]{Colors.ENDC} 执行 SOP (Researcher → Analyst → Critic)
   └─ 各 Agent 可访问 context 中的记忆信息

3. {Colors.CYAN}[Memory Write]{Colors.ENDC} CEO.execute() 完成时
   └─ add_turn("user", task) → 保存用户任务
   └─ add_turn("assistant", result) → 保存执行结果

4. {Colors.YELLOW}[Auto Archive]{Colors.ENDC} 当 buffer > threshold 时
   └─ LLM 生成摘要 → Embedding → 存入 Milvus

{Colors.BOLD}Key Observations:{Colors.ENDC}

- 第一次任务: Memory 为空，直接执行
- 更新偏好后: 用户画像被持久化
- 第二次任务: Memory 被检索，相关历史被注入 context
- 检索时: 向量相似度 + 关键词匹配 (Hybrid Search)
""")

    # 清理
    print_step(4, "清理资源")
    ceo.memory.close()
    print(f"{Colors.GREEN}Demo 完成{Colors.ENDC}\n")


if __name__ == "__main__":
    asyncio.run(main())
