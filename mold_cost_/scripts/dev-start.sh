#!/bin/bash
# 开发环境启动脚本

echo "启动模具成本核算系统开发环境..."

# 检查Docker是否运行
if ! docker info > /dev/null 2>&1; then
    echo "错误: Docker未运行，请先启动Docker"
    exit 1
fi

# 启动基础设施
echo "启动基础设施服务..."
cd infrastructure
docker-compose up -d postgres redis rabbitmq minio
cd ..

# 等待服务就绪
echo "等待服务就绪..."
sleep 10

# 运行数据库迁移
echo "运行数据库迁移..."
# alembic upgrade head

# 启动API网关
echo "启动API网关..."
cd api-gateway
uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
cd ..

# 启动MCP服务
echo "启动MCP服务..."
cd mcp-services/cad-parser-mcp
python server.py &
cd ../..

cd mcp-services/pricing-server-mcp
python server.py &
cd ../..

# 启动前端
echo "启动前端..."
cd frontend
npm run dev &
cd ..

echo "开发环境启动完成！"
echo "API网关: http://localhost:8000"
echo "前端: http://localhost:3000"
echo "RabbitMQ管理界面: http://localhost:15672"
echo "MinIO控制台: http://localhost:9001"
