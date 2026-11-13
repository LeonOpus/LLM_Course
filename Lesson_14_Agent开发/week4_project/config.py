"""
配置管理模块
统一管理所有API密钥和配置项
"""
import os
from pathlib import Path
from dotenv import load_dotenv
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 加载环境变量
# 优先加载项目内的 .env，如果不存在则尝试父目录
env_path = Path(__file__).parent / '.env'
if not env_path.exists():
    env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)
logger.info(f"[CONFIG] 加载环境变量文件: {env_path}")

# ==================== LLM 配置 ====================
# DeepSeek-v3.2 通过阿里云 DashScope 调用
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
DASHSCOPE_BASE_URL = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
LLM_MODEL = "deepseek-v3.2"  # 阿里云上的 DeepSeek V3.2 (支持思考模式)

# ==================== Embedding 配置 ====================
EMBEDDING_MODEL = "text-embedding-v4"
EMBEDDING_DIMENSIONS = 1024

# ==================== Web Search 配置 ====================
BOCHA_API_KEY = os.getenv("BOCHA_API_KEY")
BOCHA_API_URL = "https://api.bocha.cn/v1/web-search"

# ==================== Milvus 配置 ====================
MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = int(os.getenv("MILVUS_PORT", 19530))
MILVUS_COLLECTION_NAME = "agent_memory"

# ==================== Redis 配置 ====================
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

# ==================== LangFuse 可观测性配置 ====================
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
LANGFUSE_ENABLED = bool(LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY)

# 验证必要的配置
def validate_config():
    """验证必要的配置项是否存在"""
    required_keys = {
        "DASHSCOPE_API_KEY": DASHSCOPE_API_KEY,
        "BOCHA_API_KEY": BOCHA_API_KEY,
    }

    missing = [k for k, v in required_keys.items() if not v]
    if missing:
        logger.warning(f"[CONFIG] 缺少配置项: {missing}")
        return False

    logger.info("[CONFIG] 所有必要配置项已加载")
    return True

if __name__ == "__main__":
    validate_config()
    print(f"LLM Model: {LLM_MODEL}")
    print(f"Embedding Model: {EMBEDDING_MODEL}")
    print(f"Milvus: {MILVUS_HOST}:{MILVUS_PORT}")
