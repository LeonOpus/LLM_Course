"""
Deep Research - 基于 Orchestrator-Workers 架构的深度研究智能体

这是一个多智能体协作系统，用于自动化深度研究任务：
- Orchestrator: 负责任务拆解、分发、汇总和质量控制
- Workers: 并行执行搜索、分析、写作等子任务

使用方法:
    from deep_research import DeepResearchAgent

    agent = DeepResearchAgent()
    report = agent.research("2024年电动汽车市场分析报告")
"""

from .main import DeepResearchAgent

__version__ = "1.0.0"
__all__ = ["DeepResearchAgent"]
