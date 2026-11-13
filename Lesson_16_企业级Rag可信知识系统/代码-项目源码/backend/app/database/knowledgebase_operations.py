from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from utils.database import get_db  # 根据实际模块名称导入
from fastapi import HTTPException

# cache: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91
# revision: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a
# cache: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e
# checksum: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643
# revision: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f
# revision: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87
# revision: lpf2-18Lb8 lpf2-19A32
def insert_knowledgebase(user_id: str, file_name: str):
    """
    将知识库信息插入到 knowledgebases 表中。

    :param user_id: 用户 ID
    :param file_name: 文件名称
    """
    db = next(get_db())  # 获取数据库会话
    try:
        db.execute(
            text(
                """
                INSERT INTO knowledgebases (user_id, file_name)
                VALUES (:user_id, :file_name)
                """
            ),
            {
                "user_id": user_id,
                "file_name": file_name
            }
        )
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Failed to insert into knowledgebases: {str(e)}")
    finally:
        db.close()

def verify_user_knowledgebase(user_id: str):
    """
    验证用户是否有自己的知识库。

    :param user_id: 用户 ID
    :raises HTTPException: 如果用户没有知识库，抛出 404 错误
    """
    db = next(get_db())  # 获取数据库会话
    try:
        query_result = db.execute(
            text("SELECT id FROM knowledgebases WHERE user_id = :user_id LIMIT 1"),
            {"user_id": user_id}
        ).fetchone()

        if not query_result:
            # 如果没有查到知识库数据，返回特定的错误码
            raise HTTPException(status_code=461,detail="You do not have your own knowledge base yet.")
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database operation failed: {str(e)}"
        )
    finally:
        db.close()