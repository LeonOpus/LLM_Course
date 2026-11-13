"""
Web搜索工具
使用Bocha API进行网络搜索
"""
import httpx
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import sys
sys.path.append(str(__file__).rsplit('/', 3)[0])

from config import BOCHA_API_KEY, BOCHA_API_URL

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """搜索结果数据类"""
    title: str
    url: str
    snippet: str
    summary: Optional[str] = None
    site_name: Optional[str] = None
    date_published: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "summary": self.summary,
            "site_name": self.site_name,
            "date_published": self.date_published
        }


class WebSearchTool:
    """
    Web搜索工具类
    使用Bocha API进行网络搜索，支持迭代搜索和来源引用
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or BOCHA_API_KEY
        self.api_url = BOCHA_API_URL
        logger.info(f"[WebSearch] 初始化WebSearchTool, API URL: {self.api_url}")

    async def search(
        self,
        query: str,
        count: int = 10,
        freshness: str = "noLimit",
        summary: bool = True,
        include: Optional[str] = None,
        exclude: Optional[str] = None
    ) -> List[SearchResult]:
        """
        执行单次搜索

        Args:
            query: 搜索关键词
            count: 返回结果数量 (1-50)
            freshness: 时间范围 (noLimit/oneDay/oneWeek/oneMonth/oneYear)
            summary: 是否返回摘要
            include: 限定搜索的域名
            exclude: 排除的域名

        Returns:
            搜索结果列表
        """
        logger.info(f"[WebSearch] 开始搜索: query='{query}', count={count}, freshness={freshness}")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "query": query,
            "count": min(count, 50),
            "freshness": freshness,
            "summary": summary
        }

        if include:
            payload["include"] = include
        if exclude:
            payload["exclude"] = exclude

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.api_url,
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                data = response.json()

            logger.info(f"[WebSearch] API返回状态码: {data.get('code')}")

            if data.get("code") != 200:
                logger.error(f"[WebSearch] API错误: {data.get('msg')}")
                return []

            results = []
            web_pages = data.get("data", {}).get("webPages", {}).get("value", [])
            logger.info(f"[WebSearch] 获取到 {len(web_pages)} 条结果")

            for page in web_pages:
                result = SearchResult(
                    title=page.get("name", ""),
                    url=page.get("url", ""),
                    snippet=page.get("snippet", ""),
                    summary=page.get("summary"),
                    site_name=page.get("siteName"),
                    date_published=page.get("datePublished") or page.get("dateLastCrawled")
                )
                results.append(result)
                logger.debug(f"[WebSearch] 结果: {result.title[:50]}...")

            return results

        except httpx.HTTPStatusError as e:
            logger.error(f"[WebSearch] HTTP错误: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"[WebSearch] 搜索失败: {str(e)}")
            raise

    async def iterative_search(
        self,
        initial_query: str,
        max_iterations: int = 3,
        results_per_iteration: int = 5,
        llm_refine_func=None
    ) -> Dict[str, Any]:
        """
        迭代搜索：根据初步结果自动生成新的搜索词

        Args:
            initial_query: 初始搜索词
            max_iterations: 最大迭代次数
            results_per_iteration: 每次迭代返回的结果数
            llm_refine_func: 用于生成新搜索词的LLM函数 (async callable)

        Returns:
            包含所有搜索结果和搜索历史的字典
        """
        logger.info(f"[WebSearch] 开始迭代搜索: query='{initial_query}', max_iterations={max_iterations}")

        all_results = []
        search_history = []
        current_query = initial_query
        seen_urls = set()

        for iteration in range(max_iterations):
            logger.info(f"[WebSearch] 迭代 {iteration + 1}/{max_iterations}: query='{current_query}'")

            # 执行搜索
            results = await self.search(
                query=current_query,
                count=results_per_iteration,
                summary=True
            )

            # 去重并添加结果
            new_results = []
            for r in results:
                if r.url not in seen_urls:
                    seen_urls.add(r.url)
                    new_results.append(r)
                    all_results.append(r)

            search_history.append({
                "iteration": iteration + 1,
                "query": current_query,
                "new_results_count": len(new_results),
                "total_results": len(all_results)
            })

            logger.info(f"[WebSearch] 迭代 {iteration + 1} 完成: 新增 {len(new_results)} 条结果")

            # 如果没有新结果或没有LLM函数，停止迭代
            if not new_results or not llm_refine_func:
                logger.info(f"[WebSearch] 停止迭代: new_results={len(new_results)}, has_llm={llm_refine_func is not None}")
                break

            # 使用LLM生成新的搜索词
            if iteration < max_iterations - 1:
                context = "\n".join([
                    f"- {r.title}: {r.snippet[:100]}..."
                    for r in new_results[:3]
                ])
                new_query = await llm_refine_func(initial_query, current_query, context)
                if new_query and new_query != current_query:
                    current_query = new_query
                    logger.info(f"[WebSearch] LLM生成新搜索词: '{new_query}'")
                else:
                    logger.info("[WebSearch] LLM未生成新搜索词，停止迭代")
                    break

        logger.info(f"[WebSearch] 迭代搜索完成: 共获取 {len(all_results)} 条结果")

        return {
            "results": all_results,
            "search_history": search_history,
            "total_unique_results": len(all_results)
        }

    def format_results_with_citations(self, results: List[SearchResult]) -> str:
        """
        格式化搜索结果并添加引用标注

        Args:
            results: 搜索结果列表

        Returns:
            带引用标注的格式化文本
        """
        logger.info(f"[WebSearch] 格式化 {len(results)} 条结果")

        formatted = []
        for i, result in enumerate(results, 1):
            citation = f"[{i}]"
            text = f"{citation} **{result.title}**\n"
            text += f"   来源: {result.site_name or '未知'} | {result.date_published or '日期未知'}\n"
            text += f"   链接: {result.url}\n"
            if result.summary:
                text += f"   摘要: {result.summary[:200]}...\n" if len(result.summary) > 200 else f"   摘要: {result.summary}\n"
            else:
                text += f"   描述: {result.snippet}\n"
            formatted.append(text)

        return "\n".join(formatted)


# 测试代码
async def test_web_search():
    """测试Web搜索功能"""
    logger.info("=" * 50)
    logger.info("[TEST] 开始测试WebSearchTool")
    logger.info("=" * 50)

    tool = WebSearchTool()

    # 测试单次搜索
    print("\n=== 测试单次搜索 ===")
    results = await tool.search("低空经济 2024", count=5, summary=True)
    print(f"获取到 {len(results)} 条结果:")
    for r in results:
        print(f"  - {r.title}")
        print(f"    URL: {r.url}")
        print()

    # 测试格式化输出
    print("\n=== 测试格式化输出 ===")
    formatted = tool.format_results_with_citations(results[:3])
    print(formatted)

    logger.info("[TEST] WebSearchTool测试完成")
    return results


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_web_search())
