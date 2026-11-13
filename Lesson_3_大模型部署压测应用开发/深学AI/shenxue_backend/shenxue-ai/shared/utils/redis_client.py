import redis.asyncio as redis
import json
import logging
from typing import Optional, Any
import os

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis异步客户端封装"""
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._client: Optional[redis.Redis] = None
    
    async def get_client(self) -> redis.Redis:
        """获取Redis客户端"""
        if self._client is None:
            self._client = redis.from_url(self.redis_url, decode_responses=True)
        return self._client
    
    async def close(self):
        """关闭连接"""
        if self._client:
            await self._client.close()
    
    async def set_cache(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """设置缓存"""
        try:
            client = await self.get_client()
            serialized_value = json.dumps(value, ensure_ascii=False)
            await client.setex(key, ttl, serialized_value)
            return True
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False
    
    async def get_cache(self, key: str) -> Optional[Any]:
        """获取缓存"""
        try:
            client = await self.get_client()
            value = await client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    async def delete_cache(self, key: str) -> bool:
        """删除缓存"""
        try:
            client = await self.get_client()
            await client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False
    
    async def ping(self) -> bool:
        """检查连接"""
        try:
            client = await self.get_client()
            await client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis ping error: {e}")
            return False
    
    async def flush_all(self) -> bool:
        """清除所有缓存数据"""
        try:
            client = await self.get_client()
            await client.flushall()
            logger.warning("All Redis data has been flushed")
            return True
        except Exception as e:
            logger.error(f"Redis flushall error: {e}")
            return False
    
    async def get_info(self) -> Optional[dict]:
        """获取Redis服务器信息"""
        try:
            client = await self.get_client()
            info = await client.info()
            return info
        except Exception as e:
            logger.error(f"Redis info error: {e}")
            return None


# 全局Redis客户端实例
_redis_client: Optional[RedisClient] = None


def get_redis_client() -> RedisClient:
    """获取全局Redis客户端"""
    global _redis_client
    if _redis_client is None:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        _redis_client = RedisClient(redis_url)
    return _redis_client 