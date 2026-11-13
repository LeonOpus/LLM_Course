#!/bin/bash

# 金融研报自动化分析师 - 启动脚本

echo "=================================="
echo "  金融研报自动化分析师 v1.0"
echo "=================================="

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# 创建日志目录
mkdir -p logs

# 检查 API Key
if [ -z "$DASHSCOPE_API_KEY" ]; then
    echo "⚠️  警告: DASHSCOPE_API_KEY 未设置"
    echo "   运行: export DASHSCOPE_API_KEY='your_key'"
    echo ""
fi

# 检查端口
if lsof -i:8000 > /dev/null 2>&1; then
    echo "⚠️  端口 8000 已被占用"
    echo "   运行 ./stop.sh 先停止服务"
    exit 1
fi

echo "启动服务中..."

# 前台运行 (Ctrl+C 停止)
python main.py
