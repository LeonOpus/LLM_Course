"""
金融研报自动化分析师 - 配置文件
自动从 .env 文件或环境变量读取配置
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # API Keys（从 .env 或环境变量读取）
    DASHSCOPE_API_KEY: str = ""      # 阿里云 DashScope
    BOCHAAI_API_KEY: str = ""        # 博查搜索

    # LLM配置
    LLM_MODEL: str = "qwen-max"
    LLM_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    # Embedding配置
    EMBEDDING_MODEL: str = "text-embedding-v4"
    EMBEDDING_DIMENSIONS: int = 1024

    # 博查搜索配置
    BOCHAAI_BASE_URL: str = "https://api.bochaai.com/v1"

    # 数据库配置
    DATABASE_URL: str = "sqlite:///./database/finance.db"
    DATABASE_PATH: str = "./database/finance.db"

    # Milvus配置
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    MILVUS_COLLECTION: str = "finance_reports"

    # PDF路径
    SAMPLE_PDF_PATH: str = "data/中金公司2025年中期报告.pdf"

    # 代码执行器配置
    CODE_EXECUTOR_TIMEOUT: int = 30
    CODE_EXECUTOR_MAX_OUTPUT: int = 10000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # 忽略 .env 中多余的变量


settings = Settings()


# 打印配置状态（调试用）
def print_config_status():
    print("=" * 50)
    print("配置状态")
    print("=" * 50)
    print(f"DASHSCOPE_API_KEY: {'已设置' if settings.DASHSCOPE_API_KEY else '未设置'}")
    print(f"BOCHAAI_API_KEY: {'已设置' if settings.BOCHAAI_API_KEY else '未设置'}")
    print(f"数据库路径: {settings.DATABASE_PATH}")
    print("=" * 50)
