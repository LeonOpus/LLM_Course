"""
CEO Agent (总控智能体)
负责SOP定义、任务分解和智能体编排
实现DAG任务流和Review Loop机制
"""
import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import asyncio
from datetime import datetime
import sys
sys.path.append(str(__file__).rsplit('/', 4)[0])

from core.agents.base import BaseAgent, TaskResult, AgentState, AgentMessage
from core.agents.researcher import ResearcherAgent
from core.agents.analyst import AnalystAgent
from core.agents.critic import CriticAgent, ReviewDecision
from core.tools.llm import LLMService
from core.memory.memory_pipeline import MemoryPipeline
from core.utils.log_formatter import log_fmt

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    REVIEWING = "reviewing"
    REVISION = "revision"


@dataclass
class SOPNode:
    """SOP节点"""
    id: str
    name: str
    agent_type: str  # researcher, analyst, critic
    task_template: str
    dependencies: List[str] = field(default_factory=list)
    max_retries: int = 2
    review_required: bool = True


@dataclass
class SOPDefinition:
    """SOP定义"""
    name: str
    description: str
    nodes: List[SOPNode]
    final_output_node: str


@dataclass
class ExecutionLog:
    """执行日志"""
    node_id: str
    status: TaskStatus
    start_time: str
    end_time: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    retry_count: int = 0


class CEOAgent(BaseAgent):
    """
    CEO总控智能体
    - 定义和管理SOP (标准作业程序)
    - 实现DAG任务流编排
    - 协调多个专业智能体协作
    - 实现Review Loop机制
    """

    def __init__(
        self,
        name: str = "CEO",
        llm_service: Optional[LLMService] = None,
        max_global_retries: int = 3
    ):
        super().__init__(
            name=name,
            role="总控 - 负责任务分解和智能体编排",
            llm_service=llm_service
        )
        self.max_global_retries = max_global_retries

        # 初始化子智能体
        self.agents: Dict[str, BaseAgent] = {
            "researcher": ResearcherAgent(llm_service=self.llm),
            "analyst": AnalystAgent(llm_service=self.llm),
            "critic": CriticAgent(llm_service=self.llm)
        }

        # 执行日志
        self.execution_logs: List[ExecutionLog] = []

        # 节点结果缓存
        self.node_results: Dict[str, Any] = {}

        # 记忆管道 - 集成长期记忆
        self.memory = MemoryPipeline()
        self._memory_enabled = self.memory.initialize()

        logger.info(f"[{self.name}] CEO智能体初始化完成")
        logger.info(f"[{self.name}] 记忆系统: {'已启用' if self._memory_enabled else '未启用'}")
        logger.info(f"[{self.name}] 可用智能体: {list(self.agents.keys())}")

    def _build_system_prompt(self) -> str:
        return """你是CEO总控智能体，负责协调多个专业智能体完成复杂任务。

你的核心能力：
1. 任务分解：将复杂任务分解为多个子任务
2. 智能体编排：根据任务类型分配给合适的智能体
3. 流程控制：管理任务的执行顺序和依赖关系
4. 质量把控：通过Review Loop确保输出质量

可用智能体：
- Researcher: 负责信息搜索和研究
- Analyst: 负责数据分析和可视化
- Critic: 负责质量评估和审核

工作原则：
- 合理分配任务，发挥各智能体专长
- 确保任务依赖关系正确
- 对不合格的输出进行重做
- 最终输出要综合所有智能体的结果
"""

    async def execute(self, task: str, context: Optional[Dict[str, Any]] = None) -> TaskResult:
        """
        执行复杂任务

        Args:
            task: 任务描述
            context: 上下文信息，可包含:
                - sop: SOP定义（可选，如未提供则自动生成）
                - user_preferences: 用户偏好

        Returns:
            最终执行结果
        """
        import time
        start_time = time.time()

        self.state = AgentState.EXECUTING
        logger.info(f"[{self.name}] 开始执行任务: {task[:100]}...")

        context = context or {}

        try:
            # [Memory Read] 检索相关记忆
            if self._memory_enabled:
                print(log_fmt.memory_read_start(task))
                memory_context = await self.memory.retrieve_context(task)
                # 注入记忆到上下文
                context["memory_context"] = memory_context.compressed_context
                context["user_profile"] = memory_context.user_profile
                print(log_fmt.memory_read_result(
                    short_term_count=len(memory_context.short_term),
                    long_term_count=len(memory_context.relevant_memories),
                    context_length=len(memory_context.compressed_context),
                    user_profile=memory_context.user_profile
                ))

            # 获取或生成SOP
            sop = context.get("sop")
            if not sop:
                sop = await self._generate_sop(task, context)

            print(log_fmt.phase_header(f"SOP Execution: {sop.name}", "⚙️"))
            print(log_fmt.arrow(f"节点数: {len(sop.nodes)}"))
            print(log_fmt.arrow(f"节点流程: {' → '.join([n.id for n in sop.nodes])}"))

            # 执行SOP
            final_result = await self._execute_sop(sop, task, context)

            self.state = AgentState.COMPLETED
            execution_time = time.time() - start_time

            # [Memory Write] 保存任务和结果到记忆
            if self._memory_enabled:
                # 保存用户任务
                print(log_fmt.memory_write_start("user", task[:50] + "..." if len(task) > 50 else task))
                await self.memory.add_turn("user", task, {"type": "task"})

                # 保存执行结果摘要
                result_summary = self._summarize_result(final_result)
                print(log_fmt.memory_write_start("assistant", result_summary[:50] + "..." if len(result_summary) > 50 else result_summary))
                await self.memory.add_turn("assistant", result_summary, {
                    "type": "research_result",
                    "sop": sop.name,
                    "nodes": len(sop.nodes)
                })
                print(log_fmt._c('green', "  ✓ Memory Write 完成"))

            print(log_fmt.task_complete(True, execution_time, len(self.execution_logs)))

            return TaskResult(
                success=True,
                output=final_result,
                metadata={
                    "sop_name": sop.name,
                    "nodes_executed": len(self.execution_logs),
                    "execution_logs": [
                        {"node": log.node_id, "status": log.status.value}
                        for log in self.execution_logs
                    ]
                },
                execution_time=execution_time
            )

        except Exception as e:
            self.state = AgentState.ERROR
            logger.error(f"[{self.name}] 任务失败: {str(e)}")
            return TaskResult(
                success=False,
                output=None,
                error=str(e),
                execution_time=time.time() - start_time
            )

    async def _generate_sop(self, task: str, context: Dict[str, Any]) -> SOPDefinition:
        """
        根据任务自动生成SOP

        Args:
            task: 任务描述
            context: 上下文

        Returns:
            SOP定义
        """
        logger.info(f"[{self.name}] 自动生成SOP...")

        prompt = f"""为以下任务生成一个SOP（标准作业程序）。

任务: {task}

可用智能体:
- researcher: 信息搜索和研究
- analyst: 数据分析和可视化
- critic: 质量评估和审核

请以JSON格式返回SOP定义:
{{
    "name": "SOP名称",
    "description": "SOP描述",
    "nodes": [
        {{
            "id": "节点ID",
            "name": "节点名称",
            "agent_type": "智能体类型",
            "task_template": "任务模板（使用{{{{input}}}}表示输入）",
            "dependencies": ["依赖的节点ID"],
            "review_required": true/false
        }}
    ],
    "final_output_node": "最终输出节点ID"
}}

注意：
1. 确保节点依赖关系形成DAG（无环）
2. 需要审核的节点设置review_required为true
3. task_template中可以使用{{{{results.节点ID}}}}引用其他节点的结果"""

        try:
            response = await self.llm.achat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )

            result = self.llm.parse_json_response(response)

            nodes = [
                SOPNode(
                    id=n["id"],
                    name=n["name"],
                    agent_type=n["agent_type"],
                    task_template=n["task_template"],
                    dependencies=n.get("dependencies", []),
                    review_required=n.get("review_required", True)
                )
                for n in result["nodes"]
            ]

            sop = SOPDefinition(
                name=result["name"],
                description=result["description"],
                nodes=nodes,
                final_output_node=result["final_output_node"]
            )

            logger.info(f"[{self.name}] 生成SOP: {sop.name}")
            return sop

        except Exception as e:
            logger.warning(f"[{self.name}] SOP生成失败, 使用默认SOP: {str(e)}")
            return self._get_default_sop(task)

    def _get_default_sop(self, task: str) -> SOPDefinition:
        """获取默认SOP"""
        return SOPDefinition(
            name="默认研究分析流程",
            description="研究 -> 分析 -> 审核",
            nodes=[
                SOPNode(
                    id="research",
                    name="信息研究",
                    agent_type="researcher",
                    task_template=task,
                    dependencies=[],
                    review_required=True
                ),
                SOPNode(
                    id="analysis",
                    name="数据分析",
                    agent_type="analyst",
                    task_template="基于研究结果进行数据分析和可视化: {{results.research}}",
                    dependencies=["research"],
                    review_required=True
                ),
                SOPNode(
                    id="final_review",
                    name="最终审核",
                    agent_type="critic",
                    task_template="综合审核研究和分析结果",
                    dependencies=["research", "analysis"],
                    review_required=False
                )
            ],
            final_output_node="final_review"
        )

    async def _execute_sop(
        self,
        sop: SOPDefinition,
        original_task: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行SOP

        Args:
            sop: SOP定义
            original_task: 原始任务
            context: 上下文

        Returns:
            执行结果
        """
        logger.info(f"[{self.name}] 开始执行SOP: {sop.name}")

        # 清空缓存
        self.node_results.clear()
        self.execution_logs.clear()

        # 按拓扑顺序执行节点
        executed = set()
        pending = {node.id: node for node in sop.nodes}

        while pending:
            # 找到所有依赖已满足的节点
            ready = [
                node_id for node_id, node in pending.items()
                if all(dep in executed for dep in node.dependencies)
            ]

            if not ready:
                raise RuntimeError("检测到循环依赖或无法执行的节点")

            # 真正的并行执行：使用 asyncio.gather
            logger.info(f"[{self.name}] 并行执行 {len(ready)} 个节点: {ready}")

            async def execute_and_track(node_id: str):
                """执行节点并返回结果元组"""
                node = pending[node_id]
                try:
                    result = await self._execute_node(node, original_task, context)
                    return (node_id, result, None)
                except Exception as e:
                    return (node_id, None, e)

            # 使用 asyncio.gather 实现真正的并行执行
            results = await asyncio.gather(
                *[execute_and_track(node_id) for node_id in ready],
                return_exceptions=False
            )

            # 处理结果
            for node_id, result, error in results:
                if error:
                    logger.error(f"[{self.name}] 节点 {node_id} 执行失败: {str(error)}")
                    raise error
                self.node_results[node_id] = result
                executed.add(node_id)
                del pending[node_id]
                logger.info(f"[{self.name}] 节点 {node_id} 执行完成")

        # 返回最终结果
        final_result = self.node_results.get(sop.final_output_node)

        return {
            "final_output": final_result,
            "all_results": self.node_results,
            "sop_name": sop.name
        }

    async def _execute_node(
        self,
        node: SOPNode,
        original_task: str,
        context: Dict[str, Any]
    ) -> Any:
        """
        执行单个节点

        Args:
            node: SOP节点
            original_task: 原始任务
            context: 上下文

        Returns:
            节点执行结果
        """
        print(log_fmt.sop_node_start(node.id, node.name, node.agent_type))

        # 创建执行日志
        log = ExecutionLog(
            node_id=node.id,
            status=TaskStatus.RUNNING,
            start_time=datetime.now().isoformat()
        )
        self.execution_logs.append(log)

        # 渲染任务模板
        task_text = self._render_template(node.task_template, original_task)
        logger.debug(f"[{self.name}] 节点 {node.id} 任务模板渲染结果: {task_text[:200]}...")

        # 获取智能体
        agent = self.agents.get(node.agent_type)
        if not agent:
            raise ValueError(f"未知的智能体类型: {node.agent_type}")

        # 为 Critic 节点准备 content（从依赖节点获取结果）
        if node.agent_type == "critic" and "content" not in context:
            # 收集所有依赖节点的结果作为待审核内容
            dep_contents = []
            for dep_id in node.dependencies:
                if dep_id in self.node_results:
                    dep_result = self.node_results[dep_id]
                    if hasattr(dep_result, "summary"):
                        dep_contents.append(f"[{dep_id}]: {dep_result.summary}")
                    elif hasattr(dep_result, "output"):
                        dep_contents.append(f"[{dep_id}]: {str(dep_result.output)[:500]}")
                    else:
                        dep_contents.append(f"[{dep_id}]: {str(dep_result)[:500]}")

            if dep_contents:
                context["content"] = "\n\n".join(dep_contents)
                context["content_type"] = "general"
                context["original_task"] = original_task
                logger.info(f"[{self.name}] 为 Critic 节点 {node.id} 构建 content, 来源: {node.dependencies}")
            else:
                logger.warning(f"[{self.name}] Critic 节点 {node.id} 无依赖结果可审核")

        # 执行任务（带重试和审核）
        for retry in range(node.max_retries + 1):
            log.retry_count = retry

            # 执行
            logger.debug(f"[{self.name}] 执行 {node.agent_type}.execute(), context keys: {list(context.keys())}")
            result = await agent.execute(task_text, context)

            if not result.success:
                logger.warning(f"[{self.name}] 节点 {node.id} 执行失败: {result.error}")
                if retry < node.max_retries:
                    continue
                log.status = TaskStatus.FAILED
                log.error = result.error
                log.end_time = datetime.now().isoformat()
                raise RuntimeError(f"节点 {node.id} 执行失败: {result.error}")

            # 如果需要审核
            if node.review_required and node.agent_type != "critic":
                log.status = TaskStatus.REVIEWING
                review_result = await self._review_node_output(
                    node, result.output, original_task
                )

                if review_result.decision == ReviewDecision.REJECT:
                    logger.warning(f"[{self.name}] 节点 {node.id} 审核未通过，需要重做")
                    if retry < node.max_retries:
                        log.status = TaskStatus.REVISION
                        # 将审核反馈加入上下文
                        context["review_feedback"] = {
                            "issues": review_result.issues,
                            "suggestions": review_result.suggestions
                        }
                        continue
                    log.status = TaskStatus.FAILED
                    log.error = "审核未通过"
                    log.end_time = datetime.now().isoformat()
                    raise RuntimeError(f"节点 {node.id} 审核未通过")

            # 成功
            log.status = TaskStatus.COMPLETED
            log.result = result.output
            log.end_time = datetime.now().isoformat()
            duration = self._calculate_duration(log)
            print(log_fmt.sop_node_complete(node.id, "completed", duration))
            return result.output

    async def _review_node_output(
        self,
        node: SOPNode,
        output: Any,
        original_task: str
    ) -> Any:
        """审核节点输出"""
        logger.info(f"[{self.name}] 审核节点输出: {node.id}")

        critic = self.agents["critic"]

        # 将输出转换为可审核的文本
        if hasattr(output, "summary"):
            content = output.summary
        elif hasattr(output, "output"):
            content = str(output.output)
        else:
            content = str(output)

        result = await critic.execute(
            task="审核内容",
            context={
                "content": content[:4000],
                "content_type": "research" if node.agent_type == "researcher" else "code",
                "original_task": original_task
            }
        )

        return result.output if result.success else None

    def _render_template(self, template: str, original_task: str) -> str:
        """渲染任务模板"""
        result = template.replace("{{input}}", original_task)

        # 替换节点结果引用
        import re
        pattern = r'\{\{results\.(\w+)\}\}'
        matches = re.findall(pattern, result)

        for node_id in matches:
            if node_id in self.node_results:
                node_result = self.node_results[node_id]
                if hasattr(node_result, "summary"):
                    replacement = node_result.summary
                else:
                    replacement = str(node_result)[:500]
                result = result.replace(f"{{{{results.{node_id}}}}}", replacement)

        return result

    def get_execution_summary(self) -> Dict[str, Any]:
        """获取执行摘要"""
        return {
            "total_nodes": len(self.execution_logs),
            "completed": sum(1 for log in self.execution_logs if log.status == TaskStatus.COMPLETED),
            "failed": sum(1 for log in self.execution_logs if log.status == TaskStatus.FAILED),
            "logs": [
                {
                    "node_id": log.node_id,
                    "status": log.status.value,
                    "retry_count": log.retry_count,
                    "duration": self._calculate_duration(log)
                }
                for log in self.execution_logs
            ]
        }

    def _calculate_duration(self, log: ExecutionLog) -> Optional[float]:
        """计算执行时长"""
        if log.end_time and log.start_time:
            from datetime import datetime
            start = datetime.fromisoformat(log.start_time)
            end = datetime.fromisoformat(log.end_time)
            return (end - start).total_seconds()
        return None

    def _summarize_result(self, result: Dict[str, Any]) -> str:
        """
        提取结果摘要用于记忆存储

        Args:
            result: 执行结果

        Returns:
            摘要文本
        """
        try:
            final_output = result.get("final_output")
            if hasattr(final_output, "summary"):
                return final_output.summary[:500]
            elif hasattr(final_output, "output"):
                return str(final_output.output)[:500]
            elif isinstance(final_output, dict):
                return json.dumps(final_output, ensure_ascii=False)[:500]
            else:
                return str(final_output)[:500]
        except:
            return f"任务完成: {result.get('sop_name', 'Unknown')}"


# 预定义的SOP模板
def get_market_research_sop(topic: str) -> SOPDefinition:
    """获取市场研究SOP"""
    return SOPDefinition(
        name="市场研究SOP",
        description="全面的市场研究流程",
        nodes=[
            SOPNode(
                id="research",
                name="市场调研",
                agent_type="researcher",
                task_template=f"对{topic}进行深度研究，收集市场规模、竞争格局、发展趋势等信息",
                dependencies=[],
                review_required=True
            ),
            SOPNode(
                id="analysis",
                name="数据分析",
                agent_type="analyst",
                task_template="基于研究结果创建市场分析图表，包括市场规模趋势图、竞争格局饼图等",
                dependencies=["research"],
                review_required=True
            ),
            SOPNode(
                id="final_review",
                name="报告审核",
                agent_type="critic",
                task_template="审核研究报告和分析图表的质量",
                dependencies=["research", "analysis"],
                review_required=False
            )
        ],
        final_output_node="analysis"
    )


# 测试代码
async def test_ceo():
    """测试CEO智能体"""
    logger.info("=" * 50)
    logger.info("[TEST] 开始测试CEOAgent")
    logger.info("=" * 50)

    agent = CEOAgent()

    # 测试使用预定义SOP
    print("\n=== 测试市场研究任务 ===")

    # 使用简单任务进行测试
    result = await agent.execute(
        task="分析2024年低空经济的市场发展情况",
        context={
            "sop": get_market_research_sop("低空经济"),
            "user_preferences": {"chart_color": "red"}
        }
    )

    if result.success:
        print(f"任务完成!")
        print(f"- 执行节点数: {result.metadata.get('nodes_executed')}")
        print(f"\n执行日志:")
        for log in result.metadata.get("execution_logs", []):
            print(f"  - {log['node']}: {log['status']}")

        # 打印执行摘要
        summary = agent.get_execution_summary()
        print(f"\n执行摘要:")
        print(f"  - 总节点: {summary['total_nodes']}")
        print(f"  - 完成: {summary['completed']}")
        print(f"  - 失败: {summary['failed']}")
    else:
        print(f"任务失败: {result.error}")

    logger.info("[TEST] CEOAgent测试完成")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_ceo())
