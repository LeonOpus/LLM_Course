from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging
import sys
import os

# 添加共享模块路径
sys.path.append('/app/shared')

from app.api.routes import router
from app.core.config import settings

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="数学可视化服务",
    description="为数学问题生成可视化图形的服务",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境需要限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件服务
static_path = settings.STATIC_FILES_PATH
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")
    logger.info(f"Mounted static files at: {static_path}")

# 包含路由
app.include_router(router, prefix="/v1")

@app.get("/health")
async def health_check():
    """健康检查端点"""
    try:
        return {
            "status": "healthy",
            "service": "viz-service",
            "version": "1.0.0",
            "static_path": static_path
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "数学可视化服务",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.on_event("startup")
async def startup_event():
    """启动事件"""
    logger.info("Visualization service starting up...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Static files path: {static_path}")
    
    # 确保静态文件目录存在
    os.makedirs(os.path.join(static_path, "images"), exist_ok=True)

@app.on_event("shutdown")
async def shutdown_event():
    """关闭事件"""
    logger.info("Visualization service shutting down...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001) 