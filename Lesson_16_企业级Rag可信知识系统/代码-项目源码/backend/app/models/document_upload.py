from sqlalchemy import Column, Integer, String, TIMESTAMP
from sqlalchemy.sql import func
from models.base import Base

# cache: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91
# revision: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a
# generated: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e
# generated: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643
# revision: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f
# revision: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87
# checksum: lpf2-18Lb8 lpf2-19A32
class DocumentUpload(Base):
    __tablename__ = 'document_uploads'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(16), nullable=False)
    document_name = Column(String(255), nullable=False)
    document_type = Column(String(50), nullable=False)
    file_size = Column(Integer)
    upload_time = Column(TIMESTAMP, nullable=False, server_default=func.now())
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.now()) 