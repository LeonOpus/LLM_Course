"""
Analyst Agent (数据分析师智能体)
负责数据分析，直接返回文字结论
"""
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
import json
import sys
sys.path.append(str(__file__).rsplit('/', 4)[0])

from core.agents.base import BaseAgent, TaskResult, AgentState
from core.tools.llm import LLMService

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """分析结果"""
    summary: str          # 分析摘要
    key_findings: list    # 关键发现
    conclusion: str       # 结论


class AnalystAgent(BaseAgent):
    """
    数据分析师智能体
    - 分析数据并生成文字结论
    - 不执行代码，直接用 LLM 分析
    """

    def __init__(
        self,
        name: str = "Analyst",
        llm_service: Optional[LLMService] = None
    ):
        super().__init__(
            name=name,
            role="数据分析师 - 负责数据分析和洞察",
            llm_service=llm_service
        )
        logger.info(f"[{self.name}] 数据分析师智能体初始化完成")

    def _build_system_prompt(self) -> str:
        return """你是一位专业的数据分析师，负责分析数据并给出洞察。

你的核心能力：
1. 数据解读：理解数据的含义和趋势
2. 洞察提取：从数据中发现关键信息
3. 结论总结：给出清晰的分析结论

输出要求：
- 使用中文
- 结论要有数据支撑
- 突出关键发现
"""

    async def execute(self, task: str, context: Optional[Dict[str, Any]] = None) -> TaskResult:
        """
        执行数据分析任务

        Args:
            task: 分析任务描述
            context: 上下文信息（可包含 data, preferences, review_feedback 等）

        Returns:
            包含分析结果的 TaskResult
        """
        import time
        start_time = time.time()

        self.state = AgentState.EXECUTING
        logger.info(f"[{self.name}] 开始分析任务: {task}")

        context = context or {}

        try:
            # 构建分析提示
            analysis = await self._analyze_data(task, context)

            self.state = AgentState.COMPLETED
            execution_time = time.time() - start_time

            logger.info(f"[{self.name}] 分析完成, 耗时: {execution_time:.2f}s")

            return TaskResult(
                success=True,
                output=analysis,
                metadata={
                    "task": task,
                    "has_data": bool(context.get("data"))
                },
                execution_time=execution_time
            )

        except Exception as e:
            self.state = AgentState.ERROR
            logger.error(f"[{self.name}] 分析失败: {str(e)}")
            return TaskResult(
                success=False,
                output=None,
                error=str(e),
                execution_time=time.time() - start_time
            )

    async def _analyze_data(self, task: str, context: Dict[str, Any]) -> AnalysisResult:
        """
        使用 LLM 分析数据

        Args:
            task: 分析任务
            context: 上下文

        Returns:
            AnalysisResult
        """
        logger.info(f"[{self.name}] 正在分析数据...")

        # 构建提示
        prompt_parts = [f"请对以下任务进行数据分析：\n\n任务: {task}"]

        # 添加数据
        if context.get("data"):
            prompt_parts.append(f"\n数据:\n{json.dumps(context['data'], ensure_ascii=False, indent=2)}")

        # 添加用户偏好
        if context.get("preferences"):
            prompt_parts.append(f"\n用户偏好: {json.dumps(context['preferences'], ensure_ascii=False)}")

        # 添加审核反馈（如果有）
        if context.get("review_feedback"):
            feedback = context["review_feedback"]
            prompt_parts.append(f"\n请注意之前的审核反馈:")
            for issue in feedback.get("issues", []):
                prompt_parts.append(f"- 问题: {issue}")
            for suggestion in feedback.get("suggestions", []):
                prompt_parts.append(f"- 建议: {suggestion}")

        prompt_parts.append("""
请按以下格式输出分析结果：

## 分析摘要
（一段话概述分析结果）

## 关键发现
1. （发现1）
2. （发现2）
3. （发现3）

## 结论
（基于数据的结论和建议）
""")

        prompt = "\n".join(prompt_parts)

        # 调用 LLM
        response = await self.llm.achat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        logger.info(f"[{self.name}] 分析完成, 结果长度: {len(response)}")

        # 解析结果
        return self._parse_analysis(response)

    def _parse_analysis(self, response: str) -> AnalysisResult:
        """解析 LLM 的分析结果"""
        # 简单解析，提取各部分
        summary = ""
        key_findings = []
        conclusion = ""

        lines = response.split("\n")
        current_section = None

        for line in lines:
            line = line.strip()
            if "分析摘要" in line or "摘要" in line:
                current_section = "summary"
            elif "关键发现" in line or "发现" in line:
                current_section = "findings"
            elif "结论" in line:
                current_section = "conclusion"
            elif line:
                if current_section == "summary":
                    summary += line + " "
                elif current_section == "findings":
                    if line.startswith(("1.", "2.", "3.", "4.", "5.", "-", "•")):
                        key_findings.append(line.lstrip("0123456789.-•） "))
                elif current_section == "conclusion":
                    conclusion += line + " "

        # 如果解析失败，使用整个响应作为摘要
        if not summary and not conclusion:
            summary = response[:500]
            conclusion = response

        return AnalysisResult(
            summary=summary.strip() or "分析完成",
            key_findings=key_findings or ["详见分析结果"],
            conclusion=conclusion.strip() or response
        )


# 测试代码
async def test_analyst():
    """测试数据分析师智能体"""
    logger.info("=" * 50)
    logger.info("[TEST] 开始测试 AnalystAgent")
    logger.info("=" * 50)

    agent = AnalystAgent()

    # 测试数据分析任务
    print("\n=== 测试数据分析任务 ===")
    result = await agent.execute(
        task="分析低空经济各领域的市场规模和发展潜力",
        context={
            "data": {
                "领域": ["无人机物流", "通用航空", "低空旅游", "应急救援", "城市空中交通"],
                "市场规模(亿元)": [120, 450, 85, 65, 200],
                "增长率(%)": [35, 12, 28, 18, 45]
            }
        }
    )

    if result.success:
        analysis = result.output
        print(f"\n分析完成!")
        print(f"\n📊 摘要: {analysis.summary}")
        print(f"\n🔍 关键发现:")
        for i, finding in enumerate(analysis.key_findings, 1):
            print(f"   {i}. {finding}")
        print(f"\n💡 结论: {analysis.conclusion[:300]}...")
    else:
        print(f"分析失败: {result.error}")

    logger.info("[TEST] AnalystAgent 测试完成")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_analyst())
