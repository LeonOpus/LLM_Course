# Industrial AI Agent Course Project

## 项目简介

本项目是一个从零到一构建工业级 AI Agent 的实战项目。通过六周的课程，我们将逐步赋予 Agent 核心知识、决策能力、工具使用能力，最终进化为具备多智能体协作（Multi-Agent）和长期记忆（Long-term Memory）的强大智能系统。

## 技术栈

- **后端**: FastAPI (Python)
- **向量数据库**: Milvus
- **Embedding**: 阿里云 text-embedding-v4
- **LLM**: DeepSeek-v3.2 (通过阿里云 DashScope)
- **Web搜索**: Bocha API
- **可观测性**: LangFuse
- **其他**: Redis (缓存/短期记忆)

## 课程进度

- [x] 第一周：Agent 的知识核心 (向量数据库 & RAG)
- [x] 第二周：DeepResearch 核心 —— 决策循环与基础工具 (ReAct, Tools)
- [x] 第三周：组件化集成 —— 高级数据分析工具集成 (Text2SQL, Code Interpreter)
- [x] **第四周：Agent 进阶 —— 多智能体协作与长期记忆 (Multi-Agent & Memory)**
- [ ] 第五周：工程级算法 —— 模型微调与部署上线 (SFT, Deployment)
- [ ] 第六周：高并发、高可用、高性能工程 (Microservices, Redis)

---

## 快速开始

### 1. 环境安装

```bash
# 解压后进入项目目录
cd week4_project

# 创建虚拟环境（二选一）
# 方式一：使用 conda
conda create -n agent python=3.10 -y
conda activate agent

# 方式二：使用 venv
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 环境变量配置

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入你的 API Key
```

`.env` 文件内容：

```env
# 必需配置
DASHSCOPE_API_KEY=your_dashscope_api_key    # 阿里云DashScope API Key (用于LLM和Embedding)
BOCHA_API_KEY=your_bocha_api_key            # Bocha搜索API Key

# 可选配置 - Milvus向量数据库
MILVUS_HOST=localhost
MILVUS_PORT=19530

# 可选配置 - Redis缓存
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
```

### 3. 启动服务

项目提供三种启动模式：

```bash
cd week4_project

# 启动API服务器
python run.py server
# 可选参数: --host 0.0.0.0 --port 8000

# 运行测试
python run.py test

# 全过程测试
python ./tests/demo_memory_integration.py

# 运行演示
python run.py demo
```

启动服务后访问 API 文档：http://localhost:8000/docs

---

## 项目结构

```
week4_project/
├── api/
│   └── main.py              # FastAPI主服务，所有API接口
├── core/
│   ├── agents/              # 智能体模块
│   │   ├── base.py          # 基础智能体类
│   │   ├── ceo.py           # CEO智能体（协调者）
│   │   ├── researcher.py    # 研究员智能体
│   │   ├── analyst.py       # 分析师智能体
│   │   └── critic.py        # 审核员智能体
│   ├── memory/              # 记忆系统
│   │   ├── memory_pipeline.py  # 记忆管道
│   │   ├── milvus_store.py     # Milvus存储
│   │   └── dreaming.py         # 记忆整理（做梦）
│   └── tools/               # 工具模块
│       ├── embedding.py     # 向量化服务
│       ├── llm.py           # LLM服务
│       └── web_search.py    # Web搜索工具
├── infrastructure/
│   └── observability.py     # LangFuse可观测性
├── tests/
│   └── test_all.py          # 综合测试脚本
├── config.py                # 配置管理
├── requirements.txt         # 依赖列表
└── run.py                   # 启动脚本
```

---

## API 接口

### 工具类接口

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/search` | POST | Web搜索 |
| `/api/embed` | POST | 文本向量化 |
| `/api/chat` | POST | LLM对话 |

### 智能体接口

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/research` | POST | 执行研究任务（Researcher Agent） |
| `/api/analyze` | POST | 执行数据分析（Analyst Agent） |
| `/api/complex-task` | POST | 执行复杂任务（多智能体协作） |

### 记忆系统接口

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/memory/add` | POST | 添加记忆 |
| `/api/memory/query` | POST | 查询记忆 |
| `/api/memory/dream` | POST | 执行记忆整理（做梦） |
| `/api/memory/reflect` | POST | 执行反思 |
| `/api/memory/status` | GET | 获取记忆系统状态 |

---

## 测试用例

### 使用 curl 测试

**1. 健康检查**
```bash
curl http://localhost:8000/health
```

**2. Web搜索**
```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "低空经济 2024", "count": 5}'
```

**3. 文本向量化**
```bash
curl -X POST http://localhost:8000/api/embed \
  -H "Content-Type: application/json" \
  -d '{"texts": ["无人机配送", "低空旅游", "应急救援"]}'
```

**4. LLM对话**
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "请用一句话解释什么是低空经济", "temperature": 0.7}'
```

**5. 研究任务**
```bash
curl -X POST http://localhost:8000/api/research \
  -H "Content-Type: application/json" \
  -d '{"topic": "低空经济的主要应用场景", "max_iterations": 2, "results_per_search": 5}'
```

**6. 数据分析**
```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "task": "创建柱状图展示市场规模数据",
    "data": {"领域": ["无人机物流", "通用航空", "低空旅游"], "规模": [120, 450, 85]},
    "preferences": {"color_scheme": "red"}
  }'
```

**7. 复杂任务（多智能体协作）**
```bash
curl -X POST http://localhost:8000/api/complex-task \
  -H "Content-Type: application/json" \
  -d '{"task": "分析2024年低空经济的市场发展情况", "use_default_sop": true}'
```

**8. 添加记忆**
```bash
curl -X POST http://localhost:8000/api/memory/add \
  -H "Content-Type: application/json" \
  -d '{"role": "user", "content": "我想了解低空经济的发展情况"}'
```

**9. 查询记忆**
```bash
curl -X POST http://localhost:8000/api/memory/query \
  -H "Content-Type: application/json" \
  -d '{"query": "低空经济", "top_k": 5}'
```

**10. 触发记忆整理（做梦）**
```bash
curl -X POST http://localhost:8000/api/memory/dream
```

### 使用 Python 测试

```python
import requests

BASE_URL = "http://localhost:8000"

# 健康检查
resp = requests.get(f"{BASE_URL}/health")
print(resp.json())

# 研究任务
resp = requests.post(f"{BASE_URL}/api/research", json={
    "topic": "低空经济发展趋势",
    "max_iterations": 2,
    "results_per_search": 5
})
print(resp.json())

# 复杂任务
resp = requests.post(f"{BASE_URL}/api/complex-task", json={
    "task": "分析低空经济市场规模",
    "use_default_sop": True,
    "preferences": {"chart_color": "blue"}
})
print(resp.json())
```

### 运行自动化测试

```bash
cd week4_project
python run.py test
```

测试覆盖内容：
- Embedding服务（阿里云 text-embedding-v4）
- LLM服务（DeepSeek-v3）
- Web搜索（Bocha API）
- Researcher Agent（研究员）
- Analyst Agent（分析师）
- Critic Agent（审核员）
- Memory Pipeline（记忆管道）

---

## 注意事项

1. **API Key**：确保 `DASHSCOPE_API_KEY` 和 `BOCHA_API_KEY` 已正确配置
2. **Milvus**：如需使用向量存储功能，需先启动 Milvus 服务
3. **Redis**：如需使用缓存功能，需先启动 Redis 服务
4. **LangFuse**：可观测性功能为可选，配置后可在 LangFuse 平台查看追踪数据


Deepresearch 的简化逻辑

  ┌──────────────────────────────────────────────────────────────────────────┐
  │  CEO Agent (黑色)                                                         │
  │  ┌──────────┐   ┌──────────────────┐   ┌────────────────┐   ┌──────────┐ │
  │  │ Input    │──>│ _generate_sop()  │──>│ _execute_sop() │──>│ Output   │ │
  │  │ Task     │   │ SOPDefinition    │   │ asyncio.gather │   │ Result   │ │
  │  └──────────┘   └──────────────────┘   └────────────────┘   └──────────┘ │
  └──────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
  ┌──────────────────── DAG Task Flow ───────────────────────────────────────┐
  │                                                                          │
  │  ┌─────────────────┐        ┌───────────────┐                            │
  │  │ RESEARCHER (蓝) │──────> │ CRITIC (棕)   │                            │
  │  │ - 迭代搜索       │ output │ - 审核 research│                           │
  │  │ - 信源引用       │        │ - score,issues │                           │
  │  │ → ResearchReport│        └───────┬───────┘                            │
  │  └────────▲────────┘                │                                    │
  │           │                    ┌────▼────┐                               │
  │           │                    │ Pass?   │                               │
  │           │                    └────┬────┘                               │
  │           │                    PASS │    │ REJECT                        │
  │  ┌────────┴────────┐               │    │                                │
  │  │ Feedback        │<──────────────┼────┘                                │
  │  │ Injection       │               │                                     │
  │  │ issues,         │               ▼                                     │
  │  │ suggestions     │  ┌─────────────────┐        ┌───────────────┐       │
  │  └─────────────────┘  │ ANALYST (绿)    │──────> │ CRITIC (棕)   │       │
  │                       │ dependencies:   │ output │ - 审核 code   │       │
  │                       │   [research]    │        │               │       │
  │                       │ - 代码生成执行   │        └───────┬───────┘       │
  │                       └────────▲────────┘                │               │
  │                                │                    PASS │               │
  │                                │ REJECT                  ▼               │
  │                                └─────────────   ┌──────────────┐         │
  │                                                 │ Final Output │         │
  │                                                 │ (CEO 汇总)   │         │
  │                                                 └──────────────┘         │
  └──────────────────────────────────────────────────────────────────────────┘

Dreaming 的逻辑

  模拟生物睡眠时大脑整理记忆的机制，在系统空闲时执行：

                          dream()
                             │
      ┌──────────────────────┼──────────────────────┐
      │                      │                      │
      ▼                      ▼                      ▼
  1. 记忆聚类            2. 去重              3. 提取洞察
     _cluster_memories      _find_duplicates      _extract_insights
     │                      │                      │
     │ 相似记忆分组         │ 删除重复内容         │ 聚类 → LLM 总结
     │                      │                      │ 情景记忆 → 语义记忆
     │                      │                      │
      ┌──────────────────────┼──────────────────────┐
      │                      │                      │
      ▼                      ▼                      ▼
  4. 矛盾修正            5. 归档低频          6. 反思 reflect()
     _resolve_contradictions _archive_old_memories   │
     │                      │                      │ 分析用户画像
     │ 检测矛盾的偏好        │ 30天+低访问→归档     │ 提取行为模式
     │ 保留较新的            │                      │

  五大功能

  | 功能     | 说明                     | 输入 → 输出                      |
  |----------|--------------------------|----------------------------------|
  | 聚类     | 相似记忆分组             | 所有记忆 → {cluster: [memories]} |
  | 去重     | 删除重复内容             | 记忆列表 → 删除重复ID            |
  | 提取洞察 | 从情景记忆升维为语义记忆 | 聚类 → LLM总结 → 新语义记忆      |
  | 矛盾修正 | 检测并删除矛盾的记忆     | 偏好记忆 → 保留最新              |
  | 归档     | 低频旧记忆降级           | >30天 + 访问<3次 → 归档          |

  调用方式（独立使用）

  from core.memory.dreaming import DreamingService

  service = DreamingService()
  service.initialize()

  # 执行做梦（整理记忆）
  report = await service.dream(time_range_hours=24)

  # 执行反思（提取用户画像）
  reflection = await service.reflect()