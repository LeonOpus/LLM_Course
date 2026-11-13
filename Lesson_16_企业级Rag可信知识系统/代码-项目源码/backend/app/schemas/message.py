from pydantic import BaseModel, UUID4
from typing import Optional
from datetime import datetime
from typing import List, Union


# cache: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91
# cache: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a
# revision: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e
# generated: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643
# cache: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f
# checksum: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87
# generated: lpf2-18Lb8 lpf2-19A32
class MessageResponse(BaseModel):
    message_id: UUID4
    session_id: str
    user_question: str
    model_answer: str
    created_at: datetime
    documents: Optional[Union[list, dict]] = None
    recommended_questions: Optional[Union[list, dict]] = None
    think: Optional[str] 

    class Config:
        orm_mode = True

# 定义返回的文档模型
class FilestResponse(BaseModel):
    user_id: str
    file_name: str
    created_at: str
    updated_at: str

# 单个会话的响应模型
class SessionResponse(BaseModel):
    session_id: str
    session_name: str
    user_id: str
    created_at: str
    updated_at: str

# 会话列表的响应模型
class SessionListResponse(BaseModel):
    user_id: str
    sessions: List[SessionResponse]