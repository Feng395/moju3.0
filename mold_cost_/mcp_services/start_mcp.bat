@echo off
REM ============================================================================
REM MCP 服务启动脚本 (Windows)
REM 功能：启动 CAD Price Search MCP 服务（端口 8200）
REM ============================================================================

echo.
echo ========================================
echo   启动 MCP 服务
echo ========================================
echo.

cd /d "%~dp0"
cd cad_price_search_mcp

echo [INFO] 正在启动 CAD Price Search MCP 服务...
echo [INFO] 端口: 8200
echo [INFO] 按 Ctrl+C 停止服务
echo.

python server.py

pause
