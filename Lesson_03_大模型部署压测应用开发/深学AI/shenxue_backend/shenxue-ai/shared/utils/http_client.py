import httpx
import asyncio
import logging
from typing import Optional, Dict, Any
import json

logger = logging.getLogger(__name__)


class AsyncHTTPClient:
    """异步HTTP客户端封装"""
    
    def __init__(self, timeout: float = 30.0, max_retries: int = 3):
        self.timeout = httpx.Timeout(timeout)
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None
    
    async def get_client(self) -> httpx.AsyncClient:
        """获取HTTP客户端"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client
    
    async def close(self):
        """关闭客户端"""
        if self._client:
            await self._client.aclose()
    
    async def post_json(
        self, 
        url: str, 
        data: Dict[str, Any], 
        headers: Optional[Dict[str, str]] = None,
        retry_on_failure: bool = True
    ) -> Optional[Dict[str, Any]]:
        """发送POST JSON请求"""
        
        default_headers = {"Content-Type": "application/json"}
        if headers:
            default_headers.update(headers)
        
        for attempt in range(self.max_retries if retry_on_failure else 1):
            try:
                client = await self.get_client()
                response = await client.post(
                    url,
                    json=data,
                    headers=default_headers
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"HTTP {response.status_code}: {response.text}")
                    if not retry_on_failure:
                        return None
                        
            except httpx.TimeoutException:
                logger.warning(f"HTTP timeout on attempt {attempt + 1}")
                if not retry_on_failure:
                    return None
            except Exception as e:
                logger.error(f"HTTP error on attempt {attempt + 1}: {e}")
                if not retry_on_failure:
                    return None
            
            if attempt < self.max_retries - 1:
                await asyncio.sleep(1)  # 重试前等待
        
        return None
    
    async def get(
        self, 
        url: str, 
        headers: Optional[Dict[str, str]] = None,
        retry_on_failure: bool = True
    ) -> Optional[httpx.Response]:
        """发送GET请求"""
        
        for attempt in range(self.max_retries if retry_on_failure else 1):
            try:
                client = await self.get_client()
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    return response
                else:
                    logger.warning(f"HTTP {response.status_code}: {response.text}")
                    if not retry_on_failure:
                        return None
                        
            except httpx.TimeoutException:
                logger.warning(f"HTTP timeout on attempt {attempt + 1}")
                if not retry_on_failure:
                    return None
            except Exception as e:
                logger.error(f"HTTP error on attempt {attempt + 1}: {e}")
                if not retry_on_failure:
                    return None
            
            if attempt < self.max_retries - 1:
                await asyncio.sleep(1)
        
        return None 