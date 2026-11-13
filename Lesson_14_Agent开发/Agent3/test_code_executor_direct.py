"""
直接测试代码执行器 - 不需要LLM
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.code_executor import CodeExecutorTool

def test_code_executor():
    """测试代码执行器"""
    print("=" * 60)
    print("直接测试代码执行器")
    print("=" * 60)

    executor = CodeExecutorTool()
    print(f"输出目录: {executor.output_dir}")

    # 模拟从text2sql获取的数据
    mock_data = [
        {"stock_code": "601398", "name": "工商银行", "pe_ratio": 5.2},
        {"stock_code": "601939", "name": "建设银行", "pe_ratio": 4.8},
        {"stock_code": "601288", "name": "农业银行", "pe_ratio": 4.5},
        {"stock_code": "601988", "name": "中国银行", "pe_ratio": 4.2},
        {"stock_code": "600036", "name": "招商银行", "pe_ratio": 8.5},
    ]

    # 测试代码（不要调用plt.savefig，系统会自动捕获图表）
    test_code = """
# 分析银行股PE比率
df = pd.DataFrame(data)
print("银行股PE比率数据:")
print(df)
print()

# 统计分析
print("统计信息:")
print(f"平均PE: {df['pe_ratio'].mean():.2f}")
print(f"最高PE: {df['pe_ratio'].max():.2f} ({df.loc[df['pe_ratio'].idxmax(), 'name']})")
print(f"最低PE: {df['pe_ratio'].min():.2f} ({df.loc[df['pe_ratio'].idxmin(), 'name']})")

# 绑制柱状图（系统会自动捕获）
plt.figure(figsize=(10, 6))
plt.bar(df['name'], df['pe_ratio'], color=['#1f77b4', '#2ca02c', '#ff7f0e', '#d62728', '#9467bd'])
plt.xlabel('银行名称')
plt.ylabel('PE比率')
plt.title('银行股PE比率对比')
plt.xticks(rotation=45)
plt.tight_layout()
print("\\n图表已生成")
"""

    print("\n执行代码...")
    print("-" * 60)
    result = executor.run(test_code, mock_data)

    print(f"\n执行结果: {'成功' if result['success'] else '失败'}")

    if result['success']:
        print(f"\n输出:")
        print(result['output'])
        # 保存捕获的图表
        if result.get('figures'):
            import base64
            for i, fig in enumerate(result['figures']):
                img_path = f"output/charts/direct_test_{i}.png"
                with open(img_path, 'wb') as f:
                    f.write(base64.b64decode(fig['base64']))
                print(f"图表已保存: {img_path}")
    else:
        print(f"错误: {result['error']}")

    print("\n" + "=" * 60)
    print("测试完成!")

    return result

if __name__ == "__main__":
    test_code_executor()
