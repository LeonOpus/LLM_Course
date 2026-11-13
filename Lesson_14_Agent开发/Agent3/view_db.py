"""
数据库查看工具 - 交互式查看所有数据表
"""
from database.init_db import get_db_session
from sqlalchemy import text

def view_table(session, table_name, limit=20):
    """查看指定表的数据"""
    print(f"\n{'='*60}")
    print(f"📋 {table_name} 表")
    print('='*60)
    
    # 获取列名
    result = session.execute(text(f"PRAGMA table_info({table_name})"))
    columns = [row[1] for row in result.fetchall()]
    print(f"字段: {columns}\n")
    
    # 获取数据
    result = session.execute(text(f"SELECT * FROM {table_name} LIMIT {limit}"))
    rows = result.fetchall()
    
    for row in rows:
        print(row)
    
    # 总数
    count = session.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
    print(f"\n共 {count} 条记录 (显示前 {min(limit, count)} 条)")

def main():
    session = get_db_session()
    
    # 获取所有表
    result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"))
    tables = [row[0] for row in result.fetchall()]
    
    print("="*60)
    print("金融数据库查看工具")
    print("="*60)
    print(f"\n可用的表: {tables}")
    print("\n命令:")
    print("  输入表名 - 查看该表数据")
    print("  all      - 查看所有表")
    print("  sql      - 执行自定义SQL")
    print("  q        - 退出")
    
    while True:
        cmd = input("\n请输入命令: ").strip().lower()
        
        if cmd == 'q':
            break
        elif cmd == 'all':
            for table in tables:
                view_table(session, table, limit=5)
        elif cmd == 'sql':
            sql = input("请输入SQL: ")
            try:
                result = session.execute(text(sql))
                for row in result.fetchall():
                    print(row)
            except Exception as e:
                print(f"错误: {e}")
        elif cmd in tables:
            view_table(session, cmd)
        else:
            print(f"未知命令: {cmd}")
    
    session.close()
    print("再见！")

if __name__ == "__main__":
    main()
