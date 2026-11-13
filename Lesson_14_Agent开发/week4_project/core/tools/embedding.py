"""
Embedding服务
使用阿里云text-embedding-v4模型
"""
import logging
from typing import List, Union, Optional
from openai import OpenAI
import numpy as np
import sys
sys.path.append(str(__file__).rsplit('/', 3)[0])

from config import DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL, EMBEDDING_MODEL, EMBEDDING_DIMENSIONS

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Embedding服务类
    使用阿里云text-embedding-v4模型进行文本向量化
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = EMBEDDING_MODEL,
        dimensions: int = EMBEDDING_DIMENSIONS
    ):
        self.api_key = api_key or DASHSCOPE_API_KEY
        self.base_url = base_url or DASHSCOPE_BASE_URL
        self.model = model
        self.dimensions = dimensions

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

        logger.info(f"[Embedding] 初始化EmbeddingService")
        logger.info(f"[Embedding] Model: {self.model}, Dimensions: {self.dimensions}")
        logger.info(f"[Embedding] Base URL: {self.base_url}")

    def embed_text(self, text: str) -> List[float]:
        """
        将单个文本转换为向量

        Args:
            text: 输入文本

        Returns:
            向量列表
        """
        logger.info(f"[Embedding] 处理文本: '{text[:50]}...' (长度: {len(text)})")

        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
                dimensions=self.dimensions,
                encoding_format="float"
            )

            embedding = response.data[0].embedding
            logger.info(f"[Embedding] 生成向量成功, 维度: {len(embedding)}")

            return embedding

        except Exception as e:
            logger.error(f"[Embedding] 向量化失败: {str(e)}")
            raise

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        批量将文本转换为向量

        Args:
            texts: 文本列表

        Returns:
            向量列表
        """
        logger.info(f"[Embedding] 批量处理 {len(texts)} 条文本")

        try:
            # 阿里云API支持批量处理
            response = self.client.embeddings.create(
                model=self.model,
                input=texts,
                dimensions=self.dimensions,
                encoding_format="float"
            )

            embeddings = [item.embedding for item in response.data]
            logger.info(f"[Embedding] 批量处理完成, 生成 {len(embeddings)} 个向量")

            return embeddings

        except Exception as e:
            logger.error(f"[Embedding] 批量向量化失败: {str(e)}")
            raise

    def compute_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """
        计算两个向量的余弦相似度

        Args:
            embedding1: 第一个向量
            embedding2: 第二个向量

        Returns:
            余弦相似度 (-1 到 1)
        """
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)

        # 计算余弦相似度
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = dot_product / (norm1 * norm2)
        logger.debug(f"[Embedding] 计算相似度: {similarity:.4f}")

        return float(similarity)

    def find_most_similar(
        self,
        query_embedding: List[float],
        candidate_embeddings: List[List[float]],
        top_k: int = 5
    ) -> List[tuple]:
        """
        在候选向量中找到最相似的top_k个

        Args:
            query_embedding: 查询向量
            candidate_embeddings: 候选向量列表
            top_k: 返回数量

        Returns:
            [(index, similarity), ...] 索引和相似度的列表
        """
        logger.info(f"[Embedding] 在 {len(candidate_embeddings)} 个候选中查找Top-{top_k}")

        similarities = []
        for i, candidate in enumerate(candidate_embeddings):
            sim = self.compute_similarity(query_embedding, candidate)
            similarities.append((i, sim))

        # 按相似度降序排序
        similarities.sort(key=lambda x: x[1], reverse=True)

        result = similarities[:top_k]
        logger.info(f"[Embedding] Top-{top_k} 相似度: {[f'{s:.4f}' for _, s in result]}")

        return result


# 测试代码
def test_embedding():
    """测试Embedding服务"""
    logger.info("=" * 50)
    logger.info("[TEST] 开始测试EmbeddingService")
    logger.info("=" * 50)

    service = EmbeddingService()

    # 测试单文本向量化
    print("\n=== 测试单文本向量化 ===")
    text = "低空经济是指以各种有人驾驶和无人驾驶航空器的低空飞行活动为牵引的综合性经济形态"
    embedding = service.embed_text(text)
    print(f"文本: {text}")
    print(f"向量维度: {len(embedding)}")
    print(f"向量前5个值: {embedding[:5]}")

    # 测试批量向量化
    print("\n=== 测试批量向量化 ===")
    texts = [
        "无人机配送已经成为物流行业的新趋势",
        "低空经济包括通用航空、无人机产业等多个领域",
        "今天天气很好，适合户外运动"
    ]
    embeddings = service.embed_texts(texts)
    print(f"处理 {len(texts)} 条文本")
    for i, t in enumerate(texts):
        print(f"  [{i}] {t[:30]}... -> 向量维度: {len(embeddings[i])}")

    # 测试相似度计算
    print("\n=== 测试相似度计算 ===")
    query = "无人机技术在物流领域的应用"
    query_embedding = service.embed_text(query)
    print(f"查询: {query}")

    for i, (t, emb) in enumerate(zip(texts, embeddings)):
        sim = service.compute_similarity(query_embedding, emb)
        print(f"  与 '{t[:30]}...' 的相似度: {sim:.4f}")

    # 测试找最相似
    print("\n=== 测试Top-K查找 ===")
    top_k = service.find_most_similar(query_embedding, embeddings, top_k=2)
    print(f"与查询最相似的Top-2:")
    for idx, sim in top_k:
        print(f"  [{idx}] {texts[idx][:30]}... (相似度: {sim:.4f})")

    logger.info("[TEST] EmbeddingService测试完成")
    return embedding


if __name__ == "__main__":
    test_embedding()
