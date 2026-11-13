"""
测试 Critic 节点修复
验证当 Critic 作为 SOP 节点直接执行时，能正确获取 content
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from core.agents.ceo import CEOAgent, SOPDefinition, SOPNode

async def test_critic_node():
    """测试包含 Critic 节点的 SOP 执行"""
    print("\n" + "="*60)
    print("测试: Critic 节点作为 SOP 直接节点执行")
    print("="*60 + "\n")

    ceo = CEOAgent()

    # 创建一个简单的 SOP，包含 Researcher -> Critic 流程
    # 这模拟了自动生成 SOP 时 Critic 作为最终节点的情况
    test_sop = SOPDefinition(
        name="测试SOP",
        description="测试 Critic 节点能否正确获取依赖节点的内容",
        nodes=[
            SOPNode(
                id="research",
                name="研究任务",
                agent_type="researcher",
                task_template="简要介绍什么是人工智能",
                dependencies=[],
                max_retries=1,
                review_required=False  # 不需要内部审核，让它快速完成
            ),
            SOPNode(
                id="final_review",
                name="最终审核",
                agent_type="critic",
                task_template="审核研究内容的质量",
                dependencies=["research"],  # 依赖 research 节点
                max_retries=1,
                review_required=False
            )
        ],
        final_output_node="final_review"
    )

    print("SOP 结构:")
    print("  research (researcher) -> final_review (critic)")
    print("\n预期行为:")
    print("  1. research 节点执行完成")
    print("  2. final_review 节点能从 research 结果中获取 content")
    print("  3. Critic 正常执行审核，不报 '没有提供待审核的内容' 错误")
    print("\n开始执行...\n")

    result = await ceo.execute(
        task="测试Critic节点",
        context={"sop": test_sop}
    )

    print("\n" + "="*60)
    print("执行结果:")
    print("="*60)
    print(f"  成功: {result.success}")

    if result.success:
        print(f"  执行时间: {result.execution_time:.2f}s")
        print(f"  节点执行日志:")
        for log in result.metadata.get("execution_logs", []):
            status = "✓" if log["status"] == "completed" else "✗"
            print(f"    {status} {log['node']}: {log['status']}")
        print("\n✅ 测试通过! Critic 节点正确获取了依赖节点的内容")
    else:
        print(f"  错误: {result.error}")
        if "没有提供待审核的内容" in str(result.error):
            print("\n❌ 测试失败! Bug 未修复")
        else:
            print("\n⚠️ 执行出错，但不是 content 问题")

    return result.success


async def main():
    try:
        success = await test_critic_node()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
