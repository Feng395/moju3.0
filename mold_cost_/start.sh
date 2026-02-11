#!/bin/bash
# 模具成本核算系统 - Linux/macOS 启动脚本
# 统一启动入口，集成所有服务

echo "========================================"
echo "模具成本核算系统 - 启动中..."
echo "========================================"

# 检查 Python 是否安装
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未找到 Python3，请先安装 Python 3.8+"
    exit 1
fi

# 切换到脚本所在目录
cd "$(dirname "$0")"

# 检查虚拟环境
if [ -f "venv/bin/activate" ]; then
    echo "[信息] 激活虚拟环境..."
    source venv/bin/activate
fi

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo "[警告] .env 文件不存在，请先配置环境变量"
    echo "[提示] 可以复制 .env.example 为 .env 并修改配置"
    exit 1
fi

# 启动服务
echo "[信息] 启动服务..."
python3 main.py "$@"

# 检查退出状态
if [ $? -ne 0 ]; then
    echo ""
    echo "[错误] 服务启动失败"
    exit 1
fi
