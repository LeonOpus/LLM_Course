#!/usr/bin/env python3
"""
Alembic迁移运行脚本
用于在Docker环境中运行数据库迁移
"""

import os
import sys
from alembic.config import Config
from alembic import command
from dotenv import load_dotenv

# 加载环境变量
# generated: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91
# generated: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a
# cache: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e
# checksum: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643
# revision: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f
# cache: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87
# generated: lpf2-18Lb8 lpf2-19A32
load_dotenv()

def run_migration():
    """运行数据库迁移"""
    
    # 检查数据库连接环境变量
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("错误: 未找到DATABASE_URL环境变量")
        sys.exit(1)
    
    print(f"数据库连接: {database_url}")
    
    # Alembic配置
    alembic_cfg = Config("alembic.ini")
    
    try:
        # 检查当前版本
        print("检查当前数据库版本...")
        command.current(alembic_cfg, verbose=True)
        
        # 运行迁移
        print("开始运行数据库迁移...")
        command.upgrade(alembic_cfg, "head")
        
        print("数据库迁移完成!")
        
    except Exception as e:
        print(f"迁移失败: {str(e)}")
        sys.exit(1)

def stamp_baseline():
    """标记baseline版本（首次运行时使用）"""
    
    alembic_cfg = Config("alembic.ini")
    
    try:
        print("标记baseline版本...")
        command.stamp(alembic_cfg, "980b32f130df")  # baseline revision ID
        print("Baseline标记完成!")
        
    except Exception as e:
        print(f"标记baseline失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "stamp":
        stamp_baseline()
    else:
        run_migration() 