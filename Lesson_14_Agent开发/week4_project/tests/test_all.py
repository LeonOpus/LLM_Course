"""
综合测试脚本
测试所有核心功能
"""
import asyncio
import logging
import sys
sys.path.append(str(__file__).rsplit('/', 2)[0])

from config import validate_config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_embedding_service():
    """测试Embedding服务"""
    print("\n" + "=" * 60)
    print("测试1: Embedding服务 (阿里云 text-embedding-v4)")
    print("=" * 60)

    from core.tools.embedding import EmbeddingService

    service = EmbeddingService()

    # 测试单文本
    text = "低空经济是指以各种有人驾驶和无人驾驶航空器的低空飞行活动为牵引的综合性经济形态"
    embedding = service.embed_text(text)

    print(f"✓ 单文本向量化成功")
    print(f"  文本: {text[:40]}...")
    print(f"  向量维度: {len(embedding)}")
    print(f"  向量前3个值: {embedding[:3]}")

    # 测试批量
    texts = ["无人机配送", "低空旅游", "应急救援"]
    embeddings = service.embed_texts(texts)

    print(f"✓ 批量向量化成功: {len(texts)} 条 -> {len(embeddings)} 个向量")

    # 测试相似度
    sim = service.compute_similarity(embeddings[0], embeddings[1])
    print(f"✓ 相似度计算: '{texts[0]}' 与 '{texts[1]}' = {sim:.4f}")

    return True


async def test_llm_service():
    """测试LLM服务"""
    print("\n" + "=" * 60)
    print("测试2: LLM服务 (DeepSeek-v3)")
    print("=" * 60)

    from core.tools.llm import LLMService

    service = LLMService()

    # 测试基础对话
    messages = [{"role": "user", "content": "请用一句话解释什么是低空经济"}]
    response = service.chat(messages, max_tokens=100)

    print(f"✓ 基础对话成功")
    print(f"  问题: {messages[0]['content']}")
    print(f"  回答: {response[:100]}...")

    # 测试异步对话
    response2 = await service.achat(messages, max_tokens=100)
    print(f"✓ 异步对话成功")

    return True


async def test_web_search():
    """测试Web搜索"""
    print("\n" + "=" * 60)
    print("测试3: Web搜索服务 (Bocha API)")
    print("=" * 60)

    from core.tools.web_search import WebSearchTool

    tool = WebSearchTool()

    # 测试搜索
    results = await tool.search("低空经济 2024", count=3, summary=True)

    print(f"✓ 搜索成功: 返回 {len(results)} 条结果")
    for i, r in enumerate(results[:2], 1):
        print(f"  [{i}] {r.title[:40]}...")
        print(f"      URL: {r.url[:50]}...")

    # 测试格式化输出
    formatted = tool.format_results_with_citations(results[:2])
    print(f"✓ 格式化输出成功 ({len(formatted)} 字符)")

    return True


async def test_researcher_agent():
    """测试研究员智能体"""
    print("\n" + "=" * 60)
    print("测试4: Researcher Agent (研究员)")
    print("=" * 60)

    from core.agents.researcher import ResearcherAgent

    agent = ResearcherAgent()

    result = await agent.execute(
        task="低空经济的主要应用场景有哪些",
        context={"max_iterations": 1, "results_per_search": 3}
    )

    if result.success:
        report = result.output
        print(f"✓ 研究完成")
        print(f"  迭代次数: {report.iterations}")
        print(f"  来源数量: {len(report.sources)}")
        print(f"  关键发现: {len(report.key_findings)} 条")
        print(f"  摘要: {report.summary[:100]}...")
    else:
        print(f"✗ 研究失败: {result.error}")
        return False

    return True


async def test_analyst_agent():
    """测试分析师智能体"""
    print("\n" + "=" * 60)
    print("测试5: Analyst Agent (分析师)")
    print("=" * 60)

    from core.agents.analyst import AnalystAgent

    agent = AnalystAgent()

    result = await agent.execute(
        task="创建一个简单的柱状图展示以下数据",
        context={
            "data": {
                "领域": ["无人机物流", "通用航空", "低空旅游"],
                "规模": [120, 450, 85]
            },
            "preferences": {"color_scheme": "red"}
        }
    )

    if result.success:
        exec_result = result.output
        print(f"✓ 分析完成")
        print(f"  代码执行: {'成功' if exec_result.success else '失败'}")
        print(f"  图表文件: {exec_result.figures}")
        print(f"  输出: {exec_result.output[:100] if exec_result.output else 'None'}...")
    else:
        print(f"✗ 分析失败: {result.error}")
        return False

    return True


async def test_critic_agent():
    """测试审核员智能体"""
    print("\n" + "=" * 60)
    print("测试6: Critic Agent (审核员)")
    print("=" * 60)

    from core.agents.critic import CriticAgent

    agent = CriticAgent()

    content = """
    低空经济是指以各种有人驾驶和无人驾驶航空器的低空飞行活动为牵引的综合性经济形态。
    根据预测，2025年中国低空经济市场规模将达到1.5万亿元。
    主要应用场景包括无人机物流、低空旅游和应急救援等。
    """

    result = await agent.execute(
        task="审核研究内容",
        context={
            "content": content,
            "content_type": "research",
            "original_task": "介绍低空经济"
        }
    )

    if result.success:
        review = result.output
        print(f"✓ 审核完成")
        print(f"  决定: {review.decision.value}")
        print(f"  得分: {review.overall_score:.1f}/100")
        print(f"  问题数: {len(review.issues)}")
        print(f"  建议数: {len(review.suggestions)}")
    else:
        print(f"✗ 审核失败: {result.error}")
        return False

    return True


async def test_memory_pipeline():
    """测试记忆管道"""
    print("\n" + "=" * 60)
    print("测试7: Memory Pipeline (记忆管道)")
    print("=" * 60)

    from core.memory.memory_pipeline import MemoryPipeline

    pipeline = MemoryPipeline(short_term_window=5, buffer_overflow_threshold=4)

    # 注意：Milvus可能未运行，所以只测试缓冲区功能
    pipeline._initialized = False  # 不连接Milvus

    # 添加对话
    await pipeline.add_turn("user", "我想了解低空经济")
    await pipeline.add_turn("assistant", "低空经济是一种新兴的经济形态...")

    state = pipeline.get_buffer_state()
    print(f"✓ 对话添加成功")
    print(f"  缓冲区大小: {state['buffer_size']}")
    print(f"  最近对话: {len(state['recent_turns'])} 条")

    # 更新用户画像
    await pipeline.update_user_profile("preferences", {"chart_color": "red"})
    print(f"✓ 用户画像更新成功: {pipeline.user_profile}")

    return True


async def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("多智能体协作与长期记忆系统 - 综合测试")
    print("=" * 60)

    # 验证配置
    print("\n检查配置...")
    if not validate_config():
        print("⚠ 部分配置缺失，某些测试可能失败")

    results = {}

    # 运行测试
    tests = [
        ("Embedding服务", test_embedding_service),
        ("LLM服务", test_llm_service),
        ("Web搜索", test_web_search),
        ("Researcher Agent", test_researcher_agent),
        ("Analyst Agent", test_analyst_agent),
        ("Critic Agent", test_critic_agent),
        ("Memory Pipeline", test_memory_pipeline),
    ]

    for name, test_func in tests:
        try:
            result = await test_func()
            results[name] = "✓ 通过" if result else "✗ 失败"
        except Exception as e:
            results[name] = f"✗ 错误: {str(e)[:50]}"
            logger.error(f"测试 {name} 失败: {str(e)}")

    # 打印总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v.startswith("✓"))
    total = len(results)

    for name, result in results.items():
        print(f"  {name}: {result}")

    print(f"\n总计: {passed}/{total} 通过")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
