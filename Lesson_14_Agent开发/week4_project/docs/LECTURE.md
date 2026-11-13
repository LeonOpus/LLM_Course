# 第四周教学讲义：多智能体协作与长期记忆系统

## 目录

0. [代码阅读指南](#0-代码阅读指南) 
1. [课程概述](#1-课程概述)
2. [系统架构](#2-系统架构)
3. [核心组件详解](#3-核心组件详解)
4. [代码实战](#4-代码实战)
5. [运行与测试](#5-运行与测试)
6. [进阶扩展](#6-进阶扩展)
7. [作业与思考](#7-作业与思考)

---

## 0. 代码阅读指南

> 建议阅读时间：45分钟
>
> 本节提供从 API 入口到核心逻辑的完整阅读路径

### 0.1 阅读顺序总览

```
api/main.py                    ← 入口
    │
    ├─► /api/complex-task      ← 多智能体协作入口
    │       │
    │       └─► core/agents/ceo.py
    │             │
    │             ├─► [Memory Read] retrieve_context()  ⭐ 检索历史记忆
    │             │
    │             ├─► _execute_sop()         (DAG 编排)
    │             │       │
    │             │       ├─► researcher.py  (研究)
    │             │       ├─► analyst.py     (分析)
    │             │       └─► critic.py      (审核)
    │             │
    │             ├─► _execute_node()        (Review Loop)
    │             │       └─► context["review_feedback"] = {...}
    │             │
    │             └─► [Memory Write] add_turn()         ⭐ 保存结果
    │                     └─► 自动归档到 Milvus
    │
    ├─► /api/memory/add        ← 记忆入口
    │       │
    │       └─► core/memory/memory_pipeline.py
    │             ├─► add_turn()             (短期缓冲)
    │             ├─► _archive_buffer()      (归档)
    │             └─► retrieve_context()     (检索)
    │                     └─► milvus_store.py:hybrid_search()
    │
    └─► /api/memory/dream      ← 做梦入口
            │
            └─► core/memory/dreaming.py
                  ├─► _cluster_memories()
                  ├─► _extract_insights()    (episodic → semantic)
                  └─► _resolve_contradictions()
```

---

### 0.2 Step 1: 从 main.py 入口开始

**文件**: `api/main.py`

#### 1.1 生命周期管理 (L46-82)

首先看服务启动时初始化了什么：

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 初始化所有服务
    services["llm"] = LLMService()                    # LLM 服务
    services["ceo"] = CEOAgent(llm_service=...)       # CEO 总控
    services["researcher"] = ResearcherAgent(...)     # 研究员
    services["analyst"] = AnalystAgent(...)           # 分析师
    services["critic"] = CriticAgent(...)             # 审核员
    services["memory_pipeline"] = MemoryPipeline()    # 记忆管道
    services["dreaming"] = DreamingService()          # 做梦服务
```

**要点**: 所有智能体和记忆服务在启动时初始化，共享同一个 LLM 服务

#### 1.2 核心 API 接口 (L273-564)

| 接口 | 行号 | 用途 | 下一步跳转 |
|------|------|------|-----------|
| `POST /api/complex-task` | L430 | **多智能体协作** | → `ceo.py` |
| `POST /api/research` | L367 | 单独研究 | → `researcher.py` |
| `POST /api/analyze` | L399 | 单独分析 | → `analyst.py` |
| `POST /api/memory/add` | L460 | 添加记忆 | → `memory_pipeline.py` |
| `POST /api/memory/query` | L483 | 检索记忆 | → `memory_pipeline.py` |
| `POST /api/memory/dream` | L507 | 触发做梦 | → `dreaming.py` |

#### 1.3 找到 `/api/complex-task` (L430-455)

```python
@app.post("/api/complex-task")
async def complex_task(request: ComplexTaskRequest):
    agent = services["ceo"]                              # 获取 CEO Agent
    context = {"sop": get_market_research_sop(...)}      # 使用默认 SOP
    result = await agent.execute(task=request.task, context=context)
```

**下一步**: 跳转到 `core/agents/ceo.py` 看 `execute()` 方法

---

### 0.3 Step 2: CEO 编排器

**文件**: `core/agents/ceo.py`

#### 2.1 execute() 入口 (L127-200)

```python
async def execute(self, task, context):
    # ⭐ [Memory Read] 检索历史记忆
    if self._memory_enabled:
        memory_context = await self.memory.retrieve_context(task)
        context["memory_context"] = memory_context.compressed_context
        context["user_profile"] = memory_context.user_profile

    # 1. 获取或生成 SOP
    sop = context.get("sop") or await self._generate_sop(task)

    # 2. 执行 SOP（DAG 编排）
    final_result = await self._execute_sop(sop, task, context)

    # ⭐ [Memory Write] 保存任务和结果
    if self._memory_enabled:
        await self.memory.add_turn("user", task, {"type": "task"})
        result_summary = self._summarize_result(final_result)
        await self.memory.add_turn("assistant", result_summary, {"type": "research_result"})

    return TaskResult(success=True, output=final_result, ...)
```

**记忆集成要点**:
- 执行前: `retrieve_context()` 检索相关历史记忆和用户偏好
- 执行后: `add_turn()` 保存任务和结果摘要到短期缓冲区
- 缓冲区溢出时自动归档到 Milvus 长期存储

#### 2.2 默认 SOP 结构 (L266-298)

看 `_get_default_sop()` 理解任务如何分解：

```python
def _get_default_sop(self):
    return SOPDefinition(
        nodes=[
            SOPNode(id="research", agent_type="researcher",
                    task_template=task,
                    dependencies=[]),              # 无依赖，可立即执行

            SOPNode(id="analysis", agent_type="analyst",
                    task_template="基于研究结果...: {{results.research}}",
                    dependencies=["research"]),    # 依赖 research 完成

            SOPNode(id="final_review", agent_type="critic",
                    dependencies=["research", "analysis"])
        ],
        final_output_node="final_review"
    )
```

**要点**:
- `dependencies` 定义了 DAG 依赖关系
- `{{results.research}}` 引用上游节点结果

#### 2.3 DAG 执行器 (L300-372)

```python
async def _execute_sop(self, sop, ...):
    executed = set()
    pending = {node.id: node for node in sop.nodes}

    while pending:
        # 找到依赖已满足的节点
        ready = [n for n in pending if all(dep in executed for dep in n.deps)]

        # 并行执行 (asyncio.gather)
        results = await asyncio.gather(*[execute_node(n) for n in ready])

        for node_id, result in zip(ready, results):
            self.node_results[node_id] = result
            executed.add(node_id)
```

#### 2.4 Review Loop 核心 (L374-451)

```python
async def _execute_node(self, node, ...):
    for retry in range(max_retries):
        # 1. 执行智能体
        agent = self.agents[node.agent_type]
        result = await agent.execute(task_text, context)

        # 2. 如果需要审核
        if node.review_required:
            review = await self._review_node_output(node, result)

            if review.decision == REJECT:
                # ⭐ 关键: 注入反馈到 context
                context["review_feedback"] = {
                    "issues": review.issues,
                    "suggestions": review.suggestions
                }
                continue  # 用反馈重试

        return result  # 通过
```

**要点**: `context["review_feedback"]` 是反馈注入的关键

**下一步**: 跳转到 `researcher.py` 看如何使用这个反馈

---

### 0.4 Step 3: Researcher Agent

**文件**: `core/agents/researcher.py`

#### 3.1 execute() 检查反馈 (L72-131)

```python
async def execute(self, task, context):
    # ⭐ 检查审核反馈（重试时会有）
    review_feedback = context.get("review_feedback")
    if review_feedback:
        logger.info("检测到审核反馈，将调整搜索策略")

    # 执行迭代搜索，传入反馈
    report = await self._iterative_research(
        query=task,
        review_feedback=review_feedback
    )
```

#### 3.2 迭代搜索 (L133-195)

```python
async def _iterative_research(self, query, review_feedback=None):
    # ⭐ 根据反馈调整首次搜索词
    if review_feedback:
        refined = await self._refine_query_from_feedback(query, review_feedback)
        current_query = refined or query

    for i in range(max_iterations):
        # 1. 搜索
        results = await web_search.search(current_query)

        # 2. 评估充足度
        is_sufficient, new_query = await self._evaluate_and_refine(...)

        if is_sufficient:
            break
        current_query = new_query  # 迭代优化搜索词

    # 3. 生成报告
    return await self._generate_report(query, all_results)
```

#### 3.3 反馈处理方法 (L266-308)

```python
async def _refine_query_from_feedback(self, query, feedback):
    prompt = f"""原始研究问题: {query}

    审核发现的问题:
    {feedback['issues']}

    改进建议:
    {feedback['suggestions']}

    请生成一个更精准的搜索词来补充缺失的信息。"""

    return await self.llm.achat(prompt)
```

**要点**: 这就是"真正的重试"——不是简单重复，而是根据反馈调整策略

---

### 0.5 Step 4: Analyst Agent

**文件**: `core/agents/analyst.py`

#### 4.1 execute() 检查反馈 (L93-150)

```python
async def execute(self, task, context):
    review_feedback = context.get("review_feedback")

    # 生成代码（传入反馈）
    code = await self._generate_code(task, context, review_feedback)

    # 执行代码（带自修复重试）
    result = await self._execute_with_retry(code, task, context)
```

#### 4.2 反馈注入到代码生成 (L152-208)

```python
async def _generate_code(self, task, context, review_feedback=None):
    feedback_str = ""
    if review_feedback:
        feedback_str = "⚠️ 上次提交被审核退回，请特别注意:\n"
        for issue in review_feedback['issues']:
            feedback_str += f"- 问题: {issue}\n"
        for s in review_feedback['suggestions']:
            feedback_str += f"- 建议: {s}\n"

    prompt = f"请为任务生成代码\n{feedback_str}..."
```

---

### 0.6 Step 5: Critic Agent

**文件**: `core/agents/critic.py`

#### 5.1 审核 Prompt (L188-227)

```python
prompt = f"""请对以下内容进行全面审核...

请以JSON格式返回:
{{
    "overall_score": 0-100,
    "issues": ["具体问题描述"],
    "suggestions": ["具体可执行的改进建议"]
}}

重要：
- issues 必须具体指出问题所在，如"缺少XX方面的数据"
- suggestions 必须给出可执行的建议，如"补充搜索XX相关信息"
"""
```

**要点**: Critic 的反馈越具体，Researcher/Analyst 的调整越有效

---

### 0.7 Step 6: Memory 系统

**文件**: `core/memory/memory_pipeline.py`

从 `/api/memory/add` 接口进入：

#### 6.1 add_turn() - 短期缓冲 (L99-133)

```python
async def add_turn(self, role, content):
    turn = ConversationTurn(role=role, content=content)
    self.buffer.append(turn)  # 加入短期缓冲区

    # ⭐ 触发归档
    if len(self.buffer) >= self.buffer_overflow_threshold:  # 默认 8
        await self._archive_buffer()

    # 保持窗口大小
    while len(self.buffer) > self.short_term_window:  # 默认 10
        self.buffer.pop(0)
```

#### 6.2 _archive_buffer() - 归档到 Milvus (L135-184)

```python
async def _archive_buffer(self):
    to_archive = self.buffer[:-2]  # 保留最近2轮

    # 1. 生成摘要
    summary = await self._summarize_conversation(conversation_text)

    # 2. 向量化
    embedding = self.embedding.embed_text(summary)

    # 3. 存入 Milvus
    memory = MemoryItem(
        content=summary,
        memory_type="episodic",
        embedding=embedding
    )
    self.milvus.insert([memory])
```

#### 6.3 retrieve_context() - 混合检索 (L215-263)

```python
async def retrieve_context(self, query, top_k=5):
    # 1. 提取关键词
    keywords = await self._extract_keywords(query)

    # 2. 混合检索
    results = self.milvus.hybrid_search(
        query_vector=embedding,
        keywords=keywords,
        vector_weight=0.7,
        keyword_weight=0.3
    )

    # 3. 压缩上下文
    compressed = await self._compress_context(short_term, results, query)
```

**下一步**: 看 `milvus_store.py:hybrid_search()` 了解混合检索实现

---

### 0.8 Step 7: Dreaming 服务

**文件**: `core/memory/dreaming.py`

从 `/api/memory/dream` 接口进入：

#### 7.1 dream() 主流程 (L85-158)

```python
async def dream(self):
    memories = self.milvus.get_all_memories()

    # 1. 聚类相似记忆
    clusters = await self._cluster_memories(memories)

    # 2. 去重
    duplicates = await self._find_duplicates(memories)
    self.milvus.delete(duplicates)

    # 3. ⭐ 提取洞察 (episodic → semantic)
    insights = await self._extract_insights(clusters)

    # 4. 矛盾修正
    await self._resolve_contradictions(memories)

    # 5. 归档低频记忆
    await self._archive_old_memories(memories)
```

#### 7.2 _extract_insights() - 记忆升维 (L255-325)

```python
async def _extract_insights(self, clusters):
    for cluster_id, memories in clusters.items():
        prompt = f"""分析以下相关记忆，提取一条高层次的洞察:
        {contents}
        生成一条简洁的洞察（不超过50字）"""

        insight = await self.llm.achat(prompt)

        # ⭐ 保存为语义记忆（从 episodic 升级）
        memory = MemoryItem(
            content=insight,
            memory_type="semantic",
            importance_score=0.8
        )
        self.milvus.insert([memory])
```

**要点**: episodic (具体事件) → semantic (抽象知识)

---

### 0.9 关键设计模式速查

| 模式 | 文件:行号 | 作用 |
|------|-----------|------|
| DAG 编排 | `ceo.py:316-388` | 拓扑排序 + 并行执行 |
| Review Loop | `ceo.py:390-467` | 审核-反馈-重试 |
| Feedback Injection | `researcher.py:93-96`, `analyst.py:112-119` | 反馈注入 |
| Iterative Search | `researcher.py:133-195` | 自动生成新搜索词 |
| Hybrid Search | `milvus_store.py:331-405` | 向量 + 关键词 |
| Memory Consolidation | `dreaming.py:85-158` | episodic → semantic |
| **Memory Integration** | `ceo.py:155-188` | 执行前检索 + 执行后保存 |

---

### 0.10 调试技巧

#### 日志追踪
```bash
python api/main.py
# 观察日志:
# [CEOAgent] 开始执行任务: ...
# [CEOAgent] 执行节点: 信息研究 (researcher)
# [Researcher] 检测到审核反馈，将调整搜索策略
# [Researcher] 根据反馈调整搜索词: '...'
# [CEOAgent] 审核节点输出: research
# [Critic] 审核完成: PASS, 得分: 85
```

#### API 测试
```bash
# 测试完整流程
curl -X POST http://localhost:8000/api/complex-task \
  -H "Content-Type: application/json" \
  -d '{"task": "分析低空经济市场", "use_default_sop": true}'
```

---

## 1. 课程概述

### 1.1 本周学习目标

本周我们将构建一个**工业级多智能体协作系统**，具备以下核心能力：

- **多智能体协作**：CEO、Researcher、Analyst、Critic四种专业智能体
- **DAG任务编排**：支持复杂任务的分解和并行执行
- **Review Loop机制**：执行-评估-修正的质量保证闭环
- **仿生记忆系统**：短期缓冲、长期存储、记忆整理（做梦）

### 1.2 技术栈

| 组件 | 技术选型 | 说明 |
|------|----------|------|
| LLM | DeepSeek-v3.2 (阿里云DashScope) | 主力推理模型 |
| Embedding | 阿里云 text-embedding-v4 | 1024维向量 |
| 向量数据库 | Milvus | 高性能向量检索 |
| Web搜索 | Bocha API | 全网信息检索 |
| API框架 | FastAPI | 高性能异步框架 |

### 1.3 项目结构

```
week4_project/
├── config.py              # 配置管理
├── requirements.txt       # 依赖
├── run.py                 # 启动脚本
├── core/
│   ├── tools/             # 工具层
│   │   ├── web_search.py  # Web搜索
│   │   ├── embedding.py   # 向量化
│   │   └── llm.py         # LLM服务
│   ├── agents/            # 智能体层
│   │   ├── base.py        # 基础类
│   │   ├── researcher.py  # 研究员
│   │   ├── analyst.py     # 分析师
│   │   ├── critic.py      # 审核员
│   │   └── ceo.py         # 总控
│   └── memory/            # 记忆层
│       ├── milvus_store.py    # Milvus存储
│       ├── memory_pipeline.py # 记忆管道
│       └── dreaming.py        # 做梦服务
├── infrastructure/
│   └── observability.py   # LangFuse可观测性
├── api/
│   └── main.py            # FastAPI服务
└── tests/
    └── test_all.py        # 综合测试
```

---

## 2. 系统架构

### 2.1 整体架构图

> 📊 **高清架构图**: 查看 [architecture.svg](./architecture.svg) 获取完整的矢量架构图

![Architecture](./architecture.svg)

**简化文本版本**:

```
┌─────────────────────────────────────────────────────────────┐
│                         用户请求                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI 服务层                          │
│  /api/research  /api/analyze  /api/complex-task  /api/memory│
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     CEO Agent (总控)                         │
│  ┌─────────┐  ┌──────────┐  ┌─────────┐  ┌─────────────┐   │
│  │Researcher│→│ Analyst  │→│ Critic  │→│  Review Loop │   │
│  │  Agent   │  │  Agent   │  │  Agent  │  │             │   │
│  └─────────┘  └──────────┘  └─────────┘  └─────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     工具层 (Tools)                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  Web Search  │  │  Embedding   │  │       LLM        │  │
│  │  (Bocha API) │  │ (阿里云API)  │  │ (DeepSeek-v3.2)  │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    记忆系统 (Memory)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Short-term   │  │  Long-term   │  │   Dreaming      │  │
│  │ Buffer       │→│  (Milvus)    │←│   Service       │  │
│  │ (滑动窗口)   │  │ (向量存储)   │  │  (记忆整理)     │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  可观测性 (LangFuse)                         │
│     Token Usage • Latency • Trace Context • Cost Analysis   │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 多智能体协作流程

```
用户任务: "分析低空经济市场"
         │
         ▼
┌─────────────────┐
│   CEO Agent     │  1. 解析任务，生成SOP
│   (任务分解)    │  2. 分配给专业Agent
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌────────┐
│Researcher│ │Analyst │  并行执行
│ (研究)  │ │ (分析) │
└────┬───┘ └────┬───┘
     │          │
     └────┬─────┘
          ▼
    ┌──────────┐
    │  Critic  │  审核质量
    │  (审核)  │
    └────┬─────┘
         │
    ┌────┴────┐
    │ 通过?   │
    └────┬────┘
    Yes  │  No
    ▼    └──→ 返回修改
输出结果
```

### 2.3 记忆系统层次

```
┌─────────────────────────────────────────┐
│         感官记忆 (Sensory Memory)        │
│         - 最近N轮原始对话               │
│         - 滑动窗口机制                  │
└───────────────────┬─────────────────────┘
                    │ 缓冲区溢出时归档
                    ▼
┌─────────────────────────────────────────┐
│        情景记忆 (Episodic Memory)        │
│         - 具体事件和经历                │
│         - Who, When, What               │
│         - 存储于Milvus                  │
└───────────────────┬─────────────────────┘
                    │ 做梦时抽象
                    ▼
┌─────────────────────────────────────────┐
│        语义记忆 (Semantic Memory)        │
│         - 抽象知识和规律                │
│         - 用户偏好和模式                │
│         - 高价值洞察                    │
└─────────────────────────────────────────┘
```

---

## 3. 核心组件详解

### 3.1 工具层

#### 3.1.1 Web搜索 (web_search.py)

**核心功能**：
- 单次搜索：调用Bocha API获取网页结果
- 迭代搜索：根据初步结果自动生成新搜索词
- 来源引用：格式化输出带URL的引用

**关键代码解析**：

```python
async def search(self, query: str, count: int = 10, ...) -> List[SearchResult]:
    """
    执行单次搜索

    日志点：
    - 搜索开始时记录query和参数
    - API返回后记录状态码和结果数
    """
    logger.info(f"[WebSearch] 开始搜索: query='{query}', count={count}")

    # 构建请求
    headers = {"Authorization": f"Bearer {self.api_key}", ...}
    payload = {"query": query, "count": count, "summary": True, ...}

    # 发送请求
    async with httpx.AsyncClient() as client:
        response = await client.post(self.api_url, headers=headers, json=payload)

    logger.info(f"[WebSearch] 获取到 {len(results)} 条结果")
    return results
```

**迭代搜索的设计思想**：

```python
async def iterative_search(self, initial_query: str, max_iterations: int = 3, ...):
    """
    迭代搜索实现信息充足度自动评估

    核心循环：
    1. 执行搜索
    2. 评估信息是否充足
    3. 如不充足，LLM生成新搜索词
    4. 重复直到充足或达到最大迭代
    """
    for i in range(max_iterations):
        results = await self.search(current_query, ...)

        if await self._is_sufficient(results):
            break

        new_query = await self._generate_new_query(original, current, results)
        current_query = new_query
```

#### 3.1.2 Embedding服务 (embedding.py)

**核心功能**：
- 单文本/批量文本向量化
- 相似度计算
- Top-K相似查找

**技术要点**：

```python
class EmbeddingService:
    def __init__(self):
        # 使用OpenAI兼容接口调用阿里云API
        self.client = OpenAI(
            api_key=DASHSCOPE_API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self.model = "text-embedding-v4"
        self.dimensions = 1024  # 可配置的向量维度

    def embed_text(self, text: str) -> List[float]:
        response = self.client.embeddings.create(
            model=self.model,
            input=text,
            dimensions=self.dimensions,
            encoding_format="float"
        )
        return response.data[0].embedding
```

#### 3.1.3 LLM服务 (llm.py)

**核心功能**：
- 同步/异步对话接口
- 流式输出
- JSON模式解析

**关键设计**：

```python
class LLMService:
    def __init__(self):
        # 通过阿里云DashScope调用DeepSeek-v3
        self.client = OpenAI(
            api_key=DASHSCOPE_API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self.model = "deepseek-v3"

    async def achat(self, messages: List[Dict], ...) -> str:
        """异步对话接口"""
        response = await self.async_client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
```

### 3.2 智能体层

#### 3.2.1 基础智能体 (base.py)

**设计模式**：模板方法模式

```python
class BaseAgent(ABC):
    """所有智能体的基类"""

    @abstractmethod
    def _build_system_prompt(self) -> str:
        """子类必须实现：构建系统提示"""
        pass

    @abstractmethod
    async def execute(self, task: str, context: Dict) -> TaskResult:
        """子类必须实现：执行任务"""
        pass

    async def think(self, input_text: str, context: Dict) -> str:
        """通用思考方法：调用LLM生成回复"""
        messages = [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": input_text}
        ]
        return await self.llm.achat(messages)
```

#### 3.2.2 研究员智能体 (researcher.py)

**核心能力**：
- 迭代搜索（信息充足度评估）
- 强制来源引用
- 研究报告生成

**关键流程**：

```python
class ResearcherAgent(BaseAgent):
    async def execute(self, task: str, context: Dict) -> TaskResult:
        # 1. 迭代搜索
        report = await self._iterative_research(
            query=task,
            max_iterations=context.get("max_iterations", 3)
        )

        # 2. 返回带来源的报告
        return TaskResult(
            success=True,
            output=report,  # ResearchReport对象
            metadata={"sources": report.sources}
        )

    async def _iterative_research(self, query: str, max_iterations: int):
        """迭代研究流程"""
        for i in range(max_iterations):
            # 搜索
            results = await self.web_search.search(query, ...)

            # 评估充足度
            is_sufficient, new_query = await self._evaluate_and_refine(...)

            if is_sufficient:
                break
            query = new_query

        # 生成报告
        return await self._generate_report(query, all_results)
```

#### 3.2.3 分析师智能体 (analyst.py)

**核心能力**：
- 代码生成和执行
- 错误自修复（最多重试N次）
- 持久化变量空间（模拟Jupyter）

**错误自修复机制**：

```python
class AnalystAgent(BaseAgent):
    async def _execute_with_retry(self, code: str, task: str, ...) -> CodeExecutionResult:
        """带重试的代码执行"""
        for attempt in range(self.max_retries):
            result = self._execute_code(code)

            if result.success:
                return result

            # 执行失败，尝试修复
            logger.warning(f"执行失败: {result.error}")
            code = await self._fix_code(code, result.error, task)

        return CodeExecutionResult(success=False, error="重试次数耗尽")

    async def _fix_code(self, code: str, error: str, task: str) -> str:
        """使用LLM修复代码"""
        prompt = f"""代码执行出错，请修复：

原始代码: {code}
错误信息: {error}

请提供修复后的代码。"""

        response = await self.llm.achat([{"role": "user", "content": prompt}])
        return self._extract_code(response)
```

#### 3.2.4 审核员智能体 (critic.py)

**核心能力**：
- 多维度质量评分
- 事实核查（Fact Check）
- 通过/修改/拒绝决策

**评分机制**：

```python
class CriticAgent(BaseAgent):
    def __init__(self, pass_threshold=70.0, revise_threshold=50.0):
        self.pass_threshold = pass_threshold    # 70分以上通过
        self.revise_threshold = revise_threshold # 50-70需修改，50以下拒绝

    async def _review_content(self, content: str, ...) -> ReviewResult:
        # 调用LLM进行评估
        prompt = f"""评估以下内容的质量：

{content}

请从准确性、完整性、相关性等维度打分(0-100)，并指出问题和建议。"""

        result = await self.llm.achat([{"role": "user", "content": prompt}])

        # 根据分数决定结果
        score = result["overall_score"]
        if score >= self.pass_threshold:
            decision = ReviewDecision.PASS
        elif score >= self.revise_threshold:
            decision = ReviewDecision.REVISE
        else:
            decision = ReviewDecision.REJECT

        return ReviewResult(decision=decision, overall_score=score, ...)
```

#### 3.2.5 CEO智能体 (ceo.py)

**核心能力**：
- SOP（标准作业程序）定义和执行
- DAG任务编排
- Review Loop闭环

**SOP执行流程**：

```python
class CEOAgent(BaseAgent):
    async def _execute_sop(self, sop: SOPDefinition, ...) -> Dict:
        """执行SOP流程"""
        executed = set()
        pending = {node.id: node for node in sop.nodes}

        while pending:
            # 找到依赖已满足的节点
            ready = [n for n in pending.values()
                     if all(dep in executed for dep in n.dependencies)]

            # 并行执行就绪节点
            for node in ready:
                result = await self._execute_node(node, ...)
                self.node_results[node.id] = result
                executed.add(node.id)

        return self.node_results[sop.final_output_node]

    async def _execute_node(self, node: SOPNode, ...) -> Any:
        """执行单个节点（含Review Loop）"""
        for retry in range(node.max_retries + 1):
            # 执行
            agent = self.agents[node.agent_type]
            result = await agent.execute(node.task_template, ...)

            # 审核
            if node.review_required:
                review = await self._review_node_output(node, result)

                if review.decision == ReviewDecision.REJECT:
                    continue  # 重做

            return result
```

### 3.3 记忆系统

#### 3.3.1 Milvus存储 (milvus_store.py)

**核心功能**：
- 记忆的CRUD操作
- 向量相似度搜索
- 混合检索（向量+关键词）

**混合检索实现**：

```python
class MilvusMemoryStore:
    def hybrid_search(
        self,
        query_vector: List[float],
        keywords: List[str],
        top_k: int = 10,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3
    ) -> List[Dict]:
        """混合检索：结合向量相似度和关键词匹配"""

        # 1. 向量搜索
        vector_results = self.search_by_vector(query_vector, top_k * 2)

        # 2. 关键词搜索
        keyword_results = {}
        for kw in keywords:
            for r in self.search_by_keyword(kw, limit=top_k * 2):
                if r["id"] not in keyword_results:
                    keyword_results[r["id"]] = r
                    keyword_results[r["id"]]["keyword_hits"] = 1
                else:
                    keyword_results[r["id"]]["keyword_hits"] += 1

        # 3. 分数融合
        combined = {}
        for r in vector_results:
            combined[r["id"]] = {
                **r,
                "combined_score": r["similarity"] * vector_weight
            }

        for id, r in keyword_results.items():
            kw_score = r["keyword_hits"] / max_hits * keyword_weight
            if id in combined:
                combined[id]["combined_score"] += kw_score
            else:
                combined[id] = {**r, "combined_score": kw_score}

        # 4. 排序返回
        return sorted(combined.values(),
                      key=lambda x: x["combined_score"],
                      reverse=True)[:top_k]
```

#### 3.3.2 记忆管道 (memory_pipeline.py)

**核心功能**：
- 短期缓冲区管理
- 自动归档到长期存储
- 上下文压缩

**缓冲区溢出归档机制**：

```python
class MemoryPipeline:
    async def add_turn(self, role: str, content: str, ...) -> ConversationTurn:
        """添加对话轮次"""
        self.buffer.append(turn)

        # 检查是否需要归档
        if len(self.buffer) >= self.buffer_overflow_threshold:
            await self._archive_buffer()

        # 保持窗口大小
        while len(self.buffer) > self.short_term_window:
            self.buffer.pop(0)

    async def _archive_buffer(self):
        """归档缓冲区到长期存储"""
        to_archive = self.buffer[:-2]  # 保留最近2轮

        # 生成摘要
        summary = await self._summarize_conversation(to_archive)

        # 向量化并存储
        embedding = self.embedding.embed_text(summary)
        memory = MemoryItem(
            content=summary,
            memory_type="episodic",
            embedding=embedding,
            ...
        )
        self.milvus.insert([memory])
```

#### 3.3.3 做梦服务 (dreaming.py)

**核心功能**：
- 记忆聚类和去重
- 洞察提取（情景→语义）
- 矛盾检测和修正

**做梦过程**：

```python
class DreamingService:
    async def dream(self, time_range_hours: int = 24) -> DreamingReport:
        """执行做梦过程"""
        memories = self.milvus.get_all_memories()

        # 1. 聚类
        clusters = await self._cluster_memories(memories)

        # 2. 去重
        duplicates = await self._find_duplicates(memories)
        self.milvus.delete(duplicates)

        # 3. 提取洞察
        insights = await self._extract_insights(clusters)

        # 4. 矛盾修正
        await self._resolve_contradictions(memories)

        # 5. 归档旧记忆
        await self._archive_old_memories(memories)

        return DreamingReport(...)

    async def _extract_insights(self, clusters: Dict) -> List[str]:
        """从聚类中提取高层次洞察"""
        insights = []
        for cluster_id, memories in clusters.items():
            prompt = f"""分析以下相关记忆，提取一条洞察：

{memories}

返回一条简洁的经验法则。"""

            insight = await self.llm.achat([{"role": "user", "content": prompt}])

            # 保存为语义记忆
            self.milvus.insert([MemoryItem(
                content=insight,
                memory_type="semantic",
                ...
            )])
            insights.append(insight)

        return insights
```

---

## 4. 代码实战

### 4.1 环境准备

```bash
# 1. 进入项目目录
cd week4_project

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量（复制.env模板并填写API Key）
cp ../.env.example ../.env
```

### 4.2 基础功能测试

```python
# test_basics.py
import asyncio
from core.tools.embedding import EmbeddingService
from core.tools.llm import LLMService
from core.tools.web_search import WebSearchTool

async def main():
    # 测试Embedding
    embedding = EmbeddingService()
    vec = embedding.embed_text("测试文本")
    print(f"向量维度: {len(vec)}")

    # 测试LLM
    llm = LLMService()
    response = llm.chat([{"role": "user", "content": "你好"}])
    print(f"LLM回复: {response}")

    # 测试搜索
    search = WebSearchTool()
    results = await search.search("低空经济", count=3)
    print(f"搜索结果: {len(results)}条")

asyncio.run(main())
```

### 4.3 智能体使用

```python
# test_agents.py
import asyncio
from core.agents.researcher import ResearcherAgent
from core.agents.analyst import AnalystAgent
from core.agents.ceo import CEOAgent, get_market_research_sop

async def main():
    # 研究员Agent
    researcher = ResearcherAgent()
    result = await researcher.execute(
        task="低空经济的发展趋势",
        context={"max_iterations": 2}
    )
    print(f"研究报告: {result.output.summary}")

    # 分析师Agent
    analyst = AnalystAgent()
    result = await analyst.execute(
        task="创建市场规模柱状图",
        context={
            "data": {"领域": ["物流", "旅游"], "规模": [100, 50]}
        }
    )
    print(f"图表: {result.output.figures}")

    # CEO Agent（多智能体协作）
    ceo = CEOAgent()
    result = await ceo.execute(
        task="分析低空经济市场",
        context={"sop": get_market_research_sop("低空经济")}
    )
    print(f"执行完成: {ceo.get_execution_summary()}")

asyncio.run(main())
```

### 4.4 记忆系统使用

```python
# test_memory.py
import asyncio
from core.memory.memory_pipeline import MemoryPipeline
from core.memory.dreaming import DreamingService

async def main():
    # 记忆管道
    pipeline = MemoryPipeline()
    pipeline.initialize()

    # 添加对话
    await pipeline.add_turn("user", "我对无人机配送很感兴趣")
    await pipeline.add_turn("assistant", "好的，无人机配送是低空经济的重要应用...")

    # 更新用户画像
    await pipeline.update_user_profile("interests", ["无人机", "低空经济"])

    # 检索相关记忆
    context = await pipeline.retrieve_context("无人机技术")
    print(f"相关记忆: {len(context.relevant_memories)}条")

    # 做梦（记忆整理）
    dreaming = DreamingService()
    dreaming.initialize()
    report = await dreaming.dream()
    print(f"生成洞察: {report.insights_generated}条")

asyncio.run(main())
```

---

## 5. 运行与测试

### 5.1 运行测试

```bash
# 运行综合测试
python run.py test

# 输出示例:
# 测试1: Embedding服务 ✓ 通过
# 测试2: LLM服务 ✓ 通过
# 测试3: Web搜索 ✓ 通过
# ...
# 总计: 7/7 通过
```

### 5.2 启动API服务

```bash
# 启动服务器
python run.py server

# 或指定端口
python run.py server --port 8080
```

### 5.3 API接口测试

```bash
# 测试搜索接口
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "低空经济", "count": 5}'

# 测试研究接口
curl -X POST http://localhost:8000/api/research \
  -H "Content-Type: application/json" \
  -d '{"topic": "低空经济发展趋势", "max_iterations": 2}'

# 测试复杂任务
curl -X POST http://localhost:8000/api/complex-task \
  -H "Content-Type: application/json" \
  -d '{"task": "分析低空经济市场", "use_default_sop": true}'
```

### 5.4 查看API文档

浏览器访问: http://localhost:8000/docs

---

## 6. 进阶扩展

### 6.1 可观测性增强 (LangFuse)

本项目已集成 **LangFuse** 实现 LLM 调用的全链路追踪，包括：

- **Token 消耗追踪**：记录每次 LLM 调用的 input/output tokens
- **延迟监控**：记录每次调用的响应时间
- **请求链路追踪**：通过 Trace 和 Span 追踪完整请求链路
- **API 中间件**：自动为所有 `/api/*` 请求创建追踪上下文

#### 6.1.1 配置 LangFuse

在 `.env` 文件中配置：

```bash
LANGFUSE_PUBLIC_KEY=pk-xxx
LANGFUSE_SECRET_KEY=sk-xxx
LANGFUSE_HOST=https://cloud.langfuse.com
```

#### 6.1.2 核心组件

**TraceContext - 追踪上下文管理器**

```python
from infrastructure.observability import TraceContext, LANGFUSE_ENABLED

# 创建追踪上下文
with TraceContext(
    name="research_task",
    user_id="user_123",
    session_id="session_456",
    metadata={"task": "分析低空经济"}
) as trace_ctx:
    # 记录 LLM 调用
    trace_ctx.log_generation(
        name="research_query",
        model="deepseek-v3.2",
        input_messages=[{"role": "user", "content": "..."}],
        output="...",
        usage={"input": 100, "output": 200},
        latency_ms=1500
    )

    # 创建子 Span
    with trace_ctx.create_span("sub_task", input_data={"query": "..."}) as span:
        # 子任务逻辑
        span.set_output({"result": "..."})
```

**LLM 服务自动追踪**

```python
# core/tools/llm.py 已集成自动追踪
class LLMService:
    def chat(self, messages, ..., trace_name="chat"):
        # 自动记录到 LangFuse:
        # - Token 使用量 (input/output/total)
        # - 延迟 (latency_ms)
        # - 温度等参数
        ...

    async def achat(self, messages, ..., trace_name="achat"):
        # 异步版本，同样支持追踪
        ...
```

**API 中间件**

```python
# api/main.py 中的 ObservabilityMiddleware
class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # 自动为 /api/* 请求创建追踪
        # 记录请求ID、路径、用户ID、延迟等
        with TraceContext(
            name=f"{method} {path}",
            user_id=request.headers.get("X-User-ID"),
            ...
        ) as trace_ctx:
            request.state.trace_context = trace_ctx
            response = await call_next(request)
        return response
```

#### 6.1.3 LangFuse 控制台

访问 https://cloud.langfuse.com 查看：

- **Traces**: 完整请求链路
- **Generations**: 所有 LLM 调用详情
- **Dashboard**: Token 消耗、延迟统计、成本分析

```
┌─────────────────────────────────────────────────────────────┐
│                    LangFuse Dashboard                       │
├─────────────────────────────────────────────────────────────┤
│  Trace: POST /api/research                                  │
│  ├── Span: researcher_execute                               │
│  │   ├── Generation: evaluate_sufficiency (deepseek-v3.2)  │
│  │   │   └── tokens: 150 in / 80 out, latency: 1.2s        │
│  │   ├── Generation: generate_report (deepseek-v3.2)       │
│  │   │   └── tokens: 500 in / 800 out, latency: 3.5s       │
│  │   └── ...                                                │
│  └── Total: 5 generations, 2500 tokens, 8.2s               │
└─────────────────────────────────────────────────────────────┘
```

#### 6.1.4 进一步增强（可选）

可以结合 OpenTelemetry 进行更全面的分布式追踪：

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

tracer = trace.get_tracer(__name__)

class CEOAgent(BaseAgent):
    async def execute(self, task: str, context: Dict) -> TaskResult:
        with tracer.start_as_current_span("ceo_execute") as span:
            span.set_attribute("task", task)

            for node in sop.nodes:
                with tracer.start_as_current_span(f"node_{node.id}"):
                    result = await self._execute_node(node, ...)

            return result
```

### 6.2 沙箱代码执行

可以使用Docker实现安全的代码执行环境：

```python
import docker

class SandboxExecutor:
    def __init__(self):
        self.client = docker.from_env()

    def execute(self, code: str) -> str:
        container = self.client.containers.run(
            "python:3.10-slim",
            command=["python", "-c", code],
            mem_limit="512m",
            cpu_quota=50000,
            network_disabled=True,
            remove=True,
            timeout=30
        )
        return container.decode()
```

### 6.3 Rerank重排序

可以添加Rerank模型提升检索质量：

```python
class MilvusMemoryStore:
    async def search_with_rerank(
        self,
        query: str,
        query_vector: List[float],
        top_k: int = 10
    ) -> List[Dict]:
        # 1. 初步检索
        candidates = self.search_by_vector(query_vector, top_k * 3)

        # 2. 调用Rerank模型重排序
        reranked = await self.rerank_model.rerank(
            query=query,
            documents=[c["content"] for c in candidates],
            top_k=top_k
        )

        return reranked
```

---

## 7. 作业与思考

### 7.1 课后作业

1. **基础**：运行所有测试，确保功能正常
2. **进阶**：为AnalystAgent添加更多图表类型支持
3. **挑战**：实现一个新的FinanceAgent，专门处理财务数据分析

### 7.2 思考题

1. 如何优化多智能体间的通信效率？
2. 记忆系统如何处理隐私和敏感信息？
3. 如何评估多智能体系统的整体性能？

### 7.3 扩展阅读

- [Multi-Agent Systems: An Introduction](https://en.wikipedia.org/wiki/Multi-agent_system)
- [Memory in Language Models](https://arxiv.org/abs/2302.01318)
- [Milvus Documentation](https://milvus.io/docs)

---

## 附录：日志级别说明

项目中使用的日志格式：

```
2024-12-27 10:30:15,123 - [ModuleName] - INFO - [Component] 操作描述
```

关键日志点：
- `[CONFIG]` - 配置加载
- `[WebSearch]` - 搜索操作
- `[Embedding]` - 向量化操作
- `[LLM]` - 模型调用（含Token使用量和延迟）
- `[Milvus]` - 数据库操作
- `[Agent名称]` - 智能体操作
- `[MemoryPipeline]` - 记忆管道
- `[DreamingService]` - 做梦服务
- `[API]` - API请求处理（含请求ID和耗时）
- `[Observability]` - LangFuse追踪操作
