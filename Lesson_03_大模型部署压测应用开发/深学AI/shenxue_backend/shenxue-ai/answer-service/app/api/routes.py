from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Form
from fastapi.responses import StreamingResponse
import json
import asyncio
import logging
import time
import sys
import os
import uuid
from typing import Optional, Union
sys.path.append('/app/shared')

from shared.models.request_models import QuestionRequest
from shared.models.response_models import AnswerResponse, StreamResponse, ErrorResponse
from shared.utils.constants import *
from app.core.config import settings
from app.core.dependencies import get_answer_orchestrator
from app.services.answer_orchestrator import AnswerOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter()

# 上传目录配置
UPLOAD_DIR = os.path.join(settings.STATIC_FILES_PATH, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/ask")
async def ask_question_stream(
    # 支持JSON请求
    request: Optional[QuestionRequest] = None,
    # 支持表单上传
    subject: Optional[str] = Form(None),
    text: Optional[str] = Form(None),
    image_url: Optional[str] = Form(None, description="图片URL地址"),
    stream: Optional[bool] = Form(None),
    image: Optional[UploadFile] = File(None),
    orchestrator: AnswerOrchestrator = Depends(get_answer_orchestrator)
):
    """
    问答接口 - 支持流式输出和文件上传
    
    支持两种请求方式：
    1. JSON请求（application/json）:
       - subject: 学科类型 (选填，默认为通用)
       - text: 问题文本 (选填)
       - image_url: 图片地址 (选填)
       - stream: 是否使用流式输出 (默认True)
    
    2. 文件上传请求（multipart/form-data）:
       - subject: 学科类型 (选填，默认为通用)
       - text: 问题文本 (选填)
       - image_url: 图片URL地址 (选填)
       - image: 上传的图片文件 (选填)
       - stream: 是否使用流式输出 (默认True)
    
    注意：text、image_url、image 至少需要提供一个
    """
    
    # 判断请求类型并处理参数
    if request is None:
        # 表单请求 (multipart/form-data)
        # 参数验证
        if not text and not image and not image_url:
            raise HTTPException(
                status_code=400,
                detail="text、image 和 image_url 至少需要提供一个"
            )
        
        # 验证学科类型（如果提供了的话）
        subject_enum = None
        if subject:
            try:
                from shared.models.subject_models import SubjectType
                subject_enum = SubjectType(subject)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"不支持的学科类型: {subject}"
                )
        else:
            # 如果没有提供学科类型，使用默认的通用类型
            from shared.models.subject_models import SubjectType
            subject_enum = SubjectType.GENERAL
        
        # 处理图片
        final_image_url = None
        
        # 优先处理上传的文件
        if image:
            # 验证文件类型
            if not image.content_type or not image.content_type.startswith('image/'):
                raise HTTPException(
                    status_code=400,
                    detail="只支持图片文件"
                )
            
            # 验证文件大小 (最大10MB)
            MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
            content = await image.read()
            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail="文件大小不能超过10MB"
                )
            
            # 生成唯一文件名
            file_extension = image.filename.split('.')[-1] if image.filename and '.' in image.filename else 'jpg'
            unique_filename = f"{uuid.uuid4()}.{file_extension}"
            file_path = os.path.join(UPLOAD_DIR, unique_filename)
            
            # 保存文件
            with open(file_path, "wb") as f:
                f.write(content)
            
            # 生成本地文件路径，参考阿里云百炼API的本地文件格式
            final_image_url = f"file://{file_path}"
            logger.info(f"Saved uploaded image: {file_path}")
            
        # 如果没有上传文件，但有image_url，则使用image_url
        elif image_url:
            final_image_url = image_url
            logger.info(f"Using provided image_url: {image_url}")
        
        # 创建请求对象
        final_request = QuestionRequest(
            subject=subject_enum,
            text=text,
            image_url=final_image_url,
            stream=stream if stream is not None else True
        )
        
        logger.info(f"Processing form request: subject={subject}, has_image={image is not None}, has_image_url={image_url is not None}, stream={stream}")
        
    else:
        # JSON请求 (application/json)
        # 参数验证
        if not request.text and not request.image_url:
            raise HTTPException(
                status_code=400, 
                detail="text 和 image_url 至少需要提供一个"
            )
        
        final_request = request
        logger.info(f"Processing JSON request: subject={request.subject}, stream={request.stream}")
    
    if final_request.stream:
        # 流式响应
        return StreamingResponse(
            stream_answer(final_request, orchestrator),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
            }
        )
    else:
        # 非流式响应
        try:
            response = await orchestrator.process_question(final_request)
            return response
        except Exception as e:
            logger.error(f"Error processing question: {e}")
            raise HTTPException(status_code=500, detail=str(e))


async def stream_answer(request: QuestionRequest, orchestrator: AnswerOrchestrator):
    """流式回答生成器"""
    start_time = time.time()
    
    try:
        # 发送开始事件
        yield format_sse_data({
            "type": "start",
            "content": "开始处理您的问题...",
            "metadata": {"timestamp": start_time}
        })
        
        # 流式获取文字回答
        full_text = ""
        async for text_chunk in orchestrator.get_answer_stream(request):
            full_text += text_chunk
            
            # 发送文本块
            yield format_sse_data({
                "type": STREAM_TYPE_TEXT,
                "content": text_chunk,
                "metadata": {"chunk_length": len(text_chunk)}
            })
            
            # 小延迟，避免过快发送
            await asyncio.sleep(0.01)
        
        # 尝试生成可视化（如果需要）
        try:
            image_info = await orchestrator.try_generate_visualization(request)
            
            if image_info:
                yield format_sse_data({
                    "type": STREAM_TYPE_IMAGE,
                    "content": image_info.get("url", ""),
                    "metadata": {
                        "image_id": image_info.get("id"),
                        "image_url": image_info.get("url")
                    }
                })
            
        except Exception as viz_error:
            logger.warning(f"Visualization generation failed: {viz_error}")
            yield format_sse_data({
                "type": "warning",
                "content": f"图片生成失败: {str(viz_error)}",
                "metadata": {"error_type": "visualization"}
            })
        
        # 发送完成事件
        processing_time = time.time() - start_time
        yield format_sse_data({
            "type": STREAM_TYPE_DONE,
            "content": "处理完成",
            "metadata": {
                "total_time": processing_time,
                "text_length": len(full_text),
                "subject": request.subject
            }
        })
        
    except Exception as e:
        logger.error(f"Stream processing error: {e}")
        yield format_sse_data({
            "type": STREAM_TYPE_ERROR,
            "content": f"处理过程中出现错误: {str(e)}",
            "metadata": {"error_type": "processing"}
        })


def format_sse_data(data: dict) -> str:
    """格式化SSE数据"""
    json_data = json.dumps(data, ensure_ascii=False)
    return f"data: {json_data}\n\n"


@router.get("/subjects")
async def get_supported_subjects():
    """获取支持的学科列表"""
    from shared.models.subject_models import SUBJECT_CONFIG
    
    subjects = []
    for subject_type, config in SUBJECT_CONFIG.items():
        subjects.append({
            "code": subject_type.value,
            "name": config["name"],
            "supports_visualization": config["supports_visualization"]
        })
    
    return {"subjects": subjects}


@router.post("/ask/sync")
async def ask_question_sync(
    request: QuestionRequest,
    orchestrator: AnswerOrchestrator = Depends(get_answer_orchestrator)
):
    """
    同步问答接口 - 返回完整结果
    """
    try:
        # 强制设置为非流式
        request.stream = False
        response = await orchestrator.process_question(request)
        return response
    except Exception as e:
        logger.error(f"Sync processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cache/stats")
async def get_cache_stats():
    """获取缓存统计信息"""
    try:
        from app.core.dependencies import get_cache_service
        cache_service = get_cache_service()
        stats = await cache_service.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Cache stats error: {e}")
        return {"error": str(e)}


@router.delete("/cache/clear")
async def clear_all_caches():
    """清除所有缓存（紧急情况使用）"""
    try:
        from app.core.dependencies import get_cache_service
        cache_service = get_cache_service()
        success = await cache_service.flush_all_caches()
        
        if success:
            return {"message": "所有缓存已清除", "success": True}
        else:
            return {"message": "清除缓存失败", "success": False}
            
    except Exception as e:
        logger.error(f"Clear cache error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cache/errors")
async def clear_error_caches():
    """清除错误缓存"""
    try:
        from app.core.dependencies import get_cache_service
        cache_service = get_cache_service()
        cleared_count = await cache_service.clear_error_caches()
        
        return {
            "message": f"已尝试清除错误缓存",
            "cleared_count": cleared_count,
            "note": "建议使用 DELETE /v1/cache/clear 清除所有缓存"
        }
        
    except Exception as e:
        logger.error(f"Clear error cache error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 
