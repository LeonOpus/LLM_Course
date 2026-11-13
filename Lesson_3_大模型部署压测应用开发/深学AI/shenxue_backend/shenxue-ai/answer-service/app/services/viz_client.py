import logging
import httpx
from typing import Optional, Dict, Any
import sys
sys.path.append('/app/shared')

from shared.models.request_models import QuestionRequest

logger = logging.getLogger(__name__)


class VisualizationClient:
    """可视化服务客户端"""
    
    def __init__(self, viz_service_url: str, timeout: int = 15, max_retries: int = 2):
        self.viz_service_url = viz_service_url
        self.timeout = timeout
        self.max_retries = max_retries
    
    async def check_need_visualization(self, request: QuestionRequest) -> bool:
        """检查是否需要可视化"""
        try:
            check_data = {
                "subject": request.subject.value,
                "text": request.text or "",
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.viz_service_url}/v1/check",
                    json=check_data
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get("need_visualization", False)
                else:
                    logger.warning(f"Visualization check failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error checking visualization need: {e}")
            return False
    
    async def generate_visualization(self, request: QuestionRequest, answer_text: str = "") -> Optional[Dict[str, Any]]:
        """生成可视化"""
        try:
            generate_data = {
                "subject": request.subject.value,  
                "text": request.text or "",
                "answer_text": answer_text,
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.viz_service_url}/v1/generate",
                    json=generate_data
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("success"):
                        return {
                            "id": result.get("image_id"),
                            "url": result.get("image_url"),
                            "local_path": result.get("local_path")
                        }
                    else:
                        logger.warning(f"Visualization generation failed: {result.get('error_message')}")
                        return None
                else:
                    logger.error(f"Visualization service error: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error generating visualization: {e}")
            return None
    
    async def get_image_info(self, image_id: str) -> Optional[Dict[str, Any]]:
        """获取图片信息"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.viz_service_url}/v1/images/{image_id}"
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"Get image info failed: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting image info: {e}")
            return None 