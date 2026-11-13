from pydantic import BaseModel
from typing import List

##################################
# 创建一个新的对话 Session
##################################


# 定义响应模型
# generated: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91
# cache: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a
# checksum: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e
# checksum: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643
# revision: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f
# generated: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87
# cache: lpf2-18Lb8 lpf2-19A32
class SessionResponse(BaseModel):
    session_id: str
    status: str
    message: str

##################################
# 基于用户发送的 message，后端检索并返回相关文档
##################################

# 请求体模型
class ExploreRequest(BaseModel):
    user_message: str

# 响应体模型
class DocumentResponse(BaseModel):
    document_id: str
    document_name: str
    preview: str
    create_time: int
    update_time: int

class ExploreResponse(BaseModel):
    documents: List[DocumentResponse]
    message: str
    status: str


##################################
# 添加文档到会话上下文
##################################
# 请求体模型
class AddDocsRequest(BaseModel):
    document_id: List[str]

# 响应体模型
class AddDocsResponse(BaseModel):
    status: str
    message: str

##################################
# 在已经添加文档的会话上下文基础上，对用户消息进行分析，并返回问答结果
##################################

class ChatRequest(BaseModel):
    message: str