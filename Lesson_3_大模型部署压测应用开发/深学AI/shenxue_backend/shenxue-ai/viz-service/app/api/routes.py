from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import logging
import sys
sys.path.append('/app/shared')

from shared.models.subject_models import SubjectType, SUBJECT_CONFIG
from app.services.visualization_engine import VisualizationEngine
from app.services.need_checker import NeedChecker
from app.models.viz_models import CheckRequest, GenerateRequest, CheckResponse, GenerateResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# 初始化服务
viz_engine = VisualizationEngine()
need_checker = NeedChecker()


@router.post("/check", response_model=CheckResponse)
async def check_need_visualization(request: CheckRequest):
    """检查是否需要可视化"""
    try:
        need_viz = await need_checker.check_need(request)
        
        return CheckResponse(
            need_visualization=need_viz,
            confidence=0.8 if need_viz else 0.2,
            reason="基于关键词和学科类型判断" if need_viz else "未检测到可视化需求"
        )
        
    except Exception as e:
        logger.error(f"Error checking visualization need: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate", response_model=GenerateResponse)
async def generate_visualization(request: GenerateRequest):
    """生成可视化图片"""
    try:
        result = await viz_engine.generate_visualization(request)
        
        if result:
            return GenerateResponse(
                success=True,
                image_id=result["image_id"],
                image_url=result["image_url"],
                local_path=result["local_path"],
                generation_time=result.get("generation_time", 0)
            )
        else:
            return GenerateResponse(
                success=False,
                error_message="无法生成可视化图片"
            )
            
    except Exception as e:
        logger.error(f"Error generating visualization: {e}")
        return GenerateResponse(
            success=False,
            error_message=str(e)
        )


@router.get("/images/{image_id}")
async def get_image(image_id: str):
    """获取图片文件"""
    try:
        image_path = viz_engine.get_image_path(image_id)
        
        if image_path and image_path.exists():
            return FileResponse(
                path=str(image_path),
                media_type="image/png",
                filename=f"{image_id}.png"
            )
        else:
            raise HTTPException(status_code=404, detail="Image not found")
            
    except Exception as e:
        logger.error(f"Error serving image: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/images/{image_id}/info")
async def get_image_info(image_id: str):
    """获取图片信息"""
    try:
        info = await viz_engine.get_image_info(image_id)
        
        if info:
            return info
        else:
            raise HTTPException(status_code=404, detail="Image not found")
            
    except Exception as e:
        logger.error(f"Error getting image info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_stats():
    """获取服务统计信息"""
    try:
        stats = await viz_engine.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return {"error": str(e)} 