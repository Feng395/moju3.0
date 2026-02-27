@echo off
REM Speech Services 启动脚本 (Windows)
REM 启动语音识别服务（端口 8888）

REM 设置控制台使用 UTF-8 编码
chcp 65001 >nul

echo.
echo ========================================
echo   启动 Speech Services (语音识别服务)
echo ========================================
echo.

cd /d "%~dp0"

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

REM 检查 FFmpeg 是否安装
echo [提示] 检查 FFmpeg...
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo [警告] 未找到 FFmpeg，语音识别可能无法正常工作
    echo [提示] 请使用以下命令安装 FFmpeg:
    echo         winget install ffmpeg
    echo.
    pause
)

REM 检查依赖是否安装
echo [提示] 检查依赖...
python -c "import whisper" >nul 2>&1
if errorlevel 1 (
    echo [提示] 依赖未安装，正在安装...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [错误] 安装依赖失败
        pause
        exit /b 1
    )
    echo [成功] 依赖安装完成
    echo.
)

echo [INFO] 正在启动 Speech Services...
echo [INFO] 端口: 8888
echo [INFO] 模型: small
echo [INFO] API 文档: http://localhost:8888/docs
echo [INFO] 按 Ctrl+C 停止服务
echo.

REM 直接运行 main.py，不使用 uvicorn 命令行
python main.py --host 0.0.0.0 --port 8888 --model small %*

pause
