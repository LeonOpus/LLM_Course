"""
Researcher Agent (研究员智能体)
负责Deep Research，具备迭代搜索和信源引用能力
"""
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import json
import sys
sys.path.append(str(__file__).rsplit('/', 4)[0])

from core.agents.base import BaseAgent, TaskResult, AgentState
from core.tools.web_search import WebSearchTool, SearchResult
from core.tools.llm import LLMService

logger = logging.getLogger(__name__)


@dataclass
class ResearchReport:
    """研究报告"""
    query: str
    summary: str
    key_findings: List[str]
    sources: List[Dict[str, str]]
    raw_results: List[SearchResult]
    iterations: int


class ResearcherAgent(BaseAgent):
    """
    研究员智能体
    - 支持迭代搜索 (Iterative Search)
    - 强制信源引用 (Source Citation)
    - 信息充足度评估
    """

    def __init__(
        self,
        name: str = "Researcher",
        llm_service: Optional[LLMService] = None,
        web_search: Optional[WebSearchTool] = None
    ):
        super().__init__(
            name=name,
            role="研究员 - 负责深度搜索和信息收集",
            llm_service=llm_service
        )
        self.web_search = web_search or WebSearchTool()
        logger.info(f"[{self.name}] 研究员智能体初始化完成")

    def _build_system_prompt(self) -> str:
        return """你是一位专业的研究员智能体，负责进行深度信息搜索和分析。

核心能力：
1. 迭代搜索：根据初步结果自动生成新搜索词
2. 信源引用：所有信息必须标注来源
3. 信息综合：整合多来源信息

工作原则：
- 客观中立，不添加臆测
- 优先权威来源（官方、知名媒体、研究机构）
- 交叉验证信息
- 区分事实与观点

输出要求：
- 必须包含来源引用 [1], [2]
- 每个关键发现都要有引用支撑
- 来源URL必须完整列出
"""

    async def execute(self, task: str, context: Optional[Dict[str, Any]] = None) -> TaskResult:
        """
        执行研究任务

        Args:
            task: 研究主题或问题
            context: 上下文信息（可包含max_iterations, results_per_search, review_feedback等参数）

        Returns:
            包含研究报告的TaskResult
        """
        import time
        start_time = time.time()

        self.state = AgentState.EXECUTING
        logger.info(f"[{self.name}] 开始研究任务: {task}")

        context = context or {}
        max_iterations = context.get("max_iterations", 3)
        results_per_search = context.get("results_per_search", 5)

        # 检查是否有审核反馈（重试时会有）
        review_feedback = context.get("review_feedback")
        if review_feedback:
            logger.info(f"[{self.name}] 检测到审核反馈，将调整搜索策略")

        try:
            # 执行迭代搜索
            report = await self._iterative_research(
                query=task,
                max_iterations=max_iterations,
                results_per_search=results_per_search,
                review_feedback=review_feedback
            )

            self.state = AgentState.COMPLETED
            execution_time = time.time() - start_time

            logger.info(f"[{self.name}] 研究完成, 耗时: {execution_time:.2f}s, 迭代次数: {report.iterations}")

            return TaskResult(
                success=True,
                output=report,
                metadata={
                    "iterations": report.iterations,
                    "source_count": len(report.sources),
                    "findings_count": len(report.key_findings)
                },
                execution_time=execution_time
            )

        except Exception as e:
            self.state = AgentState.ERROR
            logger.error(f"[{self.name}] 研究失败: {str(e)}")
            return TaskResult(
                success=False,
                output=None,
                error=str(e),
                execution_time=time.time() - start_time
            )

    async def _iterative_research(
        self,
        query: str,
        max_iterations: int = 3,
        results_per_search: int = 5,
        review_feedback: Optional[Dict[str, Any]] = None
    ) -> ResearchReport:
        """
        迭代式研究

        Args:
            query: 初始查询
            max_iterations: 最大迭代次数
            results_per_search: 每次搜索结果数
            review_feedback: 审核反馈（重试时使用）

        Returns:
            研究报告
        """
        all_results: List[SearchResult] = []
        seen_urls = set()
        current_query = query
        iteration = 0

        # 如果有审核反馈，根据反馈调整搜索策略
        if review_feedback:
            refined_query = await self._refine_query_from_feedback(query, review_feedback)
            if refined_query:
                current_query = refined_query
                logger.info(f"[{self.name}] 根据反馈调整搜索词: '{current_query}'")

        for i in range(max_iterations):
            iteration = i + 1
            logger.info(f"[{self.name}] 迭代 {iteration}/{max_iterations}: 搜索 '{current_query}'")

            # 执行搜索
            results = await self.web_search.search(
                query=current_query,
                count=results_per_search,
                summary=True
            )

            # 去重
            new_results = []
            for r in results:
                if r.url not in seen_urls:
                    seen_urls.add(r.url)
                    new_results.append(r)
                    all_results.append(r)

            logger.info(f"[{self.name}] 迭代 {iteration} 获取 {len(new_results)} 条新结果")

            if not new_results:
                logger.info(f"[{self.name}] 没有新结果，停止迭代")
                break

            # 评估信息充足度
            if i < max_iterations - 1:
                is_sufficient, new_query = await self._evaluate_and_refine(
                    original_query=query,
                    current_query=current_query,
                    results=new_results
                )

                if is_sufficient:
                    logger.info(f"[{self.name}] 信息充足，停止迭代")
                    break

                if new_query and new_query != current_query:
                    current_query = new_query
                    logger.info(f"[{self.name}] 生成新搜索词: '{new_query}'")
                else:
                    break

        # 生成研究报告
        report = await self._generate_report(query, all_results, iteration)

        return report

    async def _evaluate_and_refine(
        self,
        original_query: str,
        current_query: str,
        results: List[SearchResult]
    ) -> tuple:
        """
        评估信息充足度并生成新搜索词

        Returns:
            (is_sufficient, new_query)
        """
        logger.info(f"[{self.name}] 评估信息充足度...")

        # 构建上下文
        context = "\n".join([
            f"- 标题: {r.title}\n  摘要: {r.snippet[:150]}..."
            for r in results[:5]
        ])

        prompt = f"""作为研究员，评估以下搜索结果对于回答问题的充足度。

原始问题: {original_query}
当前搜索词: {current_query}

搜索结果:
{context}

请以JSON格式回答:
{{
    "is_sufficient": true/false,  // 信息是否足够回答问题
    "missing_aspects": ["..."],  // 缺少的方面
    "new_query": "..."  // 如果信息不足，建议的新搜索词（留空如果充足）
}}"""

        try:
            response = await self.llm.achat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )

            result = self.llm.parse_json_response(response)

            is_sufficient = result.get("is_sufficient", False)
            new_query = result.get("new_query", "")

            logger.info(f"[{self.name}] 信息充足度: {is_sufficient}, 新搜索词: {new_query}")

            return is_sufficient, new_query

        except Exception as e:
            logger.warning(f"[{self.name}] 评估失败: {str(e)}, 继续使用当前结果")
            return True, ""

    async def _refine_query_from_feedback(
        self,
        original_query: str,
        feedback: Dict[str, Any]
    ) -> Optional[str]:
        """
        根据审核反馈调整搜索策略

        Args:
            original_query: 原始查询
            feedback: 审核反馈 (包含 issues 和 suggestions)

        Returns:
            调整后的搜索词，如果无需调整返回None
        """
        issues = feedback.get("issues", [])
        suggestions = feedback.get("suggestions", [])

        if not issues and not suggestions:
            return None

        prompt = f"""原始研究问题: {original_query}

审核发现的问题:
{chr(10).join(f'- {issue}' for issue in issues)}

改进建议:
{chr(10).join(f'- {s}' for s in suggestions)}

请根据以上反馈，生成一个更精准的搜索词来补充缺失的信息。
只返回搜索词本身，不要解释。"""

        try:
            response = await self.llm.achat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            refined = response.strip().strip('"\'')
            logger.info(f"[{self.name}] 根据反馈生成新搜索词: {refined}")
            return refined
        except Exception as e:
            logger.warning(f"[{self.name}] 生成新搜索词失败: {e}")
            return None

    async def _generate_report(
        self,
        query: str,
        results: List[SearchResult],
        iterations: int
    ) -> ResearchReport:
        """
        生成研究报告

        Args:
            query: 原始查询
            results: 所有搜索结果
            iterations: 迭代次数

        Returns:
            研究报告
        """
        logger.info(f"[{self.name}] 生成研究报告, 共 {len(results)} 条来源")

        # 构建带引用的内容
        sources_text = "\n".join([
            f"[{i+1}] {r.title}\n    URL: {r.url}\n    摘要: {r.summary or r.snippet}"
            for i, r in enumerate(results)
        ])

        prompt = f"""基于以下搜索结果，为问题生成一份结构化的研究报告。

问题: {query}

搜索结果（共{len(results)}条）:
{sources_text}

请生成JSON格式的报告:
{{
    "summary": "总结性回答（200-300字）",
    "key_findings": [
        "关键发现1 [引用编号]",
        "关键发现2 [引用编号]",
        ...
    ]
}}

要求:
1. 必须在关键发现中标注来源引用，如 [1], [2]
2. 综合多个来源的信息
3. 保持客观准确"""

        try:
            response = await self.llm.achat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )

            result = self.llm.parse_json_response(response)

            # 构建来源列表
            sources = [
                {"id": i+1, "title": r.title, "url": r.url}
                for i, r in enumerate(results)
            ]

            report = ResearchReport(
                query=query,
                summary=result.get("summary", ""),
                key_findings=result.get("key_findings", []),
                sources=sources,
                raw_results=results,
                iterations=iterations
            )

            logger.info(f"[{self.name}] 报告生成完成: {len(report.key_findings)} 条发现, {len(report.sources)} 个来源")

            return report

        except Exception as e:
            logger.error(f"[{self.name}] 生成报告失败: {str(e)}")
            # 返回基础报告
            return ResearchReport(
                query=query,
                summary=f"搜索到 {len(results)} 条相关结果",
                key_findings=[r.title for r in results[:5]],
                sources=[{"id": i+1, "title": r.title, "url": r.url} for i, r in enumerate(results)],
                raw_results=results,
                iterations=iterations
            )

    def format_report_markdown(self, report: ResearchReport) -> str:
        """
        将报告格式化为Markdown

        Args:
            report: 研究报告

        Returns:
            Markdown格式的报告
        """
        md = f"""# 研究报告: {report.query}

## 摘要
{report.summary}

## 关键发现
"""
        for finding in report.key_findings:
            md += f"- {finding}\n"

        md += "\n## 参考来源\n"
        for source in report.sources:
            md += f"[{source['id']}] [{source['title']}]({source['url']})\n"

        md += f"\n---\n*迭代次数: {report.iterations} | 来源数量: {len(report.sources)}*"

        return md


# 测试代码
async def test_researcher():
    """测试研究员智能体"""
    logger.info("=" * 50)
    logger.info("[TEST] 开始测试ResearcherAgent")
    logger.info("=" * 50)

    agent = ResearcherAgent()

    # 测试研究任务
    print("\n=== 执行研究任务 ===")
    result = await agent.execute(
        task="2024年低空经济政策和市场发展情况",
        context={"max_iterations": 2, "results_per_search": 3}
    )

    if result.success:
        report = result.output
        print(f"研究完成!")
        print(f"- 迭代次数: {report.iterations}")
        print(f"- 来源数量: {len(report.sources)}")
        print(f"- 关键发现数: {len(report.key_findings)}")
        print(f"\n摘要:\n{report.summary}")

        # 打印Markdown报告
        print("\n=== Markdown报告 ===")
        md = agent.format_report_markdown(report)
        print(md)
    else:
        print(f"研究失败: {result.error}")

    # 获取状态
    print("\n=== 智能体状态 ===")
    status = agent.get_status()
    print(f"状态: {status}")

    logger.info("[TEST] ResearcherAgent测试完成")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_researcher())
