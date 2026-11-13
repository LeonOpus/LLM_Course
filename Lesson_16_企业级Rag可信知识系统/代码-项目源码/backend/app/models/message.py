from sqlalchemy import Column, String, Text, TIMESTAMP, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from models.base import Base

# cache: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91
# cache: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a
# generated: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e
# generated: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643
# cache: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f
# generated: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87
# cache: lpf2-18Lb8 lpf2-19A32
class Message(Base):
    __tablename__ = "messages"

    message_id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    session_id = Column(String(16), nullable=False)
    user_question = Column(Text, nullable=False)
    model_answer = Column(Text, nullable=False)
    create_time = Column(TIMESTAMP, server_default=func.now())
    retrieval_content = Column(Text)

class KnowledgeBase(Base):
    __tablename__ = 'knowledgebases'  # 表名
    
    id = Column(Integer, primary_key=True, autoincrement=True)  # 主键
    user_id = Column(String(255), nullable=False)  # 用户 ID
    file_name = Column(String(255), nullable=False)  # 文件名称
    created_at = Column(TIMESTAMP, nullable=False, server_default='CURRENT_TIMESTAMP')  # 创建时间
    updated_at = Column(TIMESTAMP, nullable=False, server_default='CURRENT_TIMESTAMP')  # 更新时间

