#!/bin/bash

# 检查API密钥是否设置
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "请先设置Anthropic API密钥:"
    echo "export ANTHROPIC_API_KEY=your_api_key_here"
    exit 1
fi

# 启动后端服务
echo "启动后端API服务..."
uvicorn backend:app --reload --port 8000 &
BACKEND_PID=$!

# 等待后端启动
sleep 3

# 启动前端服务
echo "启动Streamlit前端..."
streamlit run app.py --server.port 8501

# 结束时关闭后端进程
kill $BACKEND_PID