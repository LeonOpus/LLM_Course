from pydantic_settings import BaseSettings
from typing import Optional
import os
from pathlib import Path


DEFAULT_STATIC_FILES_PATH = (
    "/app/static"
    if os.path.isdir("/app")
    else str(Path(__file__).resolve().parents[3] / "viz-service" / "static")
)


class Settings(BaseSettings):
    """应用配置"""
    
    # 基础配置
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    
    # 阿里云百炼API配置
    DASHSCOPE_API_KEY: str
    DASHSCOPE_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    DASHSCOPE_MODEL: str = "qwen-vl-max"
    
    # Redis配置
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_PASSWORD: Optional[str] = None
    
    # 服务配置
    VIZ_SERVICE_URL: str = "http://viz-service:8001"
    VIZ_SERVICE_BASE_URL: str = "http://localhost:8000"
    STATIC_FILES_PATH: str = DEFAULT_STATIC_FILES_PATH
    
    # 超时配置
    LLM_TIMEOUT: int = 30
    LLM_SYNC_TIMEOUT: int = 90  # 非流式请求的超时时间，更长
    VIZ_TIMEOUT: int = 15
    
    # 重试配置
    LLM_MAX_RETRIES: int = 3
    VIZ_MAX_RETRIES: int = 2
    
    # 缓存配置
    CACHE_TTL: int = 3600
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# 全局配置实例
settings = Settings()
