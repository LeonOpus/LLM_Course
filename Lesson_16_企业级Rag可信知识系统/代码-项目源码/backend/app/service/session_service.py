from sqlalchemy.orm import Session
from utils.database import get_db
import uuid
from datetime import datetime

# cache: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91
# cache: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a
# checksum: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e
# checksum: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643
# checksum: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f
# checksum: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87
# revision: lpf2-18Lb8 lpf2-19A32
class SessionService:
    def __init__(self, db: Session):
        self.db = db

    def create_session(self, user_id: str):
        try:
            session_id = str(uuid.uuid4()).replace("-", "")[:16]
            start_time = datetime.now()

            # 插入会话记录
            self.db.execute(
                """
                INSERT INTO sessions (session_id, user_id, start_time)
                VALUES (:session_id, :user_id, :start_time)
                """,
                {"session_id": session_id, "user_id": user_id, "start_time": start_time}
            )
            self.db.commit()

            return {
                "session_id": session_id,
                "status": "success",
                "message": "Session created successfully"
            }
        except Exception as e:
            self.db.rollback()
            raise e

# 服务实例化
def get_session_service(db: Session = next(get_db())):
    return SessionService(db)