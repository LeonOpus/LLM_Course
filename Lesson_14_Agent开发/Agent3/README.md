# 🏦 金融研报自动化分析师

基于 **LangGraph** 的多智能体金融分析系统，集成 Text2SQL、代码解释器、PDF解析、网络搜索和 RAG 检索能力。

## ✨ 功能特性

| 功能 | 描述 |
|------|------|
| 🔍 **Text2SQL** | 自然语言转 SQL，智能查询股票/财务/行情数据 |
| 💻 **代码解释器** | 安全执行 Python 代码，支持数据分析和可视化 |
| 📄 **PDF 解析** | 解析研报 PDF，提取关键信息 |
| 🌐 **网络搜索** | 实时获取最新市场动态和新闻 |
| 📚 **RAG 检索** | 基于向量的语义检索，深度理解研报内容 |
| 🔄 **ReAct 反思** | 多轮推理机制，自我评估和改进 |

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Backend                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                 LangGraph Orchestrator                     │  │
│  │                                                           │  │
│  │   Router ──▶ Planner ──▶ Executor ──▶ Reflector ──▶ Critic│  │
│  │     │                       │            │                │  │
│  │     └───────────────────────┼────────────┘                │  │
│  │                             ▼                             │  │
│  │   ┌─────────────────────────────────────────────────┐    │  │
│  │   │               Tool Registry                      │    │  │
│  │   ├─────────┬─────────┬─────────┬─────────┬────────┤    │  │
│  │   │Text2SQL │  Code   │   PDF   │   Web   │  RAG   │    │  │
│  │   │  Tool   │Executor │ Parser  │ Search  │ Search │    │  │
│  │   └─────────┴─────────┴─────────┴─────────┴────────┘    │  │
│  └───────────────────────────────────────────────────────────┘  │
│           ▼           ▼           ▼           ▼                 │
│     [ SQLite ]  [ Python ]  [ DocMind ]  [ 博查API ]            │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 快速开始

### 1. 安装依赖

```bash
cd Agent3
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 阿里云 DashScope API Key (用于 qwen-max 和 text-embedding-v4)
export DASHSCOPE_API_KEY="your_dashscope_api_key"
```

### 3. 启动服务

```bash
python main.py
```

启动后访问：
- **API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

## 📁 项目结构

```
Agent3/
├── main.py                 # FastAPI 入口
├── config.py               # 配置文件
├── requirements.txt        # 依赖列表
├── test_system.py          # 系统测试脚本
├── ARCHITECTURE.md         # 详细架构文档
│
├── database/               # 数据库模块
│   ├── models.py           # SQLAlchemy 模型定义
│   ├── init_db.py          # 数据库初始化 & 模拟数据
│   └── finance.db          # SQLite 数据库文件
│
├── agents/                 # LangGraph 智能体
│   ├── nodes.py            # Agent 节点实现
│   └── graph.py            # 工作流定义
│
├── tools/                  # 工具集
│   ├── text2sql.py         # 自然语言转 SQL
│   ├── code_executor.py    # Python 代码执行器
│   ├── pdf_parser.py       # PDF 解析工具
│   ├── web_search.py       # 网络搜索 (博查API)
│   └── rag_search.py       # RAG 语义检索
│
├── services/               # 服务层
│   ├── llm.py              # LLM 服务 (qwen-max)
│   └── embedding.py        # Embedding 服务
│
└── api/                    # API 路由
    └── routes.py           # FastAPI 路由定义
```

## 📊 数据库设计

系统内置 **15 只 A 股股票** 的模拟数据：

| 表名 | 说明 | 数据量 |
|------|------|--------|
| `stocks` | 股票基本信息 | 15 条 |
| `financials` | 财务数据 (营收/利润/ROE等) | 75 条 |
| `market_data` | 行情数据 (价格/成交量等) | 300 条 |
| `research_reports` | 研报记录 | 51 条 |

**涵盖行业**: 银行、白酒、新能源、医药、券商、地产

## 🔌 API 接口

### 核心接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/chat` | POST | 智能对话 (主入口) |
| `/api/chat/stream` | POST | 流式对话 |

### 工具接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/sql/query` | POST | Text2SQL 查询 |
| `/api/code/execute` | POST | 执行 Python 代码 |
| `/api/search` | POST | 网络搜索 |
| `/api/rag/search` | POST | RAG 检索 |
| `/api/upload/pdf` | POST | 上传 PDF 文件 |

### 数据接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/stocks` | GET | 获取股票列表 |
| `/api/stocks/{code}` | GET | 获取股票详情 |
| `/api/financials/{code}` | GET | 获取财务数据 |
| `/api/reports` | GET | 获取研报列表 |
| `/api/schema` | GET | 获取数据库结构 |

## 💡 使用示例

### 1. 智能对话

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "市值最大的5只银行股是哪些？"}'
```

### 2. Text2SQL 查询

```bash
curl -X POST http://localhost:8000/api/sql/query \
  -H "Content-Type: application/json" \
  -d '{"question": "ROE大于15%的股票有哪些？"}'
```

### 3. 代码执行

```bash
curl -X POST http://localhost:8000/api/code/execute \
  -H "Content-Type: application/json" \
  -d '{
    "code": "import pandas as pd\ndf = pd.DataFrame({\"stock\": [\"茅台\", \"工行\"], \"pe\": [28, 5]})\nprint(df)"
  }'
```

### 4. 网络搜索

```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "A股市场最新消息", "count": 5}'
```

## 🔄 ReAct 反思工作流

```
                    ┌─────────────┐
                    │   START     │
                    └──────┬──────┘
                           ▼
                    ┌─────────────┐
                    │   Router    │ ◀── 意图识别
                    └──────┬──────┘
                           ▼
                    ┌─────────────┐
                    │   Planner   │ ◀── 任务规划
                    └──────┬──────┘
                           ▼
                    ┌─────────────┐
              ┌────▶│  Executor   │ ◀── 工具执行
              │     └──────┬──────┘
              │            ▼
              │     ┌─────────────┐
              │     │  Reflector  │ ◀── ReAct 反思
              │     └──────┬──────┘
              │            │
              │     ┌──────┴──────┐
              │     │             │
              │  需要改进       完成
              │     │             │
              └─────┘             ▼
                          ┌─────────────┐
                          │   Critic    │ ◀── 生成答案
                          └──────┬──────┘
                                 ▼
                          ┌─────────────┐
                          │    END      │
                          └─────────────┘
```

## 🛠️ 技术栈

| 组件 | 技术 |
|------|------|
| 后端框架 | FastAPI |
| 智能体框架 | LangGraph |
| 大语言模型 | qwen-max (阿里云) |
| 向量嵌入 | text-embedding-v4 (阿里云) |
| 数据库 | SQLite + SQLAlchemy |
| PDF 解析 | PyPDF2 / DocMind |
| 网络搜索 | 博查 API |

## 🧪 运行测试

```bash
python test_system.py
```

预期输出：
```
✓ 数据库: 通过
✓ 代码执行器: 通过
✓ PDF解析: 通过
✓ SQL查询: 通过
```

## ⚠️ 注意事项

1. **API Key**: 必须设置 `DASHSCOPE_API_KEY` 环境变量才能使用 LLM 功能
2. **PDF 文件**: 示例使用 `中金公司2025年中期报告.pdf`，可替换为其他研报
3. **代码安全**: 代码执行器在沙箱环境运行，禁止危险操作
4. **模拟数据**: 数据库中的数据为模拟生成，仅供演示

## 📄 License

波哥 & 吴师兄大模型 & 深维学院版权所有

---

