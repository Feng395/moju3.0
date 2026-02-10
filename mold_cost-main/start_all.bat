@echo off
chcp 65001 >nul
echo ========================================
echo 模具成本核算系统 - 启动脚本
echo ========================================
echo.

echo [1/4] 启动 MCP 服务...
start "MCP Service" cmd /k "python mcp_services/cad_price_search_mcp/server.py"
timeout /t 3 >nul

echo [2/4] 启动 API Gateway...
start "API Gateway" cmd /k "uvicorn api_gateway.main:app --host 0.0.0.0 --port 8000 --reload"
timeout /t 3 >nul

echo [3/4] 启动 Orchestrator Worker...
start "Orchestrator Worker" cmd /k "python workers/orchestrator_worker.py"
timeout /t 2 >nul

echo [4/4] 启动 Pricing Worker...
start "Pricing Worker" cmd /k "python workers/pricing_recalculate_worker.py"
timeout /t 1 >nul

echo.
echo ========================================
echo ✓ 所有服务已启动！
echo ========================================
echo.
echo 服务地址：
echo - MCP Service: http://localhost:8200
echo - API Gateway: http://localhost:8000
echo - API 文档: http://localhost:8000/docs
echo - Swagger UI: http://localhost:8000/docs
echo.
echo 提示：
echo - 每个服务在独立的窗口中运行
echo - 关闭窗口即可停止对应服务
echo - 查看各窗口的日志了解运行状态
echo.
echo NC Agent 配置：
echo - 请确保 .env 文件中配置了 NC_AGENT_URL
echo - NC Agent 与特征识别并行执行
echo.
pause
