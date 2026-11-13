# 金融研报自动化分析师 - 系统架构

## 系统概览

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            FastAPI Backend                               │
│                         http://localhost:8000                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    LangGraph Orchestrator                          │  │
│  │                                                                   │  │
│  │   ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐       │  │
│  │   │ Router  │───▶│ Planner │───▶│Executor │───▶│Reflector│       │  │
│  │   │  Node   │    │  Node   │    │  Node   │◀──▶│  Node   │       │  │
│  │   └─────────┘    └─────────┘    └────┬────┘    └────┬────┘       │  │
│  │        │                             │              │             │  │
│  │        │              ┌──────────────┴──────────────┘             │  │
│  │        │              │                                           │  │
│  │        │              ▼                                           │  │
│  │        │         ┌─────────┐                                      │  │
│  │        │         │ Critic  │──▶ Final Answer                      │  │
│  │        │         │  Node   │                                      │  │
│  │        ▼         └─────────┘                                      │  │
│  │   ┌─────────────────────────────────────────────────────────┐    │  │
│  │   │                    Tool Registry                         │    │  │
│  │   ├──────────┬──────────┬──────────┬──────────┬────────────┤    │  │
│  │   │ Text2SQL │   Code   │   PDF    │   Web    │    RAG     │    │  │
│  │   │   Tool   │ Executor │  Parser  │  Search  │   Search   │    │  │
│  │   └────┬─────┴────┬─────┴────┬─────┴────┬─────┴────┬───────┘    │  │
│  └────────│──────────│──────────│──────────│──────────│────────────┘  │
│           │          │          │          │          │               │
│           ▼          ▼          ▼          ▼          ▼               │
│     ┌─────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌─────────┐         │
│     │ SQLite  │ │ Python │ │DocMind │ │BoChat  │ │Embedding│         │
│     │   DB    │ │Sandbox │ │  API   │ │  API   │ │ Service │         │
│     └─────────┘ └────────┘ └────────┘ └────────┘ └─────────┘         │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
```

## 工作流程 (带 ReAct 反思)

```
                         ┌──────────────┐
                         │    START     │
                         └──────┬───────┘
                                │
                                ▼
                         ┌──────────────┐
                         │   Router     │ ◀── 意图识别
                         │    Node      │     (data_query/analysis/research/general)
                         └──────┬───────┘
                                │
                                ▼
                         ┌──────────────┐
                         │   Planner    │ ◀── 任务规划
                         │    Node      │     (生成执行计划)
                         └──────┬───────┘
                                │
                     ┌──────────┴──────────┐
                     │                     │
                     ▼                     │
              ┌──────────────┐             │
              │   Executor   │ ◀── 工具执行 │
              │    Node      │    (循环)   │
              └──────┬───────┘             │
                     │                     │
                     ▼                     │
           ┌─────────────────┐             │
           │ 还有更多步骤?    │             │
           └────────┬────────┘             │
                    │                      │
           ┌────────┴────────┐             │
           │                 │             │
          Yes               No             │
           │                 │             │
           │                 ▼             │
           │         ┌──────────────┐      │
           └────────▶│  Reflector   │      │
                     │    Node      │ ◀── ReAct反思
                     └──────┬───────┘      │
                            │              │
                     ┌──────┴──────┐       │
                     │             │       │
                    完成       需要更多      │
                     │          分析       │
                     │             │       │
                     │             └───────┘
                     ▼                 (重新规划)
              ┌──────────────┐
              │   Critic     │ ◀── 生成答案
              │    Node      │
              └──────┬───────┘
                     │
                     ▼
              ┌──────────────┐
              │     END      │
              └──────────────┘
```

## 数据库 Schema

### stocks (股票基本信息)
| 字段 | 类型 | 说明 |
|------|------|------|
| stock_code | VARCHAR(10) | 股票代码 (PK) |
| stock_name | VARCHAR(50) | 股票名称 |
| industry | VARCHAR(50) | 所属行业 |
| sector | VARCHAR(50) | 所属板块 |
| market_cap | FLOAT | 市值(亿元) |
| pe_ratio | FLOAT | 市盈率 |
| pb_ratio | FLOAT | 市净率 |

### financials (财务数据)
| 字段 | 类型 | 说明 |
|------|------|------|
| stock_code | VARCHAR(10) | 股票代码 (FK) |
| report_date | VARCHAR(20) | 报告期 |
| revenue | FLOAT | 营业收入(亿元) |
| net_profit | FLOAT | 净利润(亿元) |
| roe | FLOAT | ROE(%) |
| gross_margin | FLOAT | 毛利率(%) |

### market_data (行情数据)
| 字段 | 类型 | 说明 |
|------|------|------|
| stock_code | VARCHAR(10) | 股票代码 (FK) |
| trade_date | VARCHAR(20) | 交易日期 |
| close_price | FLOAT | 收盘价 |
| change_pct | FLOAT | 涨跌幅(%) |
| volume | FLOAT | 成交量(万手) |

### research_reports (研报记录)
| 字段 | 类型 | 说明 |
|------|------|------|
| stock_code | VARCHAR(10) | 股票代码 (FK) |
| title | VARCHAR(200) | 研报标题 |
| analyst | VARCHAR(50) | 分析师 |
| institution | VARCHAR(50) | 研究机构 |
| rating | VARCHAR(20) | 评级 |
| target_price | FLOAT | 目标价 |

## API 接口

### 主接口
- `POST /api/chat` - 智能对话 (支持流式)
- `POST /api/chat/stream` - 流式对话

### 工具接口
- `POST /api/sql/query` - Text2SQL查询
- `POST /api/code/execute` - 代码执行
- `POST /api/search` - 网络搜索
- `POST /api/rag/search` - RAG检索

### 数据接口
- `GET /api/stocks` - 股票列表
- `GET /api/stocks/{code}` - 股票详情
- `GET /api/financials/{code}` - 财务数据
- `GET /api/reports` - 研报列表
- `GET /api/schema` - 数据库结构

## 技术栈

- **框架**: FastAPI + LangGraph
- **LLM**: qwen-max (阿里云)
- **Embedding**: text-embedding-v4
- **数据库**: SQLite
- **PDF解析**: PyPDF2 / DocMind
- **网络搜索**: 博查API

## 启动方式

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
python main.py

# 访问
# API文档: http://localhost:8000/docs
# 健康检查: http://localhost:8000/health
```
