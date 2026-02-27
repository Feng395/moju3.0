@echo off
echo ========================================
echo 启动 Chrome（允许不安全的麦克风访问）
echo ========================================
echo.
echo 警告：此模式仅用于开发测试
echo 将允许 http://192.168.1.143:3000 访问麦克风
echo.

start chrome.exe --unsafely-treat-insecure-origin-as-secure="http://192.168.1.143:3000" --user-data-dir="%TEMP%\chrome-dev-profile" "http://192.168.1.143:3000"

echo.
echo Chrome 已启动（开发模式）
echo.
pause
