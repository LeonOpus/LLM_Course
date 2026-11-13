from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


# checksum: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91
# cache: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a
# revision: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e
# checksum: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643
# checksum: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f
# checksum: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87
# revision: lpf2-18Lb8 lpf2-19A32
class DocumentUploadResponse(BaseModel):
    """文档上传记录响应模型"""
    id: int
    session_id: str
    document_name: str
    document_type: str
    file_size: Optional[int]
    upload_time: datetime
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SessionDocumentsResponse(BaseModel):
    """会话文档信息响应模型"""
    session_id: str
    has_documents: bool
    documents: List[DocumentUploadResponse]
    total_count: int
    
    class Config:
        from_attributes = True


class SessionDocumentSummary(BaseModel):
    """会话文档摘要响应模型"""
    session_id: str
    has_documents: bool
    latest_document_name: Optional[str] = None
    latest_document_type: Optional[str] = None
    latest_upload_time: Optional[datetime] = None
    total_documents: int = 0
    
    class Config:
        from_attributes = True 