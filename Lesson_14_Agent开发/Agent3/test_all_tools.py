"""
全工具测试案例 - 使用所有5个工具
场景：综合分析芯片行业投资机会

工具清单：
1. PDF解析 - 读取芯片发展研报
2. 网络搜索 - 获取最新芯片行业新闻
3. SQL查询 - 查询科技股数据
4. RAG检索 - 从知识库检索相关内容
5. 代码执行 - 数据分析与可视化
"""
import os
import sys
import json
import base64
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.code_executor import CodeExecutorTool
from tools.pdf_parser import PDFParserTool
from tools.web_search import WebSearchTool
from tools.rag_search import RAGSearchTool
from database.init_db import get_db_session
from sqlalchemy import text


def run_all_tools_test():
    """测试所有5个工具"""
    print("=" * 70)
    print("全工具测试案例：芯片行业投资分析")
    print("=" * 70)
    print("""
使用工具：
  [1] PDF解析器 - 读取芯片发展研报
  [2] 网络搜索 - 获取芯片行业最新动态
  [3] SQL查询 - 查询科技股财务数据
  [4] RAG检索 - 从知识库检索相关研报
  [5] 代码执行 - 综合分析与可视化
""")

    results = {}

    # ============================================================
    # 工具1: PDF解析 - 读取芯片发展研报
    # ============================================================
    print("-" * 70)
    print("[工具1] PDF解析器 - 读取芯片发展研报")
    print("-" * 70)

    pdf_tool = PDFParserTool()
    pdf_path = "data/芯片发展.pdf"

    if os.path.exists(pdf_path):
        pdf_result = pdf_tool.run(pdf_path)
        if pdf_result.get("success"):
            text_content = pdf_result.get("text_content", "")
            print(f"✓ 解析成功")
            print(f"  页数: {pdf_result.get('page_count')}")
            print(f"  文本长度: {len(text_content)} 字符")
            print(f"  内容预览: {text_content[:300]}...")
            results["pdf"] = {
                "success": True,
                "pages": pdf_result.get("page_count"),
                "content": text_content[:2000]
            }
        else:
            print(f"✗ 解析失败: {pdf_result.get('error')}")
            results["pdf"] = {"success": False, "error": pdf_result.get("error")}
    else:
        print(f"✗ 文件不存在: {pdf_path}")
        results["pdf"] = {"success": False, "error": "文件不存在"}

    # ============================================================
    # 工具2: 网络搜索 - 获取芯片行业最新动态
    # ============================================================
    print("\n" + "-" * 70)
    print("[工具2] 网络搜索 - 获取芯片行业最新动态")
    print("-" * 70)

    web_tool = WebSearchTool()
    search_queries = ["中国芯片 半导体 2024", "摩尔线程 GPU"]

    web_results_all = []
    for query in search_queries:
        print(f"\n搜索: {query}")
        try:
            web_result = web_tool.run(query)
            if web_result.get("success"):
                items = web_result.get("results", [])[:3]
                print(f"✓ 获取 {len(items)} 条结果")
                for item in items:
                    print(f"  - {item.get('title', 'N/A')[:50]}")
                    web_results_all.append(item)
            else:
                print(f"✗ 搜索失败: {web_result.get('error')}")
        except Exception as e:
            print(f"✗ 搜索异常: {e}")

    results["web"] = {
        "success": len(web_results_all) > 0,
        "count": len(web_results_all),
        "results": web_results_all
    }

    # ============================================================
    # 工具3: SQL查询 - 查询科技股数据
    # ============================================================
    print("\n" + "-" * 70)
    print("[工具3] SQL查询 - 查询科技股财务数据")
    print("-" * 70)

    session = get_db_session()

    # 查询科技股基本信息
    print("\n查询: 科技股估值数据")
    sql1 = """
    SELECT stock_code, stock_name, industry, pe_ratio, pb_ratio, market_cap
    FROM stocks
    WHERE industry IN ('科技', '新能源', '芯片', '半导体')
    OR sector = '科技'
    ORDER BY market_cap DESC
    """
    try:
        result = session.execute(text(sql1))
        data_stocks = [dict(zip(result.keys(), row)) for row in result.fetchall()]
        print(f"✓ 返回 {len(data_stocks)} 条数据")
        for row in data_stocks[:3]:
            print(f"  {row}")
        results["sql_stocks"] = {"success": True, "data": data_stocks}
    except Exception as e:
        print(f"✗ 查询失败: {e}")
        results["sql_stocks"] = {"success": False, "error": str(e)}

    # 查询所有行业分布
    print("\n查询: 行业分布统计")
    sql2 = """
    SELECT industry, COUNT(*) as count, AVG(pe_ratio) as avg_pe, AVG(market_cap) as avg_cap
    FROM stocks
    GROUP BY industry
    ORDER BY count DESC
    """
    try:
        result = session.execute(text(sql2))
        data_industry = [dict(zip(result.keys(), row)) for row in result.fetchall()]
        print(f"✓ 返回 {len(data_industry)} 个行业")
        for row in data_industry:
            print(f"  {row['industry']}: {row['count']}只, 平均PE={row['avg_pe']:.1f}" if row['avg_pe'] else f"  {row['industry']}: {row['count']}只")
        results["sql_industry"] = {"success": True, "data": data_industry}
    except Exception as e:
        print(f"✗ 查询失败: {e}")
        results["sql_industry"] = {"success": False, "error": str(e)}

    # 查询研报评级
    print("\n查询: 研报评级分布")
    sql3 = """
    SELECT r.rating, COUNT(*) as count, AVG(r.target_price) as avg_target
    FROM research_reports r
    GROUP BY r.rating
    ORDER BY count DESC
    """
    try:
        result = session.execute(text(sql3))
        data_ratings = [dict(zip(result.keys(), row)) for row in result.fetchall()]
        print(f"✓ 返回 {len(data_ratings)} 种评级")
        for row in data_ratings:
            print(f"  {row['rating']}: {row['count']}份")
        results["sql_ratings"] = {"success": True, "data": data_ratings}
    except Exception as e:
        print(f"✗ 查询失败: {e}")
        results["sql_ratings"] = {"success": False, "error": str(e)}

    session.close()

    # ============================================================
    # 工具4: RAG检索 - 从知识库检索相关内容
    # ============================================================
    print("\n" + "-" * 70)
    print("[工具4] RAG检索 - 从知识库检索芯片相关研报")
    print("-" * 70)

    try:
        rag_tool = RAGSearchTool()
        rag_query = "芯片半导体行业发展趋势投资机会"

        rag_result = rag_tool.run(rag_query)
        if rag_result.get("success"):
            docs = rag_result.get("documents", [])
            print(f"✓ 检索成功，返回 {len(docs)} 条相关内容")
            for i, doc in enumerate(docs[:3]):
                content = doc.get("content", "")[:100]
                score = doc.get("score", 0)
                print(f"  [{i+1}] (相关度:{score:.2f}) {content}...")
            results["rag"] = {"success": True, "documents": docs}
        else:
            print(f"✗ 检索失败: {rag_result.get('error')}")
            results["rag"] = {"success": False, "error": rag_result.get("error")}
    except Exception as e:
        print(f"✗ RAG跳过: {str(e)[:50]}...")
        print("  (需要: DASHSCOPE_API_KEY + Milvus服务)")
        results["rag"] = {"success": False, "error": str(e)}

    # ============================================================
    # 工具5: 代码执行 - 综合分析与可视化
    # ============================================================
    print("\n" + "-" * 70)
    print("[工具5] 代码执行 - 综合分析与可视化")
    print("-" * 70)

    code_tool = CodeExecutorTool()

    # 准备所有收集到的数据
    analysis_data = {
        "stocks": results.get("sql_stocks", {}).get("data", []),
        "industry": results.get("sql_industry", {}).get("data", []),
        "ratings": results.get("sql_ratings", {}).get("data", []),
        "pdf_content": results.get("pdf", {}).get("content", ""),
        "web_news": [r.get("title", "") for r in results.get("web", {}).get("results", [])],
        "rag_docs": [d.get("content", "")[:200] for d in results.get("rag", {}).get("documents", [])]
    }

    analysis_code = '''
print("=" * 60)
print("芯片行业投资分析报告")
print("=" * 60)

# 1. 数据概览
print("\\n【1. 数据来源概览】")
print(f"  PDF研报: {'已加载' if data.get('pdf_content') else '未加载'} ({len(data.get('pdf_content', ''))}字)")
print(f"  网络新闻: {len(data.get('web_news', []))} 条")
print(f"  股票数据: {len(data.get('stocks', []))} 只")
print(f"  行业分布: {len(data.get('industry', []))} 个行业")
print(f"  RAG文档: {len(data.get('rag_docs', []))} 条")

# 2. 行业分布分析
print("\\n【2. 行业分布分析】")
if data.get("industry"):
    df_ind = pd.DataFrame(data["industry"])
    print(df_ind.to_string(index=False))

# 3. 股票估值分析
print("\\n【3. 股票估值分析】")
if data.get("stocks"):
    df_stocks = pd.DataFrame(data["stocks"])
    print(df_stocks.to_string(index=False))
    print(f"\\n  平均PE: {df_stocks['pe_ratio'].mean():.2f}")
    print(f"  平均PB: {df_stocks['pb_ratio'].mean():.2f}")
    print(f"  总市值: {df_stocks['market_cap'].sum():.0f}亿")

# 4. 研报评级分布
print("\\n【4. 研报评级分布】")
if data.get("ratings"):
    df_ratings = pd.DataFrame(data["ratings"])
    print(df_ratings.to_string(index=False))

# 5. 最新市场动态
print("\\n【5. 最新市场动态】")
for i, news in enumerate(data.get("web_news", [])[:5], 1):
    print(f"  {i}. {news[:60]}")

# 6. 生成可视化图表
print("\\n【6. 生成分析图表】")

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('芯片行业投资分析', fontsize=16, fontweight='bold')

# 图1: 行业股票数量分布（饼图）
ax1 = axes[0, 0]
if data.get("industry"):
    df = pd.DataFrame(data["industry"])
    colors = plt.cm.Set3(np.linspace(0, 1, len(df)))
    wedges, texts, autotexts = ax1.pie(
        df['count'], labels=df['industry'], autopct='%1.0f%%',
        colors=colors, startangle=90
    )
    ax1.set_title('行业股票数量分布')
else:
    ax1.text(0.5, 0.5, '无数据', ha='center', va='center')
    ax1.set_title('行业股票数量分布')

# 图2: 各行业平均PE对比（柱状图）
ax2 = axes[0, 1]
if data.get("industry"):
    df = pd.DataFrame(data["industry"])
    df_valid = df[df['avg_pe'].notna()]
    if len(df_valid) > 0:
        colors = plt.cm.Blues(np.linspace(0.4, 0.8, len(df_valid)))
        bars = ax2.bar(df_valid['industry'], df_valid['avg_pe'], color=colors)
        ax2.set_xlabel('行业')
        ax2.set_ylabel('平均PE')
        ax2.set_title('各行业平均PE对比')
        ax2.tick_params(axis='x', rotation=45)
        for bar in bars:
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                    f'{bar.get_height():.1f}', ha='center', va='bottom', fontsize=8)
else:
    ax2.text(0.5, 0.5, '无数据', ha='center', va='center')
    ax2.set_title('各行业平均PE对比')

# 图3: 研报评级分布（柱状图）
ax3 = axes[1, 0]
if data.get("ratings"):
    df = pd.DataFrame(data["ratings"])
    colors = ['#2ecc71', '#27ae60', '#f39c12', '#e74c3c', '#c0392b'][:len(df)]
    bars = ax3.bar(df['rating'], df['count'], color=colors)
    ax3.set_xlabel('评级')
    ax3.set_ylabel('研报数量')
    ax3.set_title('研报评级分布')
    for bar in bars:
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                f'{int(bar.get_height())}', ha='center', va='bottom')
else:
    ax3.text(0.5, 0.5, '无数据', ha='center', va='center')
    ax3.set_title('研报评级分布')

# 图4: 信息汇总卡片
ax4 = axes[1, 1]
ax4.axis('off')

# 从PDF提取关键信息
pdf_summary = data.get('pdf_content', '')[:500] if data.get('pdf_content') else '无PDF数据'

summary_text = f"""
【综合分析摘要】

数据来源统计:
• PDF研报: {len(data.get('pdf_content', ''))} 字符
• 网络新闻: {len(data.get('web_news', []))} 条
• 数据库股票: {len(data.get('stocks', []))} 只
• RAG检索: {len(data.get('rag_docs', []))} 条

投资建议:
• 关注科技板块龙头股票
• 芯片行业长期发展前景向好
• 注意估值风险，选择性配置
• 建议关注政策支持方向

风险提示:
• 科技股波动较大
• 行业竞争加剧
• 国际环境不确定性

* 本报告由AI自动生成，仅供参考
"""

ax4.text(0.05, 0.95, summary_text, transform=ax4.transAxes, fontsize=9,
        verticalalignment='top', fontfamily='monospace',
        bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.5))

plt.tight_layout()
print("图表生成完成")
'''

    print("\n执行分析代码...")
    code_result = code_tool.run(analysis_code, analysis_data)

    if code_result.get("success"):
        print("\n✓ 代码执行成功!")
        print(code_result.get("output", ""))

        # 保存图表
        figures = code_result.get("figures", [])
        if figures:
            os.makedirs("output/charts", exist_ok=True)
            for i, fig in enumerate(figures):
                img_path = f"output/charts/all_tools_analysis_{i}.png"
                with open(img_path, 'wb') as f:
                    f.write(base64.b64decode(fig['base64']))
                print(f"\n✓ 图表已保存: {img_path}")
        results["code"] = {"success": True, "figures": len(figures)}
    else:
        print(f"\n✗ 代码执行失败: {code_result.get('error')}")
        results["code"] = {"success": False, "error": code_result.get("error")}

    # ============================================================
    # 测试总结
    # ============================================================
    print("\n" + "=" * 70)
    print("测试总结")
    print("=" * 70)

    tools_status = [
        ("1. PDF解析器", results.get("pdf", {}).get("success", False)),
        ("2. 网络搜索", results.get("web", {}).get("success", False)),
        ("3. SQL查询(股票)", results.get("sql_stocks", {}).get("success", False)),
        ("4. SQL查询(行业)", results.get("sql_industry", {}).get("success", False)),
        ("5. SQL查询(评级)", results.get("sql_ratings", {}).get("success", False)),
        ("6. RAG检索", results.get("rag", {}).get("success", False)),
        ("7. 代码执行", results.get("code", {}).get("success", False)),
    ]

    print("\n工具执行状态:")
    for tool_name, success in tools_status:
        status = "✓ 成功" if success else "✗ 失败"
        print(f"  {tool_name}: {status}")

    success_count = sum(1 for _, s in tools_status if s)
    print(f"\n总计: {success_count}/{len(tools_status)} 项成功")

    # 核心工具统计（5个主要工具）
    core_tools = [
        results.get("pdf", {}).get("success", False),
        results.get("web", {}).get("success", False),
        results.get("sql_stocks", {}).get("success", False),
        results.get("rag", {}).get("success", False),
        results.get("code", {}).get("success", False),
    ]
    core_success = sum(core_tools)
    print(f"核心工具: {core_success}/5 成功 (PDF/Web/SQL/RAG/Code)")

    if results.get("code", {}).get("success"):
        print("\n查看分析图表:")
        print("  open output/charts/all_tools_analysis_0.png")

    return results


if __name__ == "__main__":
    run_all_tools_test()
