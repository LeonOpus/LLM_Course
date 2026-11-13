"""
配置文件 - Deep Research Agent 的全局配置

基于高级研究智能体设计优化：
- Lead Agent: 查询类型分类、动态子智能体调度
- SubAgent: OODA循环、研究预算、来源质量评估
"""

import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# ==================== LLM 配置 ====================
LLM_CONFIG = {
    "api_key": os.getenv("DASHSCOPE_API_KEY"),
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "model": "qwen-plus",  # 默认模型
    "model_smart": "qwen-max",  # 用于复杂推理的模型
    "model_fast": "qwen-turbo",  # 用于简单任务的快速模型
    "max_tokens": 8192,
    "temperature": 0.7,
}

# ==================== 搜索 API 配置 ====================
SEARCH_CONFIG = {
    "api_key": os.getenv("BOCHA_API_KEY"),
    "base_url": "https://api.bocha.cn/v1/web-search",
    "default_count": 10,  # 默认返回结果数
    "summary": True,  # 是否返回摘要
}

# ==================== Agent 配置 ====================
AGENT_CONFIG = {
    # ========== Orchestrator (Lead Agent) 配置 ==========
    "max_workers": 6,  # 最大并行 Worker 数
    "max_search_depth": 3,  # 最大搜索深度（迭代次数）
    "timeout_per_worker": 120,  # 单个 Worker 超时时间（秒）

    # ========== 查询类型与子智能体数量配置 ==========
    # 子智能体数量指南（根据查询复杂度自动调整）
    "worker_count_guidelines": {
        "simple": {"min": 1, "max": 2},      # 简单/直接查询
        "standard": {"min": 2, "max": 3},     # 标准复杂度查询
        "medium": {"min": 3, "max": 5},       # 中等复杂度查询
        "high": {"min": 5, "max": 10},        # 高复杂度查询
    },

    # ========== 研究任务配置 ==========
    "min_sources_per_topic": 3,  # 每个主题最少信息源数
    "max_sources_per_topic": 10,  # 每个主题最多信息源数

    # ========== 报告配置 ==========
    "report_language": "zh-CN",  # 报告语言
    "include_sources": True,  # 是否包含来源引用
    "include_summary": True,  # 是否包含执行摘要

    # ========== 迭代优化配置 ==========
    "min_iterations": 2,  # 最少迭代次数（即使质量通过也至少迭代2次）
    "max_iterations": 5,  # 最大迭代次数
    "quality_threshold": 80,  # 质量通过阈值（0-100）

    # ========== 智能终止配置 ==========
    "enable_diminishing_returns_check": True,  # 启用收益递减检测
    "diminishing_returns_threshold": 3,  # 连续 N 次提升小于 5 分则触发
    "early_termination_min_score": 75,  # 提前终止的最低分数要求

    # ========== SubAgent (Worker) 配置 ==========
    # OODA 循环配置
    "worker_max_ooda_cycles": 3,  # 每个 Worker 最大 OODA 循环次数

    # 研究预算配置（根据任务复杂度自动调整）
    "research_budget": {
        "simple": {"max_queries": 3, "max_cycles": 1},
        "medium": {"max_queries": 5, "max_cycles": 2},
        "complex": {"max_queries": 8, "max_cycles": 3},
    },

    # 来源质量评估配置
    "source_quality": {
        "high_quality_domains": [
            ".gov", ".edu", ".org",
            "reuters", "bloomberg", "wsj", "nytimes",
            "nature", "science", "arxiv",
            "statista", "mckinsey", "gartner", "idc",
        ],
        "low_quality_indicators": [
            "forum", "reddit", "quora", "yahoo answers",
            "wiki", "blog", "medium.com",
        ],
        "speculative_language": [
            "可能", "也许", "据说", "传闻", "预计",
            "may", "might", "possibly", "reportedly",
        ],
    },
}

# ==================== 日志配置 ====================
LOG_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    "show_worker_details": True,  # 是否显示 Worker 详细信息
    "show_search_results": False,  # 是否显示搜索结果详情
    "show_ooda_cycles": True,  # 是否显示 OODA 循环详情
    "show_source_quality": True,  # 是否显示来源质量评估
}

# ==================== 输出配置 ====================
OUTPUT_CONFIG = {
    "save_intermediate": True,  # 是否保存中间结果
    "output_dir": "./research_output",  # 输出目录
    "formats": ["markdown", "json"],  # 输出格式
    "include_ooda_logs": True,  # 是否在输出中包含 OODA 循环日志
    "include_source_assessment": True,  # 是否在输出中包含来源质量评估
}
