"""
LangGraph 完整构建流程示例
===========================
这个脚本展示了如何从零开始构建一个完整的 LangGraph Agent

流程: State → Node → Tools → Graph → Memory → Run
"""

# ============================================================
# Step 0: 环境配置
# ============================================================
import os
from dotenv import load_dotenv

load_dotenv()

from typing import TypedDict, Annotated, Literal
import operator

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool

from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

print("=" * 60)
print("LangGraph 完整构建流程示例")
print("=" * 60)


# ============================================================
# Step 1: 定义 State (状态)
# ============================================================
print("\n[Step 1] 定义 State...")

class AgentState(MessagesState):
    """
    继承 MessagesState，自动处理消息累积

    MessagesState 内置:
        messages: Annotated[list, add_messages]  # 自动追加消息

    我们添加自定义字段:
    """
    user_name: str           # 用户名
    tool_calls_count: int    # 工具调用次数
    context: str             # 上下文信息

print("  ✓ AgentState 定义完成")
print("    - messages: list (自动累积)")
print("    - user_name: str")
print("    - tool_calls_count: int")
print("    - context: str")


# ============================================================
# Step 2: 定义 Tools (工具) - 可选
# ============================================================
print("\n[Step 2] 定义 Tools...")

@tool
def search_weather(city: str) -> str:
    """搜索指定城市的天气信息"""
    # 模拟天气查询
    weather_data = {
        "北京": "晴天，温度 25°C，空气质量良好",
        "上海": "多云，温度 28°C，有轻微雾霾",
        "广州": "小雨，温度 30°C，湿度较高",
        "深圳": "阴天，温度 29°C，傍晚有雨",
    }
    return weather_data.get(city, f"{city}天气数据暂不可用")

@tool
def calculate(expression: str) -> str:
    """计算数学表达式，例如: 2+2, 10*5, 100/4"""
    try:
        # 安全计算（仅支持基本运算）
        allowed_chars = set("0123456789+-*/.() ")
        if not all(c in allowed_chars for c in expression):
            return "不支持的表达式"
        result = eval(expression)
        return f"计算结果: {expression} = {result}"
    except Exception as e:
        return f"计算错误: {str(e)}"

@tool
def get_current_time() -> str:
    """获取当前时间"""
    from datetime import datetime
    return f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

# 工具列表
tools = [search_weather, calculate, get_current_time]

print(f"  ✓ 定义了 {len(tools)} 个工具:")
for t in tools:
    print(f"    - {t.name}: {t.description[:30]}...")


# ============================================================
# Step 3: 初始化 LLM 并绑定工具
# ============================================================
print("\n[Step 3] 初始化 LLM...")

# 使用阿里云 Qwen
llm = ChatOpenAI(
    model="qwen-max",
    temperature=0.7,
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

# 绑定工具到 LLM
llm_with_tools = llm.bind_tools(tools)

print("  ✓ Qwen LLM 初始化完成")
print("  ✓ 工具已绑定到 LLM")


# ============================================================
# Step 4: 定义 Node (节点函数)
# ============================================================
print("\n[Step 4] 定义 Node...")

def chatbot(state: AgentState) -> dict:
    """
    聊天机器人节点
    - 接收用户消息
    - 调用 LLM 生成回复
    - 可能会返回工具调用请求
    """
    # 构建系统提示
    system_prompt = SystemMessage(content="""你是一个智能助手。
你可以：
1. 查询天气（支持北京、上海、广州、深圳）
2. 进行数学计算
3. 获取当前时间

请根据用户的问题选择合适的工具，或直接回答。""")

    messages = [system_prompt] + state["messages"]

    # 调用 LLM（已绑定工具）
    response = llm_with_tools.invoke(messages)

    return {"messages": [response]}


# 使用预构建的 ToolNode 处理工具调用
tool_node = ToolNode(tools)


def update_context(state: AgentState) -> dict:
    """
    更新上下文节点（可选）
    统计工具调用次数
    """
    tool_count = state.get("tool_calls_count", 0)
    last_msg = state["messages"][-1]

    # 检查是否有工具调用
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        tool_count += len(last_msg.tool_calls)

    return {
        "tool_calls_count": tool_count,
        "context": f"已进行 {tool_count} 次工具调用"
    }

print("  ✓ chatbot 节点定义完成")
print("  ✓ tool_node 节点定义完成 (ToolNode)")
print("  ✓ update_context 节点定义完成")


# ============================================================
# Step 5: 定义路由函数 (条件边)
# ============================================================
print("\n[Step 5] 定义路由函数...")

def should_continue(state: AgentState) -> Literal["tools", "end"]:
    """
    判断是否需要继续执行工具

    返回值:
        - "tools": 需要执行工具调用
        - "end": 结束对话
    """
    last_message = state["messages"][-1]

    # 如果 LLM 返回了工具调用请求
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"

    # 否则结束
    return "end"

print("  ✓ should_continue 路由函数定义完成")


# ============================================================
# Step 6: 构建 Graph (图结构)
# ============================================================
print("\n[Step 6] 构建 Graph...")

# 创建图
graph = StateGraph(AgentState)

# 添加节点
graph.add_node("chatbot", chatbot)
graph.add_node("tools", tool_node)
graph.add_node("update_context", update_context)

# 添加边
# START → chatbot
graph.add_edge(START, "chatbot")

# chatbot → update_context (总是先更新上下文)
graph.add_edge("chatbot", "update_context")

# update_context → 条件路由
graph.add_conditional_edges(
    "update_context",
    should_continue,
    {
        "tools": "tools",   # 需要调用工具
        "end": END          # 结束
    }
)

# tools → chatbot (工具执行完回到聊天)
graph.add_edge("tools", "chatbot")

print("  ✓ 图结构构建完成")
print("    START → chatbot → update_context → [tools] → chatbot → ... → END")


# ============================================================
# Step 7: 添加 Memory (记忆/持久化) - 可选
# ============================================================
print("\n[Step 7] 添加 Memory...")

# 使用内存存储（重启后丢失）
memory = MemorySaver()

# 如果需要持久化，使用 SqliteSaver:
# from langgraph.checkpoint.sqlite import SqliteSaver
# memory = SqliteSaver.from_conn_string("chat_history.db")

print("  ✓ MemorySaver 初始化完成")


# ============================================================
# Step 8: 编译 Graph
# ============================================================
print("\n[Step 8] 编译 Graph...")

app = graph.compile(checkpointer=memory)

print("  ✓ 图编译完成")

# 打印图结构
print("\n[图结构 Mermaid]")
print("-" * 40)
print(app.get_graph().draw_mermaid())
print("-" * 40)


# ============================================================
# Step 9: 执行演示
# ============================================================
def run_conversation():
    """运行多轮对话演示"""
    print("\n" + "=" * 60)
    print("开始对话演示")
    print("=" * 60)

    # 配置（thread_id 用于区分不同会话）
    config = {"configurable": {"thread_id": "demo-session-001"}}

    # 对话列表
    conversations = [
        "你好！我叫小明",
        "北京今天天气怎么样？",
        "帮我算一下 123 * 456",
        "现在几点了？",
        "总结一下我们刚才聊了什么",
    ]

    for i, user_input in enumerate(conversations, 1):
        print(f"\n--- 第 {i} 轮对话 ---")
        print(f"👤 用户: {user_input}")

        # 调用 Agent
        result = app.invoke(
            {
                "messages": [HumanMessage(content=user_input)],
                "user_name": "小明",
                "tool_calls_count": 0,
            },
            config=config
        )

        # 获取最后一条 AI 回复
        ai_response = result["messages"][-1]
        print(f"🤖 助手: {ai_response.content}")

        # 显示工具调用统计
        if result.get("tool_calls_count", 0) > 0:
            print(f"   📊 {result.get('context', '')}")


def run_single_query(query: str):
    """运行单次查询"""
    print(f"\n查询: {query}")
    print("-" * 40)

    config = {"configurable": {"thread_id": "single-query"}}

    result = app.invoke(
        {
            "messages": [HumanMessage(content=query)],
            "user_name": "",
            "tool_calls_count": 0,
        },
        config=config
    )

    print(f"回复: {result['messages'][-1].content}")
    return result


# ============================================================
# Main
# ============================================================
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("LangGraph Agent 已就绪!")
    print("=" * 60)

    # 运行演示
    try:
        run_conversation()
    except Exception as e:
        print(f"\n⚠️ 运行出错: {e}")
        print("请确保已正确配置 DASHSCOPE_API_KEY 环境变量")

    print("\n" + "=" * 60)
    print("演示结束")
    print("=" * 60)
