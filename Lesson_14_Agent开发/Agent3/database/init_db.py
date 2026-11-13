"""
数据库初始化脚本 - 创建表结构并填充模拟金融数据
"""
import os
import random
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from .models import Base, Stock, Financial, MarketData, ResearchReport, AnalysisHistory

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), "finance.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"


def get_engine():
    """获取数据库引擎"""
    return create_engine(DATABASE_URL, echo=False)


def get_db_session() -> Session:
    """获取数据库会话"""
    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def init_database():
    """初始化数据库并填充模拟数据"""
    engine = get_engine()
    
    # 创建所有表
    Base.metadata.create_all(engine)
    
    session = get_db_session()
    
    # 检查是否已有数据
    if session.query(Stock).count() > 0:
        print("数据库已存在数据，跳过初始化")
        session.close()
        return
    
    print("开始初始化数据库...")
    
    # 创建模拟股票数据
    stocks_data = [
        # 银行股
        {"stock_code": "601398", "stock_name": "工商银行", "industry": "银行", "sector": "金融", "market_cap": 15000, "pe_ratio": 5.2, "pb_ratio": 0.55, "listing_date": "2006-10-27"},
        {"stock_code": "601288", "stock_name": "农业银行", "industry": "银行", "sector": "金融", "market_cap": 12000, "pe_ratio": 4.8, "pb_ratio": 0.48, "listing_date": "2010-07-15"},
        {"stock_code": "601988", "stock_name": "中国银行", "industry": "银行", "sector": "金融", "market_cap": 10000, "pe_ratio": 5.0, "pb_ratio": 0.52, "listing_date": "2006-07-05"},
        {"stock_code": "600036", "stock_name": "招商银行", "industry": "银行", "sector": "金融", "market_cap": 9500, "pe_ratio": 7.5, "pb_ratio": 1.1, "listing_date": "2002-04-09"},
        
        # 科技股
        {"stock_code": "600519", "stock_name": "贵州茅台", "industry": "白酒", "sector": "消费", "market_cap": 22000, "pe_ratio": 28.5, "pb_ratio": 8.2, "listing_date": "2001-08-27"},
        {"stock_code": "000858", "stock_name": "五粮液", "industry": "白酒", "sector": "消费", "market_cap": 6500, "pe_ratio": 22.0, "pb_ratio": 5.5, "listing_date": "1998-04-27"},
        
        # 新能源
        {"stock_code": "300750", "stock_name": "宁德时代", "industry": "新能源", "sector": "科技", "market_cap": 11000, "pe_ratio": 25.0, "pb_ratio": 6.8, "listing_date": "2018-06-11"},
        {"stock_code": "002594", "stock_name": "比亚迪", "industry": "新能源汽车", "sector": "科技", "market_cap": 7500, "pe_ratio": 30.0, "pb_ratio": 4.5, "listing_date": "2011-06-30"},
        
        # 互联网/AI
        {"stock_code": "000001", "stock_name": "平安银行", "industry": "银行", "sector": "金融", "market_cap": 2800, "pe_ratio": 5.8, "pb_ratio": 0.65, "listing_date": "1991-04-03"},
        {"stock_code": "600887", "stock_name": "伊利股份", "industry": "乳制品", "sector": "消费", "market_cap": 2200, "pe_ratio": 18.0, "pb_ratio": 4.2, "listing_date": "1996-03-12"},
        
        # 医药
        {"stock_code": "600276", "stock_name": "恒瑞医药", "industry": "医药", "sector": "医疗健康", "market_cap": 3200, "pe_ratio": 45.0, "pb_ratio": 7.5, "listing_date": "2000-10-18"},
        {"stock_code": "000538", "stock_name": "云南白药", "industry": "医药", "sector": "医疗健康", "market_cap": 1200, "pe_ratio": 25.0, "pb_ratio": 4.0, "listing_date": "1993-12-15"},
        
        # 券商
        {"stock_code": "601211", "stock_name": "国泰君安", "industry": "证券", "sector": "金融", "market_cap": 1800, "pe_ratio": 15.0, "pb_ratio": 1.2, "listing_date": "2015-06-26"},
        {"stock_code": "600030", "stock_name": "中信证券", "industry": "证券", "sector": "金融", "market_cap": 3500, "pe_ratio": 18.0, "pb_ratio": 1.5, "listing_date": "2003-01-06"},
        
        # 地产
        {"stock_code": "000002", "stock_name": "万科A", "industry": "房地产", "sector": "地产", "market_cap": 1500, "pe_ratio": 8.0, "pb_ratio": 0.8, "listing_date": "1991-01-29"},
    ]
    
    for stock_data in stocks_data:
        stock = Stock(**stock_data)
        session.add(stock)
    
    session.commit()
    print(f"已添加 {len(stocks_data)} 只股票基本信息")
    
    # 创建财务数据 (最近3年)
    report_dates = ["2024-12-31", "2024-06-30", "2023-12-31", "2023-06-30", "2022-12-31"]
    report_types = ["年报", "中报", "年报", "中报", "年报"]
    
    for stock_data in stocks_data:
        stock_code = stock_data["stock_code"]
        base_revenue = random.uniform(100, 5000)
        base_profit = base_revenue * random.uniform(0.05, 0.3)
        
        for i, (report_date, report_type) in enumerate(zip(report_dates, report_types)):
            growth_factor = 1 + random.uniform(-0.1, 0.2) * (len(report_dates) - i)
            revenue = base_revenue * growth_factor
            net_profit = base_profit * growth_factor * random.uniform(0.8, 1.2)
            
            financial = Financial(
                stock_code=stock_code,
                report_date=report_date,
                report_type=report_type,
                revenue=round(revenue, 2),
                revenue_yoy=round(random.uniform(-10, 30), 2),
                net_profit=round(net_profit, 2),
                net_profit_yoy=round(random.uniform(-15, 40), 2),
                gross_margin=round(random.uniform(15, 60), 2),
                net_margin=round(random.uniform(5, 35), 2),
                roe=round(random.uniform(5, 25), 2),
                roa=round(random.uniform(2, 15), 2),
                total_assets=round(revenue * random.uniform(2, 8), 2),
                total_liabilities=round(revenue * random.uniform(1, 5), 2),
                asset_liability_ratio=round(random.uniform(30, 75), 2),
                operating_cash_flow=round(net_profit * random.uniform(0.5, 1.5), 2),
                investing_cash_flow=round(-net_profit * random.uniform(0.2, 0.8), 2),
                financing_cash_flow=round(net_profit * random.uniform(-0.5, 0.5), 2)
            )
            session.add(financial)
    
    session.commit()
    print(f"已添加财务数据")
    
    # 创建行情数据 (最近30天)
    base_date = datetime.now()
    
    for stock_data in stocks_data:
        stock_code = stock_data["stock_code"]
        base_price = random.uniform(5, 200)
        
        for day in range(30):
            trade_date = (base_date - timedelta(days=day)).strftime("%Y-%m-%d")
            
            # 跳过周末
            weekday = (base_date - timedelta(days=day)).weekday()
            if weekday >= 5:
                continue
            
            change_pct = random.uniform(-5, 5)
            close_price = base_price * (1 + change_pct / 100)
            open_price = close_price * random.uniform(0.98, 1.02)
            high_price = max(open_price, close_price) * random.uniform(1, 1.03)
            low_price = min(open_price, close_price) * random.uniform(0.97, 1)
            
            market = MarketData(
                stock_code=stock_code,
                trade_date=trade_date,
                open_price=round(open_price, 2),
                close_price=round(close_price, 2),
                high_price=round(high_price, 2),
                low_price=round(low_price, 2),
                pre_close=round(base_price, 2),
                change_pct=round(change_pct, 2),
                volume=round(random.uniform(100, 10000), 2),
                amount=round(random.uniform(1, 100), 2),
                turnover_rate=round(random.uniform(0.5, 5), 2)
            )
            session.add(market)
            base_price = close_price
    
    session.commit()
    print(f"已添加行情数据")
    
    # 创建研报数据
    institutions = ["中金公司", "中信证券", "国泰君安", "华泰证券", "海通证券", "招商证券", "广发证券"]
    analysts = ["张三", "李四", "王五", "赵六", "钱七", "孙八", "周九"]
    ratings = ["买入", "买入", "增持", "增持", "中性"]
    
    report_templates = [
        {"title": "{}深度报告：业绩稳健增长，估值优势明显", "summary": "公司业绩保持稳健增长，估值处于历史低位，具备较强的安全边际。"},
        {"title": "{}行业专题：把握结构性机会", "summary": "行业景气度持续提升，公司作为龙头有望充分受益。"},
        {"title": "{}季报点评：超预期增长，上调盈利预测", "summary": "公司季度业绩超预期，我们上调全年盈利预测。"},
        {"title": "{}投资价值分析：长期看好", "summary": "公司具备核心竞争力，长期投资价值突出。"},
    ]
    
    for stock_data in stocks_data:
        stock_code = stock_data["stock_code"]
        stock_name = stock_data["stock_name"]
        
        for i in range(random.randint(2, 5)):
            template = random.choice(report_templates)
            days_ago = random.randint(1, 90)
            publish_date = (base_date - timedelta(days=days_ago)).strftime("%Y-%m-%d")
            current_price = random.uniform(5, 200)
            
            report = ResearchReport(
                stock_code=stock_code,
                title=template["title"].format(stock_name),
                analyst=random.choice(analysts),
                institution=random.choice(institutions),
                rating=random.choice(ratings),
                target_price=round(current_price * random.uniform(1.1, 1.5), 2),
                current_price=round(current_price, 2),
                publish_date=publish_date,
                summary=template["summary"],
                key_points=f"1. 营收增长稳健\n2. 毛利率持续改善\n3. 市场份额提升",
                risks="1. 宏观经济波动风险\n2. 行业竞争加剧风险\n3. 政策变化风险"
            )
            session.add(report)
    
    session.commit()
    print(f"已添加研报数据")
    
    session.close()
    print("数据库初始化完成!")


def get_table_schema():
    """获取数据库表结构信息，用于Text2SQL"""
    schema_info = """
数据库包含以下表：

1. stocks (股票基本信息表)
   - stock_code: 股票代码 (主键, 如 '601398')
   - stock_name: 股票名称 (如 '工商银行')
   - industry: 所属行业 (如 '银行', '白酒', '新能源')
   - sector: 所属板块 (如 '金融', '消费', '科技')
   - market_cap: 市值(亿元)
   - pe_ratio: 市盈率
   - pb_ratio: 市净率
   - listing_date: 上市日期

2. financials (财务数据表)
   - id: 主键
   - stock_code: 股票代码 (外键)
   - report_date: 报告期 (如 '2024-12-31')
   - report_type: 报告类型 ('年报'/'中报'/'季报')
   - revenue: 营业收入(亿元)
   - revenue_yoy: 营收同比增长(%)
   - net_profit: 净利润(亿元)
   - net_profit_yoy: 净利润同比增长(%)
   - gross_margin: 毛利率(%)
   - net_margin: 净利率(%)
   - roe: ROE(%)
   - roa: ROA(%)
   - total_assets: 总资产(亿元)
   - total_liabilities: 总负债(亿元)
   - asset_liability_ratio: 资产负债率(%)
   - operating_cash_flow: 经营活动现金流(亿元)
   - investing_cash_flow: 投资活动现金流(亿元)
   - financing_cash_flow: 筹资活动现金流(亿元)

3. market_data (行情数据表)
   - id: 主键
   - stock_code: 股票代码 (外键)
   - trade_date: 交易日期 (如 '2024-12-01')
   - open_price: 开盘价
   - close_price: 收盘价
   - high_price: 最高价
   - low_price: 最低价
   - pre_close: 前收盘价
   - change_pct: 涨跌幅(%)
   - volume: 成交量(万手)
   - amount: 成交额(亿元)
   - turnover_rate: 换手率(%)

4. research_reports (研报记录表)
   - id: 主键
   - stock_code: 股票代码 (外键)
   - title: 研报标题
   - analyst: 分析师
   - institution: 研究机构
   - rating: 评级 ('买入'/'增持'/'中性'/'减持'/'卖出')
   - target_price: 目标价
   - current_price: 当前价
   - publish_date: 发布日期
   - summary: 研报摘要
   - key_points: 核心观点
   - risks: 风险提示

常用查询示例：
- 查询所有银行股: SELECT * FROM stocks WHERE industry = '银行'
- 查询市值前10的股票: SELECT * FROM stocks ORDER BY market_cap DESC LIMIT 10
- 查询某股票最新财务数据: SELECT * FROM financials WHERE stock_code = '601398' ORDER BY report_date DESC LIMIT 1
- 查询ROE大于15%的股票: SELECT s.stock_name, f.roe FROM stocks s JOIN financials f ON s.stock_code = f.stock_code WHERE f.roe > 15
"""
    return schema_info


if __name__ == "__main__":
    init_database()
