"""
LangGraph节点定义 - 各Agent节点实现
"""
import os
import sys
import json
from typing import Dict, Any, List, Optional, TypedDict, Annotated
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.llm import get_llm_service
from tools.text2sql import Text2SQLTool, TEXT2SQL_TOOL_SCHEMA
from tools.code_executor import CodeExecutorTool, CODE_EXECUTOR_TOOL_SCHEMA
from tools.pdf_parser import PDFParserTool, PDF_PARSER_TOOL_SCHEMA
from tools.web_search import WebSearchTool, WEB_SEARCH_TOOL_SCHEMA
from tools.rag_search import RAGSearchTool, RAG_SEARCH_TOOL_SCHEMA


class AgentState(TypedDict):
    """Agent状态定义"""
    messages: List[Dict[str, str]]
    query: str
    intent: str
    plan: List[str]
    current_step: int
    tool_calls: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    reasoning_steps: List[str]
    reflections: List[str]
    final_answer: str
    should_continue: bool
    iteration: int
    max_iterations: int
    error: Optional[str]


class RouterNode:
    """路由节点 - 识别用户意图并路由到合适的处理流程"""
    
    def __init__(self):
        self.llm = get_llm_service()
    
    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """执行路由"""
        query = state["query"]
        
        prompt = f"""你是一个金融分析助手的路由器。分析用户的问题，判断应该使用哪种处理方式。

用户问题: {query}

可选的意图类型:
1. data_query - 数据查询：需要查询数据库获取股票、财务、行情等具体数据
2. analysis - 深度分析：需要综合多种数据进行分析，可能需要代码执行和可视化
3. research - 研报检索：需要检索研报内容或最新市场信息
4. general - 一般问答：简单的金融知识问答，不需要查询数据

请分析用户意图，返回JSON格式:
{{
    "intent": "意图类型",
    "reason": "判断理由",
    "suggested_tools": ["建议使用的工具列表"]
}}

只返回JSON，不要其他内容。"""
        
        response = self.llm.simple_chat(prompt)
        
        try:
            # 解析JSON
            result = json.loads(response.strip())
            intent = result.get("intent", "general")
            reason = result.get("reason", "")
            suggested_tools = result.get("suggested_tools", [])
        except json.JSONDecodeError:
            intent = "general"
            reason = "无法解析意图"
            suggested_tools = []
        
        return {
            "intent": intent,
            "reasoning_steps": state.get("reasoning_steps", []) + [
                f"[路由] 识别意图: {intent}，理由: {reason}"
            ]
        }


class PlannerNode:
    """规划节点 - 制定执行计划"""

    def __init__(self):
        self.llm = get_llm_service()

    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """制定计划"""
        query = state["query"]
        intent = state["intent"]

        # 如果是分析类任务，需要生成代码
        if intent == "analysis":
            return self._plan_with_code(query, state)

        prompt = f"""你是一个金融分析任务规划器。根据用户问题和识别的意图，制定详细的执行计划。

用户问题: {query}
识别意图: {intent}

可用工具:
1. text2sql - 将自然语言转SQL查询数据库（股票信息、财务数据、行情、研报记录）
2. code_executor - 执行Python代码进行数据分析和可视化，
3. pdf_parser - 解析PDF研报文档，可用文件：data/中金公司2025年中期报告.pdf、data/芯片发展.pdf、data/2025-11-16_12页_华金证券_新股覆盖研究：摩尔线程_【发现报告 fxbaogao.com】.pdf
4. web_search - 搜索最新市场信息
5. rag_search - 从研报知识库检索相关内容

请制定执行计划，返回JSON格式:
{{
    "plan": [
        {{"step": 1, "action": "动作描述", "tool": "工具名称", "params": {{"参数"}}}},
        ...
    ],
    "reasoning": "规划理由"
}}

只返回JSON，不要其他内容。"""

        response = self.llm.simple_chat(prompt)

        try:
            result = json.loads(response.strip())
            plan = result.get("plan", [])
            reasoning = result.get("reasoning", "")
        except json.JSONDecodeError:
            # 默认计划
            if intent == "data_query":
                plan = [{"step": 1, "action": "查询数据", "tool": "text2sql", "params": {"question": query}}]
            else:
                plan = [{"step": 1, "action": "直接回答", "tool": None, "params": {}}]
            reasoning = "使用默认计划"

        return {
            "plan": plan,
            "current_step": 0,
            "reasoning_steps": state.get("reasoning_steps", []) + [
                f"[规划] 制定了{len(plan)}步计划: {reasoning}"
            ]
        }

    def _plan_with_code(self, query: str, state: AgentState) -> Dict[str, Any]:
        """为分析类任务生成包含Python代码的计划"""

        # 第一步：让LLM分析需要什么数据，并生成分析代码
        prompt = f"""你是一个金融数据分析专家。用户需要进行数据分析，请制定一个包含代码的分析计划。

用户问题: {query}

可用的数据表:
1. stocks - 股票基本信息 (stock_code, stock_name, industry, sector, market_cap, pe_ratio, pb_ratio, listing_date)
2. financials - 财务数据 (stock_code, report_date, report_type, revenue, net_profit, roe, roa, total_assets, gross_margin, net_margin)
3. market_data - 行情数据 (stock_code, trade_date, open_price, close_price, high_price, low_price, volume, amount, change_pct, turnover_rate)
4. research_reports - 研报信息 (stock_code, title, analyst, institution, rating, target_price, publish_date, summary)

注意: pe_ratio和pb_ratio在stocks表中，不在financials表中

请生成分析计划，返回JSON格式:
{{
    "data_query": "需要查询的数据描述（用于text2sql），必须明确说明需要返回哪些字段",
    "expected_fields": ["查询将返回的字段列表"],
    "analysis_code": "Python分析代码（使用pandas处理data变量，可用matplotlib绑图，图表保存到 output/charts/ 目录）",
    "reasoning": "分析思路说明"
}}

重要规则:
1. data_query 中必须明确指定需要查询的所有字段，如果需要筛选某个行业，应该在SQL层面完成筛选（如：WHERE industry = '银行'）
2. expected_fields 列出查询实际会返回的字段名
3. analysis_code 只能使用 expected_fields 中列出的字段，绝对不能使用其他字段

分析代码要求:
1. 假设数据已经通过text2sql获取，存储在变量 data 中（是一个list of dict）
2. 使用 pd.DataFrame(data) 将数据转换为DataFrame
3. 使用 pandas 处理数据，打印关键的分析结果
4. 如需绑图，使用 matplotlib (plt.figure, plt.bar, plt.plot等)
5. 重要：不要调用 plt.savefig()，系统会自动捕获图表
6. 严格只使用 expected_fields 中列出的字段，不要假设存在其他字段
7. 可用变量: pd, np, plt, datetime, data

例如，如果用户问"市值最大的5只银行股"，应该：
- data_query: "查询银行行业（industry='银行'）的股票，返回 stock_code, stock_name, market_cap，按市值降序排列，取前5名"
- expected_fields: ["stock_code", "stock_name", "market_cap"]
- analysis_code: 只使用 stock_code, stock_name, market_cap 这三个字段

只返回JSON，不要其他内容。"""

        response = self.llm.simple_chat(prompt)

        try:
            result = json.loads(response.strip())
            data_query = result.get("data_query", query)
            analysis_code = result.get("analysis_code", "print('无分析代码')")
            reasoning = result.get("reasoning", "")
        except json.JSONDecodeError:
            # 默认：简单查询+基础分析
            data_query = query
            analysis_code = """
import pandas as pd
df = pd.DataFrame(data)
print("数据概览:")
print(df.describe())
print("\\n数据前5行:")
print(df.head())
"""
            reasoning = "使用默认分析计划"

        # 构建两步计划: 1.获取数据 2.执行分析代码
        plan = [
            {
                "step": 1,
                "action": f"查询数据: {data_query[:50]}...",
                "tool": "text2sql",
                "params": {"question": data_query}
            },
            {
                "step": 2,
                "action": "执行数据分析代码",
                "tool": "code_executor",
                "params": {"code": analysis_code, "use_previous_data": True}
            }
        ]

        return {
            "plan": plan,
            "current_step": 0,
            "reasoning_steps": state.get("reasoning_steps", []) + [
                f"[规划] 分析任务，生成了2步计划: {reasoning}"
            ]
        }


class ExecutorNode:
    """执行节点 - 执行具体的工具调用"""
    
    def __init__(self):
        self.llm = get_llm_service()
        self.tools = {
            "text2sql": Text2SQLTool(),
            "code_executor": CodeExecutorTool(),
            "pdf_parser": PDFParserTool(),
            "web_search": WebSearchTool(),
            "rag_search": RAGSearchTool(),
        }
    
    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """执行当前步骤"""
        plan = state.get("plan", [])
        current_step = state.get("current_step", 0)
        tool_results = state.get("tool_results", [])
        reasoning_steps = state.get("reasoning_steps", [])
        
        if current_step >= len(plan):
            return {
                "should_continue": False,
                "reasoning_steps": reasoning_steps + ["[执行] 所有步骤已完成"]
            }
        
        step = plan[current_step]
        tool_name = step.get("tool")
        params = step.get("params", {})
        action = step.get("action", "")
        
        reasoning_steps.append(f"[执行] 步骤{current_step + 1}: {action}")
        
        if tool_name and tool_name in self.tools:
            tool = self.tools[tool_name]
            
            # 根据工具类型调整参数
            if tool_name == "text2sql":
                question = params.get("question", state["query"])
                result = tool.run(question)
            elif tool_name == "code_executor":
                code = params.get("code", "")
                data = params.get("data")

                # 如果设置了use_previous_data，从上一步的text2sql结果获取数据
                if params.get("use_previous_data") and tool_results:
                    # 查找最近的text2sql结果
                    for prev_result in reversed(tool_results):
                        if prev_result.get("tool") == "text2sql":
                            prev_data = prev_result.get("result", {})
                            # text2sql返回的数据在raw_data字段中
                            raw_data = prev_data.get("raw_data") or prev_data.get("data")
                            if prev_data.get("success") and raw_data:
                                data = raw_data
                                reasoning_steps.append(f"[执行] 从text2sql获取了{len(data)}条数据")
                            else:
                                # text2sql失败或无数据，使用空列表
                                data = []
                                error_msg = prev_data.get("error", "查询无结果")
                                reasoning_steps.append(f"[警告] text2sql未返回有效数据: {error_msg}")
                            break

                result = tool.run(code, data)
            elif tool_name == "pdf_parser":
                file_path = params.get("file_path", "data/中金公司2025年中期报告.pdf")
                result = tool.run(file_path)
            elif tool_name == "web_search":
                query = params.get("query", state["query"])
                result = tool.run(query)
            elif tool_name == "rag_search":
                query = params.get("query", state["query"])
                result = tool.run(query)
            else:
                result = {"error": f"未知工具: {tool_name}"}
            
            tool_results.append({
                "step": current_step + 1,
                "tool": tool_name,
                "params": params,
                "result": result
            })
            
            reasoning_steps.append(f"[执行] 工具{tool_name}执行完成")
        else:
            # 无需工具，直接用LLM回答
            response = self.llm.simple_chat(
                f"请回答这个金融问题: {state['query']}",
                "你是一个专业的金融分析师。"
            )
            tool_results.append({
                "step": current_step + 1,
                "tool": "llm",
                "result": {"answer": response}
            })
        
        return {
            "current_step": current_step + 1,
            "tool_results": tool_results,
            "reasoning_steps": reasoning_steps,
            "should_continue": current_step + 1 < len(plan)
        }


class ReflectorNode:
    """反思节点 - ReAct反思机制"""
    
    def __init__(self):
        self.llm = get_llm_service()
    
    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """执行反思"""
        query = state["query"]
        tool_results = state.get("tool_results", [])
        reflections = state.get("reflections", [])
        iteration = state.get("iteration", 0)
        max_iterations = state.get("max_iterations", 3)
        
        # 构建反思提示
        results_summary = json.dumps(tool_results, ensure_ascii=False, indent=2)[:3000]
        
        prompt = f"""你是一个金融分析反思专家。请审视当前的分析过程和结果，进行深度反思。

用户问题: {query}

当前迭代: {iteration + 1}/{max_iterations}

已获得的结果:
{results_summary}

请进行反思，回答以下问题:
1. 当前结果是否完整回答了用户的问题？
2. 是否需要额外的数据或分析？
3. 分析过程中是否有遗漏或错误？
4. 是否需要进一步深入？

返回JSON格式:
{{
    "reflection": "反思内容",
    "is_complete": true/false,
    "missing_aspects": ["缺失的方面"],
    "suggested_actions": ["建议的后续行动"],
    "confidence": 0.0-1.0
}}

只返回JSON。"""
        
        response = self.llm.simple_chat(prompt)
        
        try:
            result = json.loads(response.strip())
            reflection = result.get("reflection", "")
            is_complete = result.get("is_complete", True)
            confidence = result.get("confidence", 0.8)
            suggested_actions = result.get("suggested_actions", [])
        except json.JSONDecodeError:
            reflection = "反思解析失败"
            is_complete = True
            confidence = 0.5
            suggested_actions = []
        
        reflections.append({
            "iteration": iteration + 1,
            "reflection": reflection,
            "confidence": confidence
        })
        
        # 决定是否继续迭代
        should_continue = (
            not is_complete and 
            iteration < max_iterations - 1 and 
            confidence < 0.85 and
            len(suggested_actions) > 0
        )
        
        new_plan = []
        if should_continue and suggested_actions:
            # 根据建议生成新计划
            new_plan = self._generate_new_plan(suggested_actions, state)
        
        return {
            "reflections": reflections,
            "iteration": iteration + 1,
            "should_continue": should_continue,
            "plan": new_plan if new_plan else state.get("plan", []),
            "current_step": 0 if new_plan else state.get("current_step", 0),
            "reasoning_steps": state.get("reasoning_steps", []) + [
                f"[反思] 第{iteration + 1}轮反思: {reflection[:100]}...",
                f"[反思] 置信度: {confidence:.2f}, 是否继续: {should_continue}"
            ]
        }
    
    def _generate_new_plan(self, suggested_actions: List[str], state: AgentState) -> List[Dict]:
        """根据建议生成新计划"""
        new_plan = []
        for i, action in enumerate(suggested_actions[:3]):  # 最多3个新步骤
            # 简单的动作到工具映射
            tool = None
            if "数据" in action or "查询" in action:
                tool = "text2sql"
            elif "分析" in action or "计算" in action:
                tool = "code_executor"
            elif "搜索" in action or "最新" in action:
                tool = "web_search"
            elif "研报" in action:
                tool = "rag_search"
            
            new_plan.append({
                "step": i + 1,
                "action": action,
                "tool": tool,
                "params": {"question": state["query"]} if tool == "text2sql" else {}
            })
        
        return new_plan


class CriticNode:
    """评估节点 - 生成最终答案"""
    
    def __init__(self):
        self.llm = get_llm_service()
    
    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """生成最终答案"""
        query = state["query"]
        tool_results = state.get("tool_results", [])
        reflections = state.get("reflections", [])
        reasoning_steps = state.get("reasoning_steps", [])
        
        # 整理所有结果
        results_summary = []
        for tr in tool_results:
            result = tr.get("result", {})
            if isinstance(result, dict):
                if "answer" in result:
                    results_summary.append(f"[{tr.get('tool', 'unknown')}]: {result['answer']}")
                elif "output" in result:
                    results_summary.append(f"[{tr.get('tool', 'unknown')}]: {result['output']}")
                elif "summary" in result:
                    results_summary.append(f"[{tr.get('tool', 'unknown')}]: {result['summary']}")
        
        prompt = f"""你是一个专业的金融分析师。根据收集到的信息，为用户提供一个全面、准确、专业的回答。

用户问题: {query}

收集到的信息:
{chr(10).join(results_summary) if results_summary else '无额外信息'}

反思记录:
{json.dumps([r['reflection'] for r in reflections], ensure_ascii=False) if reflections else '无反思'}

要求:
1. 回答要专业、准确
2. 如果涉及数据，要具体说明
3. 如果有图表，要说明图表展示的内容
4. 给出适当的风险提示
5. 语言要清晰易懂

请给出最终回答:"""
        
        final_answer = self.llm.simple_chat(prompt)
        
        return {
            "final_answer": final_answer,
            "should_continue": False,
            "reasoning_steps": reasoning_steps + [
                "[评估] 生成最终答案",
                f"[完成] 分析完成，共执行{len(tool_results)}次工具调用，{len(reflections)}轮反思"
            ]
        }
