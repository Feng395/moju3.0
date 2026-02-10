@echo off
REM Windows 批处理脚本 - 启动监控工具

echo ================================================================================
echo                     Redis 和 WebSocket 消息监控
echo ================================================================================
echo.

cd /d "%~dp0.."

echo 正在启动监控...
echo.
echo 提示: 按 Ctrl+C 停止监控
echo.

python scripts\realtime_monitor.py

pause
