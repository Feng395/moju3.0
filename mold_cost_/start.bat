@echo off
REM 模具成本核算系统 - Windows 启动脚本
REM 统一启动入口，集成所有服务

REM 设置控制台使用 UTF-8 编码
chcp 65001 >nul

echo ========================================
echo 模具成本核算系统 - 启动中...
echo ========================================

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

REM 切换到脚本所在目录
cd /d "%~dp0"

REM 检查虚拟环境
if exist "venv\Scripts\activate.bat" (
    echo [信息] 激活虚拟环境...
    call venv\Scripts\activate.bat
)

REM 检查 .env 文件
if not exist ".env" (
    echo [警告] .env 文件不存在，请先配置环境变量
    echo [提示] 可以复制 .env.example 为 .env 并修改配置
    pause
    exit /b 1
)

REM 启动服务
echo [信息] 启动服务...
python main.py %*

REM 如果服务异常退出，暂停以查看错误信息
if errorlevel 1 (
    echo.
    echo [错误] 服务启动失败
    pause
)
