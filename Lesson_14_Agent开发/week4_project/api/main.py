"""
FastAPI主服务
提供多智能体系统和记忆系统的API接口
"""
import logging
import time
import uuid
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager
import uvicorn
import sys
sys.path.append(str(__file__).rsplit('/', 2)[0])

from core.tools.web_search import WebSearchTool
from core.tools.embedding import EmbeddingService
from core.tools.llm import LLMService
from core.agents.researcher import ResearcherAgent
from core.agents.analyst import AnalystAgent
from core.agents.critic import CriticAgent
from core.agents.ceo import CEOAgent, get_market_research_sop
from core.memory.memory_pipeline import MemoryPipeline
from core.memory.dreaming import DreamingService
from infrastructure.observability import (
    TraceContext,
    get_langfuse,
    flush_langfuse,
    shutdown_langfuse,
    LANGFUSE_ENABLED
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 全局服务实例
services = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("[API] 启动服务...")

    # 初始化服务
    services["llm"] = LLMService()
    services["embedding"] = EmbeddingService()
    services["web_search"] = WebSearchTool()
    services["memory_pipeline"] = MemoryPipeline()
    services["dreaming"] = DreamingService()

    # 初始化智能体
    services["researcher"] = ResearcherAgent(llm_service=services["llm"])
    services["analyst"] = AnalystAgent(llm_service=services["llm"])
    services["critic"] = CriticAgent(llm_service=services["llm"])
    services["ceo"] = CEOAgent(llm_service=services["llm"])

    # 初始化记忆存储
    services["memory_pipeline"].initialize()
    services["dreaming"].initialize()

    logger.info("[API] 所有服务初始化完成")

    yield

    # 清理
    logger.info("[API] 关闭服务...")
    services["memory_pipeline"].close()
    services["dreaming"].close()

    # 关闭 LangFuse
    if LANGFUSE_ENABLED:
        logger.info("[API] 刷新并关闭 LangFuse...")
        flush_langfuse()
        shutdown_langfuse()


# 创建FastAPI应用
app = FastAPI(
    title="Multi-Agent Memory System",
    description="多智能体协作与长期记忆系统API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 可观测性中间件 ====================

class ObservabilityMiddleware(BaseHTTPMiddleware):
    """
    可观测性中间件
    记录每个请求的追踪信息到 LangFuse
    """

    async def dispatch(self, request: Request, call_next):
        # 生成请求ID
        request_id = str(uuid.uuid4())[:8]
        start_time = time.time()

        # 提取请求信息
        path = request.url.path
        method = request.method
        user_id = request.headers.get("X-User-ID", "anonymous")
        session_id = request.headers.get("X-Session-ID", str(uuid.uuid4()))

        logger.info(f"[API] [{request_id}] {method} {path} 开始处理")

        # 创建追踪上下文
        if LANGFUSE_ENABLED and path.startswith("/api/"):
            trace_name = f"{method} {path}"
            with TraceContext(
                name=trace_name,
                user_id=user_id,
                session_id=session_id,
                metadata={
                    "request_id": request_id,
                    "path": path,
                    "method": method
                }
            ) as trace_ctx:
                # 将追踪上下文存储到 request.state
                request.state.trace_context = trace_ctx

                try:
                    response = await call_next(request)
                    duration = time.time() - start_time

                    logger.info(
                        f"[API] [{request_id}] {method} {path} "
                        f"完成 (状态: {response.status_code}, 耗时: {duration:.2f}s)"
                    )

                    return response

                except Exception as e:
                    duration = time.time() - start_time
                    logger.error(
                        f"[API] [{request_id}] {method} {path} "
                        f"失败 (错误: {str(e)}, 耗时: {duration:.2f}s)"
                    )
                    raise
        else:
            # 非 API 路径或 LangFuse 未启用，直接处理
            response = await call_next(request)
            duration = time.time() - start_time

            logger.info(
                f"[API] [{request_id}] {method} {path} "
                f"完成 (状态: {response.status_code}, 耗时: {duration:.2f}s)"
            )

            return response


# 注册可观测性中间件
app.add_middleware(ObservabilityMiddleware)


# ==================== 请求/响应模型 ====================

class SearchRequest(BaseModel):
    """搜索请求"""
    query: str = Field(..., description="搜索关键词")
    count: int = Field(10, description="返回结果数量")
    freshness: str = Field("noLimit", description="时间范围")

class SearchResponse(BaseModel):
    """搜索响应"""
    success: bool
    results: List[Dict[str, Any]]
    total: int


class EmbeddingRequest(BaseModel):
    """向量化请求"""
    texts: List[str] = Field(..., description="文本列表")

class EmbeddingResponse(BaseModel):
    """向量化响应"""
    success: bool
    embeddings: List[List[float]]
    dimensions: int


class ChatRequest(BaseModel):
    """对话请求"""
    message: str = Field(..., description="用户消息")
    system_prompt: Optional[str] = Field(None, description="系统提示")
    temperature: float = Field(0.7, description="温度参数")

class ChatResponse(BaseModel):
    """对话响应"""
    success: bool
    response: str


class ResearchRequest(BaseModel):
    """研究请求"""
    topic: str = Field(..., description="研究主题")
    max_iterations: int = Field(3, description="最大迭代次数")
    results_per_search: int = Field(5, description="每次搜索结果数")

class ResearchResponse(BaseModel):
    """研究响应"""
    success: bool
    summary: str
    key_findings: List[str]
    sources: List[Dict[str, str]]
    iterations: int


class AnalysisRequest(BaseModel):
    """分析请求"""
    task: str = Field(..., description="分析任务描述")
    data: Optional[Dict[str, Any]] = Field(None, description="数据")
    preferences: Optional[Dict[str, Any]] = Field(None, description="偏好设置")

class AnalysisResponse(BaseModel):
    """分析响应"""
    success: bool
    output: str
    figures: List[str]
    code: str


class ComplexTaskRequest(BaseModel):
    """复杂任务请求"""
    task: str = Field(..., description="任务描述")
    use_default_sop: bool = Field(True, description="使用默认SOP")
    preferences: Optional[Dict[str, Any]] = Field(None, description="用户偏好")

class ComplexTaskResponse(BaseModel):
    """复杂任务响应"""
    success: bool
    result: Dict[str, Any]
    execution_summary: Dict[str, Any]


class MemoryAddRequest(BaseModel):
    """添加记忆请求"""
    role: str = Field(..., description="角色 (user/assistant)")
    content: str = Field(..., description="内容")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")


class MemoryQueryRequest(BaseModel):
    """记忆查询请求"""
    query: str = Field(..., description="查询内容")
    top_k: int = Field(5, description="返回数量")


class DreamingResponse(BaseModel):
    """做梦响应"""
    success: bool
    report: Dict[str, Any]


# ==================== API路由 ====================

@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "Multi-Agent Memory System",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "tools": ["/api/search", "/api/embed", "/api/chat"],
            "agents": ["/api/research", "/api/analyze", "/api/review", "/api/complex-task"],
            "memory": ["/api/memory/add", "/api/memory/query", "/api/memory/dream"]
        }
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "services": list(services.keys())}


# ==================== 工具API ====================

@app.post("/api/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """Web搜索"""
    logger.info(f"[API] 搜索请求: {request.query}")

    try:
        tool = services["web_search"]
        results = await tool.search(
            query=request.query,
            count=request.count,
            freshness=request.freshness,
            summary=True
        )

        return SearchResponse(
            success=True,
            results=[r.to_dict() for r in results],
            total=len(results)
        )
    except Exception as e:
        logger.error(f"[API] 搜索失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/embed", response_model=EmbeddingResponse)
async def embed(request: EmbeddingRequest):
    """文本向量化"""
    logger.info(f"[API] 向量化请求: {len(request.texts)} 条文本")

    try:
        service = services["embedding"]
        embeddings = service.embed_texts(request.texts)

        return EmbeddingResponse(
            success=True,
            embeddings=embeddings,
            dimensions=len(embeddings[0]) if embeddings else 0
        )
    except Exception as e:
        logger.error(f"[API] 向量化失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """LLM对话"""
    logger.info(f"[API] 对话请求: {request.message[:50]}...")

    try:
        service = services["llm"]

        if request.system_prompt:
            response = service.generate_with_system(
                system_prompt=request.system_prompt,
                user_input=request.message,
                temperature=request.temperature
            )
        else:
            messages = [{"role": "user", "content": request.message}]
            response = service.chat(messages, temperature=request.temperature)

        return ChatResponse(success=True, response=response)
    except Exception as e:
        logger.error(f"[API] 对话失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 智能体API ====================

@app.post("/api/research", response_model=ResearchResponse)
async def research(request: ResearchRequest):
    """执行研究任务"""
    logger.info(f"[API] 研究请求: {request.topic}")

    try:
        agent = services["researcher"]
        result = await agent.execute(
            task=request.topic,
            context={
                "max_iterations": request.max_iterations,
                "results_per_search": request.results_per_search
            }
        )

        if result.success:
            report = result.output
            return ResearchResponse(
                success=True,
                summary=report.summary,
                key_findings=report.key_findings,
                sources=report.sources,
                iterations=report.iterations
            )
        else:
            raise HTTPException(status_code=500, detail=result.error)

    except Exception as e:
        logger.error(f"[API] 研究失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze(request: AnalysisRequest):
    """执行数据分析任务"""
    logger.info(f"[API] 分析请求: {request.task[:50]}...")

    try:
        agent = services["analyst"]
        result = await agent.execute(
            task=request.task,
            context={
                "data": request.data,
                "preferences": request.preferences
            }
        )

        if result.success:
            exec_result = result.output
            return AnalysisResponse(
                success=True,
                output=exec_result.output,
                figures=exec_result.figures,
                code=exec_result.code
            )
        else:
            raise HTTPException(status_code=500, detail=result.error)

    except Exception as e:
        logger.error(f"[API] 分析失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/complex-task", response_model=ComplexTaskResponse)
async def complex_task(request: ComplexTaskRequest):
    """执行复杂任务（多智能体协作）"""
    logger.info(f"[API] 复杂任务请求: {request.task[:50]}...")

    try:
        agent = services["ceo"]

        context = {"user_preferences": request.preferences or {}}
        if request.use_default_sop:
            context["sop"] = get_market_research_sop(request.task[:50])

        result = await agent.execute(task=request.task, context=context)

        if result.success:
            return ComplexTaskResponse(
                success=True,
                result=result.output if isinstance(result.output, dict) else {"data": str(result.output)},
                execution_summary=agent.get_execution_summary()
            )
        else:
            raise HTTPException(status_code=500, detail=result.error)

    except Exception as e:
        logger.error(f"[API] 复杂任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 记忆API ====================

@app.post("/api/memory/add")
async def add_memory(request: MemoryAddRequest):
    """添加记忆"""
    logger.info(f"[API] 添加记忆: {request.role}")

    try:
        pipeline = services["memory_pipeline"]
        turn = await pipeline.add_turn(
            role=request.role,
            content=request.content,
            metadata=request.metadata
        )

        return {
            "success": True,
            "turn_id": turn.id,
            "buffer_state": pipeline.get_buffer_state()
        }
    except Exception as e:
        logger.error(f"[API] 添加记忆失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/memory/query")
async def query_memory(request: MemoryQueryRequest):
    """查询记忆"""
    logger.info(f"[API] 查询记忆: {request.query[:50]}...")

    try:
        pipeline = services["memory_pipeline"]
        context = await pipeline.retrieve_context(
            query=request.query,
            top_k=request.top_k
        )

        return {
            "success": True,
            "short_term_count": len(context.short_term),
            "relevant_memories": context.relevant_memories,
            "compressed_context": context.compressed_context,
            "user_profile": context.user_profile
        }
    except Exception as e:
        logger.error(f"[API] 查询记忆失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/memory/dream", response_model=DreamingResponse)
async def dream(background_tasks: BackgroundTasks):
    """执行记忆整理（做梦）"""
    logger.info("[API] 触发做梦任务")

    try:
        dreaming = services["dreaming"]
        report = await dreaming.dream(time_range_hours=24)

        return DreamingResponse(
            success=True,
            report={
                "start_time": report.start_time,
                "end_time": report.end_time,
                "memories_processed": report.memories_processed,
                "clusters_found": report.clusters_found,
                "duplicates_removed": report.duplicates_removed,
                "insights_generated": report.insights_generated,
                "new_semantic_memories": report.new_semantic_memories
            }
        )
    except Exception as e:
        logger.error(f"[API] 做梦失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/memory/reflect")
async def reflect():
    """执行反思"""
    logger.info("[API] 触发反思任务")

    try:
        dreaming = services["dreaming"]
        result = await dreaming.reflect()

        return {
            "success": True,
            "user_profile": result.get("user_profile", {}),
            "patterns": result.get("patterns", [])
        }
    except Exception as e:
        logger.error(f"[API] 反思失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/memory/status")
async def memory_status():
    """获取记忆系统状态"""
    try:
        pipeline = services["memory_pipeline"]
        return {
            "success": True,
            "buffer_state": pipeline.get_buffer_state(),
            "user_profile": pipeline.user_profile
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 启动服务 ====================

def start_server(host: str = "0.0.0.0", port: int = 8000):
    """启动服务器"""
    logger.info(f"[API] 启动服务器: http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    start_server()
