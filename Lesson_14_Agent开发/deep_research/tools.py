"""
工具层 - 封装 LLM 调用、网络搜索等基础工具
"""

import json
import re
import time
import requests
from typing import Generator, Optional
from dataclasses import dataclass, field
from openai import OpenAI

from .config import LLM_CONFIG, SEARCH_CONFIG


# ==================== 数据结构 ====================

@dataclass
class SearchResult:
    """搜索结果数据结构"""
    title: str
    url: str
    snippet: str
    site_name: str = ""
    date: str = ""

    def to_context(self) -> str:
        """转换为上下文字符串"""
        return f"【{self.title}】\n来源: {self.site_name or self.url}\n日期: {self.date or '未知'}\n内容: {self.snippet}\n"


@dataclass
class SearchResponse:
    """搜索响应数据结构"""
    query: str
    results: list[SearchResult] = field(default_factory=list)
    total_matches: int = 0
    success: bool = True
    error_msg: str = ""


@dataclass
class LLMResponse:
    """LLM 响应数据结构"""
    content: str
    model: str
    usage: dict = field(default_factory=dict)
    success: bool = True
    error_msg: str = ""


# ==================== LLM 工具 ====================

class LLMClient:
    """LLM 客户端封装"""

    def __init__(self):
        self.client = OpenAI(
            api_key=LLM_CONFIG["api_key"],
            base_url=LLM_CONFIG["base_url"],
        )
        self.default_model = LLM_CONFIG["model"]

    def chat(
        self,
        prompt: str,
        system_prompt: str = "",
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """
        同步调用 LLM

        参数:
            prompt: 用户提示
            system_prompt: 系统提示
            model: 模型名称，默认使用配置中的模型
            temperature: 温度参数
            max_tokens: 最大生成token数

        返回:
            LLMResponse: LLM 响应对象
        """
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = self.client.chat.completions.create(
                model=model or self.default_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            return LLMResponse(
                content=response.choices[0].message.content,
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
                success=True,
            )
        except Exception as e:
            return LLMResponse(
                content="",
                model=model or self.default_model,
                success=False,
                error_msg=str(e),
            )

    def chat_stream(
        self,
        prompt: str,
        system_prompt: str = "",
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> Generator[str, None, None]:
        """
        流式调用 LLM

        参数:
            prompt: 用户提示
            system_prompt: 系统提示
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大生成token数

        返回:
            Generator: 生成器，逐步返回文本
        """
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = self.client.chat.completions.create(
                model=model or self.default_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                stream_options={"include_usage": True},
            )

            for chunk in response:
                if chunk.choices and len(chunk.choices) > 0:
                    delta_content = chunk.choices[0].delta.content
                    if delta_content:
                        yield delta_content
        except Exception as e:
            yield f"\n[错误: {str(e)}]"


# ==================== 搜索工具 ====================

class SearchClient:
    """网络搜索客户端封装"""

    def __init__(self):
        self.api_key = SEARCH_CONFIG["api_key"]
        self.base_url = SEARCH_CONFIG["base_url"]
        self.default_count = SEARCH_CONFIG["default_count"]
        self.summary = SEARCH_CONFIG["summary"]

    def search(
        self,
        query: str,
        count: int = None,
        freshness: str = None,
    ) -> SearchResponse:
        """
        执行网络搜索

        参数:
            query: 搜索查询
            count: 返回结果数量
            freshness: 时效性过滤 (day/week/month)

        返回:
            SearchResponse: 搜索响应对象
        """
        try:
            payload = {
                "query": query,
                "summary": self.summary,
                "count": count or self.default_count,
            }
            if freshness:
                payload["freshness"] = freshness

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=30,
            )

            data = response.json()

            if data.get("code") != 200:
                return SearchResponse(
                    query=query,
                    success=False,
                    error_msg=data.get("msg", "搜索失败"),
                )

            # 解析搜索结果
            web_pages = data.get("data", {}).get("webPages", {})
            results = []

            for item in web_pages.get("value", []):
                results.append(SearchResult(
                    title=item.get("name", ""),
                    url=item.get("url", ""),
                    snippet=item.get("snippet", ""),
                    site_name=item.get("siteName", ""),
                    date=item.get("dateLastCrawled", "")[:10] if item.get("dateLastCrawled") else "",
                ))

            return SearchResponse(
                query=query,
                results=results,
                total_matches=web_pages.get("totalEstimatedMatches", len(results)),
                success=True,
            )

        except requests.Timeout:
            return SearchResponse(
                query=query,
                success=False,
                error_msg="搜索请求超时",
            )
        except Exception as e:
            return SearchResponse(
                query=query,
                success=False,
                error_msg=str(e),
            )

    def multi_search(
        self,
        queries: list[str],
        count: int = None,
    ) -> list[SearchResponse]:
        """
        批量执行搜索（顺序执行，可扩展为并行）

        参数:
            queries: 搜索查询列表
            count: 每个查询的返回结果数量

        返回:
            list[SearchResponse]: 搜索响应列表
        """
        results = []
        for query in queries:
            result = self.search(query, count)
            results.append(result)
            time.sleep(0.5)  # 避免请求过快
        return results


# ==================== 辅助函数 ====================

def extract_xml(text: str, tag: str) -> str:
    """
    从文本中提取指定 XML 标签的内容

    参数:
        text: 包含 XML 的文本
        tag: 要提取的标签名

    返回:
        str: 标签内容，未找到则返回空字符串
    """
    match = re.search(f"<{tag}>(.*?)</{tag}>", text, re.DOTALL)
    return match.group(1).strip() if match else ""


def extract_json(text: str) -> dict:
    """
    从文本中提取 JSON 对象

    参数:
        text: 包含 JSON 的文本

    返回:
        dict: 解析后的 JSON 对象，失败返回空字典
    """
    # 尝试找到 JSON 代码块
    json_match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # 尝试直接解析
    try:
        # 找到第一个 { 和最后一个 }
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(text[start:end])
    except json.JSONDecodeError:
        pass

    return {}


def format_search_context(results: list[SearchResult], max_results: int = 5) -> str:
    """
    将搜索结果格式化为上下文字符串

    参数:
        results: 搜索结果列表
        max_results: 最大结果数

    返回:
        str: 格式化的上下文字符串
    """
    if not results:
        return "未找到相关搜索结果。"

    context_parts = []
    for i, result in enumerate(results[:max_results], 1):
        context_parts.append(f"[来源{i}] {result.to_context()}")

    return "\n---\n".join(context_parts)


# ==================== 全局实例 ====================

# 创建全局客户端实例（惰性加载）
_llm_client = None
_search_client = None


def get_llm_client() -> LLMClient:
    """获取 LLM 客户端单例"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


def get_search_client() -> SearchClient:
    """获取搜索客户端单例"""
    global _search_client
    if _search_client is None:
        _search_client = SearchClient()
    return _search_client
