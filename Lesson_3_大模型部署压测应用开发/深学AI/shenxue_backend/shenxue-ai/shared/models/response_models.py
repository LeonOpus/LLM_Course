from pydantic import BaseModel, Field
from typing import Optional, List, Any
from .subject_models import SubjectType


class AnswerResponse(BaseModel):
    """完整答案响应模型"""
    # 核心响应（必定返回）
    success: bool = Field(..., description="请求是否成功")
    text_answer: str = Field(..., description="文字答案")
    subject: SubjectType = Field(..., description="学科类型")
    processing_time: float = Field(..., description="处理时间（秒）")
    
    # 图片相关（可选）
    has_visualization: bool = Field(False, description="是否包含可视化图片")
    image_url: Optional[str] = Field(None, description="图片访问URL")
    image_id: Optional[str] = Field(None, description="图片ID")
    
    # 错误信息（可选）
    visualization_error: Optional[str] = Field(None, description="可视化生成错误信息")
    warnings: Optional[List[str]] = Field(None, description="警告信息")


class StreamResponse(BaseModel):
    """流式响应模型"""
    type: str = Field(..., description="响应类型: text, image, error, done")
    content: str = Field(..., description="响应内容")
    metadata: Optional[dict] = Field(None, description="元数据")
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "type": "text",
                    "content": "这是一个二次方程...",
                    "metadata": {"chunk_index": 1}
                },
                {
                    "type": "image", 
                    "content": "/images/abc123.png",
                    "metadata": {"image_id": "abc123"}
                },
                {
                    "type": "done",
                    "content": "处理完成",
                    "metadata": {"total_time": 2.5}
                }
            ]
        }


class ErrorResponse(BaseModel):
    """错误响应模型"""
    success: bool = Field(False, description="请求失败")
    error_code: str = Field(..., description="错误代码")
    error_message: str = Field(..., description="错误信息")
    details: Optional[dict] = Field(None, description="错误详情") 