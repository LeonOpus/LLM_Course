"""
LLM服务
使用DeepSeek-v3模型（通过阿里云 DashScope API）
"""
import logging
import time
from typing import List, Dict, Any, Optional, AsyncGenerator
from openai import OpenAI, AsyncOpenAI
import json
import sys
sys.path.append(str(__file__).rsplit('/', 3)[0])

from config import DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL, LLM_MODEL
from infrastructure.observability import get_langfuse, LANGFUSE_ENABLED

logger = logging.getLogger(__name__)


class LLMService:
    """
    LLM服务类
    使用DeepSeek-v3模型进行文本生成（通过阿里云DashScope）
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = LLM_MODEL
    ):
        self.api_key = api_key or DASHSCOPE_API_KEY
        self.base_url = base_url or DASHSCOPE_BASE_URL
        self.model = model

        # 同步客户端
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

        # 异步客户端
        self.async_client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

        logger.info(f"[LLM] 初始化LLMService")
        logger.info(f"[LLM] Model: {self.model}")
        logger.info(f"[LLM] Base URL: {self.base_url}")

    def _log_to_langfuse(
        self,
        name: str,
        messages: List[Dict[str, str]],
        output: str,
        usage: Optional[Dict[str, int]],
        latency_ms: float,
        temperature: float,
        json_mode: bool = False
    ):
        """
        记录 LLM 调用到 LangFuse

        Args:
            name: 调用名称
            messages: 输入消息
            output: 输出内容
            usage: Token 使用量
            latency_ms: 延迟毫秒
            temperature: 温度参数
            json_mode: 是否JSON模式
        """
        if not LANGFUSE_ENABLED:
            return

        try:
            langfuse = get_langfuse()
            if langfuse:
                langfuse.generation(
                    name=name,
                    model=self.model,
                    input=messages,
                    output=output,
                    usage=usage,
                    metadata={
                        "temperature": temperature,
                        "json_mode": json_mode,
                        "latency_ms": latency_ms
                    }
                )
                logger.debug(f"[LLM] 已记录到LangFuse: {name}")
        except Exception as e:
            logger.warning(f"[LLM] LangFuse记录失败: {str(e)}")

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        json_mode: bool = False,
        trace_name: str = "chat"
    ) -> str:
        """
        同步对话接口

        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            temperature: 温度参数
            max_tokens: 最大token数
            json_mode: 是否启用JSON模式
            trace_name: 追踪名称（用于LangFuse）

        Returns:
            模型回复文本
        """
        logger.info(f"[LLM] 开始对话, 消息数: {len(messages)}, temperature: {temperature}")
        start_time = time.time()

        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
                logger.info("[LLM] 启用JSON模式")

            response = self.client.chat.completions.create(**kwargs)

            content = response.choices[0].message.content
            latency_ms = (time.time() - start_time) * 1000

            # 提取 token 使用量
            usage = None
            if hasattr(response, 'usage') and response.usage:
                usage = {
                    "input": response.usage.prompt_tokens,
                    "output": response.usage.completion_tokens,
                    "total": response.usage.total_tokens
                }
                logger.info(f"[LLM] Token使用: input={usage['input']}, output={usage['output']}, total={usage['total']}")

            logger.info(f"[LLM] 对话完成, 回复长度: {len(content)}, 延迟: {latency_ms:.0f}ms")
            logger.debug(f"[LLM] 回复内容: {content[:200]}...")

            # 记录到 LangFuse
            self._log_to_langfuse(
                name=trace_name,
                messages=messages,
                output=content,
                usage=usage,
                latency_ms=latency_ms,
                temperature=temperature,
                json_mode=json_mode
            )

            return content

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"[LLM] 对话失败: {str(e)}, 延迟: {latency_ms:.0f}ms")
            raise

    async def achat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        json_mode: bool = False,
        trace_name: str = "achat"
    ) -> str:
        """
        异步对话接口

        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            json_mode: 是否启用JSON模式
            trace_name: 追踪名称（用于LangFuse）

        Returns:
            模型回复文本
        """
        logger.info(f"[LLM] 开始异步对话, 消息数: {len(messages)}")
        start_time = time.time()

        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            response = await self.async_client.chat.completions.create(**kwargs)

            content = response.choices[0].message.content
            latency_ms = (time.time() - start_time) * 1000

            # 提取 token 使用量
            usage = None
            if hasattr(response, 'usage') and response.usage:
                usage = {
                    "input": response.usage.prompt_tokens,
                    "output": response.usage.completion_tokens,
                    "total": response.usage.total_tokens
                }
                logger.info(f"[LLM] Token使用: input={usage['input']}, output={usage['output']}, total={usage['total']}")

            logger.info(f"[LLM] 异步对话完成, 回复长度: {len(content)}, 延迟: {latency_ms:.0f}ms")

            # 记录到 LangFuse
            self._log_to_langfuse(
                name=trace_name,
                messages=messages,
                output=content,
                usage=usage,
                latency_ms=latency_ms,
                temperature=temperature,
                json_mode=json_mode
            )

            return content

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"[LLM] 异步对话失败: {str(e)}, 延迟: {latency_ms:.0f}ms")
            raise

    async def astream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> AsyncGenerator[str, None]:
        """
        异步流式对话接口

        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数

        Yields:
            流式返回的文本片段
        """
        logger.info(f"[LLM] 开始流式对话, 消息数: {len(messages)}")

        try:
            stream = await self.async_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )

            total_content = ""
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    total_content += content
                    yield content

            logger.info(f"[LLM] 流式对话完成, 总长度: {len(total_content)}")

        except Exception as e:
            logger.error(f"[LLM] 流式对话失败: {str(e)}")
            raise

    def generate_with_system(
        self,
        system_prompt: str,
        user_input: str,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> str:
        """
        使用系统提示和用户输入生成回复

        Args:
            system_prompt: 系统提示
            user_input: 用户输入
            temperature: 温度参数
            max_tokens: 最大token数

        Returns:
            模型回复
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
        return self.chat(messages, temperature, max_tokens)

    async def agenerate_with_system(
        self,
        system_prompt: str,
        user_input: str,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> str:
        """异步版本的generate_with_system"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
        return await self.achat(messages, temperature, max_tokens)

    def parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        解析JSON格式的回复

        Args:
            response: 模型回复文本

        Returns:
            解析后的字典
        """
        logger.info("[LLM] 解析JSON回复")

        try:
            # 尝试直接解析
            return json.loads(response)
        except json.JSONDecodeError:
            # 尝试提取JSON块
            logger.warning("[LLM] 直接解析失败，尝试提取JSON块")
            import re
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
            if json_match:
                return json.loads(json_match.group(1))

            # 尝试查找花括号包裹的内容
            brace_match = re.search(r'\{[\s\S]*\}', response)
            if brace_match:
                return json.loads(brace_match.group())

            logger.error("[LLM] 无法解析JSON")
            raise ValueError("无法从回复中解析JSON")


# 测试代码
def test_llm():
    """测试LLM服务"""
    logger.info("=" * 50)
    logger.info("[TEST] 开始测试LLMService")
    logger.info("=" * 50)

    service = LLMService()

    # 测试基础对话
    print("\n=== 测试基础对话 ===")
    messages = [
        {"role": "user", "content": "请用一句话解释什么是低空经济"}
    ]
    response = service.chat(messages)
    print(f"问题: {messages[0]['content']}")
    print(f"回答: {response}")

    # 测试系统提示
    print("\n=== 测试系统提示 ===")
    system_prompt = "你是一个专业的行业分析师，请用专业但易懂的语言回答问题。"
    user_input = "低空经济的主要应用场景有哪些？请列举3个。"
    response = service.generate_with_system(system_prompt, user_input)
    print(f"系统提示: {system_prompt}")
    print(f"用户输入: {user_input}")
    print(f"回答: {response}")

    # 测试JSON模式
    print("\n=== 测试JSON模式 ===")
    messages = [
        {"role": "system", "content": "请以JSON格式回复，包含name和description字段"},
        {"role": "user", "content": "描述一下无人机配送服务"}
    ]
    response = service.chat(messages, json_mode=True)
    print(f"JSON回复: {response}")

    parsed = service.parse_json_response(response)
    print(f"解析结果: {parsed}")

    logger.info("[TEST] LLMService测试完成")
    return response


async def test_llm_async():
    """测试异步LLM服务"""
    logger.info("=" * 50)
    logger.info("[TEST] 开始测试异步LLMService")
    logger.info("=" * 50)

    service = LLMService()

    # 测试异步对话
    print("\n=== 测试异步对话 ===")
    messages = [
        {"role": "user", "content": "请用一句话解释什么是多智能体系统"}
    ]
    response = await service.achat(messages)
    print(f"问题: {messages[0]['content']}")
    print(f"回答: {response}")

    # 测试流式输出
    print("\n=== 测试流式输出 ===")
    messages = [
        {"role": "user", "content": "请简要介绍RAG技术的工作原理"}
    ]
    print("流式回复: ", end="", flush=True)
    async for chunk in service.astream(messages):
        print(chunk, end="", flush=True)
    print()

    logger.info("[TEST] 异步LLMService测试完成")


if __name__ == "__main__":
    # 测试同步接口
    test_llm()

    # 测试异步接口
    import asyncio
    asyncio.run(test_llm_async())
