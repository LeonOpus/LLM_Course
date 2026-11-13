"""工具执行器 - 使用真实博查搜索 API 和 Jina.ai Reader API"""

import json
import requests
from typing import Dict, Optional
from openai import OpenAI


class ToolExecutor:
    """工具执行器 - 使用真实 API（博查搜索 + Jina Reader）"""

    def __init__(
        self,
        search_api_key: str,
        jina_api_key: str = None,
        llm_api_key: str = None,
        llm_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    ):
        # 博查搜索 API
        self.search_api_key = search_api_key
        self.search_url = "https://api.bocha.cn/v1/web-search"

        # Jina.ai Reader API（用于 visit 工具）
        self.jina_api_key = jina_api_key
        self.jina_reader_url = "https://r.jina.ai/"

        # LLM 作为 visit 的降级方案
        if llm_api_key:
            self.llm_client = OpenAI(api_key=llm_api_key, base_url=llm_base_url)
        else:
            self.llm_client = None

    def execute(self, tool_call: Dict) -> str:
        """执行工具调用，返回统一格式的结果"""
        name = tool_call.get("name")
        args = tool_call.get("arguments", {})

        if name == "search":
            return self._execute_search(args.get("query", ""))
        elif name == "visit":
            return self._execute_visit(args.get("url", ""), args.get("goal", ""))
        elif name == "calculator":
            return self._execute_calculator(args.get("expression", ""))
        elif name == "scholar":
            return self._execute_scholar(args.get("query", ""))
        elif name == "finish":
            return f"[完成] 答案: {args.get('answer', '')}\n证据: {args.get('evidence', '')}"
        else:
            return f"[错误] 未知工具: {name}"

    def _execute_search(self, query: str) -> str:
        """调用博查搜索 API - 真实搜索"""
        if not query:
            return "[错误] 搜索词不能为空"

        try:
            headers = {
                "Authorization": f"Bearer {self.search_api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "query": query,
                "summary": True,  # 获取摘要
                "count": 5        # 返回5条结果
            }

            response = requests.post(
                self.search_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            # 解析搜索结果
            if data.get("code") != 200:
                return f"[搜索错误] {data.get('msg', '未知错误')}"

            web_pages = data.get("data", {}).get("webPages", {}).get("value", [])

            if not web_pages:
                return "[搜索结果] 未找到相关结果"

            # 格式化输出（统一格式，训练和推理一致）
            results = []
            for i, page in enumerate(web_pages, 1):
                title = page.get("name", "无标题")
                url = page.get("url", "")
                snippet = page.get("snippet", "")
                site_name = page.get("siteName", "")
                date = page.get("dateLastCrawled", "")[:10] if page.get("dateLastCrawled") else ""

                result = f"[{i}] {title}\n"
                result += f"来源: {site_name}"
                if date:
                    result += f" | 日期: {date}"
                result += f"\n摘要: {snippet}\n"
                result += f"URL: {url}"
                results.append(result)

            return "\n\n".join(results)

        except requests.exceptions.Timeout:
            return "[搜索错误] 请求超时"
        except requests.exceptions.RequestException as e:
            return f"[搜索错误] 网络错误: {str(e)}"
        except Exception as e:
            return f"[搜索错误] {str(e)}"

    def _execute_visit(self, url: str, goal: str) -> str:
        """访问网页 - 优先使用 Jina.ai Reader API，降级到 LLM 模拟"""
        if not url:
            return "[错误] URL不能为空"

        # 优先使用 Jina.ai Reader API
        if self.jina_api_key:
            result = self._visit_with_jina(url, goal)
            if not result.startswith("[访问错误]"):
                return result
            # Jina 失败时降级到 LLM

        # 降级方案：使用 LLM 模拟
        if self.llm_client:
            return self._visit_with_llm(url, goal)

        return "[错误] 未配置 Jina API 或 LLM，无法执行 visit"

    def _visit_with_jina(self, url: str, goal: str) -> str:
        """使用 Jina.ai Reader API 获取真实网页内容"""
        try:
            headers = {
                "Authorization": f"Bearer {self.jina_api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-Return-Format": "markdown",
                "X-Timeout": "30"
            }

            payload = {"url": url}

            response = requests.post(
                self.jina_reader_url,
                headers=headers,
                json=payload,
                timeout=35
            )
            response.raise_for_status()
            data = response.json()

            if data.get("code") != 200:
                return f"[访问错误] Jina API: {data.get('status', '未知错误')}"

            # 提取内容
            page_data = data.get("data", {})
            title = page_data.get("title", "未知标题")
            content = page_data.get("content", "")

            if not content:
                return "[访问错误] 无法提取页面内容"

            # 截取合理长度（避免过长）
            max_content_len = 3000
            if len(content) > max_content_len:
                content = content[:max_content_len] + "\n...[内容已截断]"

            # 格式化输出
            result = f"[网页内容] {title}\n"
            result += f"URL: {url}\n"
            result += f"提取目标: {goal}\n\n"
            result += content

            return result

        except requests.exceptions.Timeout:
            return "[访问错误] 请求超时"
        except requests.exceptions.RequestException as e:
            return f"[访问错误] 网络错误: {str(e)}"
        except Exception as e:
            return f"[访问错误] {str(e)}"

    def _visit_with_llm(self, url: str, goal: str) -> str:
        """降级方案：使用 LLM 模拟网页内容"""
        prompt = f"""你是一个网页内容提取器。根据URL和目标，返回网页的关键内容。

URL: {url}
提取目标: {goal}

要求:
1. 提取与目标相关的详细信息
2. 包含具体的数据、日期、名称等
3. 内容要真实准确

格式:
[网页内容]
提取的关键信息...

[关键数据]
- 数据点1
- 数据点2"""

        try:
            response = self.llm_client.chat.completions.create(
                model="qwen-plus",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1500
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"[访问错误] {str(e)}"

    def _execute_calculator(self, expression: str) -> str:
        """执行数学计算"""
        if not expression:
            return "[错误] 表达式不能为空"

        try:
            # 安全的计算环境
            allowed_names = {
                "abs": abs, "round": round, "min": min, "max": max,
                "sum": sum, "pow": pow, "int": int, "float": float
            }
            safe_expr = expression.replace("^", "**")
            result = eval(safe_expr, {"__builtins__": {}}, allowed_names)
            return f"[计算结果] {expression} = {result}"
        except Exception as e:
            return f"[计算错误] 表达式 '{expression}' 无效: {str(e)}"

    def _execute_scholar(self, query: str) -> str:
        """学术搜索（使用博查 API + 学术站点限定）"""
        if not query:
            return "[错误] 搜索词不能为空"

        try:
            headers = {
                "Authorization": f"Bearer {self.search_api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "query": query,
                "summary": True,
                "count": 3,
                # 限定学术相关网站
                "include": "scholar.google.com|arxiv.org|pubmed.ncbi.nlm.nih.gov|cnki.net|wanfangdata.com.cn"
            }

            response = requests.post(
                self.search_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            if data.get("code") != 200:
                return f"[学术搜索错误] {data.get('msg', '未知错误')}"

            web_pages = data.get("data", {}).get("webPages", {}).get("value", [])

            if not web_pages:
                return "[学术搜索结果] 未找到相关学术文献"

            results = []
            for i, page in enumerate(web_pages, 1):
                title = page.get("name", "无标题")
                url = page.get("url", "")
                snippet = page.get("snippet", "")
                site_name = page.get("siteName", "")

                result = f"[{i}] {title}\n"
                result += f"来源: {site_name}\n"
                result += f"摘要: {snippet}\n"
                result += f"URL: {url}"
                results.append(result)

            return "\n\n".join(results)

        except Exception as e:
            return f"[学术搜索错误] {str(e)}"
