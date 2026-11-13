"""
综合测试案例 - 同时使用 PDF解析、网络搜索、Text2SQL、代码执行
测试场景：分析中金公司业绩，对比银行股数据，结合市场信息生成报告
"""
import os
import sys
import json
import base64
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.code_executor import CodeExecutorTool
from tools.pdf_parser import PDFParserTool
from tools.web_search import WebSearchTool
from database.init_db import get_db_session
from sqlalchemy import text


def test_comprehensive():
    """综合测试：PDF + Web + SQL + Code"""
    print("=" * 70)
    print("综合测试案例：金融分析全流程")
    print("=" * 70)
    print("\n场景：分析中金公司业绩，对比银行股，结合市场动态生成分析报告\n")

    results = {}

    # ============================================================
    # 步骤1: PDF解析 - 读取中金公司研报
    # ============================================================
    print("-" * 70)
    print("[步骤1] PDF解析 - 读取中金公司2025年中期报告")
    print("-" * 70)

    pdf_tool = PDFParserTool()
    pdf_path = "data/中金公司2025年中期报告.pdf"

    if os.path.exists(pdf_path):
        pdf_result = pdf_tool.run(pdf_path)
        if pdf_result.get("success"):
            text_content = pdf_result.get("text_content", "")
            print(f"✓ 解析成功，共 {pdf_result.get('page_count')} 页")
            print(f"✓ 文本长度: {len(text_content)} 字符")
            print(f"\n前500字符预览:\n{text_content[:500]}...")
            results["pdf"] = {
                "success": True,
                "pages": pdf_result.get("page_count"),
                "text_preview": text_content[:1000]
            }
        else:
            print(f"✗ 解析失败: {pdf_result.get('error')}")
            results["pdf"] = {"success": False, "error": pdf_result.get("error")}
    else:
        print(f"✗ 文件不存在: {pdf_path}")
        results["pdf"] = {"success": False, "error": "文件不存在"}

    # ============================================================
    # 步骤2: 网络搜索 - 获取最新市场动态
    # ============================================================
    print("\n" + "-" * 70)
    print("[步骤2] 网络搜索 - 获取券商行业最新动态")
    print("-" * 70)

    web_tool = WebSearchTool()
    search_query = "中金公司 2024 业绩 券商"

    try:
        web_result = web_tool.run(search_query)
        if web_result.get("success"):
            search_results = web_result.get("results", [])
            print(f"✓ 搜索成功，获取 {len(search_results)} 条结果")
            for i, item in enumerate(search_results[:3]):
                print(f"\n  [{i+1}] {item.get('title', 'N/A')}")
                print(f"      {item.get('snippet', 'N/A')[:100]}...")
            results["web"] = {
                "success": True,
                "count": len(search_results),
                "results": search_results[:5]
            }
        else:
            print(f"✗ 搜索失败: {web_result.get('error')}")
            results["web"] = {"success": False, "error": web_result.get("error")}
    except Exception as e:
        print(f"✗ 搜索异常: {str(e)}")
        results["web"] = {"success": False, "error": str(e)}

    # ============================================================
    # 步骤3: SQL查询 - 查询数据库中的金融股数据
    # ============================================================
    print("\n" + "-" * 70)
    print("[步骤3] SQL查询 - 查询银行和券商股票数据")
    print("-" * 70)

    session = get_db_session()

    # 查询1: 银行股基本信息
    print("\n查询1: 银行股PE/PB数据")
    sql1 = """
    SELECT stock_code, stock_name, industry, pe_ratio, pb_ratio, market_cap
    FROM stocks WHERE industry = '银行'
    """
    try:
        result = session.execute(text(sql1))
        data1 = [dict(zip(result.keys(), row)) for row in result.fetchall()]
        print(f"✓ 查询成功，返回 {len(data1)} 条数据")
        print(f"  SQL: {sql1.strip()}")
        for row in data1[:3]:
            print(f"  {row}")
        results["sql_banks"] = {"success": True, "data": data1}
    except Exception as e:
        print(f"✗ 查询失败: {e}")
        results["sql_banks"] = {"success": False}

    # 查询2: 财务数据
    print("\n查询2: 银行股财务数据(ROE, 净利润)")
    sql2 = """
    SELECT s.stock_code, s.stock_name, f.roe, f.net_profit, f.report_date
    FROM stocks s
    JOIN financials f ON s.stock_code = f.stock_code
    WHERE s.industry = '银行'
    ORDER BY f.report_date DESC
    """
    try:
        result = session.execute(text(sql2))
        data2 = [dict(zip(result.keys(), row)) for row in result.fetchall()]
        print(f"✓ 查询成功，返回 {len(data2)} 条数据")
        print(f"  SQL: {sql2.strip()[:80]}...")
        for row in data2[:3]:
            print(f"  {row}")
        results["sql_financials"] = {"success": True, "data": data2}
    except Exception as e:
        print(f"✗ 查询失败: {e}")
        results["sql_financials"] = {"success": False}

    # 查询3: 行情数据
    print("\n查询3: 最近的行情数据")
    sql3 = """
    SELECT s.stock_code, s.stock_name, m.trade_date, m.close_price, m.change_pct
    FROM stocks s
    JOIN market_data m ON s.stock_code = m.stock_code
    WHERE s.industry = '银行'
    ORDER BY m.trade_date DESC
    LIMIT 10
    """
    try:
        result = session.execute(text(sql3))
        data3 = [dict(zip(result.keys(), row)) for row in result.fetchall()]
        print(f"✓ 查询成功，返回 {len(data3)} 条数据")
        print(f"  SQL: {sql3.strip()[:80]}...")
        for row in data3[:3]:
            print(f"  {row}")
        results["sql_market"] = {"success": True, "data": data3}
    except Exception as e:
        print(f"✗ 查询失败: {e}")
        results["sql_market"] = {"success": False}

    session.close()

    # ============================================================
    # 步骤4: 代码执行 - 数据分析和可视化
    # ============================================================
    print("\n" + "-" * 70)
    print("[步骤4] 代码执行 - 数据分析与可视化")
    print("-" * 70)

    code_tool = CodeExecutorTool()

    # 准备综合数据
    combined_data = {
        "banks": results.get("sql_banks", {}).get("data", []),
        "financials": results.get("sql_financials", {}).get("data", []),
        "market": results.get("sql_market", {}).get("data", []),
        "pdf_summary": results.get("pdf", {}).get("text_preview", "无PDF数据"),
        "web_news": [r.get("title", "") for r in results.get("web", {}).get("results", [])]
    }

    analysis_code = '''
# 综合金融分析报告

print("=" * 60)
print("综合金融分析报告")
print("=" * 60)

# 1. 银行股基本面分析
print("\\n【1. 银行股估值分析】")
if data.get("banks"):
    df_banks = pd.DataFrame(data["banks"])
    print(df_banks)
    print(f"\\n平均PE: {df_banks['pe_ratio'].mean():.2f}" if 'pe_ratio' in df_banks.columns else "")
    print(f"平均PB: {df_banks['pb_ratio'].mean():.2f}" if 'pb_ratio' in df_banks.columns else "")
else:
    print("无银行股数据")

# 2. 财务数据分析
print("\\n【2. 财务指标分析】")
if data.get("financials"):
    df_fin = pd.DataFrame(data["financials"])
    print(df_fin)
else:
    print("无财务数据")

# 3. 行情分析
print("\\n【3. 市场行情分析】")
if data.get("market"):
    df_market = pd.DataFrame(data["market"])
    print(df_market)
else:
    print("无行情数据")

# 4. PDF研报摘要
print("\\n【4. 研报信息摘要】")
pdf_text = data.get("pdf_summary", "")[:300]
print(pdf_text if pdf_text else "无研报数据")

# 5. 市场新闻
print("\\n【5. 最新市场动态】")
for i, news in enumerate(data.get("web_news", [])[:3]):
    print(f"  {i+1}. {news}")

# 6. 生成可视化图表
print("\\n【6. 生成分析图表】")

# 创建2x2的子图
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('银行股综合分析报告', fontsize=16, fontweight='bold')

# 图1: PE比率柱状图
ax1 = axes[0, 0]
if data.get("banks"):
    df = pd.DataFrame(data["banks"])
    if 'stock_name' in df.columns and 'pe_ratio' in df.columns:
        colors = plt.cm.Blues(np.linspace(0.4, 0.8, len(df)))
        bars = ax1.bar(df['stock_name'], df['pe_ratio'], color=colors)
        ax1.set_xlabel('银行名称')
        ax1.set_ylabel('PE比率')
        ax1.set_title('银行股PE比率对比')
        ax1.tick_params(axis='x', rotation=45)
        for bar, pe in zip(bars, df['pe_ratio']):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                    f'{pe:.1f}', ha='center', va='bottom', fontsize=9)
    else:
        ax1.text(0.5, 0.5, '数据字段不匹配', ha='center', va='center', transform=ax1.transAxes)
else:
    ax1.text(0.5, 0.5, '无数据', ha='center', va='center', transform=ax1.transAxes)

# 图2: PB比率柱状图
ax2 = axes[0, 1]
if data.get("banks"):
    df = pd.DataFrame(data["banks"])
    if 'stock_name' in df.columns and 'pb_ratio' in df.columns:
        colors = plt.cm.Greens(np.linspace(0.4, 0.8, len(df)))
        bars = ax2.bar(df['stock_name'], df['pb_ratio'], color=colors)
        ax2.set_xlabel('银行名称')
        ax2.set_ylabel('PB比率')
        ax2.set_title('银行股PB比率对比')
        ax2.tick_params(axis='x', rotation=45)
        for bar, pb in zip(bars, df['pb_ratio']):
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                    f'{pb:.2f}', ha='center', va='bottom', fontsize=9)
    else:
        ax2.text(0.5, 0.5, '数据字段不匹配', ha='center', va='center', transform=ax2.transAxes)
else:
    ax2.text(0.5, 0.5, '无数据', ha='center', va='center', transform=ax2.transAxes)

# 图3: 估值散点图 (PE vs PB)
ax3 = axes[1, 0]
if data.get("banks"):
    df = pd.DataFrame(data["banks"])
    if 'pe_ratio' in df.columns and 'pb_ratio' in df.columns:
        scatter = ax3.scatter(df['pe_ratio'], df['pb_ratio'],
                             c=range(len(df)), cmap='viridis', s=100, alpha=0.7)
        ax3.set_xlabel('PE比率')
        ax3.set_ylabel('PB比率')
        ax3.set_title('银行股估值分布 (PE vs PB)')
        if 'stock_name' in df.columns:
            for i, row in df.iterrows():
                ax3.annotate(row['stock_name'], (row['pe_ratio'], row['pb_ratio']),
                           fontsize=8, ha='left')
    else:
        ax3.text(0.5, 0.5, '数据字段不匹配', ha='center', va='center', transform=ax3.transAxes)
else:
    ax3.text(0.5, 0.5, '无数据', ha='center', va='center', transform=ax3.transAxes)

# 图4: 综合信息卡片
ax4 = axes[1, 1]
ax4.axis('off')
summary_text = """
【分析总结】

数据来源:
• PDF研报: 中金公司2025年中期报告
• 数据库: 银行股估值与财务数据
• 网络: 最新市场动态

主要发现:
• 银行股整体估值较低，PE普遍在5-8倍
• PB比率大多破净，反映市场谨慎预期
• 头部银行估值相对稳定

投资建议:
• 关注高ROE、低估值标的
• 注意利率政策变化影响
• 建议分散配置降低风险

* 以上分析仅供参考，不构成投资建议
"""
ax4.text(0.1, 0.9, summary_text, transform=ax4.transAxes, fontsize=10,
        verticalalignment='top', fontfamily='sans-serif',
        bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.3))

plt.tight_layout()
print("图表已生成")
'''

    print("\n执行分析代码...")
    code_result = code_tool.run(analysis_code, combined_data)

    if code_result.get("success"):
        print("\n✓ 代码执行成功!")
        print("\n" + code_result.get("output", ""))

        # 保存图表
        figures = code_result.get("figures", [])
        if figures:
            print(f"\n✓ 生成 {len(figures)} 个图表")
            os.makedirs("output/charts", exist_ok=True)
            for i, fig in enumerate(figures):
                img_path = f"output/charts/comprehensive_analysis_{i}.png"
                with open(img_path, 'wb') as f:
                    f.write(base64.b64decode(fig['base64']))
                print(f"  图表已保存: {img_path}")
        results["code"] = {"success": True, "figures": len(figures)}
    else:
        print(f"\n✗ 代码执行失败: {code_result.get('error')}")
        results["code"] = {"success": False, "error": code_result.get("error")}

    # ============================================================
    # 总结
    # ============================================================
    print("\n" + "=" * 70)
    print("测试总结")
    print("=" * 70)

    tools_status = [
        ("PDF解析", results.get("pdf", {}).get("success", False)),
        ("网络搜索", results.get("web", {}).get("success", False)),
        ("Text2SQL (银行股)", results.get("sql_banks", {}).get("success", False)),
        ("Text2SQL (财务)", results.get("sql_financials", {}).get("success", False)),
        ("Text2SQL (行情)", results.get("sql_market", {}).get("success", False)),
        ("代码执行", results.get("code", {}).get("success", False)),
    ]

    for tool_name, success in tools_status:
        status = "✓ 成功" if success else "✗ 失败"
        print(f"  {tool_name}: {status}")

    success_count = sum(1 for _, s in tools_status if s)
    print(f"\n总计: {success_count}/{len(tools_status)} 个工具执行成功")

    if results.get("code", {}).get("success"):
        print("\n查看分析图表: open output/charts/comprehensive_analysis_0.png")

    return results


if __name__ == "__main__":
    test_comprehensive()
