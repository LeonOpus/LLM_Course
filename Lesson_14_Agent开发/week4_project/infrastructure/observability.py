"""
可观测性模块
集成 LangFuse 实现 LLM 调用追踪
"""
import logging
import time
from typing import Optional, Dict, Any, List
from functools import wraps
from contextlib import contextmanager
import uuid
import sys
sys.path.append(str(__file__).rsplit('/', 2)[0])

from config import (
    LANGFUSE_PUBLIC_KEY,
    LANGFUSE_SECRET_KEY,
    LANGFUSE_HOST,
    LANGFUSE_ENABLED
)

logger = logging.getLogger(__name__)

# LangFuse 客户端（延迟初始化）
_langfuse_client = None


def get_langfuse():
    """获取 LangFuse 客户端实例"""
    global _langfuse_client

    if not LANGFUSE_ENABLED:
        return None

    if _langfuse_client is None:
        try:
            from langfuse import Langfuse
            _langfuse_client = Langfuse(
                public_key=LANGFUSE_PUBLIC_KEY,
                secret_key=LANGFUSE_SECRET_KEY,
                host=LANGFUSE_HOST
            )
            logger.info("[Observability] LangFuse 客户端初始化成功")
        except ImportError:
            logger.warning("[Observability] LangFuse 未安装，跳过初始化")
            return None
        except Exception as e:
            logger.error(f"[Observability] LangFuse 初始化失败: {str(e)}")
            return None

    return _langfuse_client


class TraceContext:
    """
    追踪上下文管理器
    用于在多智能体协作中传递追踪信息
    """

    def __init__(
        self,
        name: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.name = name
        self.trace_id = str(uuid.uuid4())
        self.user_id = user_id
        self.session_id = session_id or str(uuid.uuid4())
        self.metadata = metadata or {}
        self.trace = None
        self.start_time = None

        logger.info(f"[Observability] 创建追踪上下文: {name} (trace_id={self.trace_id[:8]})")

    def __enter__(self):
        self.start_time = time.time()
        langfuse = get_langfuse()

        if langfuse:
            self.trace = langfuse.trace(
                id=self.trace_id,
                name=self.name,
                user_id=self.user_id,
                session_id=self.session_id,
                metadata=self.metadata
            )
            logger.info(f"[Observability] 开始追踪: {self.name}")

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time

        if self.trace:
            if exc_type:
                self.trace.update(
                    output={"error": str(exc_val)},
                    level="ERROR"
                )
            logger.info(f"[Observability] 追踪结束: {self.name} (耗时: {duration:.2f}s)")

        return False

    def create_span(
        self,
        name: str,
        input_data: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """创建子 Span"""
        if self.trace:
            return SpanContext(
                trace=self.trace,
                name=name,
                input_data=input_data,
                metadata=metadata
            )
        return DummySpanContext()

    def log_generation(
        self,
        name: str,
        model: str,
        input_messages: List[Dict[str, str]],
        output: str,
        usage: Optional[Dict[str, int]] = None,
        latency_ms: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        记录 LLM 生成调用

        Args:
            name: 生成名称
            model: 模型名称
            input_messages: 输入消息
            output: 输出内容
            usage: Token 使用量 {"input": x, "output": y}
            latency_ms: 延迟毫秒
            metadata: 额外元数据
        """
        if self.trace:
            self.trace.generation(
                name=name,
                model=model,
                input=input_messages,
                output=output,
                usage=usage,
                metadata={
                    "latency_ms": latency_ms,
                    **(metadata or {})
                }
            )
            logger.debug(f"[Observability] 记录LLM调用: {name} ({model})")


class SpanContext:
    """Span 上下文管理器"""

    def __init__(
        self,
        trace,
        name: str,
        input_data: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.trace = trace
        self.name = name
        self.input_data = input_data
        self.metadata = metadata or {}
        self.span = None
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        self.span = self.trace.span(
            name=self.name,
            input=self.input_data,
            metadata=self.metadata
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time

        if self.span:
            if exc_type:
                self.span.end(
                    output={"error": str(exc_val)},
                    level="ERROR"
                )
            else:
                self.span.end()

        logger.debug(f"[Observability] Span 结束: {self.name} (耗时: {duration:.2f}s)")
        return False

    def set_output(self, output: Any):
        """设置 Span 输出"""
        if self.span:
            self.span.update(output=output)


class DummySpanContext:
    """空 Span 上下文（LangFuse 未启用时使用）"""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def set_output(self, output: Any):
        pass


def trace_llm_call(func):
    """
    装饰器：追踪 LLM 调用

    使用方式:
        @trace_llm_call
        async def achat(self, messages, ...):
            ...
    """
    @wraps(func)
    async def async_wrapper(self, messages, *args, **kwargs):
        start_time = time.time()
        trace_ctx = getattr(self, '_trace_context', None)

        try:
            result = await func(self, messages, *args, **kwargs)
            latency_ms = (time.time() - start_time) * 1000

            # 记录到 LangFuse
            if trace_ctx:
                trace_ctx.log_generation(
                    name=func.__name__,
                    model=getattr(self, 'model', 'unknown'),
                    input_messages=messages,
                    output=result,
                    latency_ms=latency_ms,
                    metadata={"temperature": kwargs.get("temperature", 0.7)}
                )

            logger.info(f"[Observability] LLM调用完成: {func.__name__} (延迟: {latency_ms:.0f}ms)")
            return result

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"[Observability] LLM调用失败: {func.__name__} (延迟: {latency_ms:.0f}ms, 错误: {str(e)})")
            raise

    @wraps(func)
    def sync_wrapper(self, messages, *args, **kwargs):
        start_time = time.time()

        try:
            result = func(self, messages, *args, **kwargs)
            latency_ms = (time.time() - start_time) * 1000
            logger.info(f"[Observability] LLM调用完成: {func.__name__} (延迟: {latency_ms:.0f}ms)")
            return result

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"[Observability] LLM调用失败: {func.__name__} (延迟: {latency_ms:.0f}ms, 错误: {str(e)})")
            raise

    # 判断是否是异步函数
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


def flush_langfuse():
    """刷新 LangFuse 缓冲区"""
    langfuse = get_langfuse()
    if langfuse:
        langfuse.flush()
        logger.info("[Observability] LangFuse 缓冲区已刷新")


def shutdown_langfuse():
    """关闭 LangFuse 客户端"""
    global _langfuse_client
    if _langfuse_client:
        _langfuse_client.shutdown()
        _langfuse_client = None
        logger.info("[Observability] LangFuse 客户端已关闭")


# 测试代码
if __name__ == "__main__":
    print(f"LangFuse Enabled: {LANGFUSE_ENABLED}")

    if LANGFUSE_ENABLED:
        with TraceContext("test_trace", user_id="test_user") as ctx:
            ctx.log_generation(
                name="test_generation",
                model="deepseek-v3.2",
                input_messages=[{"role": "user", "content": "Hello"}],
                output="Hi there!",
                usage={"input": 10, "output": 5},
                latency_ms=100
            )

        flush_langfuse()
        print("✓ LangFuse 测试完成")
    else:
        print("LangFuse 未配置，跳过测试")
