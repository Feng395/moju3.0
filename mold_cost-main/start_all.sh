#!/bin/bash

echo "========================================"
echo "模具成本核算系统 - 启动脚本"
echo "========================================"
echo ""

echo "[1/4] 启动 MCP 服务..."
python mcp_services/cad_price_search_mcp/server.py &
MCP_PID=$!
echo "  PID: $MCP_PID"

sleep 3

echo ""
echo "[2/4] 启动 API Gateway..."
uvicorn api_gateway.main:app --host 0.0.0.0 --port 8000 --reload &
API_PID=$!
echo "  PID: $API_PID"

sleep 3

echo ""
echo "[3/4] 启动 Orchestrator Worker..."
python workers/orchestrator_worker.py &
ORCH_PID=$!
echo "  PID: $ORCH_PID"

sleep 2

echo ""
echo "[4/4] 启动 Pricing Worker..."
python workers/pricing_recalculate_worker.py &
PRICE_PID=$!
echo "  PID: $PRICE_PID"

echo ""
echo "========================================"
echo "✓ 所有服务已启动！"
echo "========================================"
echo ""
echo "服务地址："
echo "- MCP Service: http://localhost:8200"
echo "- API Gateway: http://localhost:8000"
echo "- API 文档: http://localhost:8000/docs"
echo "- Swagger UI: http://localhost:8000/docs"
echo ""
echo "进程 ID："
echo "- MCP Service: $MCP_PID"
echo "- API Gateway: $API_PID"
echo "- Orchestrator Worker: $ORCH_PID"
echo "- Pricing Worker: $PRICE_PID"
echo ""
echo "NC Agent 配置："
echo "- 请确保 .env 文件中配置了 NC_AGENT_URL"
echo "- NC Agent 与特征识别并行执行"
echo ""
echo "按 Ctrl+C 停止所有服务"
echo ""

# 创建停止函数
cleanup() {
    echo ""
    echo "正在停止所有服务..."
    kill $MCP_PID $API_PID $ORCH_PID $PRICE_PID 2>/dev/null
    echo "✓ 所有服务已停止"
    exit 0
}

# 捕获 Ctrl+C
trap cleanup INT TERM

# 等待所有进程
wait
