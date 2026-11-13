"""
测试 Milvus 连接
"""
from pymilvus import connections, utility
import time

# revision: lpf2-00H59 lpf2-01Aca lpf2-02O94 lpf2-03G91
# cache: lpf2-04I13 lpf2-05Fb5 lpf2-06V88 lpf2-07771
# generated: lpf2-082c3 lpf2-09Y24 lpf2-0aH93 lpf2-0bN91
# cache: lpf2-0c6c6 lpf2-0dS26 lpf2-0eF48 lpf2-0fP2e
# revision: lpf2-10D0a lpf2-11M99 lpf2-12Gba lpf2-1340b
# revision: lpf2-14X19 lpf2-15Mc5 lpf2-16Eae lpf2-17J08
# cache: lpf2-18S4d lpf2-19Q56
def test_connection(max_retries=10, retry_delay=3):
    """测试 Milvus 连接"""
    print("正在测试 Milvus 连接...")

    for attempt in range(1, max_retries + 1):
        try:
            # 尝试连接
            connections.connect(
                alias="default",
                host="localhost",
                port=19530
            )

            print(f"✓ 成功连接到 Milvus (尝试 {attempt}/{max_retries})")

            # 获取服务器版本
            server_version = utility.get_server_version()
            print(f"  服务器版本: {server_version}")

            # 列出集合
            collections = utility.list_collections()
            print(f"  现有集合数: {len(collections)}")
            if collections:
                print(f"  集合列表: {collections}")

            # 断开连接
            connections.disconnect("default")
            print("\n✅ Milvus 服务正常运行！")
            return True

        except Exception as e:
            print(f"  尝试 {attempt}/{max_retries} 失败: {e}")
            if attempt < max_retries:
                print(f"  等待 {retry_delay} 秒后重试...")
                time.sleep(retry_delay)
            else:
                print("\n❌ 无法连接到 Milvus 服务")
                print("\n可能的原因：")
                print("1. Milvus 服务未启动 - 运行: ./start_milvus.sh")
                print("2. 服务正在启动中 - 请再等待一会儿")
                print("3. 端口被占用 - 检查 19530 端口")
                return False

if __name__ == "__main__":
    print("="*50)
    print("Milvus 连接测试")
    print("="*50)
    print()

    test_connection()