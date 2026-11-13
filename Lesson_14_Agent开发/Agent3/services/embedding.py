"""
Embedding服务封装 - 使用阿里text-embedding-v4
"""
from typing import List, Union
from openai import OpenAI
from config import settings


class EmbeddingService:
    """Embedding服务类"""

    def __init__(self):
        if not settings.DASHSCOPE_API_KEY:
            raise ValueError("DASHSCOPE_API_KEY 未设置，请在 .env 文件中配置")

        self.client = OpenAI(
            api_key=settings.DASHSCOPE_API_KEY,
            base_url=settings.LLM_BASE_URL
        )
        self.model = settings.EMBEDDING_MODEL
        self.dimensions = settings.EMBEDDING_DIMENSIONS
    
    def embed(self, text: Union[str, List[str]]) -> List[List[float]]:
        """
        生成文本向量
        
        Args:
            text: 单个文本或文本列表
        
        Returns:
            向量列表
        """
        if isinstance(text, str):
            text = [text]
        
        response = self.client.embeddings.create(
            model=self.model,
            input=text,
            dimensions=self.dimensions,
            encoding_format="float"
        )
        
        embeddings = [item.embedding for item in response.data]
        return embeddings
    
    def embed_single(self, text: str) -> List[float]:
        """
        生成单个文本的向量
        
        Args:
            text: 文本
        
        Returns:
            向量
        """
        return self.embed(text)[0]


# 单例模式
_embedding_service = None


def get_embedding_service() -> EmbeddingService:
    """获取Embedding服务单例"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
