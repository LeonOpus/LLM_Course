"""
系统测试脚本 - 验证各个组件是否正常工作
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_database():
    """测试数据库"""
    print("\n" + "="*50)
    print("测试1: 数据库初始化")
    print("="*50)
    
    from database.init_db import init_database, get_db_session
    from database.models import Stock, Financial, MarketData, ResearchReport
    
    init_database()
    
    session = get_db_session()
    stocks = session.query(Stock).all()
    financials = session.query(Financial).all()
    market_data = session.query(MarketData).all()
    reports = session.query(ResearchReport).all()
    session.close()
    
    print(f"✓ 股票数量: {len(stocks)}")
    print(f"✓ 财务数据条数: {len(financials)}")
    print(f"✓ 行情数据条数: {len(market_data)}")
    print(f"✓ 研报数量: {len(reports)}")
    
    return True


def test_text2sql():
    """测试Text2SQL (需要API key)"""
    print("\n" + "="*50)
    print("测试2: Text2SQL")
    print("="*50)
    
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("⚠ 未设置DASHSCOPE_API_KEY环境变量，跳过测试")
        return True
    
    from tools.text2sql import Text2SQLTool
    
    tool = Text2SQLTool()
    
    question = "市值最大的3只股票是哪些？"
    print(f"问题: {question}")
    
    result = tool.run(question, return_raw=True)
    
    if result.get("success"):
        print(f"✓ SQL: {result.get('sql')}")
        print(f"✓ 结果数量: {result.get('row_count')}")
        for row in result.get("data", [])[:3]:
            print(f"  - {row}")
        return True
    else:
        print(f"✗ 错误: {result.get('error')}")
        return False


def test_code_executor():
    """测试代码执行器"""
    print("\n" + "="*50)
    print("测试3: 代码执行器")
    print("="*50)
    
    from tools.code_executor import CodeExecutorTool
    
    tool = CodeExecutorTool()
    
    code = """
import pandas as pd
import numpy as np

# 创建数据
data = {'股票': ['茅台', '工行', '宁德'], 'PE': [28, 5, 25]}
df = pd.DataFrame(data)
print(df)
print(f"平均PE: {df['PE'].mean():.1f}")
result = df.to_dict()
"""
    
    result = tool.run(code)
    
    if result.get("success"):
        print(f"✓ 输出:\n{result.get('output')}")
        print(f"✓ 变量: {list(result.get('variables', {}).keys())}")
        return True
    else:
        print(f"✗ 错误: {result.get('error')}")
        return False


def test_pdf_parser():
    """测试PDF解析"""
    print("\n" + "="*50)
    print("测试4: PDF解析器")
    print("="*50)
    
    from tools.pdf_parser import PDFParserTool
    
    tool = PDFParserTool()
    pdf_path = "data/中金公司2025年中期报告.pdf"
    
    if os.path.exists(pdf_path):
        result = tool.run(pdf_path)
        if result.get("success"):
            print(f"✓ 页数: {result.get('page_count')}")
            print(f"✓ 文本长度: {len(result.get('text_content', ''))}")
            text_preview = result.get('text_content', '')[:200]
            if text_preview:
                print(f"✓ 前200字: {text_preview}...")
            return True
        else:
            print(f"✗ 解析失败: {result.get('error')}")
            return False
    else:
        print(f"⚠ PDF文件不存在，跳过测试")
        return True


def test_web_search():
    """测试网络搜索"""
    print("\n" + "="*50)
    print("测试5: 网络搜索")
    print("="*50)
    
    from tools.web_search import WebSearchTool
    
    tool = WebSearchTool()
    
    result = tool.run("A股市场", count=3)
    
    if result.get("success"):
        print(f"✓ 搜索结果数: {result.get('total_count')}")
        if result.get("summary"):
            print(f"✓ 摘要: {result.get('summary')[:100]}...")
        for r in result.get("results", [])[:2]:
            print(f"  - {r.get('title')}")
        return True
    else:
        print(f"✗ 搜索失败: {result.get('error')}")
        return False


def test_sql_direct():
    """直接SQL查询测试"""
    print("\n" + "="*50)
    print("测试6: 直接SQL查询")
    print("="*50)
    
    from database.init_db import get_db_session
    from sqlalchemy import text
    
    session = get_db_session()
    
    queries = [
        ("市值Top5股票", "SELECT stock_code, stock_name, market_cap FROM stocks ORDER BY market_cap DESC LIMIT 5"),
        ("银行股", "SELECT stock_code, stock_name, pe_ratio FROM stocks WHERE industry = '银行'"),
        ("ROE>15%的最新财报", "SELECT s.stock_name, f.roe, f.report_date FROM stocks s JOIN financials f ON s.stock_code = f.stock_code WHERE f.roe > 15 ORDER BY f.report_date DESC LIMIT 5"),
    ]
    
    for name, sql in queries:
        print(f"\n{name}:")
        try:
            result = session.execute(text(sql))
            rows = result.fetchall()
            for row in rows:
                print(f"  {row}")
        except Exception as e:
            print(f"  错误: {e}")
    
    session.close()
    print("\n✓ SQL查询测试完成")
    return True


def run_all_tests():
    """运行所有测试"""
    print("="*50)
    print("金融研报自动化分析师 - 系统测试")
    print("="*50)
    
    results = {}
    
    try:
        results["数据库"] = test_database()
    except Exception as e:
        print(f"数据库测试异常: {e}")
        results["数据库"] = False
    
    try:
        results["代码执行器"] = test_code_executor()
    except Exception as e:
        print(f"代码执行器测试异常: {e}")
        results["代码执行器"] = False
    
    try:
        results["PDF解析"] = test_pdf_parser()
    except Exception as e:
        print(f"PDF解析测试异常: {e}")
        results["PDF解析"] = False
    
    try:
        results["SQL查询"] = test_sql_direct()
    except Exception as e:
        print(f"SQL查询测试异常: {e}")
        results["SQL查询"] = False
    
    # 需要API的测试
    if os.getenv("DASHSCOPE_API_KEY"):
        try:
            results["Text2SQL"] = test_text2sql()
        except Exception as e:
            print(f"Text2SQL测试异常: {e}")
            results["Text2SQL"] = False
    else:
        print("\n⚠ 未设置DASHSCOPE_API_KEY，跳过LLM相关测试")
    
    # 打印总结
    print("\n" + "="*50)
    print("测试结果汇总")
    print("="*50)
    
    for name, passed in results.items():
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {name}: {status}")
    
    all_passed = all(results.values())
    print(f"\n{'✓ 所有测试通过!' if all_passed else '⚠ 部分测试失败'}")
    
    return all_passed


if __name__ == "__main__":
    run_all_tests()
