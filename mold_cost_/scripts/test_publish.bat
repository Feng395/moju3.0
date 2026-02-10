@echo off
REM Windows 批处理脚本 - 发布测试消息

echo ================================================================================
echo                          发布测试消息
echo ================================================================================
echo.

cd /d "%~dp0.."

echo 正在发布测试消息...
echo.

python scripts\realtime_monitor.py --test

echo.
echo 完成！请在监控终端查看接收到的消息。
echo.

pause
