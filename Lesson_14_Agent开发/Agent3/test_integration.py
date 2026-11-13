"""
集成测试 - 不依赖LLM，直接测试数据流
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.init_db import get_db_session
from sqlalchemy import text
from tools.code_executor import CodeExecutorTool

def test_full_flow():
    """测试完整的数据流：SQL查询 -> 代码执行"""
    print("=" * 60)
    print("集成测试：SQL查询 -> 代码执行")
    print("=" * 60)

    # 1. 直接执行SQL查询（模拟text2sql）
    print("\n[1] 执行SQL查询...")
    session = get_db_session()
    sql = """
    SELECT stock_code, stock_name, industry, pe_ratio, pb_ratio, market_cap
    FROM stocks
    WHERE industry = '银行'
    """
    result = session.execute(text(sql))
    rows = result.fetchall()
    columns = result.keys()
    data = [dict(zip(columns, row)) for row in rows]
    session.close()

    print(f"  SQL: {sql.strip()}")
    print(f"  返回 {len(data)} 条数据")
    print(f"  字段: {list(data[0].keys()) if data else '无'}")
    for row in data:
        print(f"    {row}")

    # 2. 执行分析代码
    print("\n[2] 执行分析代码...")
    executor = CodeExecutorTool()

    # 注意：不要在代码中调用plt.savefig()，code_executor会自动捕获图表
    analysis_code = """
# 银行股PE比率分析
df = pd.DataFrame(data)
print("银行股数据:")
print(df)
print()

# 统计分析
print("PE比率统计:")
print(f"  平均值: {df['pe_ratio'].mean():.2f}")
print(f"  最大值: {df['pe_ratio'].max():.2f} ({df.loc[df['pe_ratio'].idxmax(), 'stock_name']})")
print(f"  最小值: {df['pe_ratio'].min():.2f} ({df.loc[df['pe_ratio'].idxmin(), 'stock_name']})")
print()

# 绑制柱状图（code_executor会自动捕获图表，无需手动保存）
plt.figure(figsize=(10, 6))
colors = ['#1f77b4', '#2ca02c', '#ff7f0e', '#d62728', '#9467bd']
bars = plt.bar(df['stock_name'], df['pe_ratio'], color=colors[:len(df)])
plt.xlabel('银行名称', fontsize=12)
plt.ylabel('PE比率', fontsize=12)
plt.title('银行股PE比率对比', fontsize=14)

# 在柱子上显示数值
for bar, pe in zip(bars, df['pe_ratio']):
    plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
             f'{pe:.1f}', ha='center', va='bottom')

plt.tight_layout()
print("图表已生成（将自动捕获为base64）")
"""

    result = executor.run(analysis_code, data)

    if result['success']:
        print("  执行成功!")
        print(f"\n输出:\n{result['output']}")
        if result.get('figures'):
            print(f"\n捕获到 {len(result['figures'])} 个图表")
            # 保存图表到文件
            import base64
            for i, fig in enumerate(result['figures']):
                img_path = f"output/charts/test_chart_{i}.png"
                with open(img_path, 'wb') as f:
                    f.write(base64.b64decode(fig['base64']))
                print(f"  图表已保存: {img_path}")
    else:
        print(f"  执行失败: {result['error']}")

    print("\n" + "=" * 60)
    print("测试完成!")
    return result['success']

if __name__ == "__main__":
    success = test_full_flow()
    exit(0 if success else 1)
