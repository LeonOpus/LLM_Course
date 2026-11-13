#!/usr/bin/env python3
"""
启动脚本
提供多种启动选项
"""
import sys
import argparse
import asyncio


def main():
    parser = argparse.ArgumentParser(description="多智能体协作与长期记忆系统")
    parser.add_argument(
        "command",
        choices=["server", "test", "demo"],
        help="启动命令: server(启动API服务), test(运行测试), demo(运行演示)"
    )
    parser.add_argument("--host", default="0.0.0.0", help="服务器主机")
    parser.add_argument("--port", type=int, default=8000, help="服务器端口")

    args = parser.parse_args()

    if args.command == "server":
        print("启动API服务器...")
        from api.main import start_server
        start_server(host=args.host, port=args.port)

    elif args.command == "test":
        print("运行测试...")
        from tests.test_all import run_all_tests
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)

    elif args.command == "demo":
        print("运行演示...")
        asyncio.run(run_demo())


async def run_demo():
    """运行完整演示"""
    print("\n" + "=" * 60)
    print("多智能体协作与长期记忆系统 - 完整演示")
    print("=" * 60)

    from core.agents.ceo import CEOAgent, get_market_research_sop
    from core.memory.memory_pipeline import MemoryPipeline

    # 初始化
    print("\n[1/4] 初始化系统...")
    ceo = CEOAgent()
    memory = MemoryPipeline()

    print("  ✓ CEO智能体初始化完成")
    print("  ✓ 记忆系统初始化完成")

    # 模拟用户交互
    print("\n[2/4] 记录用户偏好...")
    await memory.add_turn("user", "我想了解低空经济的发展情况，请帮我做一个研究分析")
    await memory.update_user_profile("preferences", {"chart_color": "red", "language": "zh"})
    await memory.update_user_profile("interests", ["低空经济", "无人机", "新兴产业"])

    print("  ✓ 用户对话已记录")
    print(f"  ✓ 用户画像: {memory.user_profile}")

    # 执行复杂任务
    print("\n[3/4] 执行多智能体研究任务...")
    print("  任务: 分析低空经济的市场发展情况")
    print("  SOP: 研究 -> 分析 -> 审核")

    try:
        result = await ceo.execute(
            task="分析2024年低空经济的市场发展情况",
            context={
                "sop": get_market_research_sop("低空经济"),
                "user_preferences": memory.user_profile.get("preferences", {})
            }
        )

        if result.success:
            print("  ✓ 任务执行成功!")
            summary = ceo.get_execution_summary()
            print(f"  ✓ 执行节点: {summary['completed']}/{summary['total_nodes']}")

            for log in summary.get("logs", []):
                print(f"    - {log['node_id']}: {log['status']}")
        else:
            print(f"  ✗ 任务失败: {result.error}")

    except Exception as e:
        print(f"  ✗ 任务异常: {str(e)}")

    # 记录到记忆
    print("\n[4/4] 保存交互记忆...")
    await memory.add_turn("assistant", "已完成低空经济市场研究分析，包括市场规模、应用场景和发展趋势等内容。")
    await memory.save_insight(
        "用户对低空经济领域感兴趣，偏好红色系图表",
        source="interaction"
    )

    print("  ✓ 交互记忆已保存")
    print(f"  ✓ 缓冲区状态: {memory.get_buffer_state()}")

    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)

    # 提示启动服务器
    print("\n要启动完整的API服务，请运行:")
    print("  python run.py server")
    print("\nAPI文档地址: http://localhost:8000/docs")


if __name__ == "__main__":
    main()
