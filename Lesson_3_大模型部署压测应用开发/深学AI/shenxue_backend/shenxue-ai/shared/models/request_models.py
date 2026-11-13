from pydantic import BaseModel, Field
from typing import Optional
from .subject_models import SubjectType


class QuestionRequest(BaseModel):
    """问题请求模型"""
    subject: Optional[SubjectType] = Field(SubjectType.GENERAL, description="学科类型，选填，默认为通用")
    text: Optional[str] = Field(None, description="问题文本，选填")
    image_url: Optional[str] = Field(None, description="图片地址，选填")
    stream: bool = Field(True, description="是否使用流式输出")
    
    class Config:
        json_schema_extra = {
            "example": {
                "subject": "math",
                "text": "求解方程 x² - 5x + 6 = 0",
                "stream": True
            }
        } 