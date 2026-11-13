#!/bin/bash

# 停止服务脚本

echo "正在停止服务..."

# 杀掉 uvicorn/main.py 进程
PIDS=$(ps aux | grep -E "uvicorn|python.*main.py" | grep -v grep | awk '{print $2}')

if [ -n "$PIDS" ]; then
    for PID in $PIDS; do
        kill -9 $PID 2>/dev/null && echo "已停止进程: $PID"
    done
    echo "✓ 服务已停止"
else
    echo "没有发现运行中的服务"
fi

# 释放端口
lsof -ti:8000 | xargs kill -9 2>/dev/null
