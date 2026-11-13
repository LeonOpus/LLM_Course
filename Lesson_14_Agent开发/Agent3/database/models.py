"""
数据库模型定义 - 金融数据表结构
"""
from sqlalchemy import Column, Integer, String, Float, Text, Date, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Stock(Base):
    """股票基本信息表"""
    __tablename__ = "stocks"
    
    stock_code = Column(String(10), primary_key=True, comment="股票代码")
    stock_name = Column(String(50), nullable=False, comment="股票名称")
    industry = Column(String(50), comment="所属行业")
    sector = Column(String(50), comment="所属板块")
    market_cap = Column(Float, comment="市值(亿元)")
    pe_ratio = Column(Float, comment="市盈率")
    pb_ratio = Column(Float, comment="市净率")
    listing_date = Column(String(20), comment="上市日期")
    
    # 关系
    financials = relationship("Financial", back_populates="stock")
    market_data = relationship("MarketData", back_populates="stock")
    reports = relationship("ResearchReport", back_populates="stock")


class Financial(Base):
    """财务数据表"""
    __tablename__ = "financials"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(10), ForeignKey("stocks.stock_code"), nullable=False)
    report_date = Column(String(20), nullable=False, comment="报告期")
    report_type = Column(String(20), comment="报告类型(年报/中报/季报)")
    
    # 营收指标
    revenue = Column(Float, comment="营业收入(亿元)")
    revenue_yoy = Column(Float, comment="营收同比增长(%)")
    net_profit = Column(Float, comment="净利润(亿元)")
    net_profit_yoy = Column(Float, comment="净利润同比增长(%)")
    
    # 盈利能力
    gross_margin = Column(Float, comment="毛利率(%)")
    net_margin = Column(Float, comment="净利率(%)")
    roe = Column(Float, comment="ROE(%)")
    roa = Column(Float, comment="ROA(%)")
    
    # 资产负债
    total_assets = Column(Float, comment="总资产(亿元)")
    total_liabilities = Column(Float, comment="总负债(亿元)")
    asset_liability_ratio = Column(Float, comment="资产负债率(%)")
    
    # 现金流
    operating_cash_flow = Column(Float, comment="经营活动现金流(亿元)")
    investing_cash_flow = Column(Float, comment="投资活动现金流(亿元)")
    financing_cash_flow = Column(Float, comment="筹资活动现金流(亿元)")
    
    # 关系
    stock = relationship("Stock", back_populates="financials")


class MarketData(Base):
    """行情数据表"""
    __tablename__ = "market_data"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(10), ForeignKey("stocks.stock_code"), nullable=False)
    trade_date = Column(String(20), nullable=False, comment="交易日期")
    
    open_price = Column(Float, comment="开盘价")
    close_price = Column(Float, comment="收盘价")
    high_price = Column(Float, comment="最高价")
    low_price = Column(Float, comment="最低价")
    pre_close = Column(Float, comment="前收盘价")
    change_pct = Column(Float, comment="涨跌幅(%)")
    volume = Column(Float, comment="成交量(万手)")
    amount = Column(Float, comment="成交额(亿元)")
    turnover_rate = Column(Float, comment="换手率(%)")
    
    # 关系
    stock = relationship("Stock", back_populates="market_data")


class ResearchReport(Base):
    """研报记录表"""
    __tablename__ = "research_reports"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(10), ForeignKey("stocks.stock_code"))
    title = Column(String(200), nullable=False, comment="研报标题")
    analyst = Column(String(50), comment="分析师")
    institution = Column(String(50), comment="研究机构")
    rating = Column(String(20), comment="评级(买入/增持/中性/减持/卖出)")
    target_price = Column(Float, comment="目标价")
    current_price = Column(Float, comment="当前价")
    publish_date = Column(String(20), comment="发布日期")
    summary = Column(Text, comment="研报摘要")
    key_points = Column(Text, comment="核心观点")
    risks = Column(Text, comment="风险提示")
    
    # 关系
    stock = relationship("Stock", back_populates="reports")


class AnalysisHistory(Base):
    """分析历史记录表"""
    __tablename__ = "analysis_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(50), comment="会话ID")
    query = Column(Text, comment="用户查询")
    response = Column(Text, comment="系统回复")
    tools_used = Column(Text, comment="使用的工具")
    reasoning_steps = Column(Text, comment="推理步骤")
    created_at = Column(String(30), comment="创建时间")
