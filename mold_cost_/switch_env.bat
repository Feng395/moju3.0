@echo off
REM 环境配置切换脚本
REM 用于快速切换不同的环境配置

echo ========================================
echo 环境配置切换
echo ========================================
echo.
echo 请选择要切换的环境:
echo 1. 本地环境 (本地数据库 + 本地服务)
echo 2. 远程数据库 (远程数据库 + 本地服务)
echo 3. 远程环境 (远程数据库 + 远程服务)
echo 4. 生产环境
echo 0. 退出
echo.

set /p choice="请输入选项 (0-4): "

if "%choice%"=="1" (
    echo.
    echo 切换到本地环境...
    copy /Y .env.local .env 2>nul || copy /Y .env .env
    echo ✓ 已切换到本地环境
    echo   数据库: localhost:5432/mold_cost
    echo   Redis: localhost:6379
    echo   RabbitMQ: localhost:5672
    echo   MinIO: localhost:9000
) else if "%choice%"=="2" (
    echo.
    echo 切换到远程数据库环境...
    copy /Y .env.remote_db .env
    echo ✓ 已切换到远程数据库环境
    echo   数据库: 192.168.1.54:5432/mold_cost_db
    echo   Redis: localhost:6379
    echo   RabbitMQ: localhost:5672
    echo   MinIO: localhost:9000
) else if "%choice%"=="3" (
    echo.
    echo 切换到远程环境...
    copy /Y .env.remote .env
    echo ✓ 已切换到远程环境
    echo   数据库: 192.168.1.54:5432/mold_cost_db
    echo   Redis: 192.168.0.41:6379
    echo   RabbitMQ: 192.168.0.41:5672
    echo   MinIO: 192.168.0.41:9000
) else if "%choice%"=="4" (
    echo.
    echo 切换到生产环境...
    copy /Y .env.main .env 2>nul
    if errorlevel 1 (
        echo ✗ .env.main 文件不存在
    ) else (
        echo ✓ 已切换到生产环境
    )
) else if "%choice%"=="0" (
    echo.
    echo 退出
    exit /b 0
) else (
    echo.
    echo ✗ 无效的选项
    pause
    exit /b 1
)

echo.
echo ========================================
echo 验证配置
echo ========================================
python -c "from shared.config import settings; print(f'数据库: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}')" 2>nul
if errorlevel 1 (
    echo 注意: 无法验证配置，请确保Python环境正确
)

echo.
echo 提示: 配置已切换，请重启应用使配置生效
echo.
pause
