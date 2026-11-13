"""
测试代码执行器集成 - 验证分析类任务的完整流程
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.nodes import PlannerNode, ExecutorNode, AgentState

def test_analysis_flow():
    """测试分析流程"""
    print("=" * 60)
    print("测试代码执行器集成")
    print("=" * 60)

    # 初始化
    planner = PlannerNode()
    executor = ExecutorNode()

    # 模拟分析类问题
    query = "分析银行股的PE比率分布情况，并绘制折线图"

    print(f"\n用户问题: {query}")
    print("-" * 60)

    # 初始状态
    state: AgentState = {
        "messages": [],
        "query": query,
        "intent": "analysis",  # 假设已识别为分析类
        "plan": [],
        "current_step": 0,
        "tool_calls": [],
        "tool_results": [],
        "reasoning_steps": [],
        "reflections": [],
        "final_answer": "",
        "should_continue": True,
        "iteration": 0,
        "max_iterations": 3,
        "error": None
    }

    # 1. 规划阶段
    print("\n[1] 规划阶段...")
    plan_result = planner(state)
    state.update(plan_result)

    print(f"生成的计划: {len(state['plan'])} 步")
    for step in state['plan']:
        print(f"  步骤 {step['step']}: {step['action']}")
        print(f"    工具: {step['tool']}")
        if step['tool'] == 'code_executor':
            code = step['params'].get('code', '')
            print(f"    代码长度: {len(code)} 字符")
            print("    代码预览:")
            for line in code.split('\n')[:10]:
                print(f"      {line}")
            if len(code.split('\n')) > 10:
                print("      ...")

    # 2. 执行阶段 - 步骤1 (text2sql)
    print("\n[2] 执行步骤1 (text2sql)...")
    exec_result = executor(state)
    state.update(exec_result)

    if state['tool_results']:
        result = state['tool_results'][-1]
        print(f"  工具: {result['tool']}")
        if result['result'].get('success'):
            # text2sql返回的数据在raw_data字段
            data = result['result'].get('raw_data') or result['result'].get('data', [])
            print(f"  获取数据: {len(data)} 条")
            if data:
                print(f"  数据字段: {list(data[0].keys()) if data else '无'}")
                print(f"  数据示例: {data[0]}")
        else:
            print(f"  错误: {result['result'].get('error')}")
            print(f"  SQL: {result['result'].get('sql')}")

    # 3. 执行阶段 - 步骤2 (code_executor)
    if state.get('should_continue') and state['current_step'] < len(state['plan']):
        print("\n[3] 执行步骤2 (code_executor)...")
        exec_result = executor(state)
        state.update(exec_result)

        if len(state['tool_results']) > 1:
            result = state['tool_results'][-1]
            print(f"  工具: {result['tool']}")
            if result['result'].get('success'):
                print(f"  输出:\n{result['result'].get('output', '')[:500]}")
                figures = result['result'].get('figures', [])
                if figures:
                    print(f"  生成图表: {len(figures)} 个")
                    # 保存图表到文件
                    import base64
                    import os
                    os.makedirs("output/charts", exist_ok=True)
                    for i, fig in enumerate(figures):
                        img_path = f"output/charts/analysis_chart_{i}.png"
                        with open(img_path, 'wb') as f:
                            f.write(base64.b64decode(fig['base64']))
                        print(f"  图表已保存: {img_path}")
            else:
                print(f"  错误: {result['result'].get('error')}")

    # 打印推理步骤
    print("\n" + "=" * 60)
    print("推理过程:")
    for step in state['reasoning_steps']:
        print(f"  {step}")

    print("\n" + "=" * 60)
    print("测试完成!")

    return state

if __name__ == "__main__":
    test_analysis_flow()
