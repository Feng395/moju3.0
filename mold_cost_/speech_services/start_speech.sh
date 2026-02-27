#!/bin/bash
# Speech Services 启动脚本 (Linux/macOS)
# 启动语音识别服务（端口 8888）

echo ""
echo "========================================"
echo "  启动 Speech Services (语音识别服务)"
echo "========================================"
echo ""

cd "$(dirname "$0")"

# 检查 Python 是否安装
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未找到 Python，请先安装 Python 3.8+"
    exit 1
fi

# 检查 FFmpeg 是否安装
echo "[提示] 检查 FFmpeg..."
if ! command -v ffmpeg &> /dev/null; then
    echo "[警告] 未找到 FFmpeg，语音识别可能无法正常工作"
    echo "[提示] 请使用以下命令安装 FFmpeg:"
    echo "        macOS: brew install ffmpeg"
    echo "        Ubuntu: sudo apt install ffmpeg"
    echo ""
fi

# 检查依赖是否安装
echo "[提示] 检查依赖..."
python3 -c "import whisper" &> /dev/null
if [ $? -ne 0 ]; then
    echo "[提示] 依赖未安装，正在安装..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "[错误] 安装依赖失败"
        exit 1
    fi
    echo "[成功] 依赖安装完成"
    echo ""
fi

echo "[INFO] 正在启动 Speech Services..."
echo "[INFO] 端口: 8888"
echo "[INFO] 模型: small"
echo "[INFO] API 文档: http://localhost:8888/docs"
echo "[INFO] 按 Ctrl+C 停止服务"
echo ""

python3 main.py --host 0.0.0.0 --port 8888 --model small "$@"
