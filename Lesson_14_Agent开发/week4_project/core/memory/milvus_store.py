"""
Milvus向量数据库存储
实现记忆的存储、检索、删除和混合检索功能
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
from dataclasses import dataclass, field
from pymilvus import (
    connections,
    Collection,
    FieldSchema,
    CollectionSchema,
    DataType,
    utility
)
import sys
sys.path.append(str(__file__).rsplit('/', 3)[0])

from config import MILVUS_HOST, MILVUS_PORT, MILVUS_COLLECTION_NAME, EMBEDDING_DIMENSIONS

logger = logging.getLogger(__name__)


@dataclass
class MemoryItem:
    """记忆项数据类"""
    id: str
    content: str
    memory_type: str  # episodic, semantic, procedural
    embedding: List[float] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    access_count: int = 0
    importance_score: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "access_count": self.access_count,
            "importance_score": self.importance_score
        }


class MilvusMemoryStore:
    """
    Milvus记忆存储类
    提供记忆的CRUD操作和混合检索功能
    """

    def __init__(
        self,
        host: str = MILVUS_HOST,
        port: int = MILVUS_PORT,
        collection_name: str = MILVUS_COLLECTION_NAME,
        dim: int = EMBEDDING_DIMENSIONS
    ):
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.dim = dim
        self.collection = None

        logger.info(f"[Milvus] 初始化MilvusMemoryStore")
        logger.info(f"[Milvus] Host: {host}:{port}, Collection: {collection_name}")

    def connect(self) -> bool:
        """连接Milvus服务器"""
        try:
            connections.connect(
                alias="default",
                host=self.host,
                port=self.port
            )
            logger.info(f"[Milvus] 成功连接到 {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"[Milvus] 连接失败: {str(e)}")
            return False

    def disconnect(self):
        """断开Milvus连接"""
        try:
            connections.disconnect("default")
            logger.info("[Milvus] 已断开连接")
        except Exception as e:
            logger.error(f"[Milvus] 断开连接失败: {str(e)}")

    def create_collection(self, drop_if_exists: bool = False) -> bool:
        """
        创建集合

        Args:
            drop_if_exists: 如果集合存在是否删除重建

        Returns:
            是否创建成功
        """
        try:
            if utility.has_collection(self.collection_name):
                if drop_if_exists:
                    logger.info(f"[Milvus] 删除已存在的集合: {self.collection_name}")
                    utility.drop_collection(self.collection_name)
                else:
                    logger.info(f"[Milvus] 集合已存在: {self.collection_name}")
                    self.collection = Collection(self.collection_name)
                    self.collection.load()
                    return True

            # 定义字段
            fields = [
                FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=128),
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="memory_type", dtype=DataType.VARCHAR, max_length=32),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.dim),
                FieldSchema(name="metadata", dtype=DataType.VARCHAR, max_length=8192),
                FieldSchema(name="created_at", dtype=DataType.VARCHAR, max_length=64),
                FieldSchema(name="access_count", dtype=DataType.INT64),
                FieldSchema(name="importance_score", dtype=DataType.FLOAT),
            ]

            schema = CollectionSchema(
                fields=fields,
                description="Agent Memory Storage"
            )

            self.collection = Collection(
                name=self.collection_name,
                schema=schema
            )

            # 创建向量索引
            index_params = {
                "metric_type": "COSINE",
                "index_type": "IVF_FLAT",
                "params": {"nlist": 128}
            }
            self.collection.create_index(
                field_name="embedding",
                index_params=index_params
            )

            # 加载集合到内存
            self.collection.load()

            logger.info(f"[Milvus] 创建集合成功: {self.collection_name}")
            return True

        except Exception as e:
            logger.error(f"[Milvus] 创建集合失败: {str(e)}")
            return False

    def insert(self, memories: List[MemoryItem]) -> bool:
        """
        插入记忆

        Args:
            memories: 记忆项列表

        Returns:
            是否插入成功
        """
        if not self.collection:
            logger.error("[Milvus] 集合未初始化")
            return False

        try:
            data = [
                [m.id for m in memories],
                [m.content for m in memories],
                [m.memory_type for m in memories],
                [m.embedding for m in memories],
                [json.dumps(m.metadata, ensure_ascii=False) for m in memories],
                [m.created_at for m in memories],
                [m.access_count for m in memories],
                [m.importance_score for m in memories],
            ]

            self.collection.insert(data)
            self.collection.flush()

            logger.info(f"[Milvus] 成功插入 {len(memories)} 条记忆")
            return True

        except Exception as e:
            logger.error(f"[Milvus] 插入失败: {str(e)}")
            return False

    def delete(self, ids: List[str]) -> bool:
        """
        删除记忆

        Args:
            ids: 要删除的记忆ID列表

        Returns:
            是否删除成功
        """
        if not self.collection:
            logger.error("[Milvus] 集合未初始化")
            return False

        try:
            expr = f"id in {ids}"
            self.collection.delete(expr)
            logger.info(f"[Milvus] 成功删除 {len(ids)} 条记忆")
            return True

        except Exception as e:
            logger.error(f"[Milvus] 删除失败: {str(e)}")
            return False

    def search_by_vector(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filter_expr: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        向量相似度搜索

        Args:
            query_vector: 查询向量
            top_k: 返回数量
            filter_expr: 过滤表达式

        Returns:
            搜索结果列表
        """
        if not self.collection:
            logger.error("[Milvus] 集合未初始化")
            return []

        try:
            search_params = {
                "metric_type": "COSINE",
                "params": {"nprobe": 10}
            }

            results = self.collection.search(
                data=[query_vector],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                expr=filter_expr,
                output_fields=["id", "content", "memory_type", "metadata", "created_at", "access_count", "importance_score"]
            )

            search_results = []
            for hits in results:
                for hit in hits:
                    result = {
                        "id": hit.entity.get("id"),
                        "content": hit.entity.get("content"),
                        "memory_type": hit.entity.get("memory_type"),
                        "metadata": json.loads(hit.entity.get("metadata", "{}")),
                        "created_at": hit.entity.get("created_at"),
                        "access_count": hit.entity.get("access_count"),
                        "importance_score": hit.entity.get("importance_score"),
                        "similarity": hit.distance
                    }
                    search_results.append(result)

            logger.info(f"[Milvus] 向量搜索返回 {len(search_results)} 条结果")
            return search_results

        except Exception as e:
            logger.error(f"[Milvus] 向量搜索失败: {str(e)}")
            return []

    def search_by_keyword(
        self,
        keyword: str,
        memory_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        关键词搜索 (Python端过滤)

        注意: Milvus 不支持 LIKE "%keyword%" 包含匹配，
        因此使用 Python 端过滤实现关键词搜索。

        Args:
            keyword: 搜索关键词
            memory_type: 记忆类型过滤
            limit: 返回数量

        Returns:
            搜索结果列表
        """
        if not self.collection:
            logger.error("[Milvus] 集合未初始化")
            return []

        try:
            # 构建过滤表达式 (只按 memory_type 过滤，关键词在 Python 端处理)
            expr = f'memory_type == "{memory_type}"' if memory_type else "id != ''"

            # 获取候选记忆 (扩大搜索范围以便过滤)
            results = self.collection.query(
                expr=expr,
                output_fields=["id", "content", "memory_type", "metadata", "created_at", "access_count", "importance_score"],
                limit=limit * 10  # 扩大范围，因为要在 Python 端过滤
            )

            # Python 端关键词过滤
            search_results = []
            keyword_lower = keyword.lower()
            for item in results:
                content = item.get("content", "")
                # 检查关键词是否在内容中 (不区分大小写)
                if keyword_lower in content.lower():
                    result = {
                        "id": item.get("id"),
                        "content": content,
                        "memory_type": item.get("memory_type"),
                        "metadata": json.loads(item.get("metadata", "{}")),
                        "created_at": item.get("created_at"),
                        "access_count": item.get("access_count"),
                        "importance_score": item.get("importance_score"),
                    }
                    search_results.append(result)

                    if len(search_results) >= limit:
                        break

            logger.info(f"[Milvus] 关键词搜索 '{keyword}' 返回 {len(search_results)} 条结果")
            return search_results

        except Exception as e:
            logger.error(f"[Milvus] 关键词搜索失败: {str(e)}")
            return []

    def hybrid_search(
        self,
        query_vector: List[float],
        keywords: List[str],
        top_k: int = 10,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
        memory_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        混合检索：结合向量相似度和关键词匹配

        Args:
            query_vector: 查询向量
            keywords: 关键词列表
            top_k: 返回数量
            vector_weight: 向量相似度权重
            keyword_weight: 关键词匹配权重
            memory_type: 记忆类型过滤

        Returns:
            混合排序后的搜索结果
        """
        logger.info(f"[Milvus] 开始混合检索: keywords={keywords}, top_k={top_k}")

        # 向量搜索
        filter_expr = f'memory_type == "{memory_type}"' if memory_type else None
        vector_results = self.search_by_vector(query_vector, top_k * 2, filter_expr)

        # 关键词搜索（对每个关键词搜索并合并）
        keyword_results = {}
        for keyword in keywords:
            results = self.search_by_keyword(keyword, memory_type, top_k * 2)
            for r in results:
                if r["id"] not in keyword_results:
                    keyword_results[r["id"]] = r
                    keyword_results[r["id"]]["keyword_hits"] = 1
                else:
                    keyword_results[r["id"]]["keyword_hits"] += 1

        # 融合结果
        combined_scores = {}

        # 处理向量搜索结果
        for i, r in enumerate(vector_results):
            score = (1 - i / len(vector_results)) * vector_weight * r.get("similarity", 1)
            combined_scores[r["id"]] = {
                **r,
                "combined_score": score,
                "vector_rank": i + 1
            }

        # 融合关键词搜索结果
        max_hits = max([r.get("keyword_hits", 1) for r in keyword_results.values()]) if keyword_results else 1
        for id, r in keyword_results.items():
            keyword_score = (r.get("keyword_hits", 1) / max_hits) * keyword_weight
            if id in combined_scores:
                combined_scores[id]["combined_score"] += keyword_score
                combined_scores[id]["keyword_hits"] = r.get("keyword_hits", 0)
            else:
                combined_scores[id] = {
                    **r,
                    "combined_score": keyword_score,
                    "keyword_hits": r.get("keyword_hits", 0)
                }

        # 按综合分数排序
        sorted_results = sorted(
            combined_scores.values(),
            key=lambda x: x["combined_score"],
            reverse=True
        )[:top_k]

        logger.info(f"[Milvus] 混合检索完成: 返回 {len(sorted_results)} 条结果")
        return sorted_results

    def get_all_memories(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """获取所有记忆"""
        if not self.collection:
            logger.error("[Milvus] 集合未初始化")
            return []

        try:
            results = self.collection.query(
                expr="id != ''",
                output_fields=["id", "content", "memory_type", "metadata", "created_at", "access_count", "importance_score"],
                limit=limit
            )

            memories = []
            for item in results:
                memory = {
                    "id": item.get("id"),
                    "content": item.get("content"),
                    "memory_type": item.get("memory_type"),
                    "metadata": json.loads(item.get("metadata", "{}")),
                    "created_at": item.get("created_at"),
                    "access_count": item.get("access_count"),
                    "importance_score": item.get("importance_score"),
                }
                memories.append(memory)

            logger.info(f"[Milvus] 获取 {len(memories)} 条记忆")
            return memories

        except Exception as e:
            logger.error(f"[Milvus] 获取记忆失败: {str(e)}")
            return []

    def update_access_count(self, memory_id: str) -> bool:
        """更新记忆访问次数"""
        # Milvus不支持直接更新，需要先查询再删除再插入
        # 这里简化处理，在实际应用中可以使用Redis辅助
        logger.info(f"[Milvus] 更新访问计数: {memory_id}")
        return True

    def get_stats(self) -> Dict[str, Any]:
        """获取集合统计信息"""
        if not self.collection:
            return {"error": "Collection not initialized"}

        try:
            stats = {
                "collection_name": self.collection_name,
                "num_entities": self.collection.num_entities,
                "is_loaded": True
            }
            logger.info(f"[Milvus] 统计信息: {stats}")
            return stats

        except Exception as e:
            logger.error(f"[Milvus] 获取统计信息失败: {str(e)}")
            return {"error": str(e)}


# 测试代码
def test_milvus_store():
    """测试Milvus存储"""
    logger.info("=" * 50)
    logger.info("[TEST] 开始测试MilvusMemoryStore")
    logger.info("=" * 50)

    store = MilvusMemoryStore()

    # 连接Milvus
    print("\n=== 连接Milvus ===")
    if not store.connect():
        print("连接失败，请确保Milvus服务正在运行")
        return

    # 创建集合
    print("\n=== 创建集合 ===")
    store.create_collection(drop_if_exists=True)

    # 插入测试数据
    print("\n=== 插入记忆 ===")
    import uuid
    import random

    test_memories = [
        MemoryItem(
            id=str(uuid.uuid4()),
            content="低空经济是指以各种有人驾驶和无人驾驶航空器的低空飞行活动为牵引的综合性经济形态",
            memory_type="semantic",
            embedding=[random.random() for _ in range(EMBEDDING_DIMENSIONS)],
            metadata={"source": "research", "topic": "low_altitude_economy"},
            importance_score=0.8
        ),
        MemoryItem(
            id=str(uuid.uuid4()),
            content="无人机配送服务可以大大提高物流效率，特别是在偏远地区和城市末端配送场景",
            memory_type="episodic",
            embedding=[random.random() for _ in range(EMBEDDING_DIMENSIONS)],
            metadata={"source": "news", "topic": "drone_delivery"},
            importance_score=0.6
        ),
        MemoryItem(
            id=str(uuid.uuid4()),
            content="用户偏好使用红色系的图表进行数据可视化",
            memory_type="procedural",
            embedding=[random.random() for _ in range(EMBEDDING_DIMENSIONS)],
            metadata={"source": "user_preference", "type": "visualization"},
            importance_score=0.9
        ),
    ]

    store.insert(test_memories)

    # 获取统计信息
    print("\n=== 统计信息 ===")
    stats = store.get_stats()
    print(f"集合名称: {stats.get('collection_name')}")
    print(f"记忆数量: {stats.get('num_entities')}")

    # 向量搜索
    print("\n=== 向量搜索 ===")
    query_vector = [random.random() for _ in range(EMBEDDING_DIMENSIONS)]
    results = store.search_by_vector(query_vector, top_k=3)
    print(f"搜索结果数: {len(results)}")
    for r in results:
        print(f"  - {r['content'][:50]}... (相似度: {r.get('similarity', 0):.4f})")

    # 关键词搜索
    print("\n=== 关键词搜索 ===")
    results = store.search_by_keyword("无人机", limit=5)
    print(f"搜索结果数: {len(results)}")
    for r in results:
        print(f"  - {r['content'][:50]}...")

    # 获取所有记忆
    print("\n=== 所有记忆 ===")
    all_memories = store.get_all_memories()
    print(f"总记忆数: {len(all_memories)}")
    for m in all_memories:
        print(f"  [{m['memory_type']}] {m['content'][:40]}...")

    # 删除记忆
    print("\n=== 删除记忆 ===")
    if test_memories:
        store.delete([test_memories[0].id])
        print(f"删除后记忆数: {store.get_stats().get('num_entities')}")

    # 断开连接
    store.disconnect()

    logger.info("[TEST] MilvusMemoryStore测试完成")


if __name__ == "__main__":
    test_milvus_store()
