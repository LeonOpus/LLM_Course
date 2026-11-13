"""
金融研报自动化分析师 - FastAPI主入口
"""
import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.routes import router
from database.init_db import init_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化数据库
    print("正在初始化数据库...")
    init_database()
    print("数据库初始化完成")
    
    # 创建上传目录
    upload_dir = os.path.join(os.path.dirname(__file__), "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    
    yield
    
    # 关闭时清理（如果需要）
    print("应用关闭")


# 创建FastAPI应用
app = FastAPI(
    title="金融研报自动化分析师",
    description="""
基于LangGraph的多智能体金融分析系统

## 功能特性

- **智能对话**: 自然语言交互，理解用户意图
- **Text2SQL**: 自然语言转SQL查询
- **代码执行**: Python数据分析和可视化
- **研报解析**: PDF文档解析和RAG检索
- **网络搜索**: 获取最新市场信息
- **ReAct反思**: 多轮推理，自我改进

## 技术架构

- LangGraph多智能体工作流
- qwen-max大语言模型
- SQLite数据库 + 模拟金融数据
- text-embedding-v4向量嵌入
""",
    version="1.0.0",
    lifespan=lifespan
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(router)


# 健康检查
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "finance-analyst"}


if __name__ == "__main__":
    import uvicorn
    
    print("""
╔══════════════════════════════════════════════════════════════╗
║           金融研报自动化分析师 v1.0.0                          ║
║                                                              ║
║   基于 LangGraph 的多智能体金融分析系统                        ║
║                                                              ║
║   功能:                                                      ║
║   - Text2SQL 数据查询                                        ║
║   - 代码解释器 (数据分析/可视化)                              ║
║   - PDF研报解析                                              ║
║   - 网络搜索                                                 ║
║   - RAG知识库检索                                            ║
║   - ReAct反思推理                                            ║
║                                                              ║
║   API文档: http://localhost:8000/docs                        ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
