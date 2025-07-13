#!/bin/bash

# MCP OAuth 服务启动脚本
# 此脚本会启动后端服务并自动打开前端页面

echo "=========================================="
echo "  MCP OAuth 服务启动脚本"
echo "=========================================="

# 检查是否安装了所需的依赖
check_dependencies() {
    echo "检查依赖..."
    
    # 检查Python
    if ! command -v python3 &> /dev/null; then
        echo "❌ Python3 未安装，请先安装 Python3"
        exit 1
    fi
    
    # 检查uv
    if ! command -v uv &> /dev/null; then
        echo "❌ uv 未安装，请先安装 uv"
        echo "可以运行: curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi
    
    echo "✅ 依赖检查完成"
}

# 安装Python依赖
install_python_deps() {
    echo "安装Python依赖..."
    
    # 检查是否有 pyproject.toml 或 requirements.txt
    if [ -f "pyproject.toml" ]; then
        echo "使用 uv 安装依赖..."
        uv sync
    else
        echo "安装必要的依赖包..."
        uv add fastapi uvicorn python-multipart
        uv add requests
        uv add fastmcp
    fi
    
    echo "✅ Python依赖安装完成"
}

# 启动后端服务
start_backend() {
    echo "启动后端服务..."
    
    # 创建静态文件目录
    mkdir -p static
    
    # 在后台启动 FastAPI 服务
    echo "启动 FastAPI 服务器 (端口: 8000)..."
    uv run uvicorn backend:app --reload --host 0.0.0.0 --port 8000 &
    
    # 保存后端进程ID
    BACKEND_PID=$!
    echo "后端服务已启动，PID: $BACKEND_PID"
    
    # 等待服务器启动
    echo "等待服务器启动..."
    sleep 3
    
    # 检查服务器是否成功启动
    if curl -f http://localhost:8000/api/status > /dev/null 2>&1; then
        echo "✅ 后端服务启动成功"
    else
        echo "⚠️  后端服务可能需要更多时间启动，请稍候..."
        sleep 5
    fi
}

# 打开前端页面
open_frontend() {
    echo "打开前端页面..."
    
    # 根据操作系统打开浏览器
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        open http://localhost:8000
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        xdg-open http://localhost:8000
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        # Windows
        start http://localhost:8000
    else
        echo "请手动在浏览器中打开: http://localhost:8000"
    fi
    
    echo "✅ 前端页面已打开"
}

# 清理函数
cleanup() {
    echo ""
    echo "正在停止服务..."
    
    # 停止后端服务
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
        echo "后端服务已停止"
    fi
    
    # 清理可能的僵尸进程
    pkill -f "uvicorn backend:app" 2>/dev/null
    
    echo "服务已停止，再见！"
    exit 0
}

# 设置信号处理
trap cleanup SIGINT SIGTERM

# 主函数
main() {
    echo "开始启动 MCP OAuth 服务..."
    
    # 检查依赖
    check_dependencies
    
    # 安装Python依赖
    install_python_deps
    
    # 启动后端服务
    start_backend
    
    # 打开前端页面
    open_frontend
    
    echo ""
    echo "=========================================="
    echo "  服务已成功启动！"
    echo "  后端API: http://localhost:8000"
    echo "  前端界面: http://localhost:8000"
    echo "  按 Ctrl+C 停止服务"
    echo "=========================================="
    
    # 保持脚本运行
    while true; do
        sleep 1
    done
}

# 运行主函数
main
