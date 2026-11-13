"""
Memory Flow Demo (轻量版)
演示 Memory 的读写流程，不执行实际的 Agent 任务

运行方式:
    cd week4_project
    python tests/demo_memory_flow.py

本演示展示:
1. Memory Pipeline 的初始化
2. add_turn() - 添加对话到缓冲区
3. retrieve_context() - 检索相关记忆
4. 缓冲区溢出时的自动归档
5. Milvus 存储的变化
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.memory.memory_pipeline import MemoryPipeline
from core.memory.milvus_store import MilvusMemoryStore

# 彩色输出
class C:
    H = '\033[95m'  # Header
    B = '\033[94m'  # Blue
    C = '\033[96m'  # Cyan
    G = '\033[92m'  # Green
    Y = '\033[93m'  # Yellow
    R = '\033[91m'  # Red
    E = '\033[0m'   # End
    BOLD = '\033[1m'

def header(text):
    print(f"\n{C.H}{'='*60}{C.E}")
    print(f"{C.H}{C.BOLD}  {text}{C.E}")
    print(f"{C.H}{'='*60}{C.E}\n")

def step(n, text):
    print(f"{C.C}[Step {n}]{C.E} {C.BOLD}{text}{C.E}")

def show_buffer(pipeline, label=""):
    """显示缓冲区状态"""
    print(f"\n{C.Y}┌─ Buffer State {label} ─────────────────────────┐{C.E}")
    state = pipeline.get_buffer_state()
    print(f"{C.Y}│{C.E} Size: {state['buffer_size']} / Window: {state['window_size']} / Threshold: {state['threshold']}")

    if state['recent_turns']:
        print(f"{C.Y}│{C.E} Turns:")
        for t in state['recent_turns']:
            role_color = C.B if t['role'] == 'user' else C.G
            content = t['content'][:40] + '...' if len(t['content']) > 40 else t['content']
            print(f"{C.Y}│{C.E}   {role_color}[{t['role']:9}]{C.E} {content}")
    else:
        print(f"{C.Y}│{C.E} (empty)")
    print(f"{C.Y}└────────────────────────────────────────────────┘{C.E}")

def show_milvus(pipeline):
    """显示 Milvus 状态"""
    print(f"\n{C.B}┌─ Milvus State ─────────────────────────────────┐{C.E}")
    if pipeline._initialized and pipeline.milvus.collection:
        try:
            pipeline.milvus.collection.flush()
            count = pipeline.milvus.collection.num_entities
            print(f"{C.B}│{C.E} Connected: {C.G}Yes{C.E}")
            print(f"{C.B}│{C.E} Collection: {pipeline.milvus.collection_name}")
            print(f"{C.B}│{C.E} Entities: {count}")
        except Exception as e:
            print(f"{C.B}│{C.E} Error: {e}")
    else:
        print(f"{C.B}│{C.E} Connected: {C.R}No{C.E}")
    print(f"{C.B}└────────────────────────────────────────────────┘{C.E}")


async def main():
    header("Memory Flow Demo")

    # ==================== 初始化 ====================
    step(1, "初始化 MemoryPipeline")

    # 使用较小的阈值以便快速看到归档
    pipeline = MemoryPipeline(
        short_term_window=5,      # 保留最近5轮
        buffer_overflow_threshold=4  # 4轮后触发归档
    )

    print(f"    Window Size: 5 (保留最近5轮对话)")
    print(f"    Archive Threshold: 4 (超过4轮触发归档)")

    # 初始化存储
    step(2, "连接 Milvus")
    if pipeline.initialize():
        print(f"    {C.G}Milvus 连接成功{C.E}")
    else:
        print(f"    {C.Y}Milvus 未连接，仅使用内存缓冲区{C.E}")

    show_buffer(pipeline, "(初始)")
    show_milvus(pipeline)

    # ==================== 模拟对话 ====================
    header("Phase 1: 添加对话")

    conversations = [
        ("user", "我想了解低空经济的发展情况"),
        ("assistant", "低空经济是指以各种有人驾驶和无人驾驶航空器的低空飞行活动为牵引的综合性经济形态，主要包括无人机物流、低空旅游、应急救援等领域。"),
        ("user", "有哪些主要的应用场景？"),
        ("assistant", "主要应用场景包括：1) 无人机物流配送 - 京东、美团等企业已开展试点；2) 低空旅游观光；3) 应急救援；4) 农业植保；5) 城市空中交通(eVTOL)。"),
        ("user", "市场规模有多大？"),
        ("assistant", "根据2024年数据，中国低空经济市场规模预计将在2025年达到1.5万亿元，其中无人机物流约120亿，通用航空约450亿。"),
    ]

    for i, (role, content) in enumerate(conversations):
        step(3 + i, f"add_turn('{role}')")
        print(f"    Content: {content[:50]}...")

        await pipeline.add_turn(role, content)

        show_buffer(pipeline)

        # 检查是否触发了归档
        if i == 3:  # 第4轮后应该触发归档
            print(f"\n    {C.Y}>>> 检查: 是否触发了归档?{C.E}")
            show_milvus(pipeline)

    # ==================== 用户画像 ====================
    header("Phase 2: 更新用户画像")

    step(9, "update_user_profile()")
    await pipeline.update_user_profile("preferences", {
        "chart_color": "red",
        "language": "zh-CN"
    })
    await pipeline.update_user_profile("interests", ["低空经济", "无人机", "市场分析"])

    print(f"    Preferences: {pipeline.user_profile['preferences']}")
    print(f"    Interests: {pipeline.user_profile['interests']}")

    # ==================== 检索测试 ====================
    header("Phase 3: 检索记忆")

    queries = [
        "无人机配送",
        "市场规模",
        "低空旅游"
    ]

    for i, query in enumerate(queries):
        step(10 + i, f"retrieve_context('{query}')")

        context = await pipeline.retrieve_context(query, top_k=3)

        print(f"\n    {C.G}>>> 检索结果:{C.E}")
        print(f"    Short-term: {len(context.short_term)} 条")
        print(f"    Long-term:  {len(context.relevant_memories)} 条")

        if context.relevant_memories:
            print(f"\n    {C.B}相关长期记忆:{C.E}")
            for j, mem in enumerate(context.relevant_memories[:2]):
                content = mem.get('content', '')[:60]
                score = mem.get('combined_score', mem.get('similarity', 0))
                print(f"      [{j+1}] (score: {score:.3f}) {content}...")

        print(f"\n    {C.C}压缩上下文 (前200字):{C.E}")
        print(f"    {context.compressed_context[:200]}...")

    # ==================== 保存洞察 ====================
    header("Phase 4: 保存洞察 (Semantic Memory)")

    step(13, "save_insight()")
    insight = "用户对低空经济领域特别感兴趣，尤其关注无人机物流和市场规模数据"
    await pipeline.save_insight(insight, source="reflection", importance=0.8)
    print(f"    Insight: {insight}")
    print(f"    Type: semantic (语义记忆)")

    show_milvus(pipeline)

    # ==================== 最终状态 ====================
    header("Final State")

    show_buffer(pipeline, "(最终)")
    show_milvus(pipeline)

    print(f"\n{C.G}User Profile:{C.E}")
    print(f"    Preferences: {pipeline.user_profile['preferences']}")
    print(f"    Interests: {pipeline.user_profile['interests']}")

    # ==================== 流程总结 ====================
    header("Memory Flow Summary")

    print(f"""
{C.BOLD}数据流向:{C.E}

  User Input
      │
      ▼
  ┌─────────────────────────────────────────────────────────┐
  │  {C.Y}Short-term Buffer (Sliding Window){C.E}                     │
  │  add_turn() → 添加到缓冲区                               │
  │                                                         │
  │  当 buffer.size >= threshold (4):                       │
  │      └─► {C.C}_archive_buffer(){C.E}                              │
  │            ├─ LLM 生成摘要                              │
  │            ├─ Embedding 向量化                          │
  │            └─ 存入 Milvus                               │
  └─────────────────────────────────────────────────────────┘
      │
      ▼
  ┌─────────────────────────────────────────────────────────┐
  │  {C.B}Long-term Store (Milvus){C.E}                               │
  │  - episodic memory (情景记忆)                           │
  │  - semantic memory (语义记忆/洞察)                      │
  │  - user_profile (用户画像)                              │
  └─────────────────────────────────────────────────────────┘
      │
      ▼
  ┌─────────────────────────────────────────────────────────┐
  │  {C.G}retrieve_context(query){C.E}                                │
  │  - 向量相似度搜索 (0.7 权重)                            │
  │  - 关键词匹配 (0.3 权重)                                │
  │  - LLM 压缩上下文                                       │
  │  → 返回 MemoryContext                                   │
  └─────────────────────────────────────────────────────────┘

{C.BOLD}CEO Agent 集成:{C.E}

  CEO.execute(task):
      1. {C.B}[Read]{C.E}  memory.retrieve_context(task)
      2. {C.G}[Exec]{C.E}  _execute_sop() → Researcher, Analyst, Critic
      3. {C.C}[Write]{C.E} memory.add_turn("user", task)
                   memory.add_turn("assistant", result)
""")

    # 清理
    pipeline.close()
    print(f"\n{C.G}Demo 完成!{C.E}\n")


if __name__ == "__main__":
    asyncio.run(main())
