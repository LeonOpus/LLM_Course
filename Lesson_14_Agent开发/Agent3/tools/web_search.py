"""
网络搜索工具 - 使用博查API
"""
import os
import sys
import json
import httpx
from typing import Dict, Any, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import settings


class WebSearchTool:
    """网络搜索工具类 - 使用博查API"""

    name = "web_search"
    description = """搜索互联网获取最新信息。适用于：
    - 获取最新市场动态和新闻
    - 查询公司最新公告
    - 搜索行业研究报告
    - 获取实时财经信息"""

    def __init__(self):
        self.api_key = settings.BOCHAAI_API_KEY
        self.base_url = settings.BOCHAAI_BASE_URL
        if not self.api_key:
            print("警告: BOCHAAI_API_KEY 未设置，请在 .env 文件中配置")
    
    def search(
        self,
        query: str,
        freshness: str = "noLimit",
        summary: bool = True,
        count: int = 10
    ) -> Dict[str, Any]:
        """
        执行网络搜索
        
        Args:
            query: 搜索关键词
            freshness: 时效性过滤 (noLimit/day/week/month)
            summary: 是否返回摘要
            count: 返回结果数量
        
        Returns:
            搜索结果
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "query": query,
            "freshness": freshness,
            "summary": summary,
            "count": count
        }
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.base_url}/web-search",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return self._format_result(result, query)
                else:
                    return {
                        "success": False,
                        "error": f"API请求失败: {response.status_code}",
                        "query": query
                    }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "query": query
            }
    
    def _format_result(self, result: Dict, query: str) -> Dict[str, Any]:
        """
        格式化搜索结果
        
        Args:
            result: API原始结果
            query: 搜索查询
        
        Returns:
            格式化后的结果
        """
        formatted = {
            "success": True,
            "query": query,
            "summary": "",
            "results": [],
            "total_count": 0
        }
        
        # 提取摘要
        if "data" in result:
            data = result["data"]
            
            # 获取AI摘要
            if "summary" in data:
                formatted["summary"] = data["summary"]
            
            # 获取搜索结果
            if "webPages" in data and "value" in data["webPages"]:
                web_pages = data["webPages"]["value"]
                formatted["total_count"] = len(web_pages)
                
                for page in web_pages:
                    formatted["results"].append({
                        "title": page.get("name", ""),
                        "url": page.get("url", ""),
                        "snippet": page.get("snippet", ""),
                        "date": page.get("datePublished", ""),
                        "site_name": page.get("siteName", "")
                    })
        
        return formatted
    
    def run(
        self,
        query: str,
        freshness: str = "noLimit",
        count: int = 10
    ) -> Dict[str, Any]:
        """
        执行搜索并返回结果
        
        Args:
            query: 搜索关键词
            freshness: 时效性
            count: 结果数量
        
        Returns:
            搜索结果
        """
        return self.search(query, freshness, True, count)


# 工具函数定义（用于LangGraph）
WEB_SEARCH_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "搜索互联网获取最新信息，包括市场动态、公司公告、行业新闻等。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词，如'贵州茅台最新财报'、'新能源汽车行业趋势'"
                },
                "freshness": {
                    "type": "string",
                    "enum": ["noLimit", "day", "week", "month"],
                    "description": "时效性过滤：noLimit(不限)、day(一天内)、week(一周内)、month(一月内)",
                    "default": "noLimit"
                },
                "count": {
                    "type": "integer",
                    "description": "返回结果数量，默认10",
                    "default": 10
                }
            },
            "required": ["query"]
        }
    }
}


if __name__ == "__main__":
    # 测试
    searcher = WebSearchTool()
    
    queries = [
        "贵州茅台 股价 2024",
        "新能源汽车行业趋势",
        "A股市场最新消息"
    ]
    
    for query in queries:
        print(f"\n搜索: {query}")
        result = searcher.run(query, count=3)
        print(f"成功: {result['success']}")
        if result['success']:
            print(f"摘要: {result['summary'][:200]}..." if result['summary'] else "无摘要")
            print(f"结果数: {result['total_count']}")
            for i, r in enumerate(result['results'][:3]):
                print(f"  {i+1}. {r['title']}")
