"""
Critic Agent (审核员智能体)
负责对输出结果进行Fact Check和质量评分
"""
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import json
import sys
sys.path.append(str(__file__).rsplit('/', 4)[0])

from core.agents.base import BaseAgent, TaskResult, AgentState
from core.tools.llm import LLMService

logger = logging.getLogger(__name__)


class ReviewDecision(Enum):
    """审核决定"""
    PASS = "pass"         # 通过
    REVISE = "revise"     # 需修改
    REJECT = "reject"     # 拒绝


@dataclass
class ReviewResult:
    """审核结果"""
    decision: ReviewDecision
    overall_score: float  # 0-100
    dimension_scores: Dict[str, float]  # 各维度得分
    issues: List[str]  # 发现的问题
    suggestions: List[str]  # 改进建议
    fact_check_results: List[Dict[str, Any]]  # 事实核查结果
    summary: str  # 审核总结


class CriticAgent(BaseAgent):
    """
    审核员智能体
    - 对研究内容进行Fact Check
    - 对代码质量进行评分
    - 对输出内容进行多维度评估
    - 给出通过/修改/拒绝的决定
    """

    def __init__(
        self,
        name: str = "Critic",
        llm_service: Optional[LLMService] = None,
        pass_threshold: float = 70.0,
        revise_threshold: float = 50.0
    ):
        super().__init__(
            name=name,
            role="审核员 - 负责质量评估和事实核查",
            llm_service=llm_service
        )
        self.pass_threshold = pass_threshold
        self.revise_threshold = revise_threshold

        logger.info(f"[{self.name}] 审核员智能体初始化完成")
        logger.info(f"[{self.name}] 通过阈值: {pass_threshold}, 修改阈值: {revise_threshold}")

    def _build_system_prompt(self) -> str:
        return """你是一位严谨的审核员智能体，负责对内容进行质量评估和事实核查。

你的核心职责：
1. 事实核查 (Fact Check)：验证信息的准确性和可靠性
2. 质量评分：从多个维度评估内容质量
3. 问题识别：发现潜在的错误、遗漏或改进空间
4. 提供建议：给出具体可操作的改进建议

评估维度：
- 准确性 (Accuracy): 信息是否准确、有无错误
- 完整性 (Completeness): 是否涵盖了任务的所有方面
- 相关性 (Relevance): 内容是否与任务目标相关
- 清晰性 (Clarity): 表达是否清晰、易于理解
- 可信度 (Credibility): 信息来源是否可靠

评分标准：
- 90-100: 优秀，直接通过
- 70-89: 良好，通过但可优化
- 50-69: 及格，需要修改后重新提交
- 0-49: 不及格，需要重做

原则：
- 保持客观公正
- 提供建设性反馈
- 明确指出问题所在
"""

    async def execute(self, task: str, context: Optional[Dict[str, Any]] = None) -> TaskResult:
        """
        执行审核任务

        Args:
            task: 审核任务描述
            context: 上下文信息，应包含:
                - content: 待审核的内容
                - content_type: 内容类型 (research/code/report)
                - original_task: 原始任务描述

        Returns:
            包含审核结果的TaskResult
        """
        import time
        start_time = time.time()

        self.state = AgentState.EXECUTING
        logger.info(f"[{self.name}] 开始审核任务")

        context = context or {}
        content = context.get("content", "")
        content_type = context.get("content_type", "general")
        original_task = context.get("original_task", task)

        if not content:
            return TaskResult(
                success=False,
                output=None,
                error="没有提供待审核的内容",
                execution_time=time.time() - start_time
            )

        try:
            # 执行审核
            review_result = await self._review_content(
                content=content,
                content_type=content_type,
                original_task=original_task
            )

            self.state = AgentState.COMPLETED
            execution_time = time.time() - start_time

            logger.info(f"[{self.name}] 审核完成: {review_result.decision.value}, 得分: {review_result.overall_score:.1f}")

            return TaskResult(
                success=True,
                output=review_result,
                metadata={
                    "decision": review_result.decision.value,
                    "score": review_result.overall_score,
                    "issues_count": len(review_result.issues),
                    "suggestions_count": len(review_result.suggestions)
                },
                execution_time=execution_time
            )

        except Exception as e:
            self.state = AgentState.ERROR
            logger.error(f"[{self.name}] 审核失败: {str(e)}")
            return TaskResult(
                success=False,
                output=None,
                error=str(e),
                execution_time=time.time() - start_time
            )

    async def _review_content(
        self,
        content: str,
        content_type: str,
        original_task: str
    ) -> ReviewResult:
        """
        审核内容

        Args:
            content: 待审核内容
            content_type: 内容类型
            original_task: 原始任务

        Returns:
            审核结果
        """
        logger.info(f"[{self.name}] 审核内容类型: {content_type}")

        # 根据内容类型选择评估维度
        if content_type == "research":
            dimensions = ["准确性", "完整性", "相关性", "引用质量", "分析深度"]
        elif content_type == "code":
            dimensions = ["正确性", "可读性", "效率", "错误处理", "文档完整性"]
        else:
            dimensions = ["准确性", "完整性", "相关性", "清晰性", "可信度"]

        # 构建审核提示
        prompt = f"""请对以下内容进行全面审核。

原始任务: {original_task}

待审核内容:
---
{content[:4000]}
---

评估维度: {', '.join(dimensions)}

请以JSON格式返回审核结果:
{{
    "overall_score": 0-100的整体得分,
    "dimension_scores": {{
        "维度名": 得分,
        ...
    }},
    "issues": [
        "具体问题描述（说明哪里有问题）"
    ],
    "suggestions": [
        "具体可执行的改进建议（说明应该怎么做）"
    ],
    "fact_check_results": [
        {{
            "claim": "声明内容",
            "verified": true/false,
            "note": "核查说明"
        }}
    ],
    "summary": "审核总结（100字以内）"
}}

重要：
- issues 必须具体指出问题所在，如"缺少XX方面的数据"而非"数据不完整"
- suggestions 必须给出可执行的建议，如"补充搜索XX相关信息"而非"需要更多信息"

请严格按照JSON格式返回。"""

        try:
            response = await self.llm.achat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )

            result = self.llm.parse_json_response(response)

            # 计算决定
            overall_score = float(result.get("overall_score", 0))
            if overall_score >= self.pass_threshold:
                decision = ReviewDecision.PASS
            elif overall_score >= self.revise_threshold:
                decision = ReviewDecision.REVISE
            else:
                decision = ReviewDecision.REJECT

            review_result = ReviewResult(
                decision=decision,
                overall_score=overall_score,
                dimension_scores=result.get("dimension_scores", {}),
                issues=result.get("issues", []),
                suggestions=result.get("suggestions", []),
                fact_check_results=result.get("fact_check_results", []),
                summary=result.get("summary", "")
            )

            logger.info(f"[{self.name}] 审核完成: {decision.value}, 分数: {overall_score:.1f}")
            logger.info(f"[{self.name}] 发现 {len(review_result.issues)} 个问题")

            return review_result

        except Exception as e:
            logger.error(f"[{self.name}] 审核解析失败: {str(e)}")
            # 返回默认结果
            return ReviewResult(
                decision=ReviewDecision.REVISE,
                overall_score=60.0,
                dimension_scores={d: 60.0 for d in dimensions},
                issues=["审核过程出现错误"],
                suggestions=["请重新提交审核"],
                fact_check_results=[],
                summary=f"审核失败: {str(e)}"
            )

    async def review_research(
        self,
        research_content: str,
        sources: List[Dict[str, str]],
        original_query: str
    ) -> ReviewResult:
        """
        审核研究内容

        Args:
            research_content: 研究内容
            sources: 信息来源列表
            original_query: 原始查询

        Returns:
            审核结果
        """
        logger.info(f"[{self.name}] 审核研究内容, 来源数: {len(sources)}")

        # 构建包含来源的内容
        source_text = "\n".join([
            f"[{s.get('id', i)}] {s.get('title', 'Unknown')} - {s.get('url', 'N/A')}"
            for i, s in enumerate(sources, 1)
        ])

        content = f"""研究内容:
{research_content}

引用来源:
{source_text}"""

        result = await self.execute(
            task="审核研究内容",
            context={
                "content": content,
                "content_type": "research",
                "original_task": original_query
            }
        )

        return result.output if result.success else ReviewResult(
            decision=ReviewDecision.REJECT,
            overall_score=0,
            dimension_scores={},
            issues=[result.error],
            suggestions=["请检查审核服务"],
            fact_check_results=[],
            summary="审核失败"
        )

    async def review_code(
        self,
        code: str,
        execution_result: str,
        task_description: str
    ) -> ReviewResult:
        """
        审核代码

        Args:
            code: 代码内容
            execution_result: 执行结果
            task_description: 任务描述

        Returns:
            审核结果
        """
        logger.info(f"[{self.name}] 审核代码, 长度: {len(code)}")

        content = f"""代码:
```python
{code}
```

执行结果:
{execution_result}"""

        result = await self.execute(
            task="审核代码",
            context={
                "content": content,
                "content_type": "code",
                "original_task": task_description
            }
        )

        return result.output if result.success else ReviewResult(
            decision=ReviewDecision.REJECT,
            overall_score=0,
            dimension_scores={},
            issues=[result.error],
            suggestions=["请检查审核服务"],
            fact_check_results=[],
            summary="审核失败"
        )

    def format_review_report(self, review: ReviewResult) -> str:
        """
        格式化审核报告

        Args:
            review: 审核结果

        Returns:
            Markdown格式的报告
        """
        decision_emoji = {
            ReviewDecision.PASS: "✅",
            ReviewDecision.REVISE: "⚠️",
            ReviewDecision.REJECT: "❌"
        }

        md = f"""# 审核报告

## 审核决定: {decision_emoji.get(review.decision, '')} {review.decision.value.upper()}

**综合得分: {review.overall_score:.1f}/100**

## 各维度评分
"""
        for dim, score in review.dimension_scores.items():
            bar = "█" * int(score / 10) + "░" * (10 - int(score / 10))
            md += f"- {dim}: {bar} {score:.1f}\n"

        if review.issues:
            md += "\n## 发现的问题\n"
            for issue in review.issues:
                md += f"- ⚠️ {issue}\n"

        if review.suggestions:
            md += "\n## 改进建议\n"
            for suggestion in review.suggestions:
                md += f"- 💡 {suggestion}\n"

        if review.fact_check_results:
            md += "\n## 事实核查\n"
            for fc in review.fact_check_results:
                status = "✓" if fc.get("verified") else "✗"
                md += f"- [{status}] {fc.get('claim', 'N/A')}\n"
                if fc.get("note"):
                    md += f"  - 说明: {fc['note']}\n"

        md += f"\n## 总结\n{review.summary}"

        return md


# 测试代码
async def test_critic():
    """测试审核员智能体"""
    logger.info("=" * 50)
    logger.info("[TEST] 开始测试CriticAgent")
    logger.info("=" * 50)

    agent = CriticAgent()

    # 测试研究内容审核
    print("\n=== 测试研究内容审核 ===")
    research_content = """
低空经济是指以各种有人驾驶和无人驾驶航空器的低空飞行活动为牵引的综合性经济形态。
根据2024年的政策文件，中国将大力发展低空经济，预计到2025年市场规模将达到1.5万亿元[1]。

主要应用领域包括：
1. 无人机物流配送 - 京东、美团等企业已开展试点[2]
2. 低空旅游观光 - 多个景区推出直升机游览服务
3. 应急救援 - 无人机在灾害救援中发挥重要作用[3]

面临的挑战包括空域管理、安全监管和基础设施建设等。
"""

    sources = [
        {"id": 1, "title": "低空经济发展规划", "url": "https://example.com/policy"},
        {"id": 2, "title": "无人机物流现状报告", "url": "https://example.com/logistics"},
        {"id": 3, "title": "应急救援无人机应用", "url": "https://example.com/rescue"}
    ]

    result = await agent.review_research(
        research_content=research_content,
        sources=sources,
        original_query="介绍低空经济的发展现状"
    )

    print(f"审核决定: {result.decision.value}")
    print(f"综合得分: {result.overall_score:.1f}")
    print(f"发现问题: {len(result.issues)}个")

    # 打印格式化报告
    print("\n=== 审核报告 ===")
    report = agent.format_review_report(result)
    print(report)

    # 测试代码审核
    print("\n=== 测试代码审核 ===")
    code = """
import matplotlib.pyplot as plt
import numpy as np

# 创建数据
categories = ['无人机物流', '通用航空', '低空旅游']
values = [120, 450, 85]

# 创建柱状图
plt.figure(figsize=(10, 6))
plt.bar(categories, values, color='steelblue')
plt.title('低空经济各领域市场规模')
plt.ylabel('市场规模（亿元）')
plt.savefig('/tmp/chart.png')
print('图表已保存')
"""

    result2 = await agent.review_code(
        code=code,
        execution_result="图表已保存",
        task_description="创建低空经济市场规模柱状图"
    )

    print(f"代码审核结果: {result2.decision.value}, 得分: {result2.overall_score:.1f}")

    logger.info("[TEST] CriticAgent测试完成")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_critic())
