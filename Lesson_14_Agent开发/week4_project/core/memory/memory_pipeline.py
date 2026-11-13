"""
Memory Pipeline (记忆管道)
实现记忆的存储、检索和管理流程
包含短期缓冲区、长期存储和上下文压缩功能
"""
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import uuid
import sys
sys.path.append(str(__file__).rsplit('/', 4)[0])

from core.memory.milvus_store import MilvusMemoryStore, MemoryItem
from core.tools.embedding import EmbeddingService
from core.tools.llm import LLMService
from core.utils.log_formatter import log_fmt

logger = logging.getLogger(__name__)


@dataclass
class ConversationTurn:
    """对话轮次"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    role: str = ""  # user, assistant
    content: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryContext:
    """记忆上下文"""
    short_term: List[ConversationTurn]  # 短期记忆
    relevant_memories: List[Dict[str, Any]]  # 相关长期记忆
    user_profile: Dict[str, Any]  # 用户画像
    compressed_context: str  # 压缩后的上下文


class MemoryPipeline:
    """
    记忆管道
    - 短期缓冲区 (Sliding Window)
    - 长期存储 (Milvus)
    - 上下文压缩
    - 混合检索
    """

    def __init__(
        self,
        milvus_store: Optional[MilvusMemoryStore] = None,
        embedding_service: Optional[EmbeddingService] = None,
        llm_service: Optional[LLMService] = None,
        short_term_window: int = 10,  # 保留最近N轮对话
        buffer_overflow_threshold: int = 8  # 触发归档的阈值
    ):
        self.milvus = milvus_store or MilvusMemoryStore()
        self.embedding = embedding_service or EmbeddingService()
        self.llm = llm_service or LLMService()

        self.short_term_window = short_term_window
        self.buffer_overflow_threshold = buffer_overflow_threshold

        # 短期缓冲区
        self.buffer: List[ConversationTurn] = []

        # 用户画像
        self.user_profile: Dict[str, Any] = {
            "preferences": {},
            "interests": [],
            "interaction_patterns": {}
        }

        # 初始化Milvus连接
        self._initialized = False

        logger.info(f"[MemoryPipeline] 初始化完成")
        logger.info(f"[MemoryPipeline] 短期窗口: {short_term_window}, 归档阈值: {buffer_overflow_threshold}")

    def initialize(self) -> bool:
        """初始化存储连接"""
        if self._initialized:
            return True

        logger.info("[MemoryPipeline] 初始化存储连接...")

        try:
            if self.milvus.connect():
                self.milvus.create_collection()
                self._initialized = True
                # 获取实体数量
                entity_count = 0
                try:
                    if self.milvus.collection:
                        self.milvus.collection.flush()
                        entity_count = self.milvus.collection.num_entities
                except:
                    pass
                print(log_fmt.milvus_state(True, entity_count))
                return True
        except Exception as e:
            print(log_fmt.milvus_state(False))
            logger.error(f"[MemoryPipeline] 存储初始化失败: {str(e)}")

        return False

    async def add_turn(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ConversationTurn:
        """
        添加对话轮次

        Args:
            role: 角色 (user/assistant)
            content: 内容
            metadata: 元数据

        Returns:
            添加的对话轮次
        """
        turn = ConversationTurn(
            role=role,
            content=content,
            metadata=metadata or {}
        )

        self.buffer.append(turn)

        # 显示缓冲区状态
        print(log_fmt.buffer_state(
            size=len(self.buffer),
            window=self.short_term_window,
            threshold=self.buffer_overflow_threshold,
            turns=[{"role": t.role, "content": t.content} for t in self.buffer],
            label="After Add"
        ))

        # 检查是否需要归档
        if len(self.buffer) >= self.buffer_overflow_threshold:
            await self._archive_buffer()

        # 保持窗口大小
        while len(self.buffer) > self.short_term_window:
            self.buffer.pop(0)

        return turn

    async def _archive_buffer(self):
        """
        归档缓冲区内容到长期存储
        将对话内容总结后存入Milvus
        """
        if len(self.buffer) < 2:
            return

        from_size = len(self.buffer)

        # 获取需要归档的对话（保留最近几轮）
        to_archive = self.buffer[:-2]  # 保留最近2轮不归档

        if not to_archive:
            return

        # 生成对话摘要
        conversation_text = "\n".join([
            f"{t.role}: {t.content}"
            for t in to_archive
        ])

        summary = await self._summarize_conversation(conversation_text)

        if summary:
            # 生成embedding
            embedding = self.embedding.embed_text(summary)

            # 创建记忆项
            memory = MemoryItem(
                id=str(uuid.uuid4()),
                content=summary,
                memory_type="episodic",
                embedding=embedding,
                metadata={
                    "source": "conversation",
                    "turn_count": len(to_archive),
                    "start_time": to_archive[0].timestamp,
                    "end_time": to_archive[-1].timestamp
                },
                importance_score=0.6
            )

            # 存入Milvus
            if self._initialized:
                self.milvus.insert([memory])
                print(log_fmt.archive_triggered(from_size, len(to_archive), summary))

        # 清除已归档的内容
        self.buffer = self.buffer[-2:]

        # 显示归档后的缓冲区状态
        print(log_fmt.buffer_state(
            size=len(self.buffer),
            window=self.short_term_window,
            threshold=self.buffer_overflow_threshold,
            turns=[{"role": t.role, "content": t.content} for t in self.buffer],
            label="After Archive"
        ))

    async def _summarize_conversation(self, conversation: str) -> str:
        """总结对话内容"""
        logger.info("[MemoryPipeline] 生成对话摘要...")

        prompt = f"""请将以下对话内容总结为一段简洁的记忆，保留关键信息：

对话内容:
{conversation}

要求：
1. 提取关键事实和决策
2. 记录用户的偏好或需求
3. 保持简洁（不超过100字）
4. 使用第三人称叙述

直接返回摘要内容，不要加任何前缀。"""

        try:
            summary = await self.llm.achat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=200
            )
            logger.info(f"[MemoryPipeline] 摘要生成完成: {len(summary)} 字符")
            return summary.strip()
        except Exception as e:
            logger.error(f"[MemoryPipeline] 摘要生成失败: {str(e)}")
            return ""

    async def retrieve_context(
        self,
        query: str,
        top_k: int = 5,
        include_short_term: bool = True
    ) -> MemoryContext:
        """
        检索相关记忆上下文

        Args:
            query: 查询内容
            top_k: 返回的长期记忆数量
            include_short_term: 是否包含短期记忆

        Returns:
            记忆上下文
        """
        logger.info(f"[MemoryPipeline] 检索上下文: '{query[:50]}...'")

        # 获取短期记忆
        short_term = self.buffer.copy() if include_short_term else []

        # 检索长期记忆
        relevant_memories = []
        if self._initialized:
            query_embedding = self.embedding.embed_text(query)

            # 提取关键词
            keywords = await self._extract_keywords(query)

            # 混合检索
            results = self.milvus.hybrid_search(
                query_vector=query_embedding,
                keywords=keywords,
                top_k=top_k
            )
            relevant_memories = results

            logger.info(f"[MemoryPipeline] 检索到 {len(relevant_memories)} 条相关记忆")

        # 压缩上下文
        compressed = await self._compress_context(short_term, relevant_memories, query)

        return MemoryContext(
            short_term=short_term,
            relevant_memories=relevant_memories,
            user_profile=self.user_profile,
            compressed_context=compressed
        )

    async def _extract_keywords(self, query: str) -> List[str]:
        """提取查询关键词"""
        prompt = f"""从以下查询中提取3-5个关键词，用于搜索：

查询: {query}

只返回关键词，用逗号分隔："""

        try:
            response = await self.llm.achat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=50
            )
            keywords = [k.strip() for k in response.split(",")]
            logger.debug(f"[MemoryPipeline] 提取关键词: {keywords}")
            return keywords
        except:
            return []

    async def _compress_context(
        self,
        short_term: List[ConversationTurn],
        long_term: List[Dict[str, Any]],
        query: str
    ) -> str:
        """
        压缩上下文，减少token消耗

        Args:
            short_term: 短期记忆
            long_term: 长期记忆
            query: 当前查询

        Returns:
            压缩后的上下文
        """
        logger.info("[MemoryPipeline] 压缩上下文...")

        # 构建原始上下文
        context_parts = []

        # 短期记忆
        if short_term:
            recent = "\n".join([
                f"{t.role}: {t.content[:200]}"
                for t in short_term[-5:]  # 只保留最近5轮
            ])
            context_parts.append(f"最近对话:\n{recent}")

        # 长期记忆
        if long_term:
            memories = "\n".join([
                f"- {m.get('content', '')[:150]}"
                for m in long_term[:3]  # 只保留top 3
            ])
            context_parts.append(f"相关记忆:\n{memories}")

        # 用户画像
        if self.user_profile.get("preferences"):
            prefs = json.dumps(self.user_profile["preferences"], ensure_ascii=False)
            context_parts.append(f"用户偏好: {prefs}")

        combined = "\n\n".join(context_parts)

        # 如果上下文不长，直接返回
        if len(combined) < 1000:
            return combined

        # 使用LLM压缩
        prompt = f"""请压缩以下上下文，保留与当前查询相关的关键信息：

当前查询: {query}

上下文:
{combined}

压缩后的上下文（不超过300字）："""

        try:
            compressed = await self.llm.achat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=400
            )
            logger.info(f"[MemoryPipeline] 上下文压缩: {len(combined)} -> {len(compressed)} 字符")
            return compressed.strip()
        except Exception as e:
            logger.warning(f"[MemoryPipeline] 压缩失败，返回截断: {str(e)}")
            return combined[:1000]

    async def update_user_profile(self, key: str, value: Any):
        """
        更新用户画像

        Args:
            key: 属性键
            value: 属性值
        """
        if key == "preferences":
            self.user_profile["preferences"].update(value)
        elif key == "interests":
            for interest in value if isinstance(value, list) else [value]:
                if interest not in self.user_profile["interests"]:
                    self.user_profile["interests"].append(interest)
        else:
            self.user_profile[key] = value

        logger.info(f"[MemoryPipeline] 更新用户画像: {key}")

        # 将用户画像存入长期记忆
        if self._initialized:
            profile_text = json.dumps(self.user_profile, ensure_ascii=False)
            embedding = self.embedding.embed_text(profile_text)

            memory = MemoryItem(
                id="user_profile",
                content=profile_text,
                memory_type="semantic",
                embedding=embedding,
                metadata={"type": "user_profile"},
                importance_score=0.9
            )

            # 先删除旧的画像
            self.milvus.delete(["user_profile"])
            self.milvus.insert([memory])

    async def save_insight(
        self,
        insight: str,
        source: str = "reflection",
        importance: float = 0.7
    ):
        """
        保存洞察/经验到语义记忆

        Args:
            insight: 洞察内容
            source: 来源
            importance: 重要性评分
        """
        logger.info(f"[MemoryPipeline] 保存洞察: {insight[:50]}...")

        embedding = self.embedding.embed_text(insight)

        memory = MemoryItem(
            id=str(uuid.uuid4()),
            content=insight,
            memory_type="semantic",
            embedding=embedding,
            metadata={"source": source},
            importance_score=importance
        )

        if self._initialized:
            self.milvus.insert([memory])
            logger.info("[MemoryPipeline] 洞察已保存")

    def get_buffer_state(self) -> Dict[str, Any]:
        """获取缓冲区状态"""
        return {
            "buffer_size": len(self.buffer),
            "window_size": self.short_term_window,
            "threshold": self.buffer_overflow_threshold,
            "recent_turns": [
                {"role": t.role, "content": t.content[:50], "time": t.timestamp}
                for t in self.buffer[-3:]
            ]
        }

    def clear_buffer(self):
        """清空缓冲区"""
        self.buffer.clear()
        logger.info("[MemoryPipeline] 缓冲区已清空")

    def close(self):
        """关闭连接"""
        if self._initialized:
            self.milvus.disconnect()
            self._initialized = False
            logger.info("[MemoryPipeline] 连接已关闭")


# 测试代码
async def test_memory_pipeline():
    """测试记忆管道"""
    logger.info("=" * 50)
    logger.info("[TEST] 开始测试MemoryPipeline")
    logger.info("=" * 50)

    pipeline = MemoryPipeline(
        short_term_window=5,
        buffer_overflow_threshold=4
    )

    # 初始化
    print("\n=== 初始化 ===")
    if not pipeline.initialize():
        print("Milvus未连接，跳过长期存储测试")

    # 添加对话
    print("\n=== 添加对话 ===")
    await pipeline.add_turn("user", "我想了解一下低空经济的发展情况")
    await pipeline.add_turn("assistant", "低空经济是指以各种有人驾驶和无人驾驶航空器的低空飞行活动为牵引的综合性经济形态...")
    await pipeline.add_turn("user", "有哪些主要的应用场景？")
    await pipeline.add_turn("assistant", "主要应用场景包括无人机物流、低空旅游、应急救援等...")

    print(f"缓冲区状态: {pipeline.get_buffer_state()}")

    # 更新用户画像
    print("\n=== 更新用户画像 ===")
    await pipeline.update_user_profile("preferences", {"chart_color": "red", "language": "zh"})
    await pipeline.update_user_profile("interests", ["低空经济", "无人机"])
    print(f"用户画像: {pipeline.user_profile}")

    # 检索上下文
    print("\n=== 检索上下文 ===")
    context = await pipeline.retrieve_context("无人机配送服务的发展趋势")
    print(f"短期记忆数: {len(context.short_term)}")
    print(f"相关长期记忆数: {len(context.relevant_memories)}")
    print(f"压缩上下文:\n{context.compressed_context}")

    # 保存洞察
    print("\n=== 保存洞察 ===")
    await pipeline.save_insight(
        "用户对低空经济和无人机技术特别感兴趣，偏好使用红色系图表",
        source="reflection"
    )

    # 继续添加对话触发归档
    print("\n=== 触发归档 ===")
    await pipeline.add_turn("user", "能帮我创建一个市场规模图表吗？记得用红色")
    await pipeline.add_turn("assistant", "好的，我来为您创建一个红色主题的市场规模图表...")

    print(f"归档后缓冲区状态: {pipeline.get_buffer_state()}")

    # 关闭
    pipeline.close()

    logger.info("[TEST] MemoryPipeline测试完成")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_memory_pipeline())
