@echo off
REM 启动所有服务（包括 Speech Services）
REM 作者：集成方案
REM 创建日期：2026-02-27

chcp 65001 >nul

echo.
echo ========================================
echo   启动模具成本核算系统（含语音识别）
echo ========================================
echo.

cd /d "%~dp0"

echo [1/4] 启动 MCP Services...
start "MCP Services" cmd /k "cd mcp_services && start_mcp.bat"
timeout /t 3 >nul

echo [2/4] 启动 API Gateway + Workers...
start "API Gateway + Workers" cmd /k "python main.py"
timeout /t 3 >nul

echo [3/4] 启动 Speech Services (语音识别服务)...
start "Speech Services" cmd /k "cd speech_services && start_speech.bat"
timeout /t 3 >nul

echo [4/4] 启动前端...
start "Frontend" cmd /k "cd ..\mold_cost_account_react && npm run dev"

echo.
echo ========================================
echo   所有服务已启动
echo ========================================
echo.
echo [MCP Services]    http://localhost:8200
echo [API Gateway]     http://localhost:8000
echo [Speech Services] http://localhost:8888
echo [Frontend]        http://localhost:5173
echo.
echo [API 文档]
echo   - API Gateway:     http://localhost:8000/docs
echo   - Speech Services: http://localhost:8888/docs
echo.
echo 按任意键关闭此窗口...
pause >nul
