import asyncio
import logging
import time
from typing import AsyncGenerator, Optional, Dict, Any
import sys
sys.path.append('/app/shared')

from shared.models.request_models import QuestionRequest
from shared.models.response_models import AnswerResponse
from shared.models.subject_models import SubjectType, SUBJECT_CONFIG
from app.services.llm_service import DashScopeService
from app.services.viz_client import VisualizationClient
from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)


class AnswerOrchestrator:
    """答案编排器 - 协调文字回答和可视化生成"""
    
    def __init__(self, llm_service: DashScopeService, viz_client: VisualizationClient, cache_service: CacheService):
        self.llm_service = llm_service
        self.viz_client = viz_client
        self.cache_service = cache_service
    
    def _is_error_response(self, text: str) -> bool:
        """检查响应是否是错误信息"""
        if not text:
            return True
        
        error_keywords = [
            "服务暂时不可用",
            "API调用失败", 
            "请求超时",
            "处理问题时出现错误",
            "未收到有效回答"
        ]
        
        # 检查是否包含错误关键词
        for keyword in error_keywords:
            if keyword in text:
                return True
        
        # 检查是否过短（可能是不完整的响应）
        if len(text.strip()) < 10:
            return True
            
        return False
    
    async def get_answer_stream(self, request: QuestionRequest) -> AsyncGenerator[str, None]:
        """获取流式文字回答"""
        # 先检查缓存
        cached_answer = await self.cache_service.get_cached_answer(request)
        if cached_answer:
            logger.info("Returning cached answer")
            # 模拟流式输出缓存的答案
            for i in range(0, len(cached_answer), 10):
                chunk = cached_answer[i:i+10]
                yield chunk
                await asyncio.sleep(0.01)
            return
        
        # 流式获取新答案
        full_answer = ""
        async for chunk in self.llm_service.get_answer_stream(request):
            full_answer += chunk
            yield chunk
        
        # 只缓存成功的答案，不缓存错误信息
        if full_answer and not self._is_error_response(full_answer):
            await self.cache_service.cache_answer(request, full_answer)
            logger.info("Cached successful answer")
        else:
            logger.warning("Not caching answer due to error or empty response")
    
    async def process_question(self, request: QuestionRequest) -> AnswerResponse:
        """处理问题 - 非流式版本"""
        start_time = time.time()
        
        try:
            # 检查缓存
            cached_answer = await self.cache_service.get_cached_answer(request)
            if cached_answer:
                text_answer = cached_answer
                logger.info("Using cached answer")
            else:
                # 获取新答案
                text_answer = await self.llm_service.get_answer(request)
                
                # 只缓存成功的答案，不缓存错误信息
                if text_answer and not self._is_error_response(text_answer):
                    await self.cache_service.cache_answer(request, text_answer)
                    logger.info("Cached successful answer")
                else:
                    logger.warning("Not caching answer due to error or empty response")
            
            # 检查答案是否是错误信息
            success = not self._is_error_response(text_answer)
            
            # 尝试生成可视化（只有成功的答案才尝试）
            image_info = None
            if success:
                image_info = await self.try_generate_visualization(request, text_answer)
            
            processing_time = time.time() - start_time
            
            return AnswerResponse(
                success=success,
                text_answer=text_answer,
                subject=request.subject,
                processing_time=processing_time,
                has_visualization=bool(image_info),
                image_url=image_info.get("url") if image_info else None,
                image_id=image_info.get("id") if image_info else None
            )
            
        except Exception as e:
            logger.error(f"Error processing question: {e}")
            processing_time = time.time() - start_time
            
            return AnswerResponse(
                success=False,
                text_answer=f"处理问题时出现错误: {str(e)}",
                subject=request.subject,
                processing_time=processing_time,
                has_visualization=False
            )
    
    async def try_generate_visualization(self, request: QuestionRequest, answer_text: str = "") -> Optional[Dict[str, Any]]:
        """尝试生成可视化（不影响主流程）"""
        try:
            # 检查学科是否支持可视化
            subject_config = SUBJECT_CONFIG.get(request.subject)
            if not subject_config or not subject_config.get("supports_visualization"):
                return None
            
            # 检查是否需要可视化
            need_viz = await self.viz_client.check_need_visualization(request)
            if not need_viz:
                return None
            
            # 生成可视化
            image_info = await self.viz_client.generate_visualization(request, answer_text)
            
            if image_info:
                # 缓存图片信息
                await self.cache_service.cache_image(
                    image_info["id"], 
                    image_info
                )
                logger.info(f"Generated visualization: {image_info['id']}")
            
            return image_info
            
        except Exception as e:
            logger.warning(f"Visualization generation failed (non-critical): {e}")
            return None
    
    def _should_generate_visualization(self, request: QuestionRequest, answer_text: str) -> bool:
        """判断是否应该生成可视化"""
        # 检查学科配置
        subject_config = SUBJECT_CONFIG.get(request.subject)
        if not subject_config or not subject_config.get("supports_visualization"):
            return False
        
        # 检查关键词
        keywords = subject_config.get("visualization_keywords", [])
        text_to_check = (request.text or "") + " " + answer_text
        
        for keyword in keywords:
            if keyword in text_to_check:
                return True
        
        return False 