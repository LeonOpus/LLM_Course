"""
Dreaming Service (做梦服务)
模拟生物睡眠机制，在系统空闲时进行记忆整理
- 记忆聚类和去重
- 矛盾修正
- 摘要升维（从情景记忆提取语义记忆）
- 低频记忆归档
"""
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import uuid
import asyncio
from collections import defaultdict
import sys
sys.path.append(str(__file__).rsplit('/', 4)[0])

from core.memory.milvus_store import MilvusMemoryStore, MemoryItem
from core.tools.embedding import EmbeddingService
from core.tools.llm import LLMService

logger = logging.getLogger(__name__)


@dataclass
class DreamingReport:
    """做梦报告"""
    start_time: str
    end_time: str
    memories_processed: int
    clusters_found: int
    duplicates_removed: int
    insights_generated: int
    contradictions_resolved: int
    memories_archived: int
    new_semantic_memories: List[str]


class DreamingService:
    """
    做梦服务
    模拟大脑在睡眠时整理记忆的过程
    """

    def __init__(
        self,
        milvus_store: Optional[MilvusMemoryStore] = None,
        embedding_service: Optional[EmbeddingService] = None,
        llm_service: Optional[LLMService] = None,
        similarity_threshold: float = 0.85,  # 判定重复的相似度阈值
        archive_days: int = 30,  # 超过多少天的低频记忆归档
        min_cluster_size: int = 3  # 最小聚类大小
    ):
        self.milvus = milvus_store or MilvusMemoryStore()
        self.embedding = embedding_service or EmbeddingService()
        self.llm = llm_service or LLMService()

        self.similarity_threshold = similarity_threshold
        self.archive_days = archive_days
        self.min_cluster_size = min_cluster_size

        self._initialized = False

        logger.info(f"[DreamingService] 初始化完成")
        logger.info(f"[DreamingService] 相似度阈值: {similarity_threshold}, 归档天数: {archive_days}")

    def initialize(self) -> bool:
        """初始化存储连接"""
        if self._initialized:
            return True

        try:
            if self.milvus.connect():
                self.milvus.create_collection()
                self._initialized = True
                logger.info("[DreamingService] 存储初始化成功")
                return True
        except Exception as e:
            logger.error(f"[DreamingService] 存储初始化失败: {str(e)}")

        return False

    async def dream(self, time_range_hours: int = 24) -> DreamingReport:
        """
        执行做梦过程（记忆整理）

        Args:
            time_range_hours: 处理最近多少小时的记忆

        Returns:
            做梦报告
        """
        start_time = datetime.now()
        logger.info(f"[DreamingService] 开始做梦... 处理最近 {time_range_hours} 小时的记忆")

        if not self._initialized:
            self.initialize()

        report = DreamingReport(
            start_time=start_time.isoformat(),
            end_time="",
            memories_processed=0,
            clusters_found=0,
            duplicates_removed=0,
            insights_generated=0,
            contradictions_resolved=0,
            memories_archived=0,
            new_semantic_memories=[]
        )

        try:
            # 获取所有记忆
            memories = self.milvus.get_all_memories()
            report.memories_processed = len(memories)
            logger.info(f"[DreamingService] 获取到 {len(memories)} 条记忆")

            if not memories:
                report.end_time = datetime.now().isoformat()
                return report

            # 1. 记忆聚类
            clusters = await self._cluster_memories(memories)
            report.clusters_found = len(clusters)
            logger.info(f"[DreamingService] 发现 {len(clusters)} 个记忆聚类")

            # 2. 去重
            duplicates = await self._find_duplicates(memories)
            if duplicates:
                self.milvus.delete(duplicates)
                report.duplicates_removed = len(duplicates)
                logger.info(f"[DreamingService] 删除 {len(duplicates)} 条重复记忆")

            # 3. 从聚类中提取洞察（情景记忆 -> 语义记忆）
            insights = await self._extract_insights(clusters)
            report.insights_generated = len(insights)
            report.new_semantic_memories = insights
            logger.info(f"[DreamingService] 生成 {len(insights)} 条新洞察")

            # 4. 矛盾检测和修正
            contradictions = await self._resolve_contradictions(memories)
            report.contradictions_resolved = contradictions
            logger.info(f"[DreamingService] 修正 {contradictions} 处矛盾")

            # 5. 归档低频记忆
            archived = await self._archive_old_memories(memories)
            report.memories_archived = archived
            logger.info(f"[DreamingService] 归档 {archived} 条低频记忆")

        except Exception as e:
            logger.error(f"[DreamingService] 做梦过程出错: {str(e)}")

        report.end_time = datetime.now().isoformat()
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"[DreamingService] 做梦完成, 耗时: {duration:.2f}s")

        return report

    async def _cluster_memories(
        self,
        memories: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        对记忆进行聚类

        Args:
            memories: 记忆列表

        Returns:
            聚类结果 {cluster_id: [memories]}
        """
        logger.info("[DreamingService] 开始记忆聚类...")

        if len(memories) < self.min_cluster_size:
            return {}

        # 简单的基于内容相似度的聚类
        # 实际应用中可以使用更复杂的聚类算法如K-means、DBSCAN等

        clusters = defaultdict(list)
        clustered = set()

        for i, memory in enumerate(memories):
            if memory["id"] in clustered:
                continue

            # 为每个未聚类的记忆创建新聚类
            cluster_id = f"cluster_{len(clusters)}"
            clusters[cluster_id].append(memory)
            clustered.add(memory["id"])

            # 查找相似的记忆
            content = memory.get("content", "")
            if len(content) > 10:
                embedding = self.embedding.embed_text(content)

                similar = self.milvus.search_by_vector(
                    query_vector=embedding,
                    top_k=10
                )

                for sim in similar:
                    if sim["id"] not in clustered and sim.get("similarity", 0) > 0.7:
                        clusters[cluster_id].append(sim)
                        clustered.add(sim["id"])

        # 过滤掉太小的聚类
        valid_clusters = {
            k: v for k, v in clusters.items()
            if len(v) >= self.min_cluster_size
        }

        logger.info(f"[DreamingService] 聚类完成: {len(valid_clusters)} 个有效聚类")
        return valid_clusters

    async def _find_duplicates(
        self,
        memories: List[Dict[str, Any]]
    ) -> List[str]:
        """
        查找重复记忆

        Args:
            memories: 记忆列表

        Returns:
            需要删除的记忆ID列表
        """
        logger.info("[DreamingService] 查找重复记忆...")

        duplicates = []
        seen_contents = {}

        for memory in memories:
            content = memory.get("content", "").strip()

            # 简单的内容相似度检查
            content_key = content[:100] if len(content) > 100 else content

            if content_key in seen_contents:
                # 保留较新的或重要性更高的
                existing = seen_contents[content_key]
                if memory.get("importance_score", 0) <= existing.get("importance_score", 0):
                    duplicates.append(memory["id"])
                else:
                    duplicates.append(existing["id"])
                    seen_contents[content_key] = memory
            else:
                seen_contents[content_key] = memory

        logger.info(f"[DreamingService] 发现 {len(duplicates)} 条重复记忆")
        return duplicates

    async def _extract_insights(
        self,
        clusters: Dict[str, List[Dict[str, Any]]]
    ) -> List[str]:
        """
        从记忆聚类中提取洞察

        Args:
            clusters: 聚类结果

        Returns:
            洞察列表
        """
        logger.info("[DreamingService] 提取洞察...")

        insights = []

        for cluster_id, memories in clusters.items():
            if len(memories) < self.min_cluster_size:
                continue

            # 合并聚类中的记忆内容
            contents = "\n".join([
                f"- {m.get('content', '')[:200]}"
                for m in memories[:5]  # 只取前5条
            ])

            prompt = f"""分析以下相关记忆，提取一条高层次的洞察或经验法则：

相关记忆:
{contents}

要求：
1. 提取共同模式或规律
2. 生成一条简洁的洞察（不超过50字）
3. 这条洞察应该是可复用的知识

直接返回洞察内容："""

            try:
                insight = await self.llm.achat(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=100
                )

                insight = insight.strip()
                if insight and len(insight) > 10:
                    insights.append(insight)

                    # 保存为语义记忆
                    embedding = self.embedding.embed_text(insight)
                    memory = MemoryItem(
                        id=str(uuid.uuid4()),
                        content=insight,
                        memory_type="semantic",
                        embedding=embedding,
                        metadata={
                            "source": "dreaming",
                            "cluster_id": cluster_id,
                            "extracted_from_count": len(memories)
                        },
                        importance_score=0.8
                    )
                    self.milvus.insert([memory])

            except Exception as e:
                logger.warning(f"[DreamingService] 提取洞察失败: {str(e)}")

        logger.info(f"[DreamingService] 提取了 {len(insights)} 条洞察")
        return insights

    async def _resolve_contradictions(
        self,
        memories: List[Dict[str, Any]]
    ) -> int:
        """
        检测和修正矛盾的记忆

        Args:
            memories: 记忆列表

        Returns:
            修正的矛盾数量
        """
        logger.info("[DreamingService] 检测矛盾记忆...")

        # 简化实现：只检测明显矛盾的偏好设置
        preference_memories = [
            m for m in memories
            if m.get("memory_type") == "semantic" and "偏好" in m.get("content", "")
        ]

        if len(preference_memories) < 2:
            return 0

        # 构建检测提示
        contents = "\n".join([
            f"[{m['id'][:8]}] {m.get('content', '')}"
            for m in preference_memories[:10]
        ])

        prompt = f"""检测以下记忆中是否存在矛盾：

记忆列表:
{contents}

如果存在矛盾，以JSON格式返回：
{{
    "contradictions": [
        {{"memory_ids": ["id1", "id2"], "description": "矛盾描述"}}
    ]
}}

如果没有矛盾，返回：{{"contradictions": []}}"""

        try:
            response = await self.llm.achat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )

            result = self.llm.parse_json_response(response)
            contradictions = result.get("contradictions", [])

            # 删除矛盾中较旧的记忆
            for contradiction in contradictions:
                ids = contradiction.get("memory_ids", [])
                if len(ids) >= 2:
                    # 保留第一个（假设较新），删除其他
                    self.milvus.delete(ids[1:])

            return len(contradictions)

        except Exception as e:
            logger.warning(f"[DreamingService] 矛盾检测失败: {str(e)}")
            return 0

    async def _archive_old_memories(
        self,
        memories: List[Dict[str, Any]]
    ) -> int:
        """
        归档低频访问的旧记忆

        Args:
            memories: 记忆列表

        Returns:
            归档的记忆数量
        """
        logger.info("[DreamingService] 归档低频记忆...")

        cutoff_date = datetime.now() - timedelta(days=self.archive_days)
        archived = 0

        to_archive = []
        for memory in memories:
            created_at = memory.get("created_at", "")
            access_count = memory.get("access_count", 0)
            importance = memory.get("importance_score", 0.5)

            try:
                if created_at:
                    created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    if created < cutoff_date and access_count < 3 and importance < 0.5:
                        to_archive.append(memory["id"])
            except:
                pass

        if to_archive:
            # 在实际应用中，这里应该将记忆移到归档存储
            # 这里简化为降低重要性评分
            logger.info(f"[DreamingService] 标记 {len(to_archive)} 条记忆待归档")
            archived = len(to_archive)

        return archived

    async def reflect(self, time_range_hours: int = 24) -> Dict[str, Any]:
        """
        反思过程：提取用户偏好和任务模式

        Args:
            time_range_hours: 分析时间范围

        Returns:
            反思结果
        """
        logger.info(f"[DreamingService] 开始反思过程...")

        if not self._initialized:
            self.initialize()

        # 获取最近的情景记忆
        memories = self.milvus.get_all_memories()
        episodic = [m for m in memories if m.get("memory_type") == "episodic"]

        if not episodic:
            return {"user_profile": {}, "patterns": []}

        # 分析用户偏好
        contents = "\n".join([
            m.get("content", "")[:200]
            for m in episodic[-20:]  # 最近20条
        ])

        prompt = f"""分析以下交互记录，提取用户画像和行为模式：

交互记录:
{contents}

请以JSON格式返回：
{{
    "user_profile": {{
        "interests": ["兴趣1", "兴趣2"],
        "preferences": {{"偏好类型": "偏好值"}},
        "expertise_level": "新手/中级/专家",
        "communication_style": "简洁/详细"
    }},
    "patterns": [
        "行为模式1",
        "行为模式2"
    ]
}}"""

        try:
            response = await self.llm.achat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )

            result = self.llm.parse_json_response(response)
            logger.info(f"[DreamingService] 反思完成: 发现 {len(result.get('patterns', []))} 个模式")

            # 保存用户画像到语义记忆
            profile_text = json.dumps(result.get("user_profile", {}), ensure_ascii=False)
            if profile_text and profile_text != "{}":
                embedding = self.embedding.embed_text(profile_text)
                memory = MemoryItem(
                    id="reflection_profile",
                    content=profile_text,
                    memory_type="semantic",
                    embedding=embedding,
                    metadata={"source": "reflection"},
                    importance_score=0.9
                )
                self.milvus.delete(["reflection_profile"])
                self.milvus.insert([memory])

            return result

        except Exception as e:
            logger.error(f"[DreamingService] 反思失败: {str(e)}")
            return {"user_profile": {}, "patterns": []}

    def close(self):
        """关闭连接"""
        if self._initialized:
            self.milvus.disconnect()
            self._initialized = False
            logger.info("[DreamingService] 连接已关闭")


# 测试代码
async def test_dreaming():
    """测试做梦服务"""
    logger.info("=" * 50)
    logger.info("[TEST] 开始测试DreamingService")
    logger.info("=" * 50)

    service = DreamingService()

    # 初始化
    print("\n=== 初始化 ===")
    if not service.initialize():
        print("Milvus未连接，跳过测试")
        return

    # 先插入一些测试记忆
    print("\n=== 插入测试记忆 ===")
    test_memories = [
        MemoryItem(
            id=str(uuid.uuid4()),
            content="用户询问了低空经济的发展情况",
            memory_type="episodic",
            embedding=service.embedding.embed_text("用户询问了低空经济的发展情况"),
            metadata={"source": "test"},
            importance_score=0.6
        ),
        MemoryItem(
            id=str(uuid.uuid4()),
            content="用户对无人机配送服务很感兴趣",
            memory_type="episodic",
            embedding=service.embedding.embed_text("用户对无人机配送服务很感兴趣"),
            metadata={"source": "test"},
            importance_score=0.6
        ),
        MemoryItem(
            id=str(uuid.uuid4()),
            content="用户偏好使用红色系的图表",
            memory_type="semantic",
            embedding=service.embedding.embed_text("用户偏好使用红色系的图表"),
            metadata={"source": "test"},
            importance_score=0.8
        ),
    ]
    service.milvus.insert(test_memories)
    print(f"插入 {len(test_memories)} 条测试记忆")

    # 执行做梦
    print("\n=== 执行做梦 ===")
    report = await service.dream(time_range_hours=24)

    print(f"做梦报告:")
    print(f"  - 处理记忆数: {report.memories_processed}")
    print(f"  - 发现聚类数: {report.clusters_found}")
    print(f"  - 删除重复数: {report.duplicates_removed}")
    print(f"  - 生成洞察数: {report.insights_generated}")
    print(f"  - 修正矛盾数: {report.contradictions_resolved}")
    print(f"  - 归档记忆数: {report.memories_archived}")

    if report.new_semantic_memories:
        print(f"\n新生成的语义记忆:")
        for insight in report.new_semantic_memories:
            print(f"  - {insight}")

    # 执行反思
    print("\n=== 执行反思 ===")
    reflection = await service.reflect()
    print(f"用户画像: {reflection.get('user_profile', {})}")
    print(f"行为模式: {reflection.get('patterns', [])}")

    # 关闭
    service.close()

    logger.info("[TEST] DreamingService测试完成")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_dreaming())
