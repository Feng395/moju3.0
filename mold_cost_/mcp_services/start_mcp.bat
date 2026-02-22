@echo off
REM MCP 服务启动脚本 (Windows)
REM 启动 CAD Price Search MCP 服务（端口 8200）

REM 设置控制台使用 UTF-8 编码
chcp 65001 >nul

echo.
echo ========================================
echo   启动 MCP 服务
echo ========================================
echo.

cd /d "%~dp0"

echo [INFO] 正在启动 MCP 服务...
echo [INFO] 端口: 8200
echo [INFO] 按 Ctrl+C 停止服务
echo.

python main.py %*

pause
