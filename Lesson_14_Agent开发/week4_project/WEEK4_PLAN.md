# 第四周：Agent 进阶 —— 多智能体协作与长期记忆 (Multi-Agent & Memory)

## 1. 课程目标
本周的核心目标是将单体 Agent 进化为**工业级多智能体协作系统 (Enterprise Multi-Agent System)**，并赋予其**仿生长期记忆**能力。我们将跳出简单的 Prompt 拼接，转向**分布式微服务架构**、**基于DAG图的任务编排**以及**类人脑的记忆整理机制**。

## 2. 项目背景与场景
在此之前，我们的 Agent 只是一个“全能选手”。但在处理真实世界的复杂任务（如：“撰写一份 50 页的行业深度研报”）时，单体 Agent 会面临 Context 爆炸、注意力分散、幻觉频发等问题。

**本周场景**：构建一个**虚拟与现实结合的“分布式专家团队”**。
- **用户**：提出极其复杂的目标（例如：“监控全网关于‘低空经济’的动态，每周生成一份包含市场情绪、头部企业动作和投资建议的各种图表的深度报告”）。
- **总控 (CEO)**：负责 SOP (标准作业程序) 的定义与动态调整。
- **研究员 (Researcher)**：具备 Deep Research 能力，能进行“多跳”深度搜索。
- **数据科学家 (Data Scientist)**：运行在安全沙箱中的代码解释器，负责清洗数据、建模和绘图。
- **审计员 (Reviewer)**：负责对输出结果进行 Fact Check 和质量打分，不合格打回重做。
- **海马体 (Hippocampus)**：负责记忆的存储、检索、以及闲时的“梦境整理”（记忆压缩与升维）。

## 3. 核心内容详解

### 3.1 下一代多智能体架构 (Next-Gen MAS)
- **动态编排 (Dynamic Orchestration)**：
  - 抛弃简单的 Chain，引入 **DAG (有向无环图)** 任务流。
  - **SOP 引擎**：将复杂的业务流程固化为状态机，但允许 Agent 在节点内自主发挥。
  - **Review Loop**：引入“执行-评估-修正”的闭环机制。
- **MCP 进阶 (Advanced MCP)**：
  - 将 Agent 封装为无状态的 Micro-Services。
  - 实现 **Agent Discovery**：Master 动态发现可用资源（如 GPU 算力、特定数据库权限）。

### 3.2 仿生记忆系统 (Biomimetic Memory)
- **记忆分层 (Tiered Memory)**：
  - **Sensory Memory (感官/短期)**: Redis Sliding Window，保留最近 N 轮对话原始细节。
  - **Episodic Memory (情景/长期)**: Milvus，存储具体的事件经历（Who, When, What）。
  - **Semantic Memory (语义/知识)**: 后台异步生成的“世界观”和“经验法则”，从情景记忆中抽象而来。
- **记忆整理 (Consolidation)**：
  - 模拟生物睡眠机制，在系统空闲时启动 **Memory GC**，对碎片化记忆进行聚类、去重、矛盾修正和摘要升维。

## 4. 实战 Lab 规划

### Lab 4.1: 工业级多智能体基座
- **任务 1**: 搭建基于 **OpenTelemetry** 的可观测性平台，可视化 Agent 间的 Token 流转和耗时。
- **任务 2**: 实现 **SOP 状态机引擎**，支持定义 `Research -> Analyze -> Review -> (Pass? Publish : Rewrite)` 流程。
- **任务 3**: 构建 **Sandboxed Code Executor** (基于 Docker)，确保 Analysis Agent 的代码执行绝对安全。

### Lab 4.2: 仿生记忆与自我进化
- **任务 1**: 实现 **Hybrid Retrieval** (混合检索)，同时检索向量数据库（模糊匹配）和图数据库（实体关系，可选）/ 关键词索引。
- **任务 2**: 开发 **"Dreaming" Service (做梦服务)**，编写后台 Job，定期扫描 Milvus，将低频访问的记忆归档，将高频相关的记忆融合成新的 Insight。
- **任务 3**: 实现 **Context Compression (上下文压缩)**，使用 LLMLingua 等技术在不丢失关键信息的前提下极大压缩 Prompt Token 消耗。

## 5. 本周 TODO List (Hardcore Mode)

为了打造简历上的“杀手级”项目，本周我们将挑战以下高难度任务：

- [ ] **Phase 1: 基础设施与可观测性 (Infrastructure)**
    - [ ] **架构升级**: 按照 Clean Architecture 重构项目，分离 `Core Domain`, `Application`, `Infrastructure` 层。
    - [ ] **全链路追踪**: 集成 **Jaeger/Zipkin** 和 **OpenTelemetry**。
        - *目标*: 在 Dashboard 上能看到一个 Query 经过了 CEO -> Planner -> Researcher -> Milvus 的完整调用瀑布图。
    - [ ] **Docker 环境**: 为 Code Interpreter 编写独立的 `Dockerfile`，限制 CPU/RAM 配额，实现沙箱隔离。

- [ ] **Phase 2: 高级智能体开发 (Advanced Agents)**
    - [ ] **Researcher Agent (Deep Research)**
        - [ ] 实现 **Iterative Search (迭代搜索)**：根据初步结果自动生成新的搜索词，直到信息充足度达标。
        - [ ] 实现 **Source Citation (信源引用)**：强制要求输出结果必须标注 URL 来源。
    - [ ] **Analyst Agent (The Coder)**
        - [ ] 实现 **Stateful Jupyter Kernel**: 维护一个持久化的 Python 会话，支持变量跨轮次复用。
        - [ ] 实现 **Error Self-Correction**: 代码报错时，自动读取 Traceback 并尝试修正代码。
    - [ ] **Critic Agent (The Gatekeeper)**
        - [ ] 编写专门的 Evaluation Prompt，对 Researcher 的内容真实性和 Analyst 的代码质量进行打分。

- [ ] **Phase 3: 仿生记忆系统 (The Hippocampus)**
    - [ ] **Memory Pipeline**:
        - [ ] `User Input` -> `Short-term Buffer`
        - [ ] `Buffer Overflow` -> `Summarizer` -> `Episodic Vector Store`
    - [ ] **Reflection Process (反思进程)**:
        - [ ] 实现一个后台 Cron Job。
        - [ ] *逻辑*: "回顾过去 24 小时的交互，提取用户的偏好（User Profile）和常用任务模式，存入 `Semantic Memory`。"
    - [ ] **Retrieval Strategy**:
        - [ ] 实现 **Rerank (重排序)** 机制，对检索回来的记忆片段进行相关性打分，只保留 Top-K 注入 Prompt。

- [ ] **Phase 4: 集成与演示 (Integration)**
    - [ ] **SOP 编排**: 定义一个 "Market Research SOP" JSON 配置。
    - [ ] **端到端测试**: 运行一个完整案例，生成一份包含 Matplotlib 图表的 Markdown 报告，并验证记忆系统是否记住了用户的“绘图偏好”（例如：用户上次说喜欢红色系的图表，这次是否自动应用）。
