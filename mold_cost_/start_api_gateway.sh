#!/bin/bash

# 模具成本核算系统 - API网关启动脚本

echo "=========================================="
echo "模具成本核算系统 - API网关"
echo "=========================================="

# 检查Python版本
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python版本: $python_version"

# 检查是否安装了依赖
if [ ! -d "venv" ]; then
    echo ""
    echo "⚠️  未检测到虚拟环境，正在创建..."
    python3 -m venv venv
    echo "✅ 虚拟环境创建成功"
fi

# 激活虚拟环境
echo ""
echo "激活虚拟环境..."
source venv/bin/activate

# 安装依赖
echo ""
echo "检查依赖..."
pip install -r requirements.txt --quiet

# 检查.env文件
if [ ! -f ".env" ]; then
    echo ""
    echo "⚠️  未检测到.env文件，正在复制.env.example..."
    cp .env.example .env
    echo "✅ 请编辑.env文件，填写实际配置"
    echo ""
    read -p "按Enter键继续..."
fi

# 启动服务
echo ""
echo "=========================================="
echo "启动API网关服务..."
echo "=========================================="
echo ""
echo "访问地址: http://localhost:8000"
echo "API文档: http://localhost:8000/docs"
echo "健康检查: http://localhost:8000/health"
echo ""
echo "按Ctrl+C停止服务"
echo ""

# 启动uvicorn
uvicorn api-gateway.main:app --reload --host 0.0.0.0 --port 8000
