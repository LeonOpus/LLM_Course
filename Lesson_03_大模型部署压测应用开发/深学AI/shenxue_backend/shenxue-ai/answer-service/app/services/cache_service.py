import hashlib
import json
import logging
import time
from typing import Optional, Any, Dict
import sys
sys.path.append('/app/shared')

from shared.utils.redis_client import RedisClient
from shared.utils.constants import *
from shared.models.request_models import QuestionRequest

logger = logging.getLogger(__name__)


class CacheService:
    """缓存服务"""
    
    def __init__(self, redis_client: RedisClient, default_ttl: int = CACHE_TTL_DEFAULT):
        self.redis_client = redis_client
        self.default_ttl = default_ttl
    
    def _generate_cache_key(self, request: QuestionRequest) -> str:
        """生成缓存键"""
        key_data = {
            "subject": request.subject.value,
            "text": request.text,
            "image_url": request.image_url,
        }
        
        # 创建一致的字符串表示
        key_str = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
        
        # 使用MD5哈希生成短键
        return hashlib.md5(key_str.encode()).hexdigest()
    
    async def get_cached_answer(self, request: QuestionRequest) -> Optional[str]:
        """获取缓存的答案"""
        try:
            cache_key = self._generate_cache_key(request)
            cached_data = await self.redis_client.get_cache(cache_key)
            
            if cached_data:
                logger.info(f"Cache hit for key: {cache_key}")
                return cached_data.get("answer")
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting cached answer: {e}")
            return None
    
    async def cache_answer(self, request: QuestionRequest, answer: str, ttl: Optional[int] = None) -> bool:
        """缓存答案"""
        try:
            cache_key = self._generate_cache_key(request)
            cache_data = {
                "answer": answer,
                "subject": request.subject.value,
                "cached_at": time.time()
            }
            
            ttl = ttl or self.default_ttl
            success = await self.redis_client.set_cache(cache_key, cache_data, ttl)
            
            if success:
                logger.info(f"Cached answer for key: {cache_key}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error caching answer: {e}")
            return False
    
    async def get_cached_image(self, image_id: str) -> Optional[Dict[str, Any]]:
        """获取缓存的图片信息"""
        try:
            cache_key = f"{CACHE_PREFIX_IMAGE}{image_id}"
            cached_data = await self.redis_client.get_cache(cache_key)
            return cached_data
            
        except Exception as e:
            logger.error(f"Error getting cached image: {e}")
            return None
    
    async def cache_image(self, image_id: str, image_info: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """缓存图片信息"""
        try:
            cache_key = f"{CACHE_PREFIX_IMAGE}{image_id}"
            ttl = ttl or CACHE_TTL_LONG  # 图片缓存时间更长
            
            success = await self.redis_client.set_cache(cache_key, image_info, ttl)
            
            if success:
                logger.info(f"Cached image info for: {image_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error caching image: {e}")
            return False
    
    async def invalidate_cache(self, request: QuestionRequest) -> bool:
        """清除特定请求的缓存"""
        try:
            cache_key = self._generate_cache_key(request)
            return await self.redis_client.delete_cache(cache_key)
            
        except Exception as e:
            logger.error(f"Error invalidating cache: {e}")
            return False
    
    async def clear_error_caches(self) -> int:
        """清除所有包含错误信息的缓存"""
        try:
            cleared_count = 0
            # 获取所有缓存键（这里简化处理，实际可能需要更复杂的逻辑）
            # 由于Redis的限制，这里我们只能记录而不能真正清除所有错误缓存
            # 更好的做法是在缓存时添加错误标记
            logger.info("Error cache clearing requested - consider using FLUSHALL for full reset")
            return cleared_count
            
        except Exception as e:
            logger.error(f"Error clearing error caches: {e}")
            return 0
    
    async def flush_all_caches(self) -> bool:
        """清除所有缓存（紧急情况使用）"""
        try:
            # 注意：这会清除所有缓存，包括图片缓存
            success = await self.redis_client.flush_all()
            if success:
                logger.warning("All caches have been flushed")
            return success
            
        except Exception as e:
            logger.error(f"Error flushing all caches: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        try:
            # 这里可以实现更详细的统计
            redis_info = await self.redis_client.get_info()
            return {
                "status": "ok",
                "redis_connected": await self.redis_client.ping(),
                "redis_info": redis_info or {},
                "cache_prefixes": {
                    "answer": CACHE_PREFIX_ANSWER,
                    "image": CACHE_PREFIX_IMAGE,
                    "session": CACHE_PREFIX_SESSION
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"status": "error", "error": str(e)} 