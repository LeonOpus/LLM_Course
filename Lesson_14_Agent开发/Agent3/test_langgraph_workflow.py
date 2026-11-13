"""
测试LangGraph工作流 - 综合测试多工具调用

这个测试会让Agent通过工作流自动调用多个工具:
- Text2SQL: 查询数据库
- Code Executor: 数据分析和可视化
- Web Search: 网络搜索
- PDF Parser / RAG: 研报解析

运行方式:
    python test_langgraph_workflow.py
"""
import os
import sys
import json
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.init_db import init_database
from agents.graph import FinanceAnalystAgent


def print_separator(title: str = ""):
    """打印分隔线"""
    print("\n" + "=" * 70)
    if title:
        print(f"  {title}")
        print("=" * 70)


def print_result(result: dict):
    """格式化打印结果"""
    print(f"\n✅ 成功: {result.get('success', False)}")
    print(f"📌 意图: {result.get('intent', 'N/A')}")

    # 推理步骤
    reasoning_steps = result.get("reasoning_steps", [])
    if reasoning_steps:
        print(f"\n🔍 推理过程 ({len(reasoning_steps)} 步):")
        for i, step in enumerate(reasoning_steps, 1):
            # 截断过长的步骤
            step_text = step[:200] + "..." if len(step) > 200 else step
            print(f"   {i}. {step_text}")

    # 工具调用结果
    tool_results = result.get("tool_results", [])
    if tool_results:
        print(f"\n🛠️  工具调用 ({len(tool_results)} 次):")
        for i, tr in enumerate(tool_results, 1):
            tool_name = tr.get("tool", "unknown")
            success = tr.get("result", {}).get("success", False)
            print(f"   {i}. {tool_name} - {'成功' if success else '失败'}")

    # 反思
    reflections = result.get("reflections", [])
    if reflections:
        print(f"\n💭 反思 ({len(reflections)} 次):")
        for ref in reflections:
            print(f"   - {ref.get('summary', '')[:100]}...")

    # 最终答案
    print(f"\n📝 最终答案:")
    answer = result.get("answer", "无答案")
    # 分行显示
    for line in answer.split("\n"):
        print(f"   {line}")

    print(f"\n🔄 迭代次数: {result.get('iterations', 0)}")


def test_multi_tool_query():
    """
    测试综合查询 - 触发多个工具调用

    这个查询设计为需要:
    1. Text2SQL - 查询银行股数据
    2. Code Executor - 计算和可视化分析
    3. Web Search - 获取最新市场信息
    """
    print_separator("测试1: 综合分析 (Text2SQL + Code + Web)")

    query = """
    请帮我分析银行板块:
    1. 先查询数据库中市值最大的5只银行股
    2. 用Python计算它们的平均市盈率
    3. 搜索最新的银行业政策新闻
    最后给出综合分析结论。
    """

    print(f"📋 查询: {query.strip()}")

    agent = FinanceAnalystAgent()
    result = agent.analyze(query, max_iterations=5)
    print_result(result)

    return result


def test_data_analysis_query():
    """
    测试数据分析查询 - Text2SQL + Code Executor

    这个查询需要:
    1. Text2SQL - 查询多只股票数据
    2. Code Executor - 进行数据分析和可视化
    """
    print_separator("测试2: 数据分析 (Text2SQL + Code)")

    query = """
    查询数据库中所有科技板块(sector='科技')的股票，
    然后用Python绘制它们市盈率和市净率的散点图，
    并分析哪些股票可能被低估。
    """

    print(f"📋 查询: {query.strip()}")

    agent = FinanceAnalystAgent()
    result = agent.analyze(query, max_iterations=5)
    print_result(result)

    return result


def test_research_query():
    """
    测试研究查询 - PDF + RAG + Web Search

    这个查询需要:
    1. Web Search - 搜索最新信息
    2. RAG Search - 检索知识库
    3. Code Executor - 整理分析
    """
    print_separator("测试3: 研究分析 (Web + RAG + Code)")

    query = """
    我想了解新能源汽车行业的投资机会:
    1. 搜索2024年新能源汽车行业最新动态
    2. 从知识库中检索相关研报内容
    3. 整理成一份简洁的投资分析报告
    """

    print(f"📋 查询: {query.strip()}")

    agent = FinanceAnalystAgent()
    result = agent.analyze(query, max_iterations=5)
    print_result(result)

    return result


def test_stream_workflow():
    """
    测试流式工作流 - 观察每个节点的执行
    """
    print_separator("测试4: 流式执行 (观察工作流节点)")

    query = "查询市值最大的3只股票，并计算它们的平均涨跌幅"

    print(f"📋 查询: {query}")
    print("\n🔄 工作流执行过程:")

    agent = FinanceAnalystAgent()

    final_state = None
    for event in agent.stream_analyze(query, max_iterations=3):
        node = event.get("node", "unknown")
        timestamp = event.get("timestamp", "")

        # 打印节点执行信息
        print(f"\n   📍 节点: {node} ({timestamp})")

        state = event.get("state", {})

        # 显示关键状态变化
        if node == "router":
            print(f"      意图: {state.get('intent', 'N/A')}")
        elif node == "planner":
            plan = state.get("plan", [])
            print(f"      计划步骤: {len(plan)}")
            for i, step in enumerate(plan[:3], 1):
                print(f"        {i}. {step.get('tool', 'N/A')}")
        elif node == "executor":
            tool_results = state.get("tool_results", [])
            if tool_results:
                latest = tool_results[-1]
                print(f"      执行工具: {latest.get('tool', 'N/A')}")
        elif node == "reflector":
            reflections = state.get("reflections", [])
            if reflections:
                latest = reflections[-1]
                print(f"      反思: {latest.get('summary', '')[:50]}...")
        elif node == "critic":
            answer = state.get("final_answer", "")
            print(f"      答案长度: {len(answer)} 字符")

        final_state = state

    # 打印最终结果
    if final_state:
        print("\n" + "-" * 50)
        print("📝 最终答案:")
        answer = final_state.get("final_answer", "无答案")
        for line in answer.split("\n")[:10]:  # 只显示前10行
            print(f"   {line}")
        if len(answer.split("\n")) > 10:
            print("   ...")


def main():
    """主函数"""
    print("\n" + "╔" + "═" * 68 + "╗")
    print("║" + " " * 20 + "LangGraph 工作流测试" + " " * 28 + "║")
    print("║" + " " * 15 + "金融研报自动化分析师 Agent" + " " * 24 + "║")
    print("╚" + "═" * 68 + "╝")

    print("\n📌 初始化数据库...")
    init_database()
    print("✅ 数据库初始化完成")

    # 选择测试
    print("\n请选择要运行的测试:")
    print("  1. 综合分析 (Text2SQL + Code + Web)")
    print("  2. 数据分析 (Text2SQL + Code)")
    print("  3. 研究分析 (Web + RAG + Code)")
    print("  4. 流式执行 (观察工作流节点)")
    print("  5. 运行所有测试")
    print("  q. 退出")

    choice = input("\n请输入选项 [1-5/q]: ").strip()

    if choice == "1":
        test_multi_tool_query()
    elif choice == "2":
        test_data_analysis_query()
    elif choice == "3":
        test_research_query()
    elif choice == "4":
        test_stream_workflow()
    elif choice == "5":
        print("\n🚀 运行所有测试...")
        test_multi_tool_query()
        test_data_analysis_query()
        test_research_query()
        test_stream_workflow()
    elif choice.lower() == "q":
        print("退出测试")
        return
    else:
        print("无效选项，运行默认测试...")
        test_multi_tool_query()

    print_separator("测试完成")
    print("✅ LangGraph工作流测试结束")


if __name__ == "__main__":
    main()
