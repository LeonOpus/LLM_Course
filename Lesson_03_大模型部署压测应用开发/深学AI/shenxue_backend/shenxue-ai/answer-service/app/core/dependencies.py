from functools import lru_cache
import sys
sys.path.append('/app/shared')

from shared.utils.redis_client import RedisClient, get_redis_client
from shared.utils.http_client import AsyncHTTPClient
from app.services.llm_service import DashScopeService
from app.services.viz_client import VisualizationClient
from app.services.answer_orchestrator import AnswerOrchestrator
from app.services.cache_service import CacheService
from app.core.config import settings


@lru_cache()
def get_llm_service() -> DashScopeService:
    """获取LLM服务实例"""
    return DashScopeService(
        api_key=settings.DASHSCOPE_API_KEY,
        base_url=settings.DASHSCOPE_BASE_URL,
        model=settings.DASHSCOPE_MODEL,
        timeout=settings.LLM_TIMEOUT,
        sync_timeout=settings.LLM_SYNC_TIMEOUT,
        max_retries=settings.LLM_MAX_RETRIES
    )


@lru_cache()
def get_viz_client() -> VisualizationClient:
    """获取可视化客户端实例"""
    return VisualizationClient(
        viz_service_url=settings.VIZ_SERVICE_URL,
        timeout=settings.VIZ_TIMEOUT,
        max_retries=settings.VIZ_MAX_RETRIES
    )


@lru_cache()
def get_cache_service() -> CacheService:
    """获取缓存服务实例"""
    redis_client = get_redis_client()
    return CacheService(redis_client, default_ttl=settings.CACHE_TTL)


@lru_cache()
def get_http_client() -> AsyncHTTPClient:
    """获取HTTP客户端实例"""
    return AsyncHTTPClient(timeout=30.0, max_retries=3)


def get_answer_orchestrator() -> AnswerOrchestrator:
    """获取问答编排器实例"""
    return AnswerOrchestrator(
        llm_service=get_llm_service(),
        viz_client=get_viz_client(),
        cache_service=get_cache_service()
    ) 