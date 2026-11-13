from pydantic import BaseModel, Field
from typing import Optional
import sys
sys.path.append('/app/shared')

from shared.models.subject_models import SubjectType


class CheckRequest(BaseModel):
    """检查是否需要可视化的请求模型"""
    subject: SubjectType = Field(..., description="学科类型")
    text: str = Field(..., description="问题文本")


class CheckResponse(BaseModel):
    """检查结果响应模型"""
    need_visualization: bool = Field(..., description="是否需要可视化")
    confidence: float = Field(..., description="置信度 0-1")
    reason: str = Field(..., description="判断原因")


class GenerateRequest(BaseModel):
    """生成可视化的请求模型"""
    subject: SubjectType = Field(..., description="学科类型")
    text: str = Field(..., description="问题文本")
    answer_text: str = Field(..., description="答案文本")


class GenerateResponse(BaseModel):
    """生成结果响应模型"""
    success: bool = Field(..., description="是否成功")
    image_id: Optional[str] = Field(None, description="图片ID")
    image_url: Optional[str] = Field(None, description="图片访问URL")
    local_path: Optional[str] = Field(None, description="本地路径")
    generation_time: Optional[float] = Field(None, description="生成时间（秒）")
    error_message: Optional[str] = Field(None, description="错误信息") 