"""
FastAPI路由定义
"""
import os
import sys
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.graph import FinanceAnalystAgent, analyze_query
from tools.text2sql import Text2SQLTool
from tools.code_executor import CodeExecutorTool
from tools.pdf_parser import PDFParserTool
from tools.web_search import WebSearchTool
from tools.rag_search import RAGSearchTool
from database.init_db import get_db_session, get_table_schema
from database.models import Stock, Financial, MarketData, ResearchReport


router = APIRouter()

# 全局Agent实例
_agent = None
_rag_tool = None


def get_agent():
    global _agent
    if _agent is None:
        _agent = FinanceAnalystAgent()
    return _agent


def get_rag_tool():
    global _rag_tool
    if _rag_tool is None:
        _rag_tool = RAGSearchTool()
    return _rag_tool


# ==================== 请求模型 ====================

class ChatRequest(BaseModel):
    query: str
    max_iterations: int = 3
    stream: bool = False


class SQLRequest(BaseModel):
    question: str


class CodeRequest(BaseModel):
    code: str
    data: Optional[Dict] = None


class SearchRequest(BaseModel):
    query: str
    freshness: str = "noLimit"
    count: int = 10


class RAGRequest(BaseModel):
    query: str
    top_k: int = 5


# ==================== API路由 ====================

@router.get("/")
async def root():
    """根路由"""
    return {
        "name": "金融研报自动化分析师",
        "version": "1.0.0",
        "description": "基于LangGraph的多智能体金融分析系统",
        "endpoints": {
            "/api/chat": "主对话接口",
            "/api/sql/query": "Text2SQL查询",
            "/api/code/execute": "代码执行",
            "/api/search": "网络搜索",
            "/api/rag/search": "RAG检索",
            "/api/stocks": "获取股票列表",
            "/api/schema": "获取数据库结构"
        }
    }


@router.post("/api/chat")
async def chat(request: ChatRequest):
    """
    主对话接口 - 智能金融分析
    
    支持:
    - 数据查询 (Text2SQL)
    - 深度分析 (代码执行)
    - 研报检索 (RAG)
    - 网络搜索
    """
    agent = get_agent()
    
    if request.stream:
        # 流式响应
        async def generate():
            for event in agent.stream_analyze(request.query, request.max_iterations):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream"
        )
    else:
        # 普通响应
        result = agent.analyze(request.query, request.max_iterations)
        return result


@router.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """流式对话接口"""
    agent = get_agent()
    
    async def generate():
        for event in agent.stream_analyze(request.query, request.max_iterations):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )


@router.post("/api/sql/query")
async def sql_query(request: SQLRequest):
    """Text2SQL查询接口"""
    tool = Text2SQLTool()
    result = tool.run(request.question)
    return result


@router.post("/api/code/execute")
async def execute_code(request: CodeRequest):
    """代码执行接口"""
    tool = CodeExecutorTool()
    result = tool.run(request.code, request.data)
    return result


@router.post("/api/search")
async def web_search(request: SearchRequest):
    """网络搜索接口"""
    tool = WebSearchTool()
    result = tool.run(request.query, request.freshness, request.count)
    return result


@router.post("/api/rag/search")
async def rag_search(request: RAGRequest):
    """RAG检索接口"""
    rag = get_rag_tool()
    result = rag.run(request.query, request.top_k)
    return result


@router.post("/api/rag/load_pdf")
async def load_pdf_to_rag(file_path: str):
    """加载PDF到RAG知识库"""
    rag = get_rag_tool()
    result = rag.load_from_pdf(file_path)
    return result


@router.post("/api/upload/pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """上传并解析PDF"""
    # 保存文件
    upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, file.filename)
    
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # 解析PDF
    parser = PDFParserTool()
    result = parser.run(file_path)
    
    # 加载到RAG
    rag = get_rag_tool()
    rag_result = rag.load_from_pdf(file_path)
    
    return {
        "file_path": file_path,
        "parse_result": {
            "success": result.get("success"),
            "page_count": result.get("page_count", 0),
            "text_length": len(result.get("text_content", ""))
        },
        "rag_result": rag_result
    }


# ==================== 数据查询接口 ====================

@router.get("/api/stocks")
async def get_stocks():
    """获取所有股票列表"""
    session = get_db_session()
    try:
        stocks = session.query(Stock).all()
        return {
            "success": True,
            "count": len(stocks),
            "data": [
                {
                    "stock_code": s.stock_code,
                    "stock_name": s.stock_name,
                    "industry": s.industry,
                    "sector": s.sector,
                    "market_cap": s.market_cap,
                    "pe_ratio": s.pe_ratio,
                    "pb_ratio": s.pb_ratio
                }
                for s in stocks
            ]
        }
    finally:
        session.close()


@router.get("/api/stocks/{stock_code}")
async def get_stock_detail(stock_code: str):
    """获取单只股票详情"""
    session = get_db_session()
    try:
        stock = session.query(Stock).filter(Stock.stock_code == stock_code).first()
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")
        
        # 获取最新财务数据
        financials = session.query(Financial).filter(
            Financial.stock_code == stock_code
        ).order_by(Financial.report_date.desc()).limit(4).all()
        
        # 获取最近行情
        market_data = session.query(MarketData).filter(
            MarketData.stock_code == stock_code
        ).order_by(MarketData.trade_date.desc()).limit(10).all()
        
        # 获取研报
        reports = session.query(ResearchReport).filter(
            ResearchReport.stock_code == stock_code
        ).order_by(ResearchReport.publish_date.desc()).limit(5).all()
        
        return {
            "success": True,
            "stock": {
                "stock_code": stock.stock_code,
                "stock_name": stock.stock_name,
                "industry": stock.industry,
                "sector": stock.sector,
                "market_cap": stock.market_cap,
                "pe_ratio": stock.pe_ratio,
                "pb_ratio": stock.pb_ratio,
                "listing_date": stock.listing_date
            },
            "financials": [
                {
                    "report_date": f.report_date,
                    "report_type": f.report_type,
                    "revenue": f.revenue,
                    "net_profit": f.net_profit,
                    "roe": f.roe,
                    "gross_margin": f.gross_margin
                }
                for f in financials
            ],
            "market_data": [
                {
                    "trade_date": m.trade_date,
                    "close_price": m.close_price,
                    "change_pct": m.change_pct,
                    "volume": m.volume
                }
                for m in market_data
            ],
            "reports": [
                {
                    "title": r.title,
                    "analyst": r.analyst,
                    "institution": r.institution,
                    "rating": r.rating,
                    "target_price": r.target_price,
                    "publish_date": r.publish_date
                }
                for r in reports
            ]
        }
    finally:
        session.close()


@router.get("/api/financials/{stock_code}")
async def get_financials(stock_code: str):
    """获取股票财务数据"""
    session = get_db_session()
    try:
        financials = session.query(Financial).filter(
            Financial.stock_code == stock_code
        ).order_by(Financial.report_date.desc()).all()
        
        return {
            "success": True,
            "stock_code": stock_code,
            "count": len(financials),
            "data": [
                {
                    "report_date": f.report_date,
                    "report_type": f.report_type,
                    "revenue": f.revenue,
                    "revenue_yoy": f.revenue_yoy,
                    "net_profit": f.net_profit,
                    "net_profit_yoy": f.net_profit_yoy,
                    "gross_margin": f.gross_margin,
                    "net_margin": f.net_margin,
                    "roe": f.roe,
                    "roa": f.roa,
                    "asset_liability_ratio": f.asset_liability_ratio
                }
                for f in financials
            ]
        }
    finally:
        session.close()


@router.get("/api/schema")
async def get_schema():
    """获取数据库结构信息"""
    return {
        "success": True,
        "schema": get_table_schema()
    }


@router.get("/api/industries")
async def get_industries():
    """获取行业列表"""
    session = get_db_session()
    try:
        from sqlalchemy import distinct
        industries = session.query(distinct(Stock.industry)).all()
        return {
            "success": True,
            "industries": [i[0] for i in industries if i[0]]
        }
    finally:
        session.close()


@router.get("/api/reports")
async def get_reports(
    stock_code: Optional[str] = None,
    institution: Optional[str] = None,
    limit: int = 20
):
    """获取研报列表"""
    session = get_db_session()
    try:
        query = session.query(ResearchReport)
        
        if stock_code:
            query = query.filter(ResearchReport.stock_code == stock_code)
        if institution:
            query = query.filter(ResearchReport.institution == institution)
        
        reports = query.order_by(ResearchReport.publish_date.desc()).limit(limit).all()
        
        return {
            "success": True,
            "count": len(reports),
            "data": [
                {
                    "id": r.id,
                    "stock_code": r.stock_code,
                    "title": r.title,
                    "analyst": r.analyst,
                    "institution": r.institution,
                    "rating": r.rating,
                    "target_price": r.target_price,
                    "publish_date": r.publish_date,
                    "summary": r.summary
                }
                for r in reports
            ]
        }
    finally:
        session.close()
