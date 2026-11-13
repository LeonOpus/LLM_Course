"""
LangGraph主流程 - 金融研报自动化分析师工作流
"""
import os
import sys
from typing import Dict, Any, List, Optional, TypedDict, Annotated, Literal
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from agents.nodes import RouterNode, PlannerNode, ExecutorNode, ReflectorNode, CriticNode


class FinanceAnalystState(TypedDict):
    """金融分析师Agent状态"""
    # 输入
    messages: List[Dict[str, str]]
    query: str
    
    # 路由结果
    intent: str
    
    # 规划结果
    plan: List[Dict[str, Any]]
    current_step: int
    
    # 执行结果
    tool_calls: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    
    # 推理过程
    reasoning_steps: List[str]
    
    # 反思结果
    reflections: List[Dict[str, Any]]
    
    # 控制流
    should_continue: bool
    iteration: int
    max_iterations: int
    
    # 输出
    final_answer: str
    error: Optional[str]


def create_finance_analyst_graph():
    """
    创建金融分析师工作流图
    
    工作流程:
    1. Router: 识别用户意图
    2. Planner: 制定执行计划
    3. Executor: 执行工具调用 (循环)
    4. Reflector: ReAct反思 (可能触发重新规划)
    5. Critic: 生成最终答案
    
    Returns:
        编译后的StateGraph
    """
    # 创建节点实例
    router = RouterNode()
    planner = PlannerNode()
    executor = ExecutorNode()
    reflector = ReflectorNode()
    critic = CriticNode()
    
    # 创建状态图
    workflow = StateGraph(FinanceAnalystState)
    
    # 添加节点
    workflow.add_node("router", router)
    workflow.add_node("planner", planner)
    workflow.add_node("executor", executor)
    workflow.add_node("reflector", reflector)
    workflow.add_node("critic", critic)
    
    # 设置入口
    workflow.set_entry_point("router")
    
    # 添加边
    workflow.add_edge("router", "planner")
    workflow.add_edge("planner", "executor")
    
    # 执行器的条件边
    def should_continue_execution(state: FinanceAnalystState) -> Literal["executor", "reflector"]:
        """判断是否继续执行"""
        if state.get("should_continue", False):
            return "executor"
        return "reflector"
    
    workflow.add_conditional_edges(
        "executor",
        should_continue_execution,
        {
            "executor": "executor",
            "reflector": "reflector"
        }
    )
    
    # 反思器的条件边
    def should_reflect_again(state: FinanceAnalystState) -> Literal["planner", "critic"]:
        """判断是否需要重新规划"""
        if state.get("should_continue", False) and state.get("iteration", 0) < state.get("max_iterations", 3):
            return "planner"  # 重新规划
        return "critic"  # 生成答案
    
    workflow.add_conditional_edges(
        "reflector",
        should_reflect_again,
        {
            "planner": "planner",
            "critic": "critic"
        }
    )
    
    # 评估节点结束
    workflow.add_edge("critic", END)
    
    # 编译图
    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)
    
    return app


class FinanceAnalystAgent:
    """金融分析师Agent封装类"""
    
    def __init__(self):
        self.graph = create_finance_analyst_graph()
        self.thread_id = 0
    
    def analyze(self, query: str, max_iterations: int = 3) -> Dict[str, Any]:
        """
        执行金融分析
        
        Args:
            query: 用户查询
            max_iterations: 最大迭代次数
        
        Returns:
            分析结果
        """
        self.thread_id += 1
        
        initial_state = {
            "messages": [{"role": "user", "content": query}],
            "query": query,
            "intent": "",
            "plan": [],
            "current_step": 0,
            "tool_calls": [],
            "tool_results": [],
            "reasoning_steps": [],
            "reflections": [],
            "should_continue": True,
            "iteration": 0,
            "max_iterations": max_iterations,
            "final_answer": "",
            "error": None
        }
        
        config = {"configurable": {"thread_id": str(self.thread_id)}}
        
        try:
            # 执行工作流
            result = self.graph.invoke(initial_state, config)
            
            return {
                "success": True,
                "query": query,
                "intent": result.get("intent", ""),
                "answer": result.get("final_answer", ""),
                "reasoning_steps": result.get("reasoning_steps", []),
                "reflections": result.get("reflections", []),
                "tool_results": result.get("tool_results", []),
                "iterations": result.get("iteration", 0)
            }
        except Exception as e:
            return {
                "success": False,
                "query": query,
                "error": str(e),
                "answer": f"分析过程中出现错误: {str(e)}"
            }
    
    def stream_analyze(self, query: str, max_iterations: int = 3):
        """
        流式执行金融分析
        
        Args:
            query: 用户查询
            max_iterations: 最大迭代次数
        
        Yields:
            每个步骤的状态更新
        """
        self.thread_id += 1
        
        initial_state = {
            "messages": [{"role": "user", "content": query}],
            "query": query,
            "intent": "",
            "plan": [],
            "current_step": 0,
            "tool_calls": [],
            "tool_results": [],
            "reasoning_steps": [],
            "reflections": [],
            "should_continue": True,
            "iteration": 0,
            "max_iterations": max_iterations,
            "final_answer": "",
            "error": None
        }
        
        config = {"configurable": {"thread_id": str(self.thread_id)}}
        
        try:
            for event in self.graph.stream(initial_state, config):
                for node_name, state in event.items():
                    yield {
                        "node": node_name,
                        "state": state,
                        "timestamp": datetime.now().isoformat()
                    }
        except Exception as e:
            yield {
                "node": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


# 便捷函数
def analyze_query(query: str, max_iterations: int = 3) -> Dict[str, Any]:
    """
    便捷分析函数
    
    Args:
        query: 用户查询
        max_iterations: 最大迭代次数
    
    Returns:
        分析结果
    """
    agent = FinanceAnalystAgent()
    return agent.analyze(query, max_iterations)


if __name__ == "__main__":
    # 测试
    print("=" * 60)
    print("金融研报自动化分析师 - 测试")
    print("=" * 60)
    
    # 初始化数据库
    from database.init_db import init_database
    init_database()
    
    # 测试查询
    test_queries = [
        "市值最大的5只银行股是哪些？",
        # "分析一下贵州茅台的财务状况",
        # "最近新能源行业有什么新闻？"
    ]
    
    agent = FinanceAnalystAgent()
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"查询: {query}")
        print("=" * 60)
        
        result = agent.analyze(query)
        
        print(f"\n意图: {result.get('intent', 'N/A')}")
        print(f"\n推理过程:")
        for step in result.get("reasoning_steps", []):
            print(f"  {step}")
        
        print(f"\n最终答案:")
        print(result.get("answer", "无答案"))
        
        print(f"\n迭代次数: {result.get('iterations', 0)}")
