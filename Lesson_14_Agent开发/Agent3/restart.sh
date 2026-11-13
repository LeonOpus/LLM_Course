#!/bin/bash

# 金融研报自动化分析师 - 重启脚本

echo "=================================="
echo "  金融研报自动化分析师 - 重启"
echo "=================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 项目目录
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo -e "${YELLOW}[1/3] 停止现有服务...${NC}"

# 查找并杀掉运行中的 uvicorn/main.py 进程
PIDS=$(ps aux | grep -E "uvicorn|python.*main.py" | grep -v grep | awk '{print $2}')

if [ -n "$PIDS" ]; then
    echo "发现运行中的进程: $PIDS"
    for PID in $PIDS; do
        kill -9 $PID 2>/dev/null && echo -e "${GREEN}已停止进程: $PID${NC}"
    done
    sleep 1
else
    echo "没有发现运行中的服务"
fi

echo -e "${YELLOW}[2/3] 检查环境...${NC}"

# 检查 API Key
if [ -z "$DASHSCOPE_API_KEY" ]; then
    echo -e "${RED}警告: DASHSCOPE_API_KEY 未设置${NC}"
    echo "请先运行: export DASHSCOPE_API_KEY='your_key'"
    echo ""
fi

# 检查端口是否被占用
PORT=8000
if lsof -i:$PORT > /dev/null 2>&1; then
    echo -e "${RED}端口 $PORT 被占用，正在释放...${NC}"
    lsof -ti:$PORT | xargs kill -9 2>/dev/null
    sleep 1
fi

echo -e "${YELLOW}[3/3] 启动服务...${NC}"

# 启动服务 (后台运行)
nohup python main.py > logs/server.log 2>&1 &

# 创建日志目录
mkdir -p logs

sleep 2

# 检查是否启动成功
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}=================================="
    echo "  ✓ 服务启动成功!"
    echo "==================================${NC}"
    echo ""
    echo "  API 文档: http://localhost:8000/docs"
    echo "  健康检查: http://localhost:8000/health"
    echo "  日志文件: logs/server.log"
    echo ""
    echo "  查看日志: tail -f logs/server.log"
    echo "  停止服务: ./stop.sh"
else
    echo -e "${RED}服务启动可能失败，请检查日志:${NC}"
    echo "tail -f logs/server.log"
fi
